import json
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://findme:findme@localhost:5432/findme"
    redis_url: str = "redis://localhost:6379/0"

    supabase_url: str = ""
    supabase_jwt_secret: str = ""
    supabase_service_role_key: str = ""

    anthropic_api_key: str = ""
    openai_api_key: str = ""
    perplexity_api_key: str = ""

    dataforseo_login: str = ""
    dataforseo_password: str = ""

    cors_origins: list[str] = ["http://localhost:3000"]
    environment: str = "development"

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_growth_price_id: str = ""
    stripe_pro_price_id: str = ""

    # LinkedIn OAuth
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""

    # Twitter/X OAuth2
    twitter_client_id: str = ""
    twitter_client_secret: str = ""

    # AES-256 key for encrypting OAuth tokens (base64url, 32 bytes)
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    encryption_key: str = ""

    # Replicate (image gen — Flux)
    replicate_api_token: str = ""

    # Cloudflare R2
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "findme-assets"
    r2_public_url: str = ""  # e.g. https://assets.yourdomain.com


settings = Settings()
