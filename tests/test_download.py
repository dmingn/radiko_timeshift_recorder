import datetime
import errno
import stat
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from pytest_mock import MockerFixture

from radiko_timeshift_recorder.download import (
    download,
    generate_filename_candidates,
    try_rename_with_candidates,
)
from radiko_timeshift_recorder.job import Job
from radiko_timeshift_recorder.radiko import Program


@pytest.mark.parametrize(
    "ft_str_yyyymmddhhmmss, title, pfm, expected_candidates",
    [
        pytest.param(
            "20230101100000",
            "Test Show / Special",
            "Test Artist / Group",
            (
                "2023-01-01 10-00-00 - Test Show ／ Special - Test Artist ／ Group",
                "2023-01-01 10-00-00 - Test Show ／ Special",
                "2023-01-01 10-00-00",
            ),
            id="with_pfm",
        ),
        pytest.param(
            "20230102113015",
            "Another Show",
            None,
            (
                "2023-01-02 11-30-15 - Another Show",
                "2023-01-02 11-30-15",
            ),
            id="without_pfm",
        ),
        pytest.param(
            "20230103120000",
            "Title Only Show",
            "",
            (
                "2023-01-03 12-00-00 - Title Only Show",
                "2023-01-03 12-00-00",
            ),
            id="with_empty_string_pfm",
        ),
        pytest.param(
            "20240520000000",
            "",
            "Performer",
            (
                "2024-05-20 00-00-00 -  - Performer",
                "2024-05-20 00-00-00 - ",
                "2024-05-20 00-00-00",
            ),
            id="with_empty_string_title_and_pfm",
        ),
    ],
)
def test_generate_filename_candidates(
    ft_str_yyyymmddhhmmss: str,
    title: str,
    pfm: str | None,
    expected_candidates: tuple[str, ...],
):
    """
    Tests generate_filename_candidates with various inputs for program details.
    It checks for correct filename generation including:
    - With performer (pfm).
    - Without performer (pfm is None).
    - With performer as an empty string.
    - With title as an empty string.
    - Slash replacement in title and pfm.
    """
    program_id_for_test = "test_prog_id"
    duration_seconds_for_test = 3600

    ft_datetime = datetime.datetime.strptime(
        ft_str_yyyymmddhhmmss, "%Y%m%d%H%M%S"
    ).replace(tzinfo=ZoneInfo("Asia/Tokyo"))
    to_datetime = ft_datetime + datetime.timedelta(seconds=duration_seconds_for_test)

    program = Program(
        id=program_id_for_test,
        ft=ft_datetime,
        to=to_datetime,
        dur=duration_seconds_for_test,
        title=title,
        pfm=pfm,
    )

    assert generate_filename_candidates(program) == expected_candidates


@pytest.mark.asyncio
async def test_download_applies_file_and_dir_modes(
    tmp_path: Path, mocker: MockerFixture, sample_job: Job
) -> None:
    out = tmp_path / "out"
    out.mkdir()

    async def fake_download_stream(url: str, fp: Path) -> None:
        fp.write_bytes(b"x")

    mocker.patch(
        "radiko_timeshift_recorder.download.download_stream",
        side_effect=fake_download_stream,
    )
    mocker.patch(
        "radiko_timeshift_recorder.download.get_duration",
        return_value=900.0,
    )

    ref_dir = tmp_path / "umask_ref"
    ref_dir.mkdir(mode=0o750)
    expected_dir_mode = stat.S_IMODE(ref_dir.stat().st_mode)

    await download(
        sample_job,
        out,
        output_file_mode=0o640,
        output_dir_mode=0o750,
        output_gid=None,
    )

    mp4s = list(out.rglob("*.mp4"))
    assert len(mp4s) == 1
    assert stat.S_IMODE(mp4s[0].stat().st_mode) == 0o640

    program_dir = out / "TEST" / "test program"
    assert program_dir.is_dir()
    assert stat.S_IMODE(program_dir.stat().st_mode) == expected_dir_mode


@pytest.mark.asyncio
async def test_download_chowns_when_output_gid(
    tmp_path: Path, mocker: MockerFixture, sample_job: Job
) -> None:
    out = tmp_path / "out"
    out.mkdir()
    gid = 12345

    async def fake_download_stream(url: str, fp: Path) -> None:
        fp.write_bytes(b"x")

    mocker.patch(
        "radiko_timeshift_recorder.download.download_stream",
        side_effect=fake_download_stream,
    )
    mocker.patch(
        "radiko_timeshift_recorder.download.get_duration",
        return_value=900.0,
    )
    mock_chown = mocker.patch("radiko_timeshift_recorder.fs_unix.os.chown")

    await download(
        sample_job,
        out,
        output_file_mode=0o644,
        output_dir_mode=0o755,
        output_gid=gid,
    )

    mp4 = next(out.rglob("*.mp4"))
    station_dir = out / "TEST"
    program_dir = out / "TEST" / "test program"
    chown_targets = {Path(c.args[0]).resolve() for c in mock_chown.call_args_list}
    assert station_dir.resolve() in chown_targets
    assert program_dir.resolve() in chown_targets
    assert mp4.resolve() in chown_targets
    for call in mock_chown.call_args_list:
        assert call.args[1] == -1
        assert call.args[2] == gid


def test_try_rename_with_candidates_success_first_try(mocker: MockerFixture) -> None:
    """Test case where renaming succeeds on the first try."""
    temp_filepath = Path("/tmp/tempfile")
    out_filepath_candidates = [
        Path("/path/to/output1.mp4"),
        Path("/path/to/output2.mp4"),
    ]
    mock_replace = mocker.patch.object(Path, "replace")

    returned_path = try_rename_with_candidates(temp_filepath, out_filepath_candidates)

    mock_replace.assert_called_once_with(out_filepath_candidates[0])
    assert returned_path == out_filepath_candidates[0]


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

    returned_path = try_rename_with_candidates(temp_filepath, out_filepath_candidates)

    assert mock_replace.call_count == 2
    mock_replace.assert_has_calls(
        [
            mocker.call(out_filepath_candidates[0]),
            mocker.call(out_filepath_candidates[1]),
        ]
    )
    assert returned_path == out_filepath_candidates[1]


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


def test_try_rename_with_candidates_empty_list() -> None:
    """Test case where the list of output filepath candidates is empty."""
    temp_filepath = Path("/tmp/tempfile")

    with pytest.raises(
        ValueError, match="out_filepath_candidates list cannot be empty"
    ):
        try_rename_with_candidates(temp_filepath, [])


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
