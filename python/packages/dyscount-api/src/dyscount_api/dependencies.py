"""Dependency injection for dyscount-api."""

from functools import lru_cache

from dyscount_core.config import Config


@lru_cache()
def get_config() -> Config:
    """Get the application configuration.
    
    Uses lru_cache to ensure the config is only loaded once.
    
    Returns:
        Config instance with all settings loaded.
    """
    return Config()
