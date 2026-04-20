from pathlib import Path

from eventregistry_llm.aggregation import build_aggregates
from eventregistry_llm.cache import ArticleCache
from eventregistry_llm.models import EventAnalysisFile, NormalizedArticle, OutletSentimentAnalysis, PartyEventAnalysis


def test_article_cache_round_trip(tmp_path: Path) -> None:
    cache = ArticleCache(tmp_path)
    article = NormalizedArticle(
        article_uri="article-1",
        event_uri="event-1",
        source_name="RTV Slovenija",
        source_domain="rtvslo.si",
        outlet_key="rtv",
        title="Title",
        summary="Summary",
        body_text="Body",
    )
    cache.put(article)
    loaded = cache.get("article-1")
    assert loaded == article


def test_build_aggregates(tmp_path: Path) -> None:
    event_file = EventAnalysisFile(
        event_uri="event-1",
        event_title="Event",
        party_analyses=[
            PartyEventAnalysis(
                party_code="SDS",
                party_name="SDS",
                outlet_results=[
                    OutletSentimentAnalysis(
                        event_uri="event-1",
                        outlet_key="rtv",
                        party_code="SDS",
                        party_name="SDS",
                        relevance="meaningful",
                        sentiment_score=-2,
                        confidence="medium",
                        summary="Negative framing",
                        evidence_spans=["snippet"],
                    )
                ],
            )
        ],
    )
    path = tmp_path / "event.json"
    path.write_text(event_file.model_dump_json(indent=2), encoding="utf-8")
    aggregates = build_aggregates([path])
    assert len(aggregates.aggregates) == 1
    aggregate = aggregates.aggregates[0]
    assert aggregate.average_sentiment_score == -2.0
    assert aggregate.score_distribution["-2"] == 1
