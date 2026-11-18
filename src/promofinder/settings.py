"""Shared, environment-aware project settings."""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Optional

from .api_config import ROOT, ApiConfig, ModelSettings, load_api_config, load_environment


@dataclass(frozen=True)
class Settings:
    root: Path
    input_dir: Path
    processed_dir: Path
    output_dir: Path
    reports_dir: Path
    prompts_dir: Path
    database_path: Path
    min_duration_seconds: float
    max_duration_seconds: float
    hook_window_seconds: float
    max_validation_retries: int
    top_k: int
    scoring_weights: Dict[str, int]
    candidate_model: ModelSettings
    ranking_model: ModelSettings


def load_settings(environ: Optional[Mapping[str, str]] = None) -> Settings:
    source = load_environment(environ)

    def get(name, default):
        return source.get(name, default)

    weights = json.loads((ROOT / "config" / "scoring_rubric.json").read_text(encoding="utf-8"))
    if sum(weights.values()) != 100:
        raise ValueError("Scoring rubric weights must total 100")
    max_retries = int(get("PROMOFINDER_MAX_RETRIES", "2"))
    if not 0 <= max_retries <= 2:
        raise ValueError("PROMOFINDER_MAX_RETRIES must be between 0 and 2")
    input_dir = Path(get("PROMOFINDER_INPUT_DIR", "data/input"))
    processed_dir = Path(get("PROMOFINDER_PROCESSED_DIR", "data/processed"))
    output_dir = Path(get("PROMOFINDER_OUTPUT_DIR", "data/outputs"))
    reports_dir = Path(get("PROMOFINDER_REPORTS_DIR", "reports"))
    db_path = Path(get("PROMOFINDER_DB_PATH", str(processed_dir / "promofinder.sqlite3")))

    def rooted(path):
        return path if path.is_absolute() else ROOT / path

    minimum = float(get("PROMOFINDER_MIN_SECONDS", "20"))
    maximum = float(get("PROMOFINDER_MAX_SECONDS", "60"))
    if minimum < 0 or maximum < minimum:
        raise ValueError("Promo duration limits must be non-negative and maximum >= minimum")
    top_k = int(get("PROMOFINDER_TOP_K", "10"))
    if top_k < 0:
        raise ValueError("PROMOFINDER_TOP_K cannot be negative")
    api_config: ApiConfig = load_api_config(source)
    return Settings(
        root=ROOT, input_dir=rooted(input_dir), processed_dir=rooted(processed_dir),
        output_dir=rooted(output_dir), reports_dir=rooted(reports_dir),
        prompts_dir=ROOT / "data" / "prompts", database_path=rooted(db_path),
        min_duration_seconds=minimum, max_duration_seconds=maximum,
        hook_window_seconds=float(get("PROMOFINDER_HOOK_WINDOW_SECONDS", "3")),
        max_validation_retries=max_retries, top_k=top_k, scoring_weights=weights,
        candidate_model=api_config.candidate_model,
        ranking_model=api_config.ranking_model,
    )
