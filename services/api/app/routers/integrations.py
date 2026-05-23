import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models.cms_connection import CmsConnection
from app.db.models.social_connection import SocialConnection
from app.db.session import get_db
from app.services.vault import encrypt, decrypt

router = APIRouter()

ORG_ID = "org-dev-1"

# In-memory PKCE state store (production: use Redis with TTL)
_oauth_states: dict[str, dict] = {}


# ──────────────────────────────────────────────
# CMS Connections
# ──────────────────────────────────────────────


class CreateCmsConnectionRequest(BaseModel):
    type: str  # wordpress|webflow|shopify
    name: str
    project_id: str | None = None
    config: dict  # plaintext; keys depend on type


@router.get("/cms")
async def list_cms_connections(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CmsConnection)
        .where(CmsConnection.org_id == ORG_ID)
        .order_by(CmsConnection.created_at.desc())
    )
    return [_serialize_cms(c) for c in result.scalars().all()]


@router.post("/cms")
async def create_cms_connection(
    body: CreateCmsConnectionRequest,
    db: AsyncSession = Depends(get_db),
):
    if body.type not in ("wordpress", "webflow", "shopify"):
        raise HTTPException(status_code=400, detail=f"Unknown CMS type: {body.type}")

    # Encrypt each config value individually
    encrypted_config = {k: encrypt(str(v)) for k, v in body.config.items()}

    conn = CmsConnection(
        id=str(uuid.uuid4()),
        org_id=ORG_ID,
        project_id=body.project_id,
        type=body.type,
        name=body.name,
        config_encrypted=encrypted_config,
        status="active",
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)
    return _serialize_cms(conn)


@router.get("/cms/{connection_id}/test")
async def test_cms_connection(connection_id: str, db: AsyncSession = Depends(get_db)):
    conn = await db.get(CmsConnection, connection_id)
    if not conn or conn.org_id != ORG_ID:
        raise HTTPException(status_code=404, detail="Not found")

    raw_config = conn.config_encrypted or {}
    config = {k: decrypt(v) for k, v in raw_config.items()}

    from app.integrations.cms.base import CMSAdapter
    adapter = CMSAdapter.from_config(conn.type, config)

    try:
        ok = await adapter.test_connection()
        conn.last_tested_at = datetime.now(timezone.utc)
        conn.last_error = None if ok else "Connection test returned non-200"
        conn.status = "active" if ok else "error"
        await db.commit()
        return {"ok": ok}
    except Exception as e:
        conn.last_tested_at = datetime.now(timezone.utc)
        conn.last_error = str(e)[:1000]
        conn.status = "error"
        await db.commit()
        return {"ok": False, "error": str(e)}


@router.delete("/cms/{connection_id}", status_code=204)
async def delete_cms_connection(connection_id: str, db: AsyncSession = Depends(get_db)):
    conn = await db.get(CmsConnection, connection_id)
    if not conn or conn.org_id != ORG_ID:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(conn)
    await db.commit()


# ──────────────────────────────────────────────
# Social Connections
# ──────────────────────────────────────────────


@router.get("/social")
async def list_social_connections(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SocialConnection)
        .where(SocialConnection.org_id == ORG_ID)
        .order_by(SocialConnection.created_at.desc())
    )
    return [_serialize_social(c) for c in result.scalars().all()]


@router.delete("/social/{connection_id}", status_code=204)
async def delete_social_connection(connection_id: str, db: AsyncSession = Depends(get_db)):
    conn = await db.get(SocialConnection, connection_id)
    if not conn or conn.org_id != ORG_ID:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(conn)
    await db.commit()


@router.get("/social/{platform}/oauth-url")
async def get_oauth_url(platform: str):
    """Return the OAuth authorization URL for the given platform."""
    if platform == "linkedin":
        return _linkedin_oauth_url()
    if platform == "twitter":
        return _twitter_oauth_url()
    raise HTTPException(status_code=400, detail=f"OAuth not supported for: {platform}")


@router.post("/social/callback")
async def social_oauth_callback(
    platform: str,
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """Exchange OAuth code for tokens and store the connection."""
    stored = _oauth_states.pop(state, None)
    if not stored or stored.get("platform") != platform:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    if platform == "linkedin":
        conn = await _complete_linkedin(code, stored, db)
    elif platform == "twitter":
        conn = await _complete_twitter(code, stored, db)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown platform: {platform}")

    return _serialize_social(conn)


# ──────────────────────────────────────────────
# LinkedIn OAuth helpers
# ──────────────────────────────────────────────

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"


def _linkedin_oauth_url() -> dict:
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {"platform": "linkedin"}
    params = {
        "response_type": "code",
        "client_id": settings.linkedin_client_id,
        "redirect_uri": f"{settings.cors_origins[0]}/settings/integrations/callback/linkedin",
        "state": state,
        "scope": "openid profile email w_member_social",
    }
    return {"url": f"{LINKEDIN_AUTH_URL}?{urlencode(params)}", "state": state}


async def _complete_linkedin(code: str, stored: dict, db: AsyncSession) -> SocialConnection:
    redirect_uri = f"{settings.cors_origins[0]}/settings/integrations/callback/linkedin"
    async with httpx.AsyncClient(timeout=15.0) as client:
        token_resp = await client.post(
            LINKEDIN_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": settings.linkedin_client_id,
                "client_secret": settings.linkedin_client_secret,
            },
        )
        token_resp.raise_for_status()
        tokens = token_resp.json()

        access_token = tokens["access_token"]
        profile_resp = await client.get(
            LINKEDIN_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        profile_resp.raise_for_status()
        profile = profile_resp.json()

    result = await db.execute(
        select(SocialConnection).where(
            SocialConnection.org_id == ORG_ID,
            SocialConnection.platform == "linkedin",
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        conn = SocialConnection(id=str(uuid.uuid4()), org_id=ORG_ID, platform="linkedin")
        db.add(conn)

    conn.account_id = profile.get("sub", "")
    conn.account_name = profile.get("name", "")
    conn.access_token_encrypted = encrypt(access_token)
    conn.scopes = "openid profile email w_member_social"
    conn.status = "active"
    await db.commit()
    await db.refresh(conn)
    return conn


# ──────────────────────────────────────────────
# Twitter/X OAuth2 PKCE helpers
# ──────────────────────────────────────────────

TWITTER_AUTH_URL = "https://twitter.com/i/oauth2/authorize"
TWITTER_TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
TWITTER_ME_URL = "https://api.twitter.com/2/users/me"


def _twitter_oauth_url() -> dict:
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = (
        hashlib.sha256(verifier.encode())
        .digest()
        .hex()
    )
    _oauth_states[state] = {"platform": "twitter", "verifier": verifier}
    params = {
        "response_type": "code",
        "client_id": settings.twitter_client_id,
        "redirect_uri": f"{settings.cors_origins[0]}/settings/integrations/callback/twitter",
        "scope": "tweet.read tweet.write users.read offline.access",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return {"url": f"{TWITTER_AUTH_URL}?{urlencode(params)}", "state": state}


async def _complete_twitter(code: str, stored: dict, db: AsyncSession) -> SocialConnection:
    verifier = stored["verifier"]
    redirect_uri = f"{settings.cors_origins[0]}/settings/integrations/callback/twitter"

    async with httpx.AsyncClient(timeout=15.0) as client:
        token_resp = await client.post(
            TWITTER_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": settings.twitter_client_id,
                "code_verifier": verifier,
            },
            auth=(settings.twitter_client_id, settings.twitter_client_secret),
        )
        token_resp.raise_for_status()
        tokens = token_resp.json()

        access_token = tokens["access_token"]
        refresh_token = tokens.get("refresh_token")

        me_resp = await client.get(
            TWITTER_ME_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        me_resp.raise_for_status()
        me = me_resp.json().get("data", {})

    result = await db.execute(
        select(SocialConnection).where(
            SocialConnection.org_id == ORG_ID,
            SocialConnection.platform == "twitter",
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        conn = SocialConnection(id=str(uuid.uuid4()), org_id=ORG_ID, platform="twitter")
        db.add(conn)

    conn.account_id = me.get("id", "")
    conn.account_name = me.get("username", "")
    conn.access_token_encrypted = encrypt(access_token)
    conn.refresh_token_encrypted = encrypt(refresh_token) if refresh_token else None
    conn.scopes = "tweet.read tweet.write users.read offline.access"
    conn.status = "active"
    await db.commit()
    await db.refresh(conn)
    return conn


# ──────────────────────────────────────────────
# Serializers
# ──────────────────────────────────────────────


def _serialize_cms(c: CmsConnection) -> dict:
    return {
        "id": c.id,
        "type": c.type,
        "name": c.name,
        "projectId": c.project_id,
        "status": c.status,
        "lastTestedAt": c.last_tested_at.isoformat() if c.last_tested_at else None,
        "lastError": c.last_error,
        "createdAt": c.created_at.isoformat(),
    }


def _serialize_social(c: SocialConnection) -> dict:
    return {
        "id": c.id,
        "platform": c.platform,
        "accountName": c.account_name,
        "accountId": c.account_id,
        "status": c.status,
        "scopes": (c.scopes or "").split(),
        "createdAt": c.created_at.isoformat(),
    }
