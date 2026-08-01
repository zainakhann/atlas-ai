from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Atlas AI"
    database_url: str = "postgresql://postgres:postgres@localhost:5432/atlas_ai"
    groq_api_key: str = ""
    secret_key: str = "dev-secret-key-change-this-in-production"
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()