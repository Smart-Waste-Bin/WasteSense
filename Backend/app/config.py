from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The single .env lives in the repo root. Inside Docker, compose passes
# the values as environment variables instead, so the file is not needed there.
ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_ENV_FILE, extra="ignore")

    postgres_user: str = "smartbin"
    postgres_password: str = "change-me-db"
    postgres_db: str = "smartbin"
    database_url: str = "postgresql+psycopg://smartbin:change-me-db@localhost:5432/smartbin"

    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_tls_port: int = 8883
    mqtt_user: str = "smartbin-backend"
    mqtt_password: str = "change-me-mqtt"
    mqtt_test_device_password: str = "change-me-device"
    mqtt_sim_user: str = "smartbin-simulator"
    mqtt_sim_password: str = "change-me-sim"
    # The backend listens on MQTT while it runs. Tests turn this off (tests/conftest.py).
    mqtt_ingest_enabled: bool = True
    # The every-60-s offline check (BE-03). Tests turn this off too.
    status_job_enabled: bool = True
    # WebSocket heartbeat (BE-05, contract section 7). Tests make it shorter.
    ws_ping_interval_s: float = 25

    jwt_secret: str = "change-me-to-a-long-random-string"
    access_token_minutes: int = 60
    refresh_token_days: int = 7
    lockout_max_attempts: int = 5
    lockout_window_min: int = 10
    lockout_minutes: int = 10
    # False on laptops (plain http). Set true when deployed with HTTPS.
    cookie_secure: bool = False

    cors_origins: str = "http://localhost:5173,http://localhost:8081"
    osrm_url: str = "https://router.project-osrm.org"

    # Profile photos (AUTH-03). "local" saves them in MEDIA_DIR, "s3" in an AWS S3 bucket.
    storage_backend: str = "local"
    media_dir: Path = BACKEND_DIR / "media"
    s3_bucket: str = ""
    s3_region: str = ""
    # Only for S3-compatible storage that is not AWS (e.g. MinIO). Empty for AWS.
    s3_endpoint_url: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    seed_admin_password: str = ""
    seed_supervisor_password: str = ""
    seed_collector_password: str = ""

    @field_validator("jwt_secret")
    @classmethod
    def jwt_secret_long_enough(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError(
                "JWT_SECRET must be at least 32 characters. Make one with: "
                'python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        return value

    @field_validator("cors_origins")
    @classmethod
    def no_wildcard_origin(cls, value: str) -> str:
        # The refresh cookie needs allow_credentials=True, which must never be combined with "*".
        if "*" in value:
            raise ValueError("CORS_ORIGINS must list real origins, not '*'")
        return value

    @field_validator("storage_backend")
    @classmethod
    def known_storage_backend(cls, value: str) -> str:
        if value not in ("local", "s3"):
            raise ValueError('STORAGE_BACKEND must be "local" or "s3"')
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
