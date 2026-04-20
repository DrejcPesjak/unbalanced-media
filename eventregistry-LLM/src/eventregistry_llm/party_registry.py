from __future__ import annotations

import csv
import re
from pathlib import Path

from .models import NormalizedArticle, NormalizedEntity, PartyMention, PartyRecord


def _split_csv_list(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    parts = [item.strip() for item in raw_value.split(",")]
    return [item for item in parts if item]


def load_party_registry(path: Path) -> list[PartyRecord]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    parties: list[PartyRecord] = []
    for row in rows:
        party_code = (row.get("party_code") or row.get("Kratica stranke") or "").strip()
        party_name = (row.get("party_name") or row.get("Ime stranke") or "").strip()
        short_name = (row.get("short_name") or party_code or party_name).strip()
        president_name = (row.get("president_name") or row.get("Predsednik") or "").strip()
        members_value = row.get("member_names") or row.get("Člani") or ""
        if not party_code or not party_name:
            continue
        parties.append(
            PartyRecord(
                party_code=party_code,
                party_name=party_name,
                short_name=short_name,
                president_name=president_name,
                member_names=_split_csv_list(members_value),
                party_aliases=_split_csv_list(row.get("party_aliases")),
                president_aliases=_split_csv_list(row.get("president_aliases")),
                member_aliases=_split_csv_list(row.get("member_aliases")),
            )
        )
    return parties


def _term_patterns(party: PartyRecord) -> list[tuple[str, re.Pattern[str]]]:
    patterns: list[tuple[str, re.Pattern[str]]] = []
    for term in party.all_terms():
        normalized = term.strip()
        if len(normalized) < 2:
            continue
        patterns.append((normalized, re.compile(rf"(?<!\w){re.escape(normalized.casefold())}(?!\w)")))
    return patterns


def enrich_article_entities(article: NormalizedArticle, parties: list[PartyRecord]) -> NormalizedArticle:
    text = article.combined_text.casefold()
    extracted_entities: list[NormalizedEntity] = []
    seen_labels: set[str] = {entity.label.casefold() for entity in article.entities}
    for party in parties:
        for term, pattern in _term_patterns(party):
            if not pattern.search(text):
                continue
            label = term.strip()
            normalized_label = label.casefold()
            if normalized_label in seen_labels:
                continue
            seen_labels.add(normalized_label)
            extracted_entities.append(NormalizedEntity(label=label, uri=f"party:{party.party_code}"))
    if not extracted_entities:
        return article
    return article.model_copy(update={"entities": [*article.entities, *extracted_entities]})


def detect_party_mentions(articles: list[NormalizedArticle], parties: list[PartyRecord]) -> list[PartyMention]:
    mentions: list[PartyMention] = []
    for party in parties:
        matched_terms: set[str] = set()
        evidence_articles: set[str] = set()
        patterns = _term_patterns(party)
        for article in articles:
            text = article.combined_text.casefold()
            entity_labels = {entity.label.casefold() for entity in article.entities + article.concepts}
            for term, pattern in patterns:
                normalized_term = term.casefold()
                if normalized_term in entity_labels or pattern.search(text):
                    matched_terms.add(term)
                    evidence_articles.add(article.article_uri)
        if matched_terms:
            mentions.append(
                PartyMention(
                    party_code=party.party_code,
                    evidence_articles=sorted(evidence_articles),
                    matched_terms=sorted(matched_terms),
                )
            )
    return mentions
