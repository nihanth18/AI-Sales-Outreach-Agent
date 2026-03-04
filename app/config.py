"""
Application configuration loaded from environment variables.
Supports mock mode for local development without API keys.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    # --- Application ---
    app_env: str = Field(default="development", alias="APP_ENV")
    mock_mode: bool = Field(default=True, alias="MOCK_MODE")

    # --- OpenAI ---
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    # --- Tavily Search ---
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")

    # --- Airtable CRM ---
    airtable_api_key: str = Field(default="", alias="AIRTABLE_API_KEY")
    airtable_base_id: str = Field(default="", alias="AIRTABLE_BASE_ID")
    airtable_table_name: str = Field(default="Prospects", alias="AIRTABLE_TABLE_NAME")

    # --- Gmail ---
    gmail_credentials_path: str = Field(default="credentials.json", alias="GMAIL_CREDENTIALS_PATH")
    gmail_token_path: str = Field(default="token.json", alias="GMAIL_TOKEN_PATH")
    gmail_sender_email: Optional[str] = Field(default=None, alias="GMAIL_SENDER_EMAIL")

    # --- Database ---
    database_url: str = Field(default="sqlite:///./sales_outreach.db", alias="DATABASE_URL")

    # --- ChromaDB ---
    chroma_persist_dir: str = Field(default="./chroma_db", alias="CHROMA_PERSIST_DIR")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        populate_by_name = True

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key) and not self.openai_api_key.startswith("sk-your")

    @property
    def has_tavily(self) -> bool:
        return bool(self.tavily_api_key) and not self.tavily_api_key.startswith("tvly-your")

    @property
    def has_airtable(self) -> bool:
        return bool(self.airtable_api_key) and not self.airtable_api_key.startswith("pat_your")

    @property
    def has_gmail(self) -> bool:
        import os
        return os.path.exists(self.gmail_credentials_path)


settings = Settings()
