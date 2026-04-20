from pathlib import Path

from eventregistry_llm.party_registry import enrich_article_entities, load_party_registry
from eventregistry_llm.models import NormalizedArticle


def test_load_legacy_party_registry() -> None:
    registry_path = Path(__file__).resolve().parents[1] / "data" / "party_registry2026.csv"
    parties = load_party_registry(registry_path)
    assert parties
    svoboda = next(party for party in parties if party.party_code == "GS")
    assert svoboda.president_name
    assert svoboda.member_names


def test_alias_enrichment_matches_partial_party_name() -> None:
    registry_path = Path(__file__).resolve().parents[1] / "data" / "party_registry2026.csv"
    parties = load_party_registry(registry_path)
    article = NormalizedArticle(
        article_uri="article-1",
        event_uri="event-1",
        source_name="Delo",
        source_domain="delo.si",
        outlet_key="delo",
        title="Nova Slovenija želi v vlado",
        summary="",
        body_text="Po mnenju Logarja bi Nova Slovenija lahko sodelovala.",
    )
    enriched = enrich_article_entities(article, parties)
    assert "Nova Slovenija" in [entity.label for entity in enriched.entities]
