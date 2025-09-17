from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Existing fields
    DATABASE_URL: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # ✅ Add Cloudflare R2-related fields
    ACCOUNT_ID: str
    ACCESS_KEY_ID: str
    SECRET_ACCESS_KEY: str
    BUCKET_NAME: str
    PUBLIC_BASE_URL: str

    # Adding public upload token 
    image_upload_token: str

    # Notification
    NOTIFY_API_URL: str
    
    STRIPE_API_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()
