from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# The single .env lives in the repo root. Inside Docker, compose passes
# the values as environment variables instead, so the file is not needed there.
ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


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

    jwt_secret: str = "change-me-to-a-long-random-string"
    cors_origins: str = "http://localhost:5173,http://localhost:8081"
    osrm_url: str = "https://router.project-osrm.org"

    seed_admin_password: str = ""
    seed_supervisor_password: str = ""
    seed_collector_password: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
