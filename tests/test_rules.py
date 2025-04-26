import datetime
from pathlib import Path
from unittest.mock import call
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError
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


@pytest.mark.parametrize(
    "rules_a, rules_b, expected_rules",
    [
        pytest.param(rules_1, rules_2, rules_merged, id="merge_distinct"),
        pytest.param(rules_empty, rules_1, rules_1, id="merge_empty_left"),
        pytest.param(rules_1, rules_empty, rules_1, id="merge_empty_right"),
        pytest.param(rules_empty, rules_empty, rules_empty, id="merge_empty_both"),
        pytest.param(rules_1, rules_1, rules_1, id="merge_overlapping"),
        pytest.param(rules_merged, rules_1, rules_merged, id="merge_subset_left"),
        pytest.param(rules_1, rules_merged, rules_merged, id="merge_subset_right"),
    ],
)
def test_rules_or_operator(rules_a: Rules, rules_b: Rules, expected_rules: Rules):
    # --- Act ---
    merged_rules = rules_a | rules_b

    # --- Assert ---
    assert merged_rules == expected_rules
    assert isinstance(merged_rules, Rules)


@pytest.mark.parametrize(
    "input_paths, mock_side_effect_map, expected_rules, expected_calls",
    [
        pytest.param(
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
            id="multiple_paths",
        ),
        pytest.param(
            [Path("rules.yaml")],
            {Path("rules.yaml"): rules_1},
            rules_1,
            [call(Rules, Path("rules.yaml"))],
            id="single_path",
        ),
        pytest.param(
            [],
            {},
            rules_empty,
            [],
            id="no_paths",
        ),
        pytest.param(
            [Path("rules1.yaml"), Path("empty.yaml")],
            {Path("rules1.yaml"): rules_1, Path("empty.yaml"): rules_empty},
            rules_1,
            [call(Rules, Path("rules1.yaml")), call(Rules, Path("empty.yaml"))],
            id="one_empty_path",
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
    "input_paths, mock_side_effect, expected_exception, expected_calls_before_error",
    [
        pytest.param(
            [Path("rules1.yaml"), Path("not_found.yaml")],
            [
                rules_1,
                FileNotFoundError("File not found!"),
            ],
            FileNotFoundError,
            [call(Rules, Path("rules1.yaml"))],
            id="file_not_found",
        ),
        pytest.param(
            [Path("rules1.yaml"), Path("invalid_schema.yaml")],
            [
                rules_1,
                ValidationError.from_exception_data("Rules", []),
            ],
            ValidationError,
            [call(Rules, Path("rules1.yaml"))],
            id="validation_error",
        ),
    ],
)
def test_rules_from_yaml_paths_errors(
    mocker: MockerFixture,
    input_paths: list[Path],
    mock_side_effect: list,
    expected_exception: type[Exception],
    expected_calls_before_error: list,
):
    # --- Arrange ---
    mock_parse_yaml = mocker.patch("radiko_timeshift_recorder.rules.parse_yaml_file_as")
    mock_parse_yaml.side_effect = mock_side_effect

    # --- Act & Assert ---
    with pytest.raises(expected_exception):
        Rules.from_yaml_paths(input_paths)

    assert mock_parse_yaml.call_count == len(expected_calls_before_error) + 1
    mock_parse_yaml.assert_has_calls(expected_calls_before_error, any_order=False)


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
