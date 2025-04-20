import errno
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from radiko_timeshift_recorder.trim_filestem import trim_filestem


def test_trim_filestem_returns_original_path_when_stem_is_short_and_exists_succeeds(
    mocker: MockerFixture,
):
    """
    Tests that the path remains unchanged if the filename stem is short enough
    for the OS limits and `exists()` does not raise an OSError.
    """
    # Mock Path.exists() to always return False (scenario where no error occurs)
    mock_exists = mocker.patch.object(Path, "exists", return_value=False)
    # Mock is_dir() to return False for this test case
    mocker.patch.object(Path, "is_dir", return_value=False)
    original_path = Path("directory/short_filename.txt")

    trimmed_path = trim_filestem(original_path)

    # Assert that the path has not changed
    assert trimmed_path == original_path
    # Assert that exists() was called at least once
    mock_exists.assert_called_once_with()


def test_trim_filestem_returns_trimmed_path_when_exists_raises_enametoolong_repeatedly(
    mocker: MockerFixture,
):
    """
    Tests that the filename stem is trimmed from the end until `exists()`
    no longer raises ENAMETOOLONG.
    """
    long_stem = "a" * 255  # Hypothetical very long filename
    short_enough_stem = "a" * 250  # Hypothetical length allowed by the OS
    original_path = Path(f"directory/{long_stem}.txt")
    expected_path = Path(f"directory/{short_enough_stem}.txt")

    # Mock is_dir() to return False
    mocker.patch.object(Path, "is_dir", return_value=False)

    # Function defining the behavior of exists()
    def mock_exists_logic(self: Path):
        # self is the mocked Path instance
        if len(self.stem) > len(short_enough_stem):
            # Raise ENAMETOOLONG if the stem is too long
            raise OSError(errno.ENAMETOOLONG, "File name too long", str(self))
        # Return False (no error) when short enough
        return False

    # Mock Path.exists with the above logic
    # autospec=True maintains the signature of Path.exists
    mock_exists = mocker.patch.object(
        Path, "exists", side_effect=mock_exists_logic, autospec=True
    )

    trimmed_path = trim_filestem(original_path)

    # Assert that the result matches the expected trimmed path
    assert trimmed_path == expected_path
    # Assert that exists was called multiple times (number of trims + final successful call)
    expected_calls = (len(long_stem) - len(short_enough_stem)) + 1
    assert mock_exists.call_count == expected_calls


def test_trim_filestem_reraises_oserror_when_exists_raises_other_than_enametoolong(
    mocker: MockerFixture,
):
    """
    Tests that if `exists()` raises an OSError other than ENAMETOOLONG,
    that error is re-raised directly.
    """
    original_path = Path("directory/some_file.txt")
    # Prepare an OSError that is not ENAMETOOLONG
    test_error = OSError(errno.EACCES, "Permission denied")

    # Mock is_dir() to return False
    mocker.patch.object(Path, "is_dir", return_value=False)
    # Mock Path.exists to always raise test_error
    mock_exists = mocker.patch.object(Path, "exists", side_effect=test_error)

    # Use pytest.raises to confirm that calling trim_filestem raises test_error
    with pytest.raises(OSError) as excinfo:
        trim_filestem(original_path)

    # Assert that the raised exception is the same instance as the test_error set in the mock
    assert excinfo.value is test_error
    # Assert that exists() was called exactly once
    mock_exists.assert_called_once()


def test_trim_filestem_returns_original_path_if_is_dir(mocker: MockerFixture):
    """
    Tests that if the input path is a directory, it is returned immediately
    without calling exists().
    """
    mock_is_dir = mocker.patch.object(Path, "is_dir", return_value=True)
    mock_exists = mocker.patch.object(Path, "exists")  # To check it's not called
    original_path = Path("some/directory/")

    trimmed_path = trim_filestem(original_path)

    assert trimmed_path == original_path
    mock_is_dir.assert_called_once_with()
    mock_exists.assert_not_called()  # Ensure exists() was skipped


def test_trim_filestem_raises_exception_on_persistent_enametoolong(
    mocker: MockerFixture,
):
    """
    Tests that if ENAMETOOLONG error persists even after trimming the stem
    down to one character, the function eventually raises some exception,
    ensuring the loop terminates.
    (It's expected to be ValueError from Path.with_stem(""), but we only check
    for any Exception here).
    """
    # Use a path with a stem of 2 or more characters (e.g., "ab")
    original_path = Path("dir/ab.txt")
    enametoolong_error = OSError(errno.ENAMETOOLONG, "File name too long")

    # Mock is_dir() to return False
    mocker.patch.object(Path, "is_dir", return_value=False)

    # Mock Path.exists to *always* raise ENAMETOOLONG
    mocker.patch.object(Path, "exists", side_effect=enametoolong_error)

    # Assert that calling trim_filestem eventually raises any Exception
    # This ensures the loop terminates instead of running indefinitely.
    with pytest.raises(Exception):
        trim_filestem(original_path)
