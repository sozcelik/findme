"""
Flux image generation via Replicate API + upload to Cloudflare R2.
"""
import io
import uuid
import httpx
import boto3
from botocore.config import Config
from app.config import settings

FLUX_MODEL = "black-forest-labs/flux-dev"
REPLICATE_API_URL = "https://api.replicate.com/v1/predictions"


def _r2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


async def generate_image(prompt: str, width: int = 1200, height: int = 630) -> tuple[str, str, float]:
    """
    Generate image via Flux, upload to R2.
    Returns (storage_url, cdn_url, cost_usd).
    """
    if not settings.replicate_api_token:
        raise RuntimeError("REPLICATE_API_TOKEN not configured")

    headers = {
        "Authorization": f"Token {settings.replicate_api_token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Submit prediction
        resp = await client.post(
            REPLICATE_API_URL,
            headers=headers,
            json={
                "version": FLUX_MODEL,
                "input": {
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "num_outputs": 1,
                    "output_format": "webp",
                    "output_quality": 85,
                },
            },
        )
        resp.raise_for_status()
        prediction = resp.json()
        prediction_url = prediction["urls"]["get"]

        # Poll until done (max 90s)
        import asyncio
        for _ in range(45):
            await asyncio.sleep(2)
            poll = await client.get(prediction_url, headers=headers)
            poll.raise_for_status()
            data = poll.json()
            if data["status"] == "succeeded":
                image_urls = data["output"]
                break
            if data["status"] in ("failed", "canceled"):
                raise RuntimeError(f"Replicate prediction {data['status']}: {data.get('error')}")
        else:
            raise RuntimeError("Replicate prediction timed out")

        # Download image
        image_url = image_urls[0] if isinstance(image_urls, list) else image_urls
        img_resp = await client.get(image_url)
        img_resp.raise_for_status()
        image_bytes = img_resp.content

    # Upload to R2
    key = f"visual-assets/{uuid.uuid4()}.webp"
    r2 = _r2_client()
    r2.upload_fileobj(
        io.BytesIO(image_bytes),
        settings.r2_bucket_name,
        key,
        ExtraArgs={"ContentType": "image/webp", "CacheControl": "public, max-age=31536000"},
    )

    storage_url = f"https://{settings.r2_account_id}.r2.cloudflarestorage.com/{settings.r2_bucket_name}/{key}"
    cdn_url = f"{settings.r2_public_url.rstrip('/')}/{key}" if settings.r2_public_url else storage_url

    # Flux-dev: ~$0.055 per image (1MP equivalent)
    cost = 0.055

    return storage_url, cdn_url, cost
