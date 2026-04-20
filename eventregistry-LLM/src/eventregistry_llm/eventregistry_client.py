from __future__ import annotations

from typing import Any

import requests

from .models import EventRecord, NormalizedArticle, NormalizedEntity
from .outlets import identify_outlet


class EventRegistryClient:
    def __init__(self, api_key: str, base_url: str, category_uri: str, location_uri: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.category_uri = self._normalize_category_uri(category_uri)
        self.location_uri = location_uri
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "eventregistry-llm/0.1"})

    @staticmethod
    def _normalize_category_uri(category_uri: str) -> str:
        normalized = category_uri.strip()
        if normalized.casefold() == "politics":
            return "news/Politics"
        return normalized

    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        clean_params = {key: value for key, value in params.items() if value not in (None, "", [])}
        response = self.session.get(
            f"{self.base_url}/{path.lstrip('/')}",
            params={"apiKey": self.api_key, **clean_params},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()

    def get_events(
        self,
        *,
        date_start: str,
        date_end: str,
        max_events: int | None,
        min_articles: int,
        lang: str | None = None,
        source_uris: list[str] | None = None,
    ) -> list[EventRecord]:
        records: list[EventRecord] = []
        page = 1
        page_size = 50
        while True:
            remaining = None if max_events is None else max_events - len(records)
            if remaining is not None and remaining <= 0:
                break
            payload = self._get(
                "event/getEvents",
                categoryUri=self.category_uri,
                locationUri=self.location_uri,
                sourceUri=source_uris,
                lang=lang,
                dateStart=date_start,
                dateEnd=date_end,
                minArticlesInEvent=min_articles,
                sortBy="date",
                maxItems=page_size if remaining is None else min(page_size, remaining),
                page=page,
            )
            events = payload.get("events", {}).get("results", [])
            if not events:
                break
            for item in events:
                records.append(
                    EventRecord(
                        event_uri=item.get("uri", ""),
                        event_title=_coerce_localized_text(item.get("title")),
                        event_summary=_coerce_localized_text(item.get("summary")),
                        event_date=item.get("eventDate") or item.get("date"),
                    )
                )
            total_pages = payload.get("events", {}).get("pages")
            if len(events) < page_size:
                break
            if total_pages is not None and page >= total_pages:
                break
            page += 1
        return [record for record in records if record.event_uri]

    def get_event_articles(self, event_uri: str, *, article_lang: str | None = None) -> list[dict[str, Any]]:
        page = 1
        results: list[dict[str, Any]] = []
        while True:
            payload = self._get(
                "event/getEvent",
                eventUri=event_uri,
                resultType="articles",
                articlesLang=article_lang,
                articlesCount=100,
                articlesPage=page,
                articlesSortBy="date",
                articlesIncludeConcepts=True,
                articlesIncludeCategories=True,
                articlesIncludeSourceTitle=True,
            )
            event_node = payload.get(event_uri, {})
            articles = event_node.get("articles", {}).get("results") or payload.get("articles", {}).get("results") or []
            if not articles:
                break
            results.extend(articles)
            if len(articles) < 100:
                break
            page += 1
        return results


def _extract_entities(article: dict[str, Any], field_name: str) -> list[NormalizedEntity]:
    entities = article.get(field_name) or []
    out: list[NormalizedEntity] = []
    for item in entities:
        label = item.get("label", {}).get("eng") or item.get("label", {}).get("slv") or item.get("label") or item.get("title")
        if not label:
            continue
        out.append(NormalizedEntity(label=label, uri=item.get("uri"), score=item.get("score")))
    return out


def _coerce_localized_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for preferred_key in ("slv", "eng", "hrv", "deu"):
            localized = value.get(preferred_key)
            if isinstance(localized, str) and localized.strip():
                return localized
        for localized in value.values():
            if isinstance(localized, str) and localized.strip():
                return localized
    return ""


def normalize_article(raw_article: dict[str, Any], event_uri: str) -> NormalizedArticle | None:
    source = raw_article.get("source") or {}
    source_name = source.get("title") or raw_article.get("sourceTitle") or ""
    article_url = raw_article.get("url")
    source_domain = source.get("uri") or ""
    outlet_key = identify_outlet(source_name, source_domain, article_url)
    if outlet_key is None:
        return None
    article_uri = raw_article.get("uri") or article_url
    if not article_uri:
        return None
    title = _coerce_localized_text(raw_article.get("title"))
    summary = _coerce_localized_text(raw_article.get("summary"))
    body_text = _coerce_localized_text(raw_article.get("body")) or _coerce_localized_text(raw_article.get("content")) or summary
    return NormalizedArticle(
        article_uri=article_uri,
        event_uri=event_uri,
        source_name=source_name or outlet_key,
        source_domain=source_domain,
        outlet_key=outlet_key,
        title=title,
        summary=summary if isinstance(summary, str) else "",
        body_text=body_text if isinstance(body_text, str) else "",
        published_at=raw_article.get("dateTime") or raw_article.get("date"),
        lang=raw_article.get("lang"),
        url=article_url,
        entities=_extract_entities(raw_article, "entities"),
        concepts=_extract_entities(raw_article, "concepts"),
    )
