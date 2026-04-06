import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Voice Agent"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "voiceagent"
    POSTGRES_PASSWORD: str = "voiceagent123"
    POSTGRES_DB: str = "voiceagent"
    
    # Add this to Settings class
    MISTRAL_API_KEY: Optional[str] = os.getenv("MISTRAL_API_KEY")
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # Twilio (will add later)
    # TWILIO_ACCOUNT_SID: Optional[str] = os.getenv('TWILIO_ACCOUNT_SID')
    # TWILIO_AUTH_TOKEN: Optional[str] = os.getenv('TWILIO_AUTH_TOKEN')
    # TWILIO_PHONE_NUMBER: Optional[str] = os.getenv('TWILIO_PHONE_NUMBER')
    TWILIO_ACCOUNT_SID: str = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN: str = os.getenv('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER: int = os.getenv('TWILIO_PHONE_NUMBER')
    PUBLIC_URL: Optional[str] = os.getenv('PUBLIC_URL')
    MY_PHONE_NUMBER: Optional[str] = os.getenv('MY_PHONE_NUMBER')
    # # OpenAI (will add later)
    # OPENAI_API_KEY: Optional[str] = None

        # self.my_phone_number = 
        # self.public_url = 
    class Config:
        env_file = ".env"

settings = Settings()