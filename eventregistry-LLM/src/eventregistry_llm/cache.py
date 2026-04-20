from __future__ import annotations

import hashlib
from pathlib import Path

from pydantic import ValidationError

from .models import CachedArticle, NormalizedArticle


CACHE_VERSION = "2"


class ArticleCache:
    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, article_uri: str) -> Path:
        digest = hashlib.sha256(article_uri.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def get(self, article_uri: str) -> NormalizedArticle | None:
        path = self._path_for(article_uri)
        if not path.exists():
            return None
        raw_json = path.read_text(encoding="utf-8")
        try:
            cached = CachedArticle.model_validate_json(raw_json)
        except ValidationError:
            try:
                return NormalizedArticle.model_validate_json(raw_json)
            except ValidationError:
                return None
        if cached.cache_version != CACHE_VERSION:
            return None
        return cached.article

    def put(self, article: NormalizedArticle) -> None:
        path = self._path_for(article.article_uri)
        cached = CachedArticle(cache_version=CACHE_VERSION, article=article)
        path.write_text(cached.model_dump_json(indent=2), encoding="utf-8")
