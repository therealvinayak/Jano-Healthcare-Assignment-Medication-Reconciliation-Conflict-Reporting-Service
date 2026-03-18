from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Medication Reconciliation Service"
    environment: str = "dev"
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "med_reconciliation"
    conflict_rules_path: str = "config/conflict_rules.json"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
