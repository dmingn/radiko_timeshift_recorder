import datetime
from pathlib import Path
from unittest.mock import call
from zoneinfo import ZoneInfo

import pytest
from pytest_mock import MockerFixture

from radiko_timeshift_recorder.radiko import Program, StationId
from radiko_timeshift_recorder.rules import Rule, Rules

rule_1 = Rule(
    stations=frozenset({StationId("ABC")}),
    title_patterns=frozenset({r"foo+"}),
)
rule_2 = Rule(
    stations=frozenset({StationId("DEF")}),
    title_patterns=frozenset({r"bar"}),
)

rules_1 = Rules.model_validate(frozenset({rule_1}))
rules_2 = Rules.model_validate(frozenset({rule_2}))
rules_empty = Rules.model_validate(frozenset())
rules_merged = Rules.model_validate(frozenset({rule_1, rule_2}))


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


@pytest.mark.parametrize(
    ids=["multiple_paths", "single_path", "no_paths", "one_empty_path"],
    argnames="input_paths, mock_side_effect_map, expected_rules, expected_calls",
    argvalues=[
        (
            [Path("rules1.yaml"), Path("rules2.yaml")],
            {
                Path("rules1.yaml"): rules_1,
                Path("rules2.yaml"): rules_2,
            },
            rules_merged,
            [
                call(Rules, Path("rules1.yaml")),
                call(Rules, Path("rules2.yaml")),
            ],
        ),
        (
            [Path("rules.yaml")],
            {Path("rules.yaml"): rules_1},
            rules_1,
            [call(Rules, Path("rules.yaml"))],
        ),
        (
            [],
            {},
            rules_empty,
            [],
        ),
        (
            [Path("rules1.yaml"), Path("empty.yaml")],
            {Path("rules1.yaml"): rules_1, Path("empty.yaml"): rules_empty},
            rules_1,
            [call(Rules, Path("rules1.yaml")), call(Rules, Path("empty.yaml"))],
        ),
    ],
)
def test_rules_from_yaml_paths(
    mocker: MockerFixture,
    input_paths: list[Path],
    mock_side_effect_map: dict[Path, Rules],
    expected_rules: Rules,
    expected_calls: list,
):
    # --- Arrange ---
    mock_parse_yaml = mocker.patch("radiko_timeshift_recorder.rules.parse_yaml_file_as")
    mock_parse_yaml.side_effect = lambda cls, p: mock_side_effect_map.get(p)

    # --- Act ---
    result_rules = Rules.from_yaml_paths(input_paths)

    # --- Assert ---
    assert result_rules == expected_rules
    assert mock_parse_yaml.call_count == len(expected_calls)
    mock_parse_yaml.assert_has_calls(expected_calls, any_order=False)


@pytest.mark.parametrize(
    "station_id,program,expected",
    [
        (
            "ABC",
            Program(
                to=datetime.datetime.now(tz=ZoneInfo("Asia/Tokyo")),
                ft=datetime.datetime.now(tz=ZoneInfo("Asia/Tokyo")),
                id="id",
                dur=0,
                title="foooooo",
                pfm="",
            ),
            True,
        ),
        (
            "ABC",
            Program(
                to=datetime.datetime.now(tz=ZoneInfo("Asia/Tokyo")),
                ft=datetime.datetime.now(tz=ZoneInfo("Asia/Tokyo")),
                id="id",
                dur=0,
                title="fo",
                pfm="",
            ),
            False,
        ),
        (
            "DEF",
            Program(
                to=datetime.datetime.now(tz=ZoneInfo("Asia/Tokyo")),
                ft=datetime.datetime.now(tz=ZoneInfo("Asia/Tokyo")),
                id="id",
                dur=0,
                title="foooooo",
                pfm="",
            ),
            False,
        ),
    ],
)
def test_rules_can_match_job_titles(
    station_id: StationId, program: Program, expected: bool
):
    rule = Rule(
        stations=frozenset({StationId("ABC")}),
        title_patterns=frozenset({r"foo+"}),
    )
    rules = Rules.model_validate(frozenset({rule}))

    assert rules.to_record(station_id=station_id, program=program) is expected
