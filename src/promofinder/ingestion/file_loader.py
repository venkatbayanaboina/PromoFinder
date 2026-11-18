"""Discover screenplay files and load their original text."""
import logging
from pathlib import Path
from typing import List, Tuple

from .text_extractor import extract_text

logger = logging.getLogger(__name__)


def discover_files(input_dir) -> List[Path]:
    root = Path(input_dir)
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError("input directory does not exist: {}".format(root))
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() == ".txt")
    unsupported = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() not in {".txt"}]
    for path in unsupported:
        logger.warning("Skipping unsupported input file: %s", path)
    if not files:
        raise FileNotFoundError("no TXT episode screenplays found under {}".format(root))
    return files


def load_all_files(input_dir) -> List[Tuple[Path, str]]:
    return [(path, extract_text(path)) for path in discover_files(input_dir)]
