"""
Application configuration — reads from environment variables.
Secrets (API keys, connection strings) are fetched from Azure Key Vault at runtime.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Azure Identity
    AZURE_TENANT_ID: str = ""
    AZURE_CLIENT_ID: str = ""
    KEY_VAULT_URL: str = ""

    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_FALLBACK_ENDPOINT: str = ""
    AZURE_OPENAI_API_VERSION: str = "2025-01-01-preview"

    # Azure AI Search
    AZURE_SEARCH_ENDPOINT: str = ""
    AZURE_SEARCH_INDEX: str = "ichiba-knowledge-base"

    # Azure Cosmos DB
    COSMOS_ENDPOINT: str = ""
    COSMOS_DATABASE: str = "ichiba"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_SSL: bool = False

    # LangSmith
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_PROJECT: str = "ichiba-merchant-support"

    # Agent settings
    AGENT_MAX_ITERATIONS: int = 5
    CONFIDENCE_THRESHOLD: float = 0.75
    HALLUCINATION_THRESHOLD: float = 0.35
    SEMANTIC_CACHE_SIMILARITY: float = 0.95

    # Service Bus
    SERVICE_BUS_NAMESPACE: str = ""
    SERVICE_BUS_QUEUE: str = "merchant-queries-escalation"

    # API
    CORS_ORIGINS: list[str] = ["*"]
    METRICS_PORT: int = 9090


settings = Settings()
