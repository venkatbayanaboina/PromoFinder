"""Time parsing/formatting helpers for screenplay timestamps."""
import re

_MMSS = re.compile(r"^(\d+):(\d{1,2}(?:\.\d{1,2})?)$")
_HHMMSS = re.compile(r"^(\d+):(\d{1,2}):(\d{1,2}(?:\.\d{1,2})?)$")


def parse_timestamp(value):
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    hms_match = _HHMMSS.match(text)
    if hms_match:
        hours, minutes, seconds = int(hms_match.group(1)), int(hms_match.group(2)), float(hms_match.group(3))
        if minutes >= 60 or seconds >= 60:
            raise ValueError("timestamp minutes and seconds must be less than 60")
        return hours * 3600 + minutes * 60 + seconds
    match = _MMSS.match(text)
    if not match:
        raise ValueError("timestamp must use MM:SS, MM:SS.ss, or HH:MM:SS format")
    seconds = float(match.group(2))
    if seconds >= 60:
        raise ValueError("timestamp seconds must be less than 60")
    return int(match.group(1)) * 60 + seconds


def format_timestamp(seconds):
    whole_minutes, remainder = divmod(float(seconds), 60)
    return "{:02d}:{:05.2f}".format(int(whole_minutes), remainder)
