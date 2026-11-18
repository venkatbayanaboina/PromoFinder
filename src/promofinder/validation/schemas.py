"""Pydantic contracts shared across the pipeline and LLM boundaries."""
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Scene(StrictModel):
    scene_id: str
    heading: str = ""
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)


class ScreenplayBlock(StrictModel):
    block_id: str
    episode_id: str
    scene_id: Optional[str] = None
    block_type: str
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)
    speaker: Optional[str] = None
    text: str = ""


class Episode(StrictModel):
    episode_id: str
    source_file: str
    source_sha256: str
    screenplay_text: str
    logline: str = ""
    continuity_notes: str = ""
    duration_seconds: float = Field(ge=0)
    scenes: List[Scene] = Field(default_factory=list)
    blocks: List[ScreenplayBlock] = Field(default_factory=list)
    unparsed_lines: List[str] = Field(default_factory=list)


class CandidateSegmentDraft(StrictModel):
    start_block_id: str
    end_block_id: str
    reason: str = ""


class PromoDraft(StrictModel):
    status: Literal["candidate", "no_valid_candidate"]
    segments: List[CandidateSegmentDraft] = Field(default_factory=list)
    hook_block_id: str = ""
    cliffhanger_block_id: str = ""
    explanation: str = ""
    reason: str = ""


class PromoSegment(StrictModel):
    episode_id: str
    scene_id: Optional[str] = None
    start_block_id: str
    end_block_id: str
    start_timestamp: str
    end_timestamp: str
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)
    reason: str = ""


class PromoCandidate(StrictModel):
    promo_id: str
    episode_id: str
    segments: List[PromoSegment] = Field(min_length=1)
    duration_seconds: float = Field(gt=0)
    hook_block_id: str
    cliffhanger_block_id: str
    hook: str
    cliffhanger: str
    explanation: str
    validation_status: Literal["valid", "failed", "no_candidate"]
    generation_attempt: int = Field(ge=0)


class ValidationIssue(StrictModel):
    field: str
    error: str


class ValidationResult(StrictModel):
    is_valid: bool
    errors: List[ValidationIssue] = Field(default_factory=list)
    promo: Optional[PromoCandidate] = None


class SemanticReview(StrictModel):
    is_valid: bool
    matches_source: bool
    hook_score: int = Field(ge=0, le=5)
    cliffhanger_score: int = Field(ge=0, le=5)
    standalone_score: int = Field(ge=0, le=5)
    explanation: str
    concerns: List[str] = Field(default_factory=list)


class RankingScores(StrictModel):
    hook_strength: int = Field(ge=0, le=5)
    cliffhanger_strength: int = Field(ge=0, le=5)
    standalone_clarity: int = Field(ge=0, le=5)
    emotional_impact: int = Field(ge=0, le=5)
    duration_and_flow: int = Field(ge=0, le=5)
    justification: str
    weaknesses: List[str] = Field(default_factory=list)


class PromoRanking(StrictModel):
    promo_id: str
    episode_id: str
    scores: RankingScores
    total_score: float = Field(ge=0, le=100)
    ranking_reason: str
    weaknesses: List[str] = Field(default_factory=list)
    rank: int = Field(ge=1)
    segments: List[PromoSegment] = Field(default_factory=list)
    duration_seconds: float = Field(default=0.0, ge=0)


class ExecutionRun(StrictModel):
    run_id: str
    started_at: str
    completed_at: Optional[str] = None
    status: Literal["running", "completed", "pending_responses", "failed"]
    input_dir: str
    summary: dict = Field(default_factory=dict)
