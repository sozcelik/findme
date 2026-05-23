from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class CMSPublishPayload:
    title: str
    body_html: str
    body_markdown: str
    slug: str | None
    meta_title: str | None
    meta_description: str | None
    status: str = "draft"  # draft|publish


@dataclass
class CMSPublishResult:
    external_id: str
    external_url: str
    status: str


class CMSAdapter(ABC):
    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    async def test_connection(self) -> bool: ...

    @abstractmethod
    async def publish(self, payload: CMSPublishPayload) -> CMSPublishResult: ...

    @abstractmethod
    async def update(self, external_id: str, payload: CMSPublishPayload) -> CMSPublishResult: ...

    @classmethod
    def from_config(cls, cms_type: str, config: dict) -> "CMSAdapter":
        from app.integrations.cms.wordpress import WordPressAdapter
        from app.integrations.cms.webflow import WebflowAdapter
        from app.integrations.cms.shopify import ShopifyAdapter

        registry: dict[str, type[CMSAdapter]] = {
            "wordpress": WordPressAdapter,
            "webflow": WebflowAdapter,
            "shopify": ShopifyAdapter,
        }
        adapter_cls = registry.get(cms_type)
        if not adapter_cls:
            raise ValueError(f"Unknown CMS type: {cms_type}")
        return adapter_cls(config)
