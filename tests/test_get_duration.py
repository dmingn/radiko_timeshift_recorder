import asyncio
import json
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from radiko_timeshift_recorder.get_duration import (
    FFprobeError,
    get_duration,
    parse_ffprobe_duration,
)

valid_parse_output_str = """
{
    "streams": [
        {
            "codec_name": "aac",
            "codec_type": "audio",
            "duration": "900.123456"
        }
    ]
}
"""
valid_parse_output_bytes = valid_parse_output_str.encode("utf-8")
expected_parse_duration = 900.123456

no_streams_key_output_str = """{"format": {"filename": "test.mp4"}}"""
no_streams_key_output_bytes = no_streams_key_output_str.encode("utf-8")

empty_streams_list_output_str = """{"streams": []}"""
empty_streams_list_output_bytes = empty_streams_list_output_str.encode("utf-8")

no_duration_key_output_str = """{"streams": [{"codec_name": "aac"}]}"""
no_duration_key_output_bytes = no_duration_key_output_str.encode("utf-8")

invalid_json_bytes = b'{ "streams": [ { "duration": "900.123" } '


def test_parse_ffprobe_duration_success():
    duration = parse_ffprobe_duration(valid_parse_output_bytes)
    assert duration == expected_parse_duration
    assert isinstance(duration, float)


def test_parse_ffprobe_duration_invalid_json():
    with pytest.raises(json.JSONDecodeError):
        parse_ffprobe_duration(invalid_json_bytes)


def test_parse_ffprobe_duration_no_streams_key():
    with pytest.raises(ValueError, match="No audio streams found"):
        parse_ffprobe_duration(no_streams_key_output_bytes)


def test_parse_ffprobe_duration_empty_streams_list():
    with pytest.raises(ValueError, match="No audio streams found"):
        parse_ffprobe_duration(empty_streams_list_output_bytes)


def test_parse_ffprobe_duration_no_duration_key():
    with pytest.raises(ValueError, match="Duration not found"):
        parse_ffprobe_duration(no_duration_key_output_bytes)


def test_parse_ffprobe_duration_non_numeric_duration():
    non_numeric_duration_str = """{"streams": [{"duration": "abc"}]}"""
    non_numeric_duration_bytes = non_numeric_duration_str.encode("utf-8")
    with pytest.raises(ValueError):  # float() raises ValueError
        parse_ffprobe_duration(non_numeric_duration_bytes)


@pytest.mark.asyncio
async def test_get_duration_success(mocker: MockerFixture):
    # --- Arrange ---
    filepath = Path("test/audio.mp4")
    expected_duration = 123.456
    mock_stdout_json = json.dumps({"streams": [{"duration": str(expected_duration)}]})
    mock_stdout_bytes = mock_stdout_json.encode("utf-8")
    mock_stderr_bytes = b""

    mock_subprocess = mocker.AsyncMock()
    mock_subprocess.returncode = 0
    mock_subprocess.communicate = mocker.AsyncMock(
        return_value=(mock_stdout_bytes, mock_stderr_bytes)
    )

    mock_create_subprocess = mocker.patch(
        "radiko_timeshift_recorder.get_duration.asyncio.create_subprocess_exec",
        return_value=mock_subprocess,
    )

    expected_command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=duration",
        "-print_format",
        "json",
        str(filepath.resolve()),
    ]

    # --- Act ---
    duration = await get_duration(filepath)

    # --- Assert ---
    assert duration == expected_duration
    mock_create_subprocess.assert_called_once_with(
        *expected_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    mock_subprocess.communicate.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_duration_ffprobe_fails(mocker: MockerFixture):
    # --- Arrange ---
    filepath = Path("test/bad_file.mp4")
    mock_stdout_bytes = b""
    mock_stderr_bytes = b"ffprobe error message"

    mock_subprocess = mocker.AsyncMock()
    mock_subprocess.returncode = 1
    mock_subprocess.communicate = mocker.AsyncMock(
        return_value=(mock_stdout_bytes, mock_stderr_bytes)
    )

    mock_create_subprocess = mocker.patch(
        "radiko_timeshift_recorder.get_duration.asyncio.create_subprocess_exec",
        return_value=mock_subprocess,
    )

    # --- Act & Assert ---
    with pytest.raises(
        FFprobeError,
        match=f"Failed to run ffprobe on {filepath}: ffprobe error message",
    ):
        await get_duration(filepath)

    mock_create_subprocess.assert_called_once()
    mock_subprocess.communicate.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_duration_parse_fails(mocker: MockerFixture):
    # --- Arrange ---
    filepath = Path("test/corrupt_output.mp4")
    mock_stdout_bytes = b'{"streams": [{"duration": "123.456"'
    mock_stderr_bytes = b""

    mock_subprocess = mocker.AsyncMock()
    mock_subprocess.returncode = 0
    mock_subprocess.communicate = mocker.AsyncMock(
        return_value=(mock_stdout_bytes, mock_stderr_bytes)
    )

    mock_create_subprocess = mocker.patch(
        "radiko_timeshift_recorder.get_duration.asyncio.create_subprocess_exec",
        return_value=mock_subprocess,
    )

    # --- Act & Assert ---
    with pytest.raises(FFprobeError, match="Failed to parse ffprobe output"):
        await get_duration(filepath)

    mock_create_subprocess.assert_called_once()
    mock_subprocess.communicate.assert_awaited_once()
