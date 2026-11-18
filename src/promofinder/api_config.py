"""Backend-only model routes for generation and semantic review.

Provider, model ID, endpoint, and tuning values are read from the matching
environment variables. Keep credentials in the local ``.env`` file rather
than storing them in source code.
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

ROOT = Path(__file__).resolve().parents[2]

try:
    from dotenv import dotenv_values
except ImportError:
    dotenv_values = None


@dataclass(frozen=True)
class ModelSettings:
    provider: str
    model: str
    base_url: str
    api_key: str
    timeout_seconds: int = 120
    max_api_retries: int = 3
    temperature: float = 0.2


@dataclass(frozen=True)
class ApiConfig:
    candidate_model: ModelSettings
    ranking_model: ModelSettings


def load_environment(environ: Optional[Mapping[str, str]] = None) -> dict:
    """Read the current .env file, with process environment values taking priority."""
    if environ is not None:
        return dict(environ)
    source = {}
    if dotenv_values is not None:
        source = {key: value for key, value in dotenv_values(ROOT / ".env").items()
                  if value is not None}
    source.update(os.environ)
    return source


def _model(prefix: str, environ: Mapping[str, str]) -> ModelSettings:
    return ModelSettings(
        provider=environ.get(prefix + "_PROVIDER", "openai_compatible").strip().lower(),
        model=environ.get(prefix + "_MODEL", "z-ai/glm-5.3-flash").strip(),
        base_url=environ.get(
            prefix + "_BASE_URL",
            "https://openrouter.ai/api/v1",
        ).strip(),
        api_key=(environ.get(prefix + "_API_KEY", "")
                 or environ.get("LLM_KEY", "")).strip(),
        timeout_seconds=int(environ.get(prefix + "_TIMEOUT_SECONDS", "120")),
        max_api_retries=int(environ.get(prefix + "_API_RETRIES", "3")),
        temperature=float(environ.get(prefix + "_TEMPERATURE", "0.2")),
    )


def load_api_config(environ: Optional[Mapping[str, str]] = None) -> ApiConfig:
    """Load fixed backend routes; callers should not accept route overrides from UI."""
    source = load_environment(environ)
    return ApiConfig(
        candidate_model=_model("CANDIDATE", source),
        ranking_model=_model("RANKING", source),
    )


__all__ = ["ApiConfig", "ModelSettings", "load_api_config", "load_environment"]
