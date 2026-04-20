from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


RELEVANCE_VALUES = ("none", "incidental", "meaningful", "primary")
CONFIDENCE_VALUES = ("low", "medium", "high")


class PartyRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    party_code: str
    party_name: str
    short_name: str
    president_name: str
    member_names: list[str] = Field(default_factory=list)
    party_aliases: list[str] = Field(default_factory=list)
    president_aliases: list[str] = Field(default_factory=list)
    member_aliases: list[str] = Field(default_factory=list)

    def all_terms(self) -> list[str]:
        ordered = [
            self.party_code,
            self.party_name,
            self.short_name,
            self.president_name,
            *self.party_aliases,
            *self.president_aliases,
            *self.member_names,
            *self.member_aliases,
        ]
        seen: set[str] = set()
        out: list[str] = []
        for item in ordered:
            value = item.strip()
            if not value:
                continue
            normalized = value.casefold()
            if normalized in seen:
                continue
            seen.add(normalized)
            out.append(value)
        return out


class NormalizedEntity(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str
    uri: str | None = None
    score: float | None = None


class NormalizedArticle(BaseModel):
    model_config = ConfigDict(frozen=True)

    article_uri: str
    event_uri: str
    source_name: str
    source_domain: str
    outlet_key: str
    title: str
    summary: str
    body_text: str
    published_at: str | None = None
    lang: str | None = None
    url: str | None = None
    entities: list[NormalizedEntity] = Field(default_factory=list)
    concepts: list[NormalizedEntity] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def combined_text(self) -> str:
        return "\n\n".join(part for part in [self.title, self.summary, self.body_text] if part)


class EventRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_uri: str
    event_title: str
    event_summary: str = ""
    event_date: str | None = None
    fixed_outlet_articles: list[NormalizedArticle] = Field(default_factory=list)

    @property
    def uri_prefix(self) -> str:
        return self.event_uri.split("-", 1)[0] if "-" in self.event_uri else ""


class PartyMention(BaseModel):
    model_config = ConfigDict(frozen=True)

    party_code: str
    evidence_articles: list[str] = Field(default_factory=list)
    matched_terms: list[str] = Field(default_factory=list)


class OutletSentimentAnalysis(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_uri: str
    outlet_key: str
    party_code: str
    party_name: str
    relevance: Literal["none", "incidental", "meaningful", "primary"]
    sentiment_score: int | Literal["NaN"]
    confidence: Literal["low", "medium", "high"]
    summary: str
    evidence_spans: list[str] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("sentiment_score")
    @classmethod
    def validate_score(cls, value: int | str) -> int | str:
        if value == "NaN":
            return value
        if not isinstance(value, int) or value < -5 or value > 5:
            raise ValueError('sentiment_score must be between -5 and 5 or equal to "NaN"')
        return value


class PartyEventAnalysis(BaseModel):
    model_config = ConfigDict(frozen=True)

    party_code: str
    party_name: str
    outlet_results: list[OutletSentimentAnalysis] = Field(default_factory=list)


class EventAnalysisFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_uri: str
    event_title: str
    event_summary: str = ""
    event_date: str | None = None
    fixed_outlet_articles: list[NormalizedArticle] = Field(default_factory=list)
    detected_parties: list[PartyMention] = Field(default_factory=list)
    party_analyses: list[PartyEventAnalysis] = Field(default_factory=list)
    run_metadata: dict[str, object] = Field(default_factory=dict)


class CachedArticle(BaseModel):
    model_config = ConfigDict(frozen=True)

    cache_version: str
    article: NormalizedArticle


class PartyAggregate(BaseModel):
    model_config = ConfigDict(frozen=True)

    party_code: str
    party_name: str
    outlet_key: str
    event_count: int
    average_sentiment_score: float | None
    score_distribution: dict[str, int]
    confidence_distribution: dict[str, int]
    relevance_distribution: dict[str, int]


class AggregatesFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    generated_at: datetime = Field(default_factory=datetime.utcnow)
    aggregates: list[PartyAggregate]


def safe_filename(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value)[:160]


def event_output_path(base_dir: Path, event_uri: str) -> Path:
    return base_dir / f"{safe_filename(event_uri)}.json"
