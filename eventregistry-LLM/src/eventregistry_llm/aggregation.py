from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

from .models import AggregatesFile, EventAnalysisFile, OutletSentimentAnalysis, PartyAggregate
from .outlets import FIXED_OUTLETS


FOCUSED_PARTIES: tuple[tuple[str, str], ...] = (
    ("Levica", "levica"),
    ("Pirati", "pirati"),
    ("SD", "sd"),
    ("GS", "svoboda"),
    ("Demokrati", "demokrati"),
    ("NSi", "nsi"),
    ("Resni.ca", "resnica"),
    ("SDS", "sds"),
)


def build_aggregates(event_files: list[Path]) -> AggregatesFile:
    grouped: dict[tuple[str, str, str], list[OutletSentimentAnalysis]] = defaultdict(list)
    for event_path in event_files:
        parsed = EventAnalysisFile.model_validate_json(event_path.read_text(encoding="utf-8"))
        for party_analysis in parsed.party_analyses:
            for result in party_analysis.outlet_results:
                grouped[(party_analysis.party_code, party_analysis.party_name, result.outlet_key)].append(result)

    aggregates: list[PartyAggregate] = []
    for (party_code, party_name, outlet_key), results in sorted(grouped.items()):
        score_distribution = Counter(str(result.sentiment_score) for result in results)
        confidence_distribution = Counter(result.confidence for result in results)
        relevance_distribution = Counter(result.relevance for result in results)
        numeric_scores = [result.sentiment_score for result in results if isinstance(result.sentiment_score, int)]
        average = round(sum(numeric_scores) / len(numeric_scores), 3) if numeric_scores else None
        aggregates.append(
            PartyAggregate(
                party_code=party_code,
                party_name=party_name,
                outlet_key=outlet_key,
                event_count=len(results),
                average_sentiment_score=average,
                score_distribution=dict(score_distribution),
                confidence_distribution=dict(confidence_distribution),
                relevance_distribution=dict(relevance_distribution),
            )
        )
    return AggregatesFile(aggregates=aggregates)


def write_aggregates(path: Path, aggregates: AggregatesFile) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(aggregates.model_dump_json(indent=2), encoding="utf-8")


def write_aggregate_artifacts(base_dir: Path, aggregates: AggregatesFile) -> dict[str, Path]:
    base_dir.mkdir(parents=True, exist_ok=True)
    json_path = base_dir / "party_outlet_aggregates.json"
    write_aggregates(json_path, aggregates)

    matrix = build_focused_sentiment_matrix(aggregates)
    csv_path = base_dir / "party_outlet_sentiment_table.csv"
    svg_path = base_dir / "party_outlet_sentiment_heatmap.svg"
    write_sentiment_table(csv_path, matrix)
    write_sentiment_heatmap(svg_path, matrix)
    return {
        "json": json_path,
        "table_csv": csv_path,
        "heatmap_svg": svg_path,
    }


def build_focused_sentiment_matrix(aggregates: AggregatesFile) -> list[dict[str, object]]:
    rows_by_outlet: dict[str, dict[str, object]] = {
        outlet_key: {"outlet": outlet_key} for outlet_key in FIXED_OUTLETS
    }

    for aggregate in aggregates.aggregates:
        row = rows_by_outlet.get(aggregate.outlet_key)
        if row is None:
            continue
        for party_code, label in FOCUSED_PARTIES:
            if aggregate.party_code.casefold() == party_code.casefold():
                row[label] = aggregate.average_sentiment_score
                break

    ordered_rows: list[dict[str, object]] = []
    for outlet_key in FIXED_OUTLETS:
        row = rows_by_outlet[outlet_key]
        row["outlet"] = outlet_key
        for _, label in FOCUSED_PARTIES:
            row.setdefault(label, None)
        ordered_rows.append(row)
    return ordered_rows


def write_sentiment_table(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = ["outlet", *(label for _, label in FOCUSED_PARTIES)]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            normalized = {key: _format_score(row.get(key)) if key != "outlet" else row.get(key, "") for key in fieldnames}
            writer.writerow(normalized)


def write_sentiment_heatmap(path: Path, rows: list[dict[str, object]]) -> None:
    parties = [label for _, label in FOCUSED_PARTIES]
    cell_width = 84
    cell_height = 40
    left_margin = 110
    top_margin = 85
    width = left_margin + cell_width * len(parties) + 20
    height = top_margin + cell_height * len(rows) + 20

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#faf8f4" />',
        '<style>text{font-family:Arial,sans-serif;fill:#222} .label{font-size:14px;font-weight:700} .celltext{font-size:13px;font-weight:700;text-anchor:middle;dominant-baseline:middle} .rowlabel{font-size:14px;font-weight:700} .footer{font-size:12px;fill:#555}</style>',
        '<text x="16" y="28" class="label">Average sentiment score by outlet and party</text>',
        '<text x="16" y="48" class="footer">Scores come from aggregate event-level LLM analyses. Blank means no numeric score.</text>',
    ]

    for column_index, party_label in enumerate(parties):
        x = left_margin + column_index * cell_width + cell_width / 2
        parts.append(f'<text x="{x}" y="{top_margin - 18}" class="label" text-anchor="middle">{escape(party_label)}</text>')

    for row_index, row in enumerate(rows):
        y = top_margin + row_index * cell_height
        parts.append(f'<text x="16" y="{y + 25}" class="rowlabel">{escape(str(row["outlet"]))}</text>')
        for column_index, party_label in enumerate(parties):
            x = left_margin + column_index * cell_width
            value = row.get(party_label)
            fill = _score_to_color(value)
            display = _format_score(value)
            parts.append(
                f'<rect x="{x}" y="{y}" width="{cell_width - 4}" height="{cell_height - 4}" rx="6" ry="6" fill="{fill}" stroke="#d7d1c7" />'
            )
            text_color = "#ffffff" if isinstance(value, (int, float)) and abs(float(value)) >= 2.5 else "#222222"
            parts.append(
                f'<text x="{x + (cell_width - 4) / 2}" y="{y + (cell_height - 4) / 2 + 1}" class="celltext" fill="{text_color}">{escape(display)}</text>'
            )

    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _format_score(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def _score_to_color(value: object) -> str:
    if not isinstance(value, (int, float)):
        return "#efebe3"
    score = max(-5.0, min(5.0, float(value)))
    if score < 0:
        intensity = abs(score) / 5.0
        return _interpolate_color("#f8d8d2", "#b93a32", intensity)
    if score > 0:
        intensity = score / 5.0
        return _interpolate_color("#dcefd9", "#2d7f3b", intensity)
    return "#f3f0e9"


def _interpolate_color(start: str, end: str, factor: float) -> str:
    factor = max(0.0, min(1.0, factor))
    start_rgb = tuple(int(start[index:index + 2], 16) for index in (1, 3, 5))
    end_rgb = tuple(int(end[index:index + 2], 16) for index in (1, 3, 5))
    mixed = tuple(round(start_rgb[i] + (end_rgb[i] - start_rgb[i]) * factor) for i in range(3))
    return "#" + "".join(f"{component:02x}" for component in mixed)
