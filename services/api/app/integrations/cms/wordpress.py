import base64
import httpx
from app.integrations.cms.base import CMSAdapter, CMSPublishPayload, CMSPublishResult


class WordPressAdapter(CMSAdapter):
    """WordPress REST API v2 with Application Passwords."""

    def _headers(self) -> dict[str, str]:
        user = self.config["username"]
        pwd = self.config["app_password"].replace(" ", "")
        creds = base64.b64encode(f"{user}:{pwd}".encode()).decode()
        return {
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/json",
        }

    def _base_url(self) -> str:
        url = self.config["site_url"].rstrip("/")
        return f"{url}/wp-json/wp/v2"

    async def test_connection(self) -> bool:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{self._base_url()}/users/me", headers=self._headers())
            return r.status_code == 200

    async def publish(self, payload: CMSPublishPayload) -> CMSPublishResult:
        data = {
            "title": payload.title,
            "content": payload.body_html or _markdown_to_html(payload.body_markdown),
            "slug": payload.slug or "",
            "status": "draft" if payload.status == "draft" else "publish",
        }
        if payload.meta_description:
            data["excerpt"] = payload.meta_description

        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{self._base_url()}/posts",
                headers=self._headers(),
                json=data,
            )
            r.raise_for_status()
            result = r.json()

        return CMSPublishResult(
            external_id=str(result["id"]),
            external_url=result.get("link", ""),
            status=result.get("status", "draft"),
        )

    async def update(self, external_id: str, payload: CMSPublishPayload) -> CMSPublishResult:
        data = {
            "title": payload.title,
            "content": payload.body_html or _markdown_to_html(payload.body_markdown),
            "status": "draft" if payload.status == "draft" else "publish",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{self._base_url()}/posts/{external_id}",
                headers=self._headers(),
                json=data,
            )
            r.raise_for_status()
            result = r.json()

        return CMSPublishResult(
            external_id=str(result["id"]),
            external_url=result.get("link", ""),
            status=result.get("status", "draft"),
        )


def _markdown_to_html(markdown: str | None) -> str:
    """Minimal markdown → HTML for WordPress (no heavy deps)."""
    if not markdown:
        return ""
    lines = []
    for line in markdown.splitlines():
        if line.startswith("### "):
            lines.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("## "):
            lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("# "):
            lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("- ") or line.startswith("* "):
            lines.append(f"<li>{line[2:]}</li>")
        elif line.strip() == "":
            lines.append("")
        else:
            lines.append(f"<p>{line}</p>")
    return "\n".join(lines)
