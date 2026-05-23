from app.integrations.social.base import SocialAdapter, SocialConnectionData, SocialPostPayload, SocialPostResult


class RedditAdapter(SocialAdapter):
    """Reddit adapter generates drafts only — posting is manual per Reddit ToS."""

    def get_oauth_url(self, state: str, redirect_uri: str) -> str:
        raise NotImplementedError("Reddit manual posting only — no OAuth flow")

    async def exchange_code(self, code: str, state: str, redirect_uri: str) -> SocialConnectionData:
        raise NotImplementedError("Reddit manual posting only")

    async def post(self, connection: SocialConnectionData, payload: SocialPostPayload) -> SocialPostResult:
        # Reddit posts are drafts surfaced in the UI for one-click manual posting
        raise NotImplementedError(
            "Reddit automated posting is not permitted by ToS. "
            "Use the draft text from social_posts.body for manual posting."
        )
