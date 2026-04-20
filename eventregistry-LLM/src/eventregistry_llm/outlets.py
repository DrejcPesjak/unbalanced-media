from __future__ import annotations

from urllib.parse import urlparse


FIXED_OUTLETS: dict[str, dict[str, tuple[str, ...]]] = {
    "rtv": {
        "domains": ("rtvslo.si", "www.rtvslo.si", "rtvslovenija.si", "www.rtvslovenija.si"),
        "names": ("RTV Slovenija", "rtvslo.si"),
    },
    "24ur": {
        "domains": ("24ur.com", "www.24ur.com"),
        "names": ("24ur", "24ur.com"),
    },
    "nova24tv": {
        "domains": ("nova24tv.si", "www.nova24tv.si"),
        "names": ("Nova24TV", "nova24tv.si"),
    },
    "mladina": {
        "domains": ("mladina.si", "www.mladina.si"),
        "names": ("Mladina", "mladina.si"),
    },
    "dnevnik": {
        "domains": ("dnevnik.si", "www.dnevnik.si"),
        "names": ("Dnevnik", "dnevnik.si"),
    },
    "vecer": {
        "domains": ("vecer.com", "www.vecer.com"),
        "names": ("Večer", "vecer.com"),
    },
    "delo": {
        "domains": ("delo.si", "www.delo.si"),
        "names": ("Delo", "delo.si"),
    },
    "siol": {
        "domains": ("siol.net", "www.siol.net"),
        "names": ("Siol.net", "siol.net", "SioLNET"),
    },
    "svet24": {
        "domains": ("svet24.si", "www.svet24.si", "novice.svet24.si"),
        "names": ("Svet24", "svet24.si"),
    },
}


def _normalize(value: str | None) -> str:
    return (value or "").strip().casefold()


def query_source_uris() -> list[str]:
    return [matcher["domains"][0] for matcher in FIXED_OUTLETS.values()]


def identify_outlet(source_name: str | None, source_domain: str | None, article_url: str | None) -> str | None:
    normalized_name = _normalize(source_name)
    normalized_domains = {
        _normalize(source_domain),
        _normalize(urlparse(article_url).netloc),
    }
    for outlet_key, matcher in FIXED_OUTLETS.items():
        allowed_domains = {_normalize(item) for item in matcher["domains"]}
        allowed_names = {_normalize(item) for item in matcher["names"]}
        if normalized_name in allowed_names:
            return outlet_key
        if any(domain in allowed_domains for domain in normalized_domains if domain):
            return outlet_key
    return None
