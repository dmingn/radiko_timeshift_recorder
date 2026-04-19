from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from radiko_timeshift_recorder.fs_unix import (
    chown_group_under_ancestor,
    parse_unix_mode_string,
)


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


def test_chown_group_under_ancestor_chowns_each_segment_and_file(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    ancestor = tmp_path / "out"
    station = ancestor / "TEST"
    program_dir = station / "title"
    file_path = program_dir / "rec.mp4"
    program_dir.mkdir(parents=True)
    file_path.write_text("x")
    gid = 12345

    mock_chown = mocker.patch("radiko_timeshift_recorder.fs_unix.os.chown")
    chown_group_under_ancestor(ancestor, file_path, gid)

    chowned = {Path(c.args[0]).resolve() for c in mock_chown.call_args_list}
    assert chowned == {station.resolve(), program_dir.resolve(), file_path.resolve()}
    for call in mock_chown.call_args_list:
        assert call.args[1] == -1
        assert call.args[2] == gid


def test_chown_group_under_ancestor_only_file_when_directly_under_ancestor(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    ancestor = tmp_path / "out"
    ancestor.mkdir()
    file_path = ancestor / "x.mp4"
    file_path.write_text("x")
    mock_chown = mocker.patch("radiko_timeshift_recorder.fs_unix.os.chown")

    chown_group_under_ancestor(ancestor, file_path, 99)

    assert len(mock_chown.call_args_list) == 1
    assert Path(mock_chown.call_args_list[0].args[0]).resolve() == file_path.resolve()


def test_chown_group_under_ancestor_rejects_path_not_under_ancestor(
    tmp_path: Path,
) -> None:
    ancestor = tmp_path / "a"
    ancestor.mkdir()
    outside = tmp_path / "b" / "f.txt"
    outside.parent.mkdir()
    outside.write_text("x")

    with pytest.raises(ValueError, match="path must be under ancestor"):
        chown_group_under_ancestor(ancestor, outside, 1)
