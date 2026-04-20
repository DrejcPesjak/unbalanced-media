from __future__ import annotations

from openai import OpenAI
from pydantic import BaseModel

from .config import Settings


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def analyze(self, messages: list[dict[str, str]], response_model: type[BaseModel]) -> BaseModel:
        client, model_name = self._build_client()
        completion = client.beta.chat.completions.parse(
            model=model_name,
            messages=messages,
            response_format=response_model,
            temperature=0.2,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise ValueError("LLM returned no parsed structured output")
        return parsed

    def _build_client(self) -> tuple[OpenAI, str]:
        provider = self.settings.provider.lower()
        if provider == "openai":
            if not self.settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY is not configured")
            return OpenAI(api_key=self.settings.openai_api_key), self.settings.openai_model
        if provider == "gemini":
            if not self.settings.gemini_api_key:
                raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is not configured")
            return (
                OpenAI(
                    api_key=self.settings.gemini_api_key,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                ),
                self.settings.gemini_model,
            )
        raise ValueError(f"Unsupported provider: {self.settings.provider}")
