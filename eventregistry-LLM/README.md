# eventregistry-LLM

`eventregistry-LLM` collects Slovenian political event coverage from EventRegistry and scores how a fixed set of outlets talk about each political party within the same event.

The analysis unit is:

- `1 event`
- `1 target party`
- `all fixed outlets in that event together`

For each party in an event, the LLM sees the grouped outlet coverage at the same time and returns one structured score per outlet. That keeps the `[-5, +5]` scale relative inside the event instead of scoring each outlet in isolation.

## What it does

The pipeline has two separable stages:

1. fetch and normalize events/articles
2. analyze saved event files with the LLM

That split matters because you usually want to:

- fetch once
- inspect the saved event files
- rerun only the LLM stage while iterating on prompts/models

## Fixed outlets

The project keeps only these outlets:

- `rtv`
- `24ur`
- `nova24tv`
- `mladina`
- `dnevnik`
- `vecer`
- `delo`
- `siol`
- `svet24`

Matching is strict by domain/source identity. Similar-but-different sites like `dnevnik.hr`, `primorske.svet24.si`, or `slovenskenovice.delo.si` are excluded.

## Data flow

### 1. Event discovery

The pipeline queries EventRegistry for:

- `locationUri = Slovenia`
- `categoryUri = news/Politics`

It also pushes some filtering server-side:

- `sourceUri` limited to the fixed outlet domains
- `lang = slv` on event search
- `articlesLang = slv` on event article fetch

By default the CLI also keeps only event URIs with prefix `slv`.

### 2. Article collection and cache

For each matching event, the pipeline fetches event articles from EventRegistry and caches each article by article URI.

Article cache:

- [cache/articles](/home/drew99/Projects/unbalanced-media/eventregistry-LLM/cache/articles)

Cache behavior:

- cached articles are always preferred
- no already-known article is fetched again
- `--force-refresh-cache` is the only thing that bypasses that

### 3. Party detection

Party detection is registry-driven and regex-based.

The current registry is:

- [data/party_registry2026.csv](/home/drew99/Projects/unbalanced-media/eventregistry-LLM/data/party_registry2026.csv:1)

Each party entry can contribute:

- `Kratica stranke`
- `Ime stranke`
- `short_name`
- `Predsednik`
- `Člani`
- `party_aliases`
- `president_aliases`
- `member_aliases`

The pipeline uses those terms to enrich article `entities` locally, because EventRegistry often returns no usable `entities` or `concepts` for these articles.

### 4. LLM scoring

For each event:

- collect all detected parties first
- then run `1 party at a time`
- in each LLM call, provide `all outlets for that event`

The LLM returns a structured outlet vector:

- one JSON object per outlet
- one `sentiment_score` per outlet
- score is integer `-5..5` or `"NaN"`
- `"NaN"` means the outlet does not materially mention that party

The output also includes:

- `relevance`
- `confidence`
- `summary`
- `evidence_spans`
- `notes`

## Setup

From the repo root:

```bash
cd eventregistry-LLM
python3 -m venv .venv
source .venv/bin/activate
pip install python-dotenv pydantic requests openai
python setup.py develop
cp .env.example .env
```

Then fill in `.env`.

Typical OpenAI setup:

- `EVENTREGISTRY_API_KEY`
- `OPENAI_API_KEY`
- `AGENT_LLM_PROVIDER=openai`

Typical Gemini setup:

- `EVENTREGISTRY_API_KEY`
- `GEMINI_API_KEY`
- `AGENT_LLM_PROVIDER=gemini`

Example config:

- [.env.example](/home/drew99/Projects/unbalanced-media/eventregistry-LLM/.env.example:1)

## Commands

The CLI is split into explicit stages:

- `fetch`
  Query EventRegistry, filter to the fixed outlet set, normalize articles, detect candidate parties, and write event JSON files.
- `score`
  Read saved event JSON files and run only the LLM stage.
- `aggregate`
  Rebuild aggregate outputs from saved event JSON files only.
- `full`
  Run `fetch`, then `score`, then `aggregate`.
- `run`
  Backward-compatible alias for the older `--dry-run` and `--llm-only` workflow.

### 1. Fetch only

This builds clean event files without any LLM calls.

```bash
cd /home/drew99/Projects/unbalanced-media/eventregistry-LLM
source .venv/bin/activate

eventregistry-llm fetch \
  --date-start 2026-04-01 \
  --date-end 2026-04-20 \
  --max-events 500 \
  --force-refresh-cache \
  --clear-output
```

Use this when:

- the party registry changed
- outlet matching changed
- you want a clean dataset rebuild

To fetch another date range later without wiping the first one, omit `--clear-output`:

```bash
eventregistry-llm fetch \
  --date-start 2026-03-01 \
  --date-end 2026-03-31 \
  --max-events none
```

### 2. Score only

This does no EventRegistry fetching. It only reads the already-saved event files from `output/events` and writes/updates LLM analyses inside them.

```bash
cd /home/drew99/Projects/unbalanced-media/eventregistry-LLM
source .venv/bin/activate

eventregistry-llm score \
  --date-start 2026-04-01 \
  --date-end 2026-04-20 \
  --max-events none
```

Use this when:

- you already fetched data
- you want to rerun scores with a different model
- you are iterating on prompt/schema behavior

### 3. Aggregate only

This reads saved event JSON files and rebuilds the aggregate summary without any fetching or LLM calls.

```bash
cd /home/drew99/Projects/unbalanced-media/eventregistry-LLM
source .venv/bin/activate

eventregistry-llm aggregate \
  --date-start 2026-03-01 \
  --date-end 2026-04-20 \
  --max-events none
```

### 4. Full run

This fetches, scores, and aggregates in one pass.

```bash
cd /home/drew99/Projects/unbalanced-media/eventregistry-LLM
source .venv/bin/activate

eventregistry-llm full \
  --date-start 2026-04-01 \
  --date-end 2026-04-20 \
  --max-events 500 \
  --force-refresh-cache \
  --clear-output
```

If you want `fetch + score` but no aggregate, run two commands:

```bash
eventregistry-llm fetch --date-start 2026-04-01 --date-end 2026-04-20 --max-events none
eventregistry-llm score --date-start 2026-04-01 --date-end 2026-04-20 --max-events none
```

If you want `score + aggregate`, run:

```bash
eventregistry-llm score --date-start 2026-04-01 --date-end 2026-04-20 --max-events none
eventregistry-llm aggregate --date-start 2026-04-01 --date-end 2026-04-20 --max-events none
```

### 5. Run with Gemini

```bash
cd /home/drew99/Projects/unbalanced-media/eventregistry-LLM
source .venv/bin/activate

eventregistry-llm score \
  --date-start 2026-04-01 \
  --date-end 2026-04-20 \
  --max-events none \
  --provider gemini \
  --model gemini-2.0-flash
```

### 6. Fetch all events in a date range

`--max-events none` means paginate until all matching events in the date range are consumed.

```bash
eventregistry-llm fetch \
  --date-start 2026-04-01 \
  --date-end 2026-04-20 \
  --max-events none
```

### 7. Backward-compatible `run`

The old command still works:

```bash
eventregistry-llm run --date-start 2026-04-01 --date-end 2026-04-20 --max-events none --dry-run
eventregistry-llm run --date-start 2026-04-01 --date-end 2026-04-20 --max-events none --llm-only
eventregistry-llm run --date-start 2026-04-01 --date-end 2026-04-20 --max-events none
```

### 8. CLI help

```bash
eventregistry-llm --help
eventregistry-llm fetch --help
eventregistry-llm score --help
eventregistry-llm aggregate --help
eventregistry-llm full --help
```

## Important flags

- `--force-refresh-cache`
  Ignore cached article payloads and refetch articles.

- `--clear-output`
  Remove current output files before writing new ones.

- `--max-events 500`
  Default limit.

- `--max-events none`
  Fetch or analyze all matching events between the dates.

- `--event-uri-prefix slv`
  Keep only Slovenian event cluster URIs by default.

- `--article-lang slv`
  Keep only Slovenian-language articles by default.

## Output files

Per-event outputs:

- [output/events](/home/drew99/Projects/unbalanced-media/eventregistry-LLM/output/events)

Each event file contains:

- event metadata
- normalized fixed-outlet articles
- locally enriched `entities`
- detected parties
- per-party outlet score vectors

Aggregates:

- [output/aggregates/party_outlet_aggregates.json](/home/drew99/Projects/unbalanced-media/eventregistry-LLM/output/aggregates/party_outlet_aggregates.json)
- [output/aggregates/party_outlet_sentiment_table.csv](/home/drew99/Projects/unbalanced-media/eventregistry-LLM/output/aggregates/party_outlet_sentiment_table.csv)
- [output/aggregates/party_outlet_sentiment_heatmap.svg](/home/drew99/Projects/unbalanced-media/eventregistry-LLM/output/aggregates/party_outlet_sentiment_heatmap.svg)

That aggregate file summarizes:

- `party x outlet`
- number of event analyses
- mean score
- score distribution
- relevance distribution
- confidence distribution

The focused CSV table and SVG heatmap keep only this party order:

- `levica`
- `pirati`
- `sd`
- `svoboda`
- `demokrati`
- `nsi`
- `resnica`
- `sds`

Sample scored file:

- [output/sample_llm_results_slv-123856.json](/home/drew99/Projects/unbalanced-media/eventregistry-LLM/output/sample_llm_results_slv-123856.json:1)

## Recommended workflow

Normal cycle:

1. update [party_registry2026.csv](/home/drew99/Projects/unbalanced-media/eventregistry-LLM/data/party_registry2026.csv:1)
2. run `fetch --force-refresh-cache --clear-output`
3. inspect a few event JSON files
4. run `score`
5. inspect `output/events` and `output/aggregates`

If you change:

- registry aliases
- outlet matching
- article normalization

then do a fresh fetch run with:

- `--force-refresh-cache`
- `--clear-output`

## Current limitations

### EventRegistry article bodies are often partial

The project currently uses the article text returned by EventRegistry. If EventRegistry gives a partial body, the saved article body is partial too.

There is currently no direct fetch from the original article URL.

### EventRegistry concepts/entities are often empty

The API request for concepts is valid, but many returned articles still have no `concepts` data. That is why the project relies on local registry-driven text matching.

### Regex matching can produce false positives

This is deliberate for now. Broader alias coverage improves recall, and the LLM can return `"NaN"` when an outlet does not actually discuss the party in a meaningful way.

### Scores are event-relative, not global truth

The LLM is asked to compare outlets within one event. A `+2` in one event and a `+2` in another event are still comparable only loosely; the aggregate output is where repeated event-level signals matter.
