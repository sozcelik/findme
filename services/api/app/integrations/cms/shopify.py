import httpx
from app.integrations.cms.base import CMSAdapter, CMSPublishPayload, CMSPublishResult


class ShopifyAdapter(CMSAdapter):
    """Shopify Blog Posts REST API."""

    def _headers(self) -> dict[str, str]:
        return {
            "X-Shopify-Access-Token": self.config["access_token"],
            "Content-Type": "application/json",
        }

    def _base_url(self) -> str:
        shop = self.config["shop"].rstrip("/")
        return f"https://{shop}/admin/api/2024-01"

    async def test_connection(self) -> bool:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{self._base_url()}/shop.json",
                headers=self._headers(),
            )
            return r.status_code == 200

    async def publish(self, payload: CMSPublishPayload) -> CMSPublishResult:
        blog_id = self.config["blog_id"]
        data = {
            "article": {
                "title": payload.title,
                "body_html": payload.body_html or payload.body_markdown or "",
                "published": payload.status != "draft",
                "summary_html": payload.meta_description or "",
                "handle": payload.slug or "",
            }
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{self._base_url()}/blogs/{blog_id}/articles.json",
                headers=self._headers(),
                json=data,
            )
            r.raise_for_status()
            article = r.json()["article"]

        return CMSPublishResult(
            external_id=str(article["id"]),
            external_url=f"https://{self.config['shop']}/blogs/{self.config.get('blog_handle', 'news')}/{article.get('handle', '')}",
            status="published" if article.get("published_at") else "draft",
        )

    async def update(self, external_id: str, payload: CMSPublishPayload) -> CMSPublishResult:
        blog_id = self.config["blog_id"]
        data = {
            "article": {
                "title": payload.title,
                "body_html": payload.body_html or payload.body_markdown or "",
                "published": payload.status != "draft",
            }
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.put(
                f"{self._base_url()}/blogs/{blog_id}/articles/{external_id}.json",
                headers=self._headers(),
                json=data,
            )
            r.raise_for_status()
            article = r.json()["article"]

        return CMSPublishResult(
            external_id=external_id,
            external_url="",
            status="published" if article.get("published_at") else "draft",
        )
