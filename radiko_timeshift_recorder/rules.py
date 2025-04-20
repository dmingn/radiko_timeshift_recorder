from __future__ import annotations

import itertools
import operator
import re
from functools import reduce
from pathlib import Path

from pydantic import BaseModel, ConfigDict, RootModel
from pydantic_yaml import parse_yaml_file_as

from radiko_timeshift_recorder.radiko import Program, StationId

PatternText = str


class Rule(BaseModel):
    stations: frozenset[StationId]
    title_patterns: frozenset[PatternText]
    model_config = ConfigDict(frozen=True)


class Rules(RootModel[frozenset[Rule]]):
    model_config = ConfigDict(frozen=True)

    def __or__(self, other: Rules) -> Rules:
        return Rules.model_validate(self.root | other.root)

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> Rules:
        if yaml_path.is_dir():
            return reduce(
                operator.or_,
                (
                    parse_yaml_file_as(cls, p)
                    for p in itertools.chain(
                        yaml_path.glob("*.yaml"), yaml_path.glob("*.yml")
                    )
                ),
                cls(root=frozenset()),
            )
        else:
            return parse_yaml_file_as(cls, yaml_path)

    def to_record(self, station_id: StationId, program: Program) -> bool:
        for rule in self.root:
            if station_id not in rule.stations:
                continue

            for pattern in rule.title_patterns:
                if re.search(pattern, program.title):
                    return True

        return False
