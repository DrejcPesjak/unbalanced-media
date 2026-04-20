from __future__ import annotations

import argparse

from .config import get_settings
from .pipeline import Pipeline, RunOptions


def _parse_max_events(value: str) -> int | None:
    normalized = value.strip().casefold()
    if normalized in {"none", "all"}:
        return None
    return int(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eventregistry-llm")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_shared_filters(command_parser: argparse.ArgumentParser) -> None:
        command_parser.add_argument("--date-start", required=True)
        command_parser.add_argument("--date-end", required=True)
        command_parser.add_argument("--max-events", type=_parse_max_events, default=500)
        command_parser.add_argument("--event-uri-prefix", default="slv")
        command_parser.add_argument("--article-lang", default="slv")

    def add_fetch_options(command_parser: argparse.ArgumentParser) -> None:
        command_parser.add_argument("--min-articles", type=int, default=3)
        command_parser.add_argument("--min-outlet-hits", type=int, default=1)
        command_parser.add_argument("--force-refresh-cache", action="store_true")
        command_parser.add_argument("--clear-output", action="store_true")

    def add_score_options(command_parser: argparse.ArgumentParser) -> None:
        command_parser.add_argument("--clear-output", action="store_true")

    def add_llm_options(command_parser: argparse.ArgumentParser) -> None:
        command_parser.add_argument("--provider", choices=["openai", "gemini"])
        command_parser.add_argument("--model")

    fetch_parser = subparsers.add_parser("fetch", help="Fetch and normalize events/articles without LLM scoring")
    add_shared_filters(fetch_parser)
    add_fetch_options(fetch_parser)

    score_parser = subparsers.add_parser("score", help="Run LLM scoring on saved event files only")
    add_shared_filters(score_parser)
    add_score_options(score_parser)
    add_llm_options(score_parser)

    aggregate_parser = subparsers.add_parser("aggregate", help="Build aggregate outputs from saved event files")
    add_shared_filters(aggregate_parser)

    full_parser = subparsers.add_parser("full", help="Fetch, score, and aggregate in one run")
    add_shared_filters(full_parser)
    add_fetch_options(full_parser)
    add_llm_options(full_parser)

    run_parser = subparsers.add_parser("run", help="Backward-compatible alias for fetch/score/full")
    add_shared_filters(run_parser)
    add_fetch_options(run_parser)
    add_llm_options(run_parser)
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument("--llm-only", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = get_settings()
    provider = getattr(args, "provider", None) or settings.provider
    model = getattr(args, "model", None)
    settings = settings.model_copy(
        update={
            "provider": provider,
            "openai_model": model or settings.openai_model if provider == "openai" else settings.openai_model,
            "gemini_model": model or settings.gemini_model if provider == "gemini" else settings.gemini_model,
        }
    )

    pipeline = Pipeline(settings)
    options = RunOptions(
        date_start=args.date_start,
        date_end=args.date_end,
        max_events=args.max_events,
        min_articles=getattr(args, "min_articles", 3),
        min_outlet_hits=getattr(args, "min_outlet_hits", 1),
        event_uri_prefix=args.event_uri_prefix,
        article_lang=args.article_lang,
        dry_run=getattr(args, "dry_run", False),
        llm_only=getattr(args, "llm_only", False),
        force_refresh_cache=getattr(args, "force_refresh_cache", False),
        clear_output=getattr(args, "clear_output", False),
    )

    if args.command == "fetch":
        written = pipeline.fetch(options)
        print(f"Fetched {len(written)} event files into {settings.output_events_dir}")
    elif args.command == "score":
        written = pipeline.score(options)
        print(f"Scored {len(written)} event files in {settings.output_events_dir}")
    elif args.command == "aggregate":
        path = pipeline.aggregate(options)
        print(f"Wrote aggregates to {path}")
    elif args.command == "full":
        written = pipeline.full(options)
        print(f"Completed full pipeline for {len(written)} scored event files")
    elif args.command == "run":
        written = pipeline.run(options)
        print(f"Wrote {len(written)} event files to {settings.output_events_dir}")


if __name__ == "__main__":
    main()
