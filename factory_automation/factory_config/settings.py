"""Application configuration settings combining config.yaml and .env files."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings combining config.yaml and environment variables.

    Configuration precedence:
    1. Environment variables (highest priority)
    2. .env file
    3. config.yaml file (lowest priority)

    Sensitive data (API keys, passwords) should only be in .env
    Non-sensitive configuration should be in config.yaml
    """

    # API Keys and Secrets (from .env only)
    openai_api_key: str = Field(..., description="OpenAI API key")
    together_api_key: Optional[str] = Field(None, description="Together AI API key")
    gmail_client_id: Optional[str] = Field(None, description="Gmail OAuth client ID")
    gmail_client_secret: Optional[str] = Field(
        None, description="Gmail OAuth client secret"
    )
    database_password: Optional[str] = Field(
        "password", description="Database password"
    )
    redis_password: Optional[str] = Field(None, description="Redis password")
    secret_key: str = Field("your-secret-key-here", description="App secret key")

    # Configuration from factory_config.yaml
    config: Dict[str, Any] = Field(default_factory=dict)

    # Computed properties from config
    app_env: str = Field(default="development")
    app_port: int = Field(default=8001)
    gradio_port: int = Field(default=7860)
    use_ai_orchestrator: bool = Field(default=False)
    enable_comparison_logging: bool = Field(default=False)
    email_poll_interval: int = Field(default=300)
    email_folder: str = Field(default="INBOX")
    gmail_redirect_uri: str = Field(default="http://localhost:8080")
    gmail_token_file: str = Field(default="token.json")
    database_url: Optional[str] = Field(default=None)
    redis_url: Optional[str] = Field(default=None)
    chroma_persist_directory: str = Field(default="./chroma_data")
    chroma_host: str = Field(default="localhost")
    chroma_port: int = Field(default=8000)
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=1440)
    log_level: str = Field(default="INFO")
    comparison_log_dir: str = Field(default="./orchestrator_comparison_logs")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"

    def __init__(self, **kwargs):
        """Initialize settings by loading config.yaml first."""
        # Load config.yaml
        config_path = Path(__file__).parent.parent.parent / "config.yaml"
        if config_path.exists():
            with open(config_path, "r") as f:
                yaml_config = yaml.safe_load(f)
                kwargs["config"] = yaml_config

                # Map yaml config to settings attributes
                if yaml_config:
                    # App settings
                    app_config = yaml_config.get("app", {})
                    kwargs.setdefault(
                        "app_env", app_config.get("environment", "development")
                    )
                    kwargs.setdefault("app_port", app_config.get("port", 8001))
                    kwargs.setdefault(
                        "gradio_port", app_config.get("gradio_port", 7860)
                    )
                    kwargs.setdefault("log_level", app_config.get("log_level", "INFO"))

                    # Orchestrator settings
                    orch_config = yaml_config.get("orchestrator", {})
                    kwargs.setdefault(
                        "use_ai_orchestrator", orch_config.get("use_ai_version", False)
                    )
                    kwargs.setdefault(
                        "enable_comparison_logging",
                        orch_config.get("enable_comparison_logging", False),
                    )

                    # Email settings
                    email_config = yaml_config.get("email", {})
                    kwargs.setdefault(
                        "email_poll_interval", email_config.get("poll_interval", 300)
                    )
                    kwargs.setdefault(
                        "email_folder", email_config.get("folder", "INBOX")
                    )

                    # Gmail settings
                    gmail_config = yaml_config.get("gmail", {})
                    kwargs.setdefault(
                        "gmail_redirect_uri",
                        gmail_config.get("redirect_uri", "http://localhost:8080"),
                    )
                    kwargs.setdefault(
                        "gmail_token_file", gmail_config.get("token_file", "token.json")
                    )

                    # ChromaDB settings
                    chroma_config = yaml_config.get("chromadb", {})
                    kwargs.setdefault(
                        "chroma_persist_directory",
                        chroma_config.get("persist_directory", "./chroma_data"),
                    )
                    kwargs.setdefault(
                        "chroma_host", chroma_config.get("host", "localhost")
                    )
                    kwargs.setdefault("chroma_port", chroma_config.get("port", 8000))

                    # Security settings
                    security_config = yaml_config.get("security", {})
                    kwargs.setdefault(
                        "jwt_algorithm", security_config.get("jwt_algorithm", "HS256")
                    )
                    kwargs.setdefault(
                        "access_token_expire_minutes",
                        security_config.get("access_token_expire_minutes", 1440),
                    )

                    # Monitoring settings
                    monitoring_config = yaml_config.get("monitoring", {})
                    kwargs.setdefault(
                        "comparison_log_dir",
                        monitoring_config.get(
                            "comparison_log_dir", "./orchestrator_comparison_logs"
                        ),
                    )

        super().__init__(**kwargs)

        # Build database and redis URLs if not provided
        if not self.database_url and self.config.get("database"):
            db_config = self.config["database"]
            password = self.database_password or "password"
            self.database_url = f"postgresql://{db_config['user']}:{password}@{db_config['host']}:{db_config['port']}/{db_config['name']}"

        if not self.redis_url and self.config.get("redis"):
            redis_config = self.config["redis"]
            if self.redis_password:
                self.redis_url = f"redis://:{self.redis_password}@{redis_config['host']}:{redis_config['port']}/{redis_config.get('db', 0)}"
            else:
                self.redis_url = f"redis://{redis_config['host']}:{redis_config['port']}/{redis_config.get('db', 0)}"

    def get_model_config(self) -> Dict[str, str]:
        """Get model configuration from factory_config.yaml."""
        return self.config.get("models", {})

    def get_rag_config(self) -> Dict[str, Any]:
        """Get RAG configuration from factory_config.yaml."""
        return self.config.get("rag", {})

    def get_processing_config(self) -> Dict[str, Any]:
        """Get processing configuration from factory_config.yaml."""
        return self.config.get("processing", {})

    def get_business_rules(self) -> Dict[str, Any]:
        """Get business rules from factory_config.yaml."""
        return self.config.get("business", {})

    def get_feature_flags(self) -> Dict[str, bool]:
        """Get feature flags from factory_config.yaml."""
        return self.config.get("features", {})

    def get_chromadb_collections(self) -> Dict[str, str]:
        """Get ChromaDB collection names."""
        return self.config.get("chromadb", {}).get(
            "collection_names",
            {
                "inventory": "tag_inventory",
                "orders": "order_history",
                "customers": "customer_preferences",
            },
        )

    def get_gmail_scopes(self) -> List[str]:
        """Get Gmail API scopes."""
        return self.config.get("gmail", {}).get(
            "scopes",
            [
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.send",
            ],
        )


# Create global settings instance
settings = Settings()

# Configure logging based on settings
logging.basicConfig(level=getattr(logging, settings.log_level))
