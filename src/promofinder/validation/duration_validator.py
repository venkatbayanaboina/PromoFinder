"""Duration rules use summed segment screen time; gaps between segments are excluded."""
from .schemas import ValidationIssue


def validate_duration(duration_seconds, minimum=20.0, maximum=60.0):
    errors = []
    if duration_seconds < minimum:
        errors.append(ValidationIssue(
            field="duration_seconds",
            error="Duration {:.2f}s is below the {:.0f}s minimum".format(duration_seconds, minimum)))
    if duration_seconds > maximum:
        errors.append(ValidationIssue(
            field="duration_seconds",
            error="Duration {:.2f}s exceeds the {:.0f}s maximum".format(duration_seconds, maximum)))
    return errors
