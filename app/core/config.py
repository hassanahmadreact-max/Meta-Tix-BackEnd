# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # This will look for a variable named SECRET_KEY in your .env
    SECRET_KEY: str 
    ALGORITHM: str 
    ACCESS_TOKEN_EXPIRE_MINUTES: int 
    DB_URL: str 
    
    class Config:
        env_file = ".env"

settings = Settings()