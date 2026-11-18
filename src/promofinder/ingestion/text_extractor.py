"""Text extraction for the screenplay formats present in this project."""
from pathlib import Path


SUPPORTED_SUFFIXES = {".txt"}


class UnsupportedFileType(ValueError):
    pass


def extract_text(path):
    path = Path(path)
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise UnsupportedFileType(
            "{} is not supported; this input pack uses TXT screenplays".format(path))
    if not path.is_file():
        raise FileNotFoundError("screenplay file does not exist: {}".format(path))
    return path.read_text(encoding="utf-8-sig")
