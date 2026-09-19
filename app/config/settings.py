from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"

    # Ollama LLM Configuration
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:1.5b"

    # Database Configuration
    database_url: str = "sqlite+aiosqlite:///./data/nyra.db"

    # Personal Assistant Identity
    nyra_name: str = "Nyra"
    owner_name: str = "Rafey"

    # Telephony Provider (android | exotel)
    telephony_provider: str = "exotel"
    exotel_account_sid: str = ""
    exotel_api_key: str = ""
    exotel_api_token: str = ""
    exotel_virtual_number: str = ""
    exotel_media_encoding: str = "audio/pcm"
    exotel_media_sample_rate: int = 16000
    telephony_webhook_token: str = ""

    # WhatsApp Provider (mock | cloud_api)
    whatsapp_provider: str = "mock"
    whatsapp_token: str = ""
    whatsapp_phone_id: str = ""
    whatsapp_recipient_number: str = ""

    # Public Tunnel URL
    public_base_url: str = "http://localhost:8000"

    # Logging
    log_level: str = "INFO"

    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent.parent
    data_dir: Path = base_dir / "data"
    recordings_dir: Path = base_dir / "recordings"
    logs_dir: Path = base_dir / "logs"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# Ensure directories exist
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.recordings_dir.mkdir(parents=True, exist_ok=True)
settings.logs_dir.mkdir(parents=True, exist_ok=True)
