import os
import sys

from dotenv import load_dotenv
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    WHICHENV: str
    WA_APP_ID: str
    WA_APP_SECRET: str
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


settings: Settings = load_settings()
