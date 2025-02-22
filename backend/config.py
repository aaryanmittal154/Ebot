from pydantic_settings import BaseSettings
from typing import Optional
from dotenv import load_dotenv, find_dotenv
import os

def clear_env_cache():
    """Clear all environment variable caches and reload settings."""
    # Clear Python's environment variable cache
    os.environ.clear()

    # Clear dotenv cache by reloading
    dotenv_path = find_dotenv()
    if dotenv_path:
        load_dotenv(dotenv_path, override=True)

    # Create new settings instance to reload all values
    return Settings()

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres@localhost:5432/emaildb"
    )

    # Email
    imap_server: str = "imap.gmail.com"
    imap_port: int
    email_address: str
    email_password: str

    # Security
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    # Vector DB
    chroma_persist_directory: str = "./chroma_db"

    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
