import httpx
import urllib.parse
from app.integrations.social.base import SocialAdapter, SocialConnectionData, SocialPostPayload, SocialPostResult

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
SCOPES = "openid profile email w_member_social"


class LinkedInAdapter(SocialAdapter):
    def get_oauth_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self.config["client_id"],
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": SCOPES,
        }
        return f"{LINKEDIN_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str, state: str, redirect_uri: str) -> SocialConnectionData:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                LINKEDIN_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self.config["client_id"],
                    "client_secret": self.config["client_secret"],
                },
            )
            r.raise_for_status()
            token_data = r.json()

            # Fetch profile
            profile_r = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            profile = profile_r.json() if profile_r.status_code == 200 else {}

        return SocialConnectionData(
            platform="linkedin",
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            account_id=profile.get("sub"),
            account_name=profile.get("name"),
            scopes=SCOPES.split(),
        )

    async def post(self, connection: SocialConnectionData, payload: SocialPostPayload) -> SocialPostResult:
        hashtag_str = " ".join(f"#{h.lstrip('#')}" for h in payload.hashtags)
        text = f"{payload.body}\n\n{hashtag_str}".strip()

        post_data = {
            "author": f"urn:li:person:{connection.account_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers={
                    "Authorization": f"Bearer {connection.access_token}",
                    "Content-Type": "application/json",
                    "X-Restli-Protocol-Version": "2.0.0",
                },
                json=post_data,
            )
            r.raise_for_status()

        post_id = r.headers.get("x-restli-id", "")
        return SocialPostResult(
            external_post_id=post_id,
            url=f"https://www.linkedin.com/feed/update/{post_id}/",
        )
