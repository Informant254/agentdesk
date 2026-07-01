"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    app_name: str = "AgentDesk"
    app_url: str = "http://localhost:3000"
    debug: bool = True

    # AI
    anthropic_api_key: str = ""
    default_model: str = "claude-3-5-sonnet-20241022"

    # Database
    supabase_url: str = ""
    supabase_key: str = ""

    # Google Maps
    google_maps_api_key: str = ""

    # Stripe
    stripe_secret_key: str = ""

    # Google Calendar
    google_calendar_client_id: str = ""
    google_calendar_client_secret: str = ""

    # Jobber API
    jobber_api_key: str = ""
    jobber_api_url: str = "https://api.getjobber.com/api/graphql"

    # Security
    encryption_key: str = ""
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
