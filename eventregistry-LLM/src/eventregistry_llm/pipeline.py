from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

from .aggregation import build_aggregates, write_aggregate_artifacts
from .cache import ArticleCache
from .config import Settings
from .eventregistry_client import EventRegistryClient, normalize_article
from .llm import LLMClient
from .models import EventAnalysisFile, EventRecord, OutletSentimentAnalysis, PartyEventAnalysis, event_output_path
from .outlets import query_source_uris
from .party_registry import detect_party_mentions, enrich_article_entities, load_party_registry
from .prompts import build_analysis_messages

OUTPUT_VERSION = "3"


@dataclass(frozen=True)
class RunOptions:
    date_start: str
    date_end: str
    max_events: int | None
    min_articles: int
    min_outlet_hits: int
    event_uri_prefix: str | None
    article_lang: str | None
    dry_run: bool
    force_refresh_cache: bool
    clear_output: bool
    llm_only: bool


class Pipeline:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        if not self.settings.eventregistry_api_key:
            raise ValueError("EVENTREGISTRY_API_KEY or NEWSAPI_API_KEY must be configured")
        self.client = EventRegistryClient(
            api_key=self.settings.eventregistry_api_key,
            base_url=self.settings.eventregistry_base_url,
            category_uri=self.settings.eventregistry_category_uri,
            location_uri=self.settings.eventregistry_location_uri,
            concept_uri=self.settings.eventregistry_concept_uri,
        )
        self.cache = ArticleCache(self.settings.cache_dir)
        self.parties = load_party_registry(self.settings.party_registry_path)
        self.llm = LLMClient(settings)

    def run(self, options: RunOptions) -> list[Path]:
        if options.llm_only:
            return self.score(options)
        if options.dry_run:
            return self.fetch(options)
        return self.full(options)

    def fetch(self, options: RunOptions) -> list[Path]:
        self.settings.output_events_dir.mkdir(parents=True, exist_ok=True)
        self.settings.output_aggregates_dir.mkdir(parents=True, exist_ok=True)
        if options.clear_output:
            self._clear_directories(self.settings.output_events_dir, self.settings.output_aggregates_dir)

        print(
            f"[fetch] Querying events for {options.date_start}..{options.date_end}"
            f" (max={options.max_events if options.max_events is not None else 'all'})"
        )
        events = self.client.get_events(
            date_start=options.date_start,
            date_end=options.date_end,
            max_events=options.max_events,
            min_articles=options.min_articles,
            lang=options.article_lang,
        )
        print(f"[fetch] Retrieved {len(events)} candidate events from EventRegistry")

        written_files: list[Path] = []
        allowed_prefixes = _allowed_event_prefixes(options.event_uri_prefix)
        for index, event in enumerate(events, start=1):
            if allowed_prefixes and event.uri_prefix not in allowed_prefixes:
                continue
            print(f"[fetch] {index}/{len(events)} {event.event_uri}")
            path = self._process_event(event, options, analyze=False)
            if path is not None:
                written_files.append(path)
        print(f"[fetch] Wrote {len(written_files)} event files")
        return written_files

    def score(self, options: RunOptions) -> list[Path]:
        self.settings.output_events_dir.mkdir(parents=True, exist_ok=True)
        self.settings.output_aggregates_dir.mkdir(parents=True, exist_ok=True)
        if options.clear_output:
            self._clear_directories(self.settings.output_aggregates_dir)

        event_files = self._iter_cached_event_files(options)
        print(
            f"[score] Selected {len(event_files)} cached event files for {options.date_start}..{options.date_end}"
        )
        written_files: list[Path] = []
        for index, path in enumerate(event_files, start=1):
            print(f"[score] {index}/{len(event_files)} {path.stem}")
            written = self._analyze_cached_event_file(path, options)
            if written is not None:
                written_files.append(written)
        print(f"[score] Updated {len(written_files)} event files with LLM output")
        return written_files

    def aggregate(self, options: RunOptions) -> Path:
        self.settings.output_aggregates_dir.mkdir(parents=True, exist_ok=True)
        event_files = self._iter_cached_event_files(options)
        print(
            f"[aggregate] Building aggregates from {len(event_files)} event files"
            f" for {options.date_start}..{options.date_end}"
        )
        aggregates = build_aggregates(event_files)
        artifact_paths = write_aggregate_artifacts(self.settings.output_aggregates_dir, aggregates)
        print(f"[aggregate] Wrote {len(aggregates.aggregates)} party-outlet rows to {artifact_paths['json']}")
        print(f"[aggregate] Wrote focused sentiment table to {artifact_paths['table_csv']}")
        print(f"[aggregate] Wrote heatmap to {artifact_paths['heatmap_svg']}")
        return artifact_paths["json"]

    def full(self, options: RunOptions) -> list[Path]:
        fetched = self.fetch(options)
        if not fetched:
            print("[full] No fetched event files to score")
            self.aggregate(options)
            return fetched

        score_options = RunOptions(
            date_start=options.date_start,
            date_end=options.date_end,
            max_events=options.max_events,
            min_articles=options.min_articles,
            min_outlet_hits=options.min_outlet_hits,
            event_uri_prefix=options.event_uri_prefix,
            article_lang=options.article_lang,
            dry_run=False,
            force_refresh_cache=options.force_refresh_cache,
            clear_output=False,
            llm_only=True,
        )
        scored = self.score(score_options)
        self.aggregate(score_options)
        return scored

    def _clear_directories(self, *directories: Path) -> None:
        for directory in directories:
            if directory.exists():
                shutil.rmtree(directory)
            directory.mkdir(parents=True, exist_ok=True)

    def _iter_cached_event_files(self, options: RunOptions) -> list[Path]:
        paths = sorted(self.settings.output_events_dir.glob("*.json"))
        selected: list[Path] = []
        allowed_prefixes = _allowed_event_prefixes(options.event_uri_prefix)
        for path in paths:
            parsed = EventAnalysisFile.model_validate_json(path.read_text(encoding="utf-8"))
            if allowed_prefixes and parsed.event_uri.split("-", 1)[0].casefold() not in allowed_prefixes:
                continue
            if parsed.event_date and not (options.date_start <= parsed.event_date <= options.date_end):
                continue
            selected.append(path)
            if options.max_events is not None and len(selected) >= options.max_events:
                break
        return selected

    def _analyze_cached_event_file(self, path: Path, options: RunOptions) -> Path | None:
        cached = EventAnalysisFile.model_validate_json(path.read_text(encoding="utf-8"))
        articles = [article for article in cached.fixed_outlet_articles if not options.article_lang or article.lang == options.article_lang]
        mentions = detect_party_mentions(articles, self.parties)
        if not mentions:
            return None
        if not self._has_multi_entity_article(articles):
            return None
        party_analyses = self._build_party_analyses(cached.event_uri, mentions, articles)
        updated = EventAnalysisFile(
            event_uri=cached.event_uri,
            event_title=cached.event_title,
            event_summary=cached.event_summary,
            event_date=cached.event_date,
            fixed_outlet_articles=articles,
            detected_parties=mentions,
            party_analyses=party_analyses,
            run_metadata={
                **cached.run_metadata,
                "provider": self.settings.provider,
                "model": self.settings.openai_model if self.settings.provider == "openai" else self.settings.gemini_model,
                "dry_run": False,
                "output_version": OUTPUT_VERSION,
            },
        )
        path.write_text(updated.model_dump_json(indent=2), encoding="utf-8")
        return path

    def _process_event(self, event: EventRecord, options: RunOptions, *, analyze: bool) -> Path | None:
        output_path = event_output_path(self.settings.output_events_dir, event.event_uri)
        cached_output = None
        if output_path.exists() and not options.force_refresh_cache:
            cached_output = EventAnalysisFile.model_validate_json(output_path.read_text(encoding="utf-8"))
            if cached_output.run_metadata.get("output_version") != OUTPUT_VERSION:
                cached_output = None

        if cached_output is not None:
            normalized_articles = [
                article
                for article in cached_output.fixed_outlet_articles
                if (not options.article_lang or article.lang == options.article_lang) and article.body_text.strip()
            ]
        else:
            raw_articles = self.client.get_event_articles(
                event.event_uri,
                article_lang=options.article_lang,
                source_uris=query_source_uris(),
            )
            normalized_articles = []
            seen_article_uris: set[str] = set()
            for raw_article in raw_articles:
                article_uri = raw_article.get("uri") or raw_article.get("url")
                if not article_uri or article_uri in seen_article_uris:
                    continue
                seen_article_uris.add(article_uri)
                cached = None if options.force_refresh_cache or not article_uri else self.cache.get(article_uri)
                if cached is not None:
                    normalized = cached.model_copy(update={"event_uri": event.event_uri})
                else:
                    normalized = normalize_article(raw_article, event.event_uri)
                    if normalized is None:
                        continue
                    normalized = enrich_article_entities(normalized, self.parties)
                    self.cache.put(normalized)
                if options.article_lang and normalized.lang != options.article_lang:
                    continue
                if not normalized.body_text.strip():
                    continue
                normalized_articles.append(normalized)

        if len({article.outlet_key for article in normalized_articles}) < options.min_outlet_hits:
            return None

        mentions = detect_party_mentions(normalized_articles, self.parties)
        if not mentions:
            return None
        if analyze and not self._has_multi_entity_article(normalized_articles):
            return None

        analyses = [] if not analyze else self._build_party_analyses(event.event_uri, mentions, normalized_articles)
        output = EventAnalysisFile(
            event_uri=event.event_uri,
            event_title=event.event_title,
            event_summary=event.event_summary,
            event_date=event.event_date,
            fixed_outlet_articles=normalized_articles,
            detected_parties=mentions,
            party_analyses=analyses,
            run_metadata={
                "provider": self.settings.provider,
                "model": self.settings.openai_model if self.settings.provider == "openai" else self.settings.gemini_model,
                "dry_run": not analyze,
                "output_version": OUTPUT_VERSION,
            },
        )
        output_path.write_text(output.model_dump_json(indent=2), encoding="utf-8")
        return output_path

    def _build_party_analyses(
        self,
        event_uri: str,
        mentions,
        normalized_articles,
    ) -> list[PartyEventAnalysis]:
        analyses: list[PartyEventAnalysis] = []
        grouped_articles: dict[str, list] = {}
        for article in normalized_articles:
            grouped_articles.setdefault(article.outlet_key, []).append(article)
        for mention in mentions:
            party = next(party for party in self.parties if party.party_code == mention.party_code)
            messages = build_analysis_messages(event_uri, party, grouped_articles)
            llm_analysis = self.llm.analyze(messages, PartyEventAnalysis)
            analysis = self._normalize_party_analysis(event_uri, party.party_code, party.party_name, grouped_articles, llm_analysis)
            analyses.append(analysis)
        return analyses

    def _normalize_party_analysis(
        self,
        event_uri: str,
        party_code: str,
        party_name: str,
        grouped_articles: dict[str, list],
        llm_analysis: PartyEventAnalysis,
    ) -> PartyEventAnalysis:
        returned = {result.outlet_key: result for result in llm_analysis.outlet_results}
        outlet_results: list[OutletSentimentAnalysis] = []
        for outlet_key in sorted(grouped_articles):
            result = returned.get(outlet_key)
            if result is None:
                outlet_results.append(
                    OutletSentimentAnalysis(
                        event_uri=event_uri,
                        outlet_key=outlet_key,
                        party_code=party_code,
                        party_name=party_name,
                        relevance="none",
                        sentiment_score="NaN",
                        confidence="low",
                        summary="Missing from model output.",
                        evidence_spans=[],
                        notes="Filled by pipeline because the model omitted this outlet.",
                    )
                )
                continue
            outlet_results.append(
                result.model_copy(
                    update={
                        "event_uri": event_uri,
                        "outlet_key": outlet_key,
                        "party_code": party_code,
                        "party_name": party_name,
                    }
                )
            )
        return PartyEventAnalysis(
            party_code=party_code,
            party_name=party_name,
            outlet_results=outlet_results,
        )

    def _has_multi_entity_article(self, articles) -> bool:
        for article in articles:
            local_entity_count = sum(1 for entity in article.entities if (entity.uri or "").startswith("party:"))
            if local_entity_count >= 2:
                return True
        return False


def _allowed_event_prefixes(raw_value: str | None) -> set[str]:
    if not raw_value:
        return set()
    return {
        item.strip().casefold()
        for item in raw_value.split(",")
        if item.strip()
    }
