import json

import pytest

from promofinder.generation.llm_client import LLMClient, PendingResponse
from promofinder.settings import ModelSettings


def test_file_provider_queues_then_reuses_a_supplied_response(tmp_path):
    output_dir = tmp_path / "outputs"
    client = LLMClient(output_dir, run_id="run-test")
    model = ModelSettings(provider="file", model="", base_url="", api_key="")
    prompt = "Return one JSON object."
    with pytest.raises(PendingResponse) as pending:
        client.complete(prompt, "generation", "EP_001", model, attempt=0)

    queue = tmp_path / "prompts" / "pending_requests.jsonl"
    request = json.loads(queue.read_text(encoding="utf-8").splitlines()[0])
    assert request["request_id"] == pending.value.request_id
    request["response"] = '{"status":"no_valid_candidate","reason":"none"}'
    queue.write_text(json.dumps(request) + "\n", encoding="utf-8")

    response = client.complete(prompt, "generation", "EP_001", model, attempt=0)
    assert json.loads(response)["status"] == "no_valid_candidate"
    logged = json.loads((output_dir / "raw_llm_responses.jsonl").read_text(encoding="utf-8"))
    assert logged["response"] == response
    assert client.complete(prompt, "generation", "EP_001", model, attempt=0) == response


def test_switching_models_creates_a_distinct_request(tmp_path):
    client = LLMClient(tmp_path / "outputs")
    first = ModelSettings(provider="file", model="model-a", base_url="", api_key="")
    second = ModelSettings(provider="file", model="model-b", base_url="", api_key="")
    with pytest.raises(PendingResponse) as first_pending:
        client.complete("same prompt", "generation", "EP_001", first)
    with pytest.raises(PendingResponse) as second_pending:
        client.complete("same prompt", "generation", "EP_001", second)
    assert first_pending.value.request_id != second_pending.value.request_id
