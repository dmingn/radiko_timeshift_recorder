import errno
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from radiko_timeshift_recorder.download import try_rename_with_candidates


def test_try_rename_with_candidates_success_first_try(mocker: MockerFixture) -> None:
    """Test case where renaming succeeds on the first try."""
    temp_filepath = Path("/tmp/tempfile")
    out_filepath_candidates = [
        Path("/path/to/output1.mp4"),
        Path("/path/to/output2.mp4"),
    ]
    mock_replace = mocker.patch.object(Path, "replace")

    try_rename_with_candidates(temp_filepath, out_filepath_candidates)

    mock_replace.assert_called_once_with(out_filepath_candidates[0])


def test_try_rename_with_candidates_success_second_try(mocker: MockerFixture) -> None:
    """Test case where the first candidate fails with ENAMETOOLONG, but the second succeeds."""
    temp_filepath = Path("/tmp/tempfile")
    out_filepath_candidates = [
        Path("/path/to/long_name.mp4"),
        Path("/path/to/short_name.mp4"),
    ]
    mock_replace = mocker.patch.object(Path, "replace")
    mock_replace.side_effect = [
        OSError(errno.ENAMETOOLONG, "File name too long"),
        None,  # Second call succeeds
    ]

    try_rename_with_candidates(temp_filepath, out_filepath_candidates)

    assert mock_replace.call_count == 2
    mock_replace.assert_has_calls(
        [
            mocker.call(out_filepath_candidates[0]),
            mocker.call(out_filepath_candidates[1]),
        ]
    )


def test_try_rename_with_candidates_fail_all_name_too_long(
    mocker: MockerFixture,
) -> None:
    """Test case where all candidates fail with ENAMETOOLONG."""
    temp_filepath = Path("/tmp/tempfile")
    out_filepath_candidates = [Path("/path/to/long1.mp4"), Path("/path/to/long2.mp4")]
    mock_replace = mocker.patch.object(Path, "replace")
    mock_replace.side_effect = OSError(errno.ENAMETOOLONG, "File name too long")

    with pytest.raises(OSError) as excinfo:
        try_rename_with_candidates(temp_filepath, out_filepath_candidates)

    assert excinfo.value.errno == errno.ENAMETOOLONG
    assert mock_replace.call_count == len(out_filepath_candidates)
    mock_replace.assert_has_calls([mocker.call(p) for p in out_filepath_candidates])


def test_try_rename_with_candidates_fail_other_oserror(mocker: MockerFixture) -> None:
    """Test case where an OSError other than ENAMETOOLONG occurs."""
    temp_filepath = Path("/tmp/tempfile")
    out_filepath_candidates = [
        Path("/path/to/output1.mp4"),
        Path("/path/to/output2.mp4"),
    ]
    mock_replace = mocker.patch.object(Path, "replace")
    permission_error = OSError(errno.EACCES, "Permission denied")
    mock_replace.side_effect = permission_error

    with pytest.raises(OSError) as excinfo:
        try_rename_with_candidates(temp_filepath, out_filepath_candidates)

    assert excinfo.value.errno == errno.EACCES
    assert (
        excinfo.value is permission_error
    )  # Verify that the same exception object is re-raised
    mock_replace.assert_called_once_with(out_filepath_candidates[0])
