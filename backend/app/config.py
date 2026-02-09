from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg://khedma:khedma@127.0.0.1:5433/khedma"
    llm_provider: str = "mock"
    jwt_secret: str = "dev-secret-a-changer"
    # IA (GCP Vertex AI)
    google_application_credentials: str = ""
    gcp_service_account_json: str = ""  # contenu du JSON (hébergement), prioritaire sur un fichier absent
    gcp_project: str = ""
    gcp_location: str = "eu"
    llm_model: str = "gemini-3.8-flash"
    firecrawl_api_key: str = ""
    # Politesse du crawl : délai minimal entre deux requêtes vers une même source
    crawl_delay_s: float = 0.5
    user_agent: str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    )


settings = Settings()
