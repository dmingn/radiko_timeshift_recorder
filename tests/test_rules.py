import datetime
import tempfile
from pathlib import Path

import pytest

from radiko_timeshift_recorder.radiko import Program, StationId
from radiko_timeshift_recorder.rules import Rule, Rules


def test_rules_can_be_merged_using_or_operator():
    rule_1 = Rule(
        stations=frozenset({StationId("ABC")}),
        title_patterns=frozenset({r"foo+"}),
    )
    rules_1 = Rules(__root__=frozenset({rule_1}))

    rule_2 = Rule(
        stations=frozenset({StationId("DEF")}),
        title_patterns=frozenset({r"bar"}),
    )
    rules_2 = Rules(__root__=frozenset({rule_2}))

    merged_rules = rules_1 | rules_2

    assert len(list(merged_rules)) == 2
    assert rule_1 in merged_rules
    assert rule_2 in merged_rules


def test_rules_can_be_loaded_from_single_yml_file():
    yml_content = """
- stations:
    - ABC
  title_patterns:
    - foo+
    """

    with tempfile.NamedTemporaryFile(suffix=".yml", mode="+w") as tmpfile:
        tmpfile.write(yml_content)
        tmpfile.seek(0)

        tmpfile_path = Path(tmpfile.name)
        rules = Rules.from_yaml(tmpfile_path)

    assert (
        Rule(
            stations=frozenset({StationId("ABC")}),
            title_patterns=frozenset({r"foo+"}),
        )
        in rules
    )


def test_rules_can_be_loaded_from_directory_contains_ymls():
    yml_content_1 = """
- stations:
    - ABC
  title_patterns:
    - foo+
    """
    yml_content_2 = """
- stations:
    - DEF
  title_patterns:
    - bar
    """

    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = Path(tmpdir)
        yml_file1 = dir_path / "rules1.yml"
        yml_file2 = dir_path / "rules2.yml"
        yml_file1.write_text(yml_content_1)
        yml_file2.write_text(yml_content_2)

        rules = Rules.from_yaml(dir_path)

    assert (
        Rule(
            stations=frozenset({StationId("ABC")}),
            title_patterns=frozenset({r"foo+"}),
        )
        in rules
    )
    assert (
        Rule(
            stations=frozenset({StationId("DEF")}),
            title_patterns=frozenset({r"bar"}),
        )
        in rules
    )


@pytest.mark.parametrize(
    "program,expected",
    [
        (
            Program(
                to=datetime.datetime.now(),
                ft=datetime.datetime.now(),
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
                to=datetime.datetime.now(),
                ft=datetime.datetime.now(),
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
                to=datetime.datetime.now(),
                ft=datetime.datetime.now(),
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
    rules = Rules(__root__=frozenset({rule}))

    assert rules.to_record(program) is expected
