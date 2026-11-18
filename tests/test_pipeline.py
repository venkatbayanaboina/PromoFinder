import json
from dataclasses import replace

from promofinder import main as pipeline
from promofinder.settings import ModelSettings, load_settings


class FakeClient:
    def __init__(self, output_dir, run_id="test", prompts_dir=None):
        pass

    def complete(self, prompt, stage, key, model_settings, attempt=0):
        if stage == "generation":
            return json.dumps({
                "status": "candidate",
                "segments": [{"start_block_id": "ep1:b000", "end_block_id": "ep1:b001",
                              "reason": "Escalating conflict."}],
                "hook_block_id": "ep1:b000", "cliffhanger_block_id": "ep1:b001",
                "explanation": "The betrayal is legible without prior context."})
        if stage == "semantic_validation":
            return json.dumps({"is_valid": True, "matches_source": True,
                               "hook_score": 4, "cliffhanger_score": 4,
                               "standalone_score": 4,
                               "explanation": "The excerpt supports the proposal.", "concerns": []})
        return json.dumps({"hook_strength": 5, "cliffhanger_strength": 4,
                           "standalone_clarity": 4, "emotional_impact": 5,
                           "duration_and_flow": 4, "justification": "Strong betrayal hook.",
                           "weaknesses": []})


def test_full_pipeline_persists_and_exports_ranked_candidate(tmp_path, monkeypatch):
    source = tmp_path / "input"
    source.mkdir()
    (source / "episode-001.txt").write_text("""EPISODE NUMBER: Episode 1
EPISODE LOGLINE: A bride discovers betrayal.
CONTINUITY NOTES: First episode.
SCENE 01
Scene heading: INT. CATHEDRAL – DAY
Scene start: 00:00.00
Scene end: 00:40.00
**ACTION:**
Start: (00:00.00) | End: (00:05.00)
Juliana enters the cathedral.
**LADY JULIANA:**
Start: (00:05.00) | End: (00:25.00)
Why are you holding her hand?
""", encoding="utf-8")
    settings = load_settings()
    settings = replace(
        settings, root=tmp_path, input_dir=source,
        processed_dir=tmp_path / "processed", output_dir=tmp_path / "outputs",
        reports_dir=tmp_path / "reports", database_path=tmp_path / "processed" / "test.db",
        prompts_dir=settings.prompts_dir,
        candidate_model=ModelSettings("file", "", "", ""),
        ranking_model=ModelSettings("file", "", "", ""))
    monkeypatch.setattr(pipeline, "LLMClient", FakeClient)
    result = pipeline.run_pipeline(settings=settings)
    assert result["status"] == "completed"
    assert result["summary"]["valid_promos"] == 1
    assert result["summary"]["ranked_promos"] == 1
    assert (tmp_path / "outputs" / "top_promos.json").exists()
    assert (tmp_path / "reports" / "execution_report.md").exists()


def test_empty_ranked_set_finishes_gracefully(tmp_path, monkeypatch):
    source = tmp_path / "input"
    source.mkdir()
    (source / "episode-001.txt").write_text("""EPISODE NUMBER: Episode 1
SCENE 01
Scene heading: INT. ROOM – DAY
Scene start: 00:00.00
Scene end: 00:30.00
**ACTION:**
Start: (00:00.00) | End: (00:25.00)
An inconclusive moment.
""", encoding="utf-8")
    class NoPromoClient(FakeClient):
        def complete(self, prompt, stage, key, model_settings, attempt=0):
            if stage == "generation":
                return '{"status":"no_valid_candidate","reason":"No suitable moment."}'
            raise AssertionError("ranking must not run when no promo is valid")
    settings = load_settings()
    settings = replace(settings, root=tmp_path, input_dir=source,
                       processed_dir=tmp_path / "processed", output_dir=tmp_path / "outputs",
                       reports_dir=tmp_path / "reports", database_path=tmp_path / "processed" / "test.db")
    monkeypatch.setattr(pipeline, "LLMClient", NoPromoClient)
    result = pipeline.run_pipeline(settings=settings)
    assert result["status"] == "completed"
    assert result["summary"]["no_candidate_episodes"] == 1
    assert result["summary"]["ranked_promos"] == 0
