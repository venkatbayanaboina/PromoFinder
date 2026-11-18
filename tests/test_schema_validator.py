import pytest

from promofinder.validation.schema_validator import parse_promo_draft


def test_invalid_json_fails_schema_validation():
    with pytest.raises(ValueError):
        parse_promo_draft("{this is not JSON}")


def test_unknown_fields_are_rejected():
    with pytest.raises(ValueError):
        parse_promo_draft('{"status":"candidate","unexpected":true}')
