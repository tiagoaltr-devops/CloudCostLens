from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CloudCostLens"
    mongo_uri: str = "mongodb://mongodb:27017"
    mongo_db: str = "cloudcostlens"
    scheduler_enabled: bool = True
    collection_hour_utc: int = 2
    pricing_cache_days: int = 7
    oci_config_file: str = "~/.oci/config"
    oci_profile: str = "DEFAULT"
    oci_tenancy_ocid: str | None = None
    oci_regions: str = "us-ashburn-1"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="CCL_", extra="ignore")


settings = Settings()
