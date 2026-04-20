from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import ConfigDict, Field, BaseModel


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    project_root: Path = PROJECT_ROOT
    provider: str = Field(default_factory=lambda: os.getenv("AGENT_LLM_PROVIDER", "openai").lower())
    openai_api_key: str | None = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    openai_model: str = Field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-5.4-mini"))
    gemini_api_key: str | None = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    gemini_model: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
    eventregistry_api_key: str | None = Field(
        default_factory=lambda: os.getenv("EVENTREGISTRY_API_KEY") or os.getenv("NEWSAPI_API_KEY")
    )
    newsapi_api_key: str | None = Field(default_factory=lambda: os.getenv("NEWSAPI_API_KEY"))
    eventregistry_base_url: str = Field(
        default_factory=lambda: os.getenv("EVENTREGISTRY_BASE_URL", "https://eventregistry.org/api/v1")
    )
    eventregistry_category_uri: list[str] = Field(
        default_factory=lambda: [
            item.strip()
            for item in os.getenv("EVENTREGISTRY_CATEGORY_URI", "news/Politics,dmoz/Society/Politics").split(",")
            if item.strip()
        ]
    )
    eventregistry_location_uri: list[str] = Field(
        default_factory=lambda: [
            item.strip()
            for item in os.getenv(
                "EVENTREGISTRY_LOCATION_URI",
                "http://en.wikipedia.org/wiki/Slovenia,http://en.wikipedia.org/wiki/Ljubljana",
            ).split(",")
            if item.strip()
        ]
    )
    eventregistry_concept_uri: list[str] = Field(
        default_factory=lambda: [
            item.strip()
            for item in os.getenv(
                "EVENTREGISTRY_CONCEPT_URI",
                "http://en.wikipedia.org/wiki/Slovenia,http://en.wikipedia.org/wiki/Political_party",
            ).split(",")
            if item.strip()
        ]
    )
    cache_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "cache" / "articles")
    output_events_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "output" / "events")
    output_aggregates_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "output" / "aggregates")
    party_registry_path: Path = Field(
        default_factory=lambda: Path(
            os.getenv("PARTY_REGISTRY_PATH", str(PROJECT_ROOT / "data" / "party_registry2026.csv"))
        )
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
