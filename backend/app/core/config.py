from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Atlas AI"
    database_url: str = "postgresql://postgres:postgres@localhost:5432/atlas_ai"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    secret_key: str = "dev-secret-key-change-this-in-production"
    frontend_url: str = "https://atlas-ai-delta-nine.vercel.app"
    gemini_api_key: str = ""
    cohere_api_key: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()