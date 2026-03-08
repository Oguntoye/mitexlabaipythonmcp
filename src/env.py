import os, sys
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import ValidationError

load_dotenv()

class Settings(BaseSettings):
    MCPPORT: int
    WHICHENV: str
    MCPKEY: str

    REDISHOST: str
    REDISPORT: int
    
    model_config = SettingsConfigDict(case_sensitive=True)

def load_settings() -> Settings:
    try:
        return Settings()  # type: ignore[call-arg]
    except ValidationError as e:
        print("\n❌ Invalid environment configuration:")
        for err in e.errors():
            loc = ".".join(str(x) for x in err["loc"])
            print(f"  - {loc}: {err['msg']}")
        sys.exit(1)

settings = load_settings()
