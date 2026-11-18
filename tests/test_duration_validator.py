from promofinder.validation.duration_validator import validate_duration


def test_40_second_promo_passes():
    assert validate_duration(40) == []


def test_75_second_promo_fails():
    issues = validate_duration(75)
    assert len(issues) == 1
    assert issues[0].field == "duration_seconds"
    assert "exceeds" in issues[0].error
