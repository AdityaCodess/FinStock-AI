# finstock-ai/backend/app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Manages application settings and environment variables.
    """
    GEMINI_API_KEY: str

    class Config:
        # This tells Pydantic to load variables from a file named .env
        env_file = ".env"
        # This allows it to work even if the .env is in the parent 'backend' dir
        env_file_encoding = 'utf-8'

# Create a single, importable instance of the settings
settings = Settings()