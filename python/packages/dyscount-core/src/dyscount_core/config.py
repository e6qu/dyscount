"""Configuration for dyscount-core."""

from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TimeoutSettings(BaseSettings):
    """Server timeout settings."""
    model_config = SettingsConfigDict(env_prefix="DYSCOUNT_SERVER__TIMEOUT__")
    
    read: int = 30
    write: int = 30
    idle: int = 120


class ServerSettings(BaseSettings):
    """HTTP server settings."""
    model_config = SettingsConfigDict(env_prefix="DYSCOUNT_SERVER__")
    
    port: int = 8000
    host: str = "0.0.0.0"
    workers: int | str = "auto"
    timeout: TimeoutSettings = Field(default_factory=TimeoutSettings)
    max_request_size: int = 16777216  # 16 MB
    keep_alive: bool = True


class StorageSettings(BaseSettings):
    """SQLite storage backend settings."""
    model_config = SettingsConfigDict(env_prefix="DYSCOUNT_STORAGE__")
    
    data_directory: Path = Path("./data")
    namespace: str = "default"
    sqlite_mode: str = "wal"  # wal or normal
    persistence_mode: str = "balanced"  # durable, balanced, or fast
    cache_size_mb: int = 200
    busy_timeout_ms: int = 5000
    max_connections: int | str = "auto"
    checkpoint_interval_sec: int = 300


class AuthSettings(BaseSettings):
    """Authentication and authorization settings."""
    model_config = SettingsConfigDict(env_prefix="DYSCOUNT_AUTH__")
    
    mode: str = "local"  # local or production
    aws_region: str = "eu-west-1"
    iam_policy_file: Optional[Path] = None
    access_key_id: str = "local"
    secret_access_key: str = "local"
    signature_ttl_sec: int = 300


class LoggingSettings(BaseSettings):
    """Structured logging configuration."""
    model_config = SettingsConfigDict(env_prefix="DYSCOUNT_LOGGING__")
    
    level: str = "info"  # debug, info, warn, error
    format: str = "json"  # json or text
    output: str = "stdout"  # stdout, stderr, or file path
    include_timestamp: bool = True
    include_source: bool = False
    redact_sensitive: bool = True
    request_logging: bool = True
    slow_query_threshold_ms: int = 1000


class MetricsSettings(BaseSettings):
    """Prometheus metrics and observability settings."""
    model_config = SettingsConfigDict(env_prefix="DYSCOUNT_METRICS__")
    
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    prometheus_path: str = "/metrics"
    prometheus_host: str = "0.0.0.0"
    operation_latency_buckets: List[float] = Field(default_factory=lambda: [
        0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10
    ])
    collect_table_metrics: bool = True
    collect_query_metrics: bool = True


class CORSSettings(BaseSettings):
    """Cross-Origin Resource Sharing settings."""
    model_config = SettingsConfigDict(env_prefix="DYSCOUNT_CORS__")
    
    enabled: bool = False
    allowed_origins: List[str] = Field(default_factory=lambda: ["*"])
    allowed_methods: List[str] = Field(default_factory=lambda: ["POST", "OPTIONS"])
    allowed_headers: List[str] = Field(default_factory=lambda: ["*"])
    allow_credentials: bool = False
    max_age: int = 86400


class LimitsSettings(BaseSettings):
    """Resource and operation limits."""
    model_config = SettingsConfigDict(env_prefix="DYSCOUNT_LIMITS__")
    
    max_item_size: int = 409600  # 400 KB
    max_batch_size: int = 25
    max_batch_bytes: int = 16777216  # 16 MB
    max_query_limit: int = 1000
    max_scan_limit: int = 1000
    max_page_size: int = 1000
    max_expression_length: int = 4096
    max_gsi_per_table: int = 20
    max_lsi_per_table: int = 5
    max_table_name_length: int = 1024
    max_concurrent_requests: int = 1000
    rate_limit_rps: int = 0  # 0 = unlimited


class Config(BaseSettings):
    """Dyscount configuration.
    
    Configuration is loaded from:
    1. Built-in defaults (lowest priority)
    2. JSON config file (dyscount.json)
    3. Environment variables with DYSCOUNT_ prefix (highest priority)
    
    Environment variables use double underscore to separate sections:
    - DYSCOUNT_SERVER__PORT=8000
    - DYSCOUNT_STORAGE__DATA_DIRECTORY=/path/to/data
    - DYSCOUNT_AUTH__MODE=local
    
    Example:
        config = Config()
        print(config.server.port)  # 8000
        print(config.storage.data_directory)  # Path("./data")
    """
    
    model_config = SettingsConfigDict(
        env_prefix="DYSCOUNT_",
        env_nested_delimiter="__",
        extra="ignore",  # Allow extra fields for forward compatibility
    )
    
    server: ServerSettings = Field(default_factory=ServerSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    metrics: MetricsSettings = Field(default_factory=MetricsSettings)
    cors: CORSSettings = Field(default_factory=CORSSettings)
    limits: LimitsSettings = Field(default_factory=LimitsSettings)
    
    # Config file path (can be set via DYSCOUNT_CONFIG_FILE env var)
    config_file: Optional[Path] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure data directory exists
        self.storage.data_directory = Path(self.storage.data_directory).expanduser()
        self.storage.data_directory.mkdir(parents=True, exist_ok=True)
