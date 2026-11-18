"""Safe extraction of JSON payloads from model responses."""
import json


def extract_json(text):
    value = text.strip()
    if "```" in value:
        for part in value.split("```"):
            candidate = part.strip()
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
            if candidate.startswith(("{", "[")):
                value = candidate
                break
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start = value.find(opener)
        depth = 0
        quoted = False
        escaped = False
        for index in range(start, len(value)) if start >= 0 else ():
            char = value[index]
            if quoted:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = False
                continue
            if char == '"':
                quoted = True
            elif char == opener:
                depth += 1
            elif char == closer:
                depth -= 1
                if depth == 0:
                    return json.loads(value[start:index + 1])
    raise ValueError("model response did not contain valid JSON")
