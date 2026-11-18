import pytest

from promofinder.ingestion.episode_parser import parse_episode


@pytest.fixture
def sample_episode():
    text = """EPISODE NUMBER: Episode 1
EPISODE LOGLINE: A bride discovers a betrayal.
CONTINUITY NOTES: First episode.

--- SCRIPT START ---
SCENE 01
Scene heading: INT. CATHEDRAL – DAY
Scene start: 00:00.00
Scene end: 00:40.00

Actions and dialogue:
**ACTION:**
Start: (00:00.00) | End: (00:05.00)
Juliana enters the cathedral in her mother's gown.

**LADY JULIANA (Confused):**
Start: (00:05.00) | End: (00:25.00)
Why is my fiancé holding her hand?
"""
    return parse_episode(text, "episode-001.txt")
