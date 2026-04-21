import pytest

from radiko_timeshift_recorder.fs_unix import parse_unix_mode_string


@pytest.mark.parametrize(
    "text, expected",
    [
        ("644", 0o644),
        ("0644", 0o644),
        ("755", 0o755),
        ("2775", 0o2775),
        ("7777", 0o7777),
    ],
)
def test_parse_unix_mode_string(text: str, expected: int) -> None:
    assert parse_unix_mode_string(text) == expected


def test_parse_unix_mode_string_rejects_python_literal() -> None:
    with pytest.raises(ValueError, match="octal digits"):
        parse_unix_mode_string("0o644")


@pytest.mark.parametrize("too_large", ["77777", "100000", "777777"])
def test_parse_unix_mode_string_rejects_too_many_bits(too_large: str) -> None:
    with pytest.raises(ValueError, match="12 permission bits"):
        parse_unix_mode_string(too_large)
