#!/usr/bin/env python3
"""Thin LLM adapter so the model is swappable with one config edit.

Backends:
  openai — POST {base_url}/chat/completions (works for OpenAI, Gemini's
           OpenAI-compatible endpoint, Groq, or any provider Kuku plugs in).
  file   — prompts are written to prompts/<stage>_prompts.jsonl and a human
           or external assistant fills prompts/<stage>_responses.jsonl.
           This is how the free run works: the AI calls are executed in the
           ZCode session and every prompt/response is logged unedited.

Both backends return the raw response text. Nothing else in the pipeline
knows which backend was used.
"""
import json
import os
import urllib.request
from pathlib import Path

PROMPTS_DIR = Path("prompts")


def load_config(path: str = "config.json") -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def call(model_cfg: dict, prompt: str, stage: str, key: str) -> str:
    """Return the model's raw text response for one prompt."""
    backend = model_cfg.get("backend", "file")
    if backend == "openai":
        return _call_openai(model_cfg, prompt)
    if backend == "file":
        return _read_response(stage, key)
    raise ValueError(f"unknown backend: {backend}")


def _call_openai(cfg: dict, prompt: str) -> str:
    api_key = os.environ.get(cfg.get("api_key_env", ""), "")
    req = urllib.request.Request(
        cfg["base_url"].rstrip("/") + "/chat/completions",
        data=json.dumps({
            "model": cfg["name"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4,
        }).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["choices"][0]["message"]["content"]


def _read_response(stage: str, key: str) -> str:
    path = PROMPTS_DIR / f"{stage}_responses.jsonl"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} missing — fill responses for prompts/{stage}_prompts.jsonl")
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("key") == key:
            return rec["response"]
    raise KeyError(f"no response for key {key!r} in {path}")


def extract_json(text: str):
    """Tolerant JSON extraction: strips code fences, finds the outermost array/object."""
    t = text.strip()
    if "```" in t:
        parts = t.split("```")
        for part in parts:
            p = part.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            if p.startswith(("[", "{")):
                t = p
                break
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    for opener, closer in (("[", "]"), ("{", "}")):
        start = t.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(t)):
            if t[i] == opener:
                depth += 1
            elif t[i] == closer:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(t[start:i + 1])
                    except json.JSONDecodeError:
                        break
    raise ValueError(f"could not parse JSON from response: {text[:200]!r}")
