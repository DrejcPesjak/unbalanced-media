from __future__ import annotations

from .models import NormalizedArticle, PartyRecord


def build_analysis_messages(
    event_uri: str,
    party: PartyRecord,
    articles_by_outlet: dict[str, list[NormalizedArticle]],
) -> list[dict[str, str]]:
    outlet_sections: list[str] = []
    for outlet_key in sorted(articles_by_outlet):
        article_sections: list[str] = []
        for article in articles_by_outlet[outlet_key]:
            article_sections.append(
                "\n".join(
                    [
                        f"ARTICLE_URI: {article.article_uri}",
                        f"TITLE: {article.title}",
                        f"SUMMARY: {article.summary}",
                        f"BODY: {article.body_text}",
                    ]
                )
            )
        outlet_sections.append(f"OUTLET: {outlet_key}\n" + "\n\n".join(article_sections))

    system_prompt = (
        "You analyze how multiple outlets talk about one Slovenian political party within the same event. "
        "Return structured output only. Compare the outlets to each other within this event so the score scale is internally consistent across outlets. "
        "For each provided outlet, score how the outlet talks about the target party, its president, and its members. "
        'If an outlet does not materially mention the party, set relevance to "none" and sentiment_score to "NaN". '
        "Do not infer wider ideology. Do not score overall event negativity unless it is directed at the target party. "
        "Evidence spans must be short direct excerpts from the provided text."
    )
    user_prompt = (
        f"EVENT URI: {event_uri}\n"
        f"TARGET PARTY CODE: {party.party_code}\n"
        f"TARGET PARTY NAME: {party.party_name}\n"
        f"TARGET SHORT NAME: {party.short_name}\n"
        f"TARGET PRESIDENT: {party.president_name}\n"
        f"TARGET MEMBERS: {', '.join(party.member_names[:50])}\n\n"
        "Analyze all provided outlets for this event. "
        'For each outlet, return one result with sentiment_score as an integer from -5 to +5, or "NaN" if the outlet does not mention the target party in a meaningful way. '
        "Keep the scale relative across outlets in this same event.\n\n"
        "OUTLET ARTICLES:\n"
        + "\n\n".join(outlet_sections)
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
