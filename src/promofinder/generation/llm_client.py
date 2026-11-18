"""OpenAI-compatible LLM transport with file hand-off and raw response logging."""
import hashlib
import json
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from ..utils.logger import get_logger

_file_lock = threading.Lock()  # serialise concurrent JSONL appends across threads


class LLMError(RuntimeError):
    pass


class PendingResponse(LLMError):
    def __init__(self, request_id):
        self.request_id = request_id
        super().__init__("model response is pending for {}".format(request_id))


class LLMClient:
    def __init__(self, output_dir, run_id="manual", prompts_dir=None, force_refresh=False):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.raw_path = self.output_dir / "raw_llm_responses.jsonl"
        self.pending_dir = Path(prompts_dir) if prompts_dir else self.output_dir.parent / "prompts"
        self.pending_path = self.pending_dir / "pending_requests.jsonl"
        self.run_id = run_id
        self.force_refresh = force_refresh
        self.logger = get_logger(__name__, self.output_dir)

    def complete(self, prompt, stage, key, model_settings, attempt=0):
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        model_identity = json.dumps({
            "provider": model_settings.provider,
            "model": model_settings.model,
            "base_url": model_settings.base_url,
            "temperature": model_settings.temperature,
        }, sort_keys=True)
        model_hash = hashlib.sha256(model_identity.encode("utf-8")).hexdigest()[:12]
        request_parts = [stage, key, str(attempt), model_hash, digest[:12]]
        if self.force_refresh and model_settings.provider != "file":
            request_parts.insert(0, self.run_id)
        request_id = ":".join(request_parts)
        existing = self._existing_response(request_id)
        if existing is not None:
            return existing

        if model_settings.provider == "file":
            pending = self._pending_response(request_id)
            if pending:
                record = dict(pending)
                record.update({
                    "run_id": self.run_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "provider": "file",
                })
                self._append(self.raw_path, record)
                return pending["response"]
            self._queue_pending({
                "request_id": request_id, "stage": stage, "key": key,
                "attempt": attempt, "prompt_sha256": digest,
                "model_config_sha256": model_hash,
                "model": model_settings.model or "manual file hand-off",
                "prompt": prompt, "response": "",
            })
            raise PendingResponse(request_id)
        if model_settings.provider not in ("openai", "openai_compatible"):
            raise LLMError("unsupported model provider: {}".format(model_settings.provider))
        if not model_settings.api_key or not model_settings.base_url or not model_settings.model:
            raise LLMError(
                "API provider needs its API key, base URL, and model in .env")

        response = self._call_api(prompt, model_settings)
        record = {
            "request_id": request_id, "run_id": self.run_id, "stage": stage,
            "key": key, "attempt": attempt, "prompt_sha256": digest,
            "model_config_sha256": model_hash,
            "provider": model_settings.provider, "model": model_settings.model,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "prompt": prompt, "response": response,
        }
        self._append(self.raw_path, record)
        return response

    def _call_api(self, prompt, model_settings):
        body = json.dumps({
            "model": model_settings.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": model_settings.temperature,
        }).encode("utf-8")
        headers = {"Content-Type": "application/json",
                   "Authorization": "Bearer " + model_settings.api_key}
        attempts = max(1, model_settings.max_api_retries + 1)
        for index in range(attempts):
            request = urllib.request.Request(
                model_settings.base_url.rstrip("/") + "/chat/completions",
                data=body, headers=headers)
            try:
                with urllib.request.urlopen(request, timeout=model_settings.timeout_seconds) as resp:
                    response_text = resp.read().decode("utf-8")
                try:
                    payload = json.loads(response_text)
                    content = payload["choices"][0]["message"]["content"]
                except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
                    raise LLMError("model API returned a malformed chat-completions response") from exc
                if isinstance(content, list):
                    content = "".join(item.get("text", "") for item in content
                                      if isinstance(item, dict))
                if not isinstance(content, str) or not content.strip():
                    raise LLMError("model returned an empty or non-text response")
                return content
            except urllib.error.HTTPError as exc:
                retryable = exc.code == 429 or 500 <= exc.code < 600
                detail = exc.read().decode("utf-8", errors="replace")[:1000]
                if not retryable or index + 1 == attempts:
                    raise LLMError("model API HTTP {}: {}".format(exc.code, detail)) from exc
                self.logger.warning("temporary model API HTTP %s; retry %s/%s",
                                    exc.code, index + 1, attempts - 1)
            except (urllib.error.URLError, TimeoutError) as exc:
                if index + 1 == attempts:
                    raise LLMError("model API request failed: {}".format(exc)) from exc
                self.logger.warning("temporary model API failure; retry %s/%s: %s",
                                    index + 1, attempts - 1, exc)
            time.sleep(min(2 ** index, 8))
        raise LLMError("model API failed after retries")

    def _existing_response(self, request_id):
        if not self.raw_path.exists():
            return None
        for line in self.raw_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                self.logger.warning("Skipping malformed raw response log line")
                continue
            if record.get("request_id") == request_id and record.get("response"):
                return record["response"]
        return None

    def _pending_response(self, request_id):
        if not self.pending_path.exists():
            return None
        for line in self.pending_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("request_id") == request_id and str(record.get("response", "")).strip():
                return record
        return None

    def _queue_pending(self, record):
        self.pending_path.parent.mkdir(parents=True, exist_ok=True)
        pending = {}
        if self.pending_path.exists():
            for line in self.pending_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        self.logger.warning("Skipping malformed pending request line")
                        continue
                    pending[item["request_id"]] = item
        pending[record["request_id"]] = record
        self.pending_path.write_text(
            "".join(json.dumps(item, ensure_ascii=False) + "\n"
                    for item in pending.values()), encoding="utf-8")

    @staticmethod
    def _append(path, record):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with _file_lock:
            with Path(path).open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
