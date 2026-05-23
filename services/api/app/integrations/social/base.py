from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SocialPostPayload:
    body: str
    hashtags: list[str] = field(default_factory=list)
    reddit_title: str | None = None  # Reddit only
    media_urls: list[str] = field(default_factory=list)


@dataclass
class SocialPostResult:
    external_post_id: str
    url: str | None = None


@dataclass
class SocialConnectionData:
    platform: str
    access_token: str
    refresh_token: str | None = None
    account_id: str | None = None
    account_name: str | None = None
    token_expires_at: str | None = None
    scopes: list[str] = field(default_factory=list)


class SocialAdapter(ABC):
    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    async def post(
        self, connection: SocialConnectionData, payload: SocialPostPayload
    ) -> SocialPostResult: ...

    @abstractmethod
    def get_oauth_url(self, state: str, redirect_uri: str) -> str: ...

    @abstractmethod
    async def exchange_code(
        self, code: str, state: str, redirect_uri: str
    ) -> SocialConnectionData: ...

    @classmethod
    def from_platform(cls, platform: str) -> "SocialAdapter":
        from app.integrations.social.linkedin import LinkedInAdapter
        from app.integrations.social.twitter import TwitterAdapter
        from app.integrations.social.reddit import RedditAdapter
        from app.config import settings

        registry: dict[str, type[SocialAdapter]] = {
            "linkedin": LinkedInAdapter,
            "twitter": TwitterAdapter,
            "reddit": RedditAdapter,
        }
        adapter_cls = registry.get(platform)
        if not adapter_cls:
            raise ValueError(f"Unknown platform: {platform}")
        return adapter_cls({
            "client_id": getattr(settings, f"{platform}_client_id", ""),
            "client_secret": getattr(settings, f"{platform}_client_secret", ""),
        })
