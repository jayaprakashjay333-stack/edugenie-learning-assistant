import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str
    explanation_provider: str
    local_explanation_model: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip(),
        explanation_provider=os.getenv(
            "EDUGENIE_EXPLANATION_PROVIDER", "gemini"
        ).strip().lower(),
        local_explanation_model=os.getenv(
            "EDUGENIE_LOCAL_MODEL", "MBZUAI/LaMini-Flan-T5-783M"
        ).strip(),
    )
