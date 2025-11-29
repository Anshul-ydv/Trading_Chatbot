from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from .config import Settings, get_settings
from .utils import get_logger

logger = get_logger(__name__)


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str


class LLMClient:
    """Minimal provider switch for OpenAI-style vs local Ollama models."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.session = requests.Session()
        self.openai_client = None
        if self.settings.openai_api_key and OpenAI:
            self.openai_client = OpenAI(api_key=self.settings.openai_api_key)

    def generate(self, prompt: str) -> Optional[LLMResponse]:
        provider = self.settings.llm_provider
        
        if provider == "ollama":
            return self._generate_with_ollama(prompt)
            
        if provider == "openai":
            return self._generate_with_openai(prompt)
            
        return None

    def _generate_with_openai(self, prompt: str) -> Optional[LLMResponse]:
        if not self.openai_client:
            logger.warning("OpenAI provider requested but client not initialized (check API key)")
            return None
            
        try:
            response = self.openai_client.chat.completions.create(
                model=self.settings.llm_model,
                messages=[
                    {"role": "system", "content": "You are a helpful financial trading assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
            )
            text = response.choices[0].message.content.strip()
            return LLMResponse(text=text, provider="openai", model=self.settings.llm_model)
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return None

    def _generate_with_ollama(self, prompt: str) -> Optional[LLMResponse]:
        url = self.settings.ollama_base_url.rstrip("/") + "/api/generate"
        payload = {
            "model": self.settings.ollama_model,
            "prompt": prompt,
            "stream": False,
        }
        try:
            response = self.session.post(url, json=payload, timeout=self.settings.ollama_timeout)
            response.raise_for_status()
            data = response.json()
            text = data.get("response", "").strip()
            if not text:
                return None
            return LLMResponse(text=text, provider="ollama", model=self.settings.ollama_model)
        except Exception as exc:
            logger.warning("Ollama request failed: %s", exc)
            return None


__all__ = ["LLMClient", "LLMResponse"]
