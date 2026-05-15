from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    ROBOFLOW_API_KEY: str = ""
    POTHOLE_CONFIDENCE_THRESHOLD: int = 40
    DATABASE_URL: str = "sqlite:///./potholenet.db"

    # Roboflow model configuration
    ROBOFLOW_WORKSPACE: str = "chong-ming-zhe"
    ROBOFLOW_PROJECT: str = "pothole-sl4sr-na3pv"
    ROBOFLOW_VERSION: int = 1

    # Hazard query defaults
    DEFAULT_SEARCH_RADIUS_M: int = 2000
    MAX_SEARCH_RADIUS_M: int = 5000
    HAZARD_EXPIRY_DAYS: int = 90

    # Deduplication settings
    DEDUP_RADIUS_M: float = 5.0
    DEDUP_WINDOW_DAYS: int = 30

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()