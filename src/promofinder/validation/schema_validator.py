"""Validate model JSON against the Pydantic candidate contract."""
from ..utils.json_utils import extract_json
from .schemas import PromoDraft


def parse_promo_draft(raw_text):
    payload = extract_json(raw_text)
    return PromoDraft.model_validate(payload)
