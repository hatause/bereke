from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent

class Settings(BaseSettings):
    database_url: str = f"sqlite:///{(PROJECT / '.local/academy.sqlite3').as_posix()}"
    model_config = SettingsConfigDict(env_file=PROJECT / '.env', extra='ignore')

settings = Settings()
(PROJECT / '.local').mkdir(exist_ok=True)
