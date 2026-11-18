"""Parse the supplied Kuku screenplay text into timestamped episode blocks."""
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..utils.time_utils import parse_timestamp
from ..validation.schemas import Episode, Scene, ScreenplayBlock

HEADER_FIELDS = ("EPISODE NUMBER", "EPISODE LOGLINE", "CONTINUITY NOTES")
LABEL_RE = re.compile(r"^\*\*(.+?):\*\*$")
TIMING_RE = re.compile(
    r"Start:\s*\((\d+:\d{1,2}(?:\.\d{1,2})?)\)\s*\|\s*"
    r"End:\s*\((\d+:\d{1,2}(?:\.\d{1,2})?)\)", re.I)
SCENE_RE = re.compile(r"^SCENE\s*:?\s*(\d+)\s*$", re.I)
SCENE_FIELD_RE = re.compile(r"^Scene\s+(heading|start|end)\s*:\s*(.+)$", re.I)
EPISODE_RE = re.compile(r"episode[-_ ]?(\d+)", re.I)
HEADER_EP_RE = re.compile(r"Episode\s+(\d+)", re.I)
NON_DIALOGUE = {"CAMERA", "ACTION", "SOUND FX"}
ALIASES = {
    "LADY JULIANA": "JULIANA", "JULIANA": "JULIANA",
    "MYSTERIOUS BEARDED MAN": "ALEXANDER", "THE BEARDED STRANGER": "ALEXANDER",
    "ALEXANDER": "ALEXANDER", "LADY IN GOLD GOWN": "CLARISSA",
    "LADY CLARISSA": "CLARISSA", "CLARISSA": "CLARISSA",
    "LADY CATHERINE": "CATHERINE", "CATHERINE": "CATHERINE",
    "THE FORMER GROOM": "GERALD", "GERALD": "GERALD",
}


def _flush(block, blocks, unparsed, line_number):
    if block is None:
        return
    if "start" not in block or "end" not in block or "text" not in block:
        unparsed.append("line {}: incomplete screenplay block".format(line_number))
        return
    blocks.append(block)


def parse_episode(text: str, source_file: str, fallback_number: Optional[int] = None) -> Episode:
    lines = text.splitlines()
    header: Dict[str, str] = {}
    raw_scenes: List[dict] = []
    raw_blocks: List[dict] = []
    unparsed: List[str] = []
    current_scene = None
    current_block = None

    for line_number, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line:
            _flush(current_block, raw_blocks, unparsed, line_number)
            current_block = None
            continue

        header_line = False
        for field in HEADER_FIELDS:
            if line.upper().startswith(field + ":"):
                header[field] = line[len(field) + 1:].strip()
                header_line = True
                break
        if header_line:
            continue

        label = LABEL_RE.match(line)
        if label:
            _flush(current_block, raw_blocks, unparsed, line_number)
            label_text = label.group(1).strip()
            speaker = label_text.split("(")[0].strip().upper()
            if speaker in NON_DIALOGUE:
                current_block = {"block_type": speaker}
            else:
                current_block = {
                    "block_type": "DIALOGUE",
                    "speaker": ALIASES.get(speaker, speaker),
                }
            continue

        timing = TIMING_RE.search(line)
        if timing and current_block is not None and "start" not in current_block:
            current_block["start"] = parse_timestamp(timing.group(1))
            current_block["end"] = parse_timestamp(timing.group(2))
            if current_block["end"] < current_block["start"]:
                unparsed.append("line {}: block end precedes start".format(line_number))
                current_block = None
            continue

        scene_match = SCENE_RE.match(line)
        if scene_match:
            _flush(current_block, raw_blocks, unparsed, line_number)
            current_block = None
            current_scene = {"scene_no": int(scene_match.group(1))}
            raw_scenes.append(current_scene)
            continue

        scene_field = SCENE_FIELD_RE.match(line)
        if scene_field and current_scene is not None:
            field_name, value = scene_field.group(1).lower(), scene_field.group(2).strip()
            if field_name in ("start", "end"):
                current_scene[field_name] = parse_timestamp(value)
            else:
                current_scene["heading"] = value
            continue

        if current_block is not None and "text" not in current_block:
            current_block["text"] = line
            continue
        if line.startswith("--- SCRIPT") or re.match(r"^Actions and dialogue\s*:", line, re.I):
            continue
        unparsed.append("line {}: {}".format(line_number, line[:160]))

    _flush(current_block, raw_blocks, unparsed, len(lines))

    source = Path(source_file)
    number_match = EPISODE_RE.search(source.stem)
    if number_match:
        episode_number = int(number_match.group(1))
    else:
        header_match = HEADER_EP_RE.search(header.get("EPISODE NUMBER", ""))
        episode_number = int(header_match.group(1)) if header_match else fallback_number
    if episode_number is None:
        raise ValueError("could not determine episode number for {}".format(source_file))
    episode_id = "EP_{:03d}".format(episode_number)

    scenes: List[Scene] = []
    for raw_scene in raw_scenes:
        if "start" not in raw_scene or "end" not in raw_scene:
            unparsed.append("scene {} is missing a start or end timestamp".format(raw_scene["scene_no"]))
            continue
        scenes.append(Scene(
            scene_id="SC_{:03d}".format(raw_scene["scene_no"]),
            heading=raw_scene.get("heading", ""),
            start_seconds=raw_scene["start"], end_seconds=raw_scene["end"]))

    scene_spans = [(s.start_seconds, s.end_seconds, s.scene_id) for s in scenes]
    blocks: List[ScreenplayBlock] = []
    for index, raw_block in enumerate(raw_blocks):
        scene_id = next((sid for start, end, sid in scene_spans
                         if start - 0.01 <= raw_block["start"] <= end + 0.01), None)
        blocks.append(ScreenplayBlock(
            block_id="ep{}:b{:03d}".format(episode_number, index),
            episode_id=episode_id, scene_id=scene_id,
            block_type=raw_block["block_type"],
            start_seconds=raw_block["start"], end_seconds=raw_block["end"],
            speaker=raw_block.get("speaker"), text=raw_block["text"]))

    duration = max((scene.end_seconds for scene in scenes), default=0.0)
    return Episode(
        episode_id=episode_id, source_file=source.name,
        source_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        screenplay_text=text, logline=header.get("EPISODE LOGLINE", ""),
        continuity_notes=header.get("CONTINUITY NOTES", ""),
        duration_seconds=duration, scenes=scenes, blocks=blocks,
        unparsed_lines=unparsed)


def parse_files(files: List[Tuple[object, str]]) -> List[Episode]:
    episodes = []
    seen = set()
    for index, (path, text) in enumerate(files, 1):
        episode = parse_episode(text, str(path), index)
        if episode.episode_id in seen:
            raise ValueError("duplicate episode ID {}".format(episode.episode_id))
        if not episode.blocks:
            raise ValueError("{} contains no timestamped screenplay blocks".format(path))
        seen.add(episode.episode_id)
        episodes.append(episode)
    return sorted(episodes, key=lambda ep: ep.episode_id)
