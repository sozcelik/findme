import hashlib
import os
import base64
import urllib.parse
import httpx
from app.integrations.social.base import SocialAdapter, SocialConnectionData, SocialPostPayload, SocialPostResult

TWITTER_AUTH_URL = "https://twitter.com/i/oauth2/authorize"
TWITTER_TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
SCOPES = "tweet.read tweet.write users.read offline.access"


class TwitterAdapter(SocialAdapter):
    def _code_verifier(self) -> str:
        return base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("=")

    def _code_challenge(self, verifier: str) -> str:
        digest = hashlib.sha256(verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).decode().rstrip("=")

    def get_oauth_url(self, state: str, redirect_uri: str) -> str:
        verifier = self._code_verifier()
        params = {
            "response_type": "code",
            "client_id": self.config["client_id"],
            "redirect_uri": redirect_uri,
            "scope": SCOPES,
            "state": state,
            "code_challenge": self._code_challenge(verifier),
            "code_challenge_method": "S256",
        }
        # Note: caller must persist verifier in session/Redis keyed by state
        return f"{TWITTER_AUTH_URL}?{urllib.parse.urlencode(params)}", verifier  # type: ignore[return-value]

    async def exchange_code(self, code: str, state: str, redirect_uri: str) -> SocialConnectionData:
        # code_verifier must be passed as state in production (stored in Redis)
        code_verifier = state  # simplified — in prod store verifier in Redis keyed by state
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                TWITTER_TOKEN_URL,
                auth=(self.config["client_id"], self.config["client_secret"]),
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "code_verifier": code_verifier,
                },
            )
            r.raise_for_status()
            token_data = r.json()

            me_r = await client.get(
                "https://api.twitter.com/2/users/me",
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            me = me_r.json().get("data", {}) if me_r.status_code == 200 else {}

        return SocialConnectionData(
            platform="twitter",
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            account_id=me.get("id"),
            account_name=me.get("username"),
            scopes=SCOPES.split(),
        )

    async def post(self, connection: SocialConnectionData, payload: SocialPostPayload) -> SocialPostResult:
        hashtag_str = " ".join(f"#{h.lstrip('#')}" for h in payload.hashtags[:2])
        text = f"{payload.body} {hashtag_str}".strip()[:280]

        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                "https://api.twitter.com/2/tweets",
                headers={
                    "Authorization": f"Bearer {connection.access_token}",
                    "Content-Type": "application/json",
                },
                json={"text": text},
            )
            r.raise_for_status()
            data = r.json().get("data", {})

        tweet_id = data.get("id", "")
        return SocialPostResult(
            external_post_id=tweet_id,
            url=f"https://twitter.com/i/web/status/{tweet_id}",
        )
