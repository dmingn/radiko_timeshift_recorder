import datetime
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from pydantic_yaml import to_yaml_str

from radiko_timeshift_recorder.programs import Program
from radiko_timeshift_recorder.radiko import StationId
from radiko_timeshift_recorder.rules import Rule, Rules


def test_rules_can_be_merged_using_or_operator():
    rule_1 = Rule(
        stations=frozenset({StationId("ABC")}),
        title_patterns=frozenset({r"foo+"}),
    )
    rules_1 = Rules.model_validate(frozenset({rule_1}))

    rule_2 = Rule(
        stations=frozenset({StationId("DEF")}),
        title_patterns=frozenset({r"bar"}),
    )
    rules_2 = Rules.model_validate(frozenset({rule_2}))

    merged_rules = rules_1 | rules_2

    assert rule_1 in merged_rules.root
    assert rule_2 in merged_rules.root


def test_rules_can_be_loaded_from_single_yml_file():
    rule = Rule(
        stations=frozenset({StationId("ABC")}),
        title_patterns=frozenset({r"foo+"}),
    )
    yml_content = to_yaml_str(Rules.model_validate(frozenset({rule})))

    with tempfile.NamedTemporaryFile(suffix=".yml", mode="+w") as tmpfile:
        tmpfile.write(yml_content)
        tmpfile.seek(0)

        tmpfile_path = Path(tmpfile.name)
        rules = Rules.from_yaml(tmpfile_path)

    assert rule in rules.root


def test_rules_can_be_loaded_from_directory_contains_ymls():
    rule_1 = Rule(
        stations=frozenset({StationId("ABC")}),
        title_patterns=frozenset({r"foo+"}),
    )
    yml_content_1 = to_yaml_str(Rules.model_validate(frozenset({rule_1})))

    rule_2 = Rule(
        stations=frozenset({StationId("DEF")}),
        title_patterns=frozenset({r"bar"}),
    )
    yml_content_2 = to_yaml_str(Rules.model_validate(frozenset({rule_2})))

    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = Path(tmpdir)
        yml_file1 = dir_path / "rules1.yml"
        yml_file2 = dir_path / "rules2.yml"
        yml_file1.write_text(yml_content_1)
        yml_file2.write_text(yml_content_2)

        rules = Rules.from_yaml(dir_path)

    assert rule_1 in rules.root
    assert rule_2 in rules.root


@pytest.mark.parametrize(
    "program,expected",
    [
        (
            Program(
                to=datetime.datetime.now(tz=ZoneInfo("Asia/Tokyo")),
                ft=datetime.datetime.now(tz=ZoneInfo("Asia/Tokyo")),
                id="id",
                dur=0,
                title="foooooo",
                pfm="",
                station_id="ABC",
            ),
            True,
        ),
        (
            Program(
                to=datetime.datetime.now(tz=ZoneInfo("Asia/Tokyo")),
                ft=datetime.datetime.now(tz=ZoneInfo("Asia/Tokyo")),
                id="id",
                dur=0,
                title="fo",
                pfm="",
                station_id="ABC",
            ),
            False,
        ),
        (
            Program(
                to=datetime.datetime.now(tz=ZoneInfo("Asia/Tokyo")),
                ft=datetime.datetime.now(tz=ZoneInfo("Asia/Tokyo")),
                id="id",
                dur=0,
                title="foooooo",
                pfm="",
                station_id="DEF",
            ),
            False,
        ),
    ],
)
def test_rules_can_match_program_titles(program: Program, expected: bool):
    rule = Rule(
        stations=frozenset({StationId("ABC")}),
        title_patterns=frozenset({r"foo+"}),
    )
    rules = Rules.model_validate(frozenset({rule}))

    assert rules.to_record(program) is expected
