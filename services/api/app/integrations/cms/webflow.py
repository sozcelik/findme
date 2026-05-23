import httpx
from app.integrations.cms.base import CMSAdapter, CMSPublishPayload, CMSPublishResult


class WebflowAdapter(CMSAdapter):
    """Webflow CMS Items API v2."""

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config['api_token']}",
            "Content-Type": "application/json",
            "accept-version": "1.0.0",
        }

    async def test_connection(self) -> bool:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://api.webflow.com/v2/token/introspect",
                headers=self._headers(),
            )
            return r.status_code == 200

    async def publish(self, payload: CMSPublishPayload) -> CMSPublishResult:
        collection_id = self.config["collection_id"]
        data = {
            "isArchived": False,
            "isDraft": payload.status == "draft",
            "fieldData": {
                "name": payload.title,
                "slug": payload.slug or "",
                "post-body": payload.body_html or payload.body_markdown or "",
                "post-summary": payload.meta_description or "",
            },
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"https://api.webflow.com/v2/collections/{collection_id}/items",
                headers=self._headers(),
                json=data,
            )
            r.raise_for_status()
            result = r.json()

        item_id = result.get("id", "")
        return CMSPublishResult(
            external_id=item_id,
            external_url=f"https://webflow.com/design/{self.config.get('site_id', '')}",
            status=result.get("isDraft", True) and "draft" or "published",
        )

    async def update(self, external_id: str, payload: CMSPublishPayload) -> CMSPublishResult:
        collection_id = self.config["collection_id"]
        data = {
            "isDraft": payload.status == "draft",
            "fieldData": {
                "name": payload.title,
                "post-body": payload.body_html or payload.body_markdown or "",
            },
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.patch(
                f"https://api.webflow.com/v2/collections/{collection_id}/items/{external_id}",
                headers=self._headers(),
                json=data,
            )
            r.raise_for_status()
            result = r.json()

        return CMSPublishResult(
            external_id=external_id,
            external_url="",
            status="draft" if result.get("isDraft") else "published",
        )
