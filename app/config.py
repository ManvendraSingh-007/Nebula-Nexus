import os
from dotenv import load_dotenv

# Load variables from .env into memory
load_dotenv()

class Config:
    # App Secrets
    SECRET_KEY = os.getenv("SECRET_KEY", "default-dev-key")
    
    # Database Settings (Casting Port to int)
    DB_USER = os.getenv("DATABASE_USER")
    DB_PASSWORD = os.getenv("DATABASE_PASSWORD")
    DB_HOST = os.getenv("DATABASE_HOST", "localhost")
    DB_PORT = int(os.getenv("DATABASE_PORT", 3306))
    DB_NAME = os.getenv("DATABASE_NAME")
    
    # Mail Settings
    MAIL_PWD = os.getenv("MAIL_APP_PASSWORD")

    # Default Settings
    ACCESS_TOKEN_EXPIRE_MINUTES=60*24*2
    ALGORITHM="HS256"


    # Mandatory check: Fail fast if critical keys are missing
    @classmethod
    def validate(cls):
        required = ["SECRET_KEY", "DB_USER", "DB_PASSWORD", "DB_NAME"]
        for key in required:
            if not getattr(cls, key):
                raise ValueError(f"CRITICAL: {key} is not set in .env")

# Run validation on startup
Config.validate()
