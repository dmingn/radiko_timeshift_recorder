from __future__ import annotations

import operator
import re
from functools import reduce
from pathlib import Path
from typing import Iterable

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
    def from_yaml_paths(cls, yaml_paths: Iterable[Path]) -> Rules:
        return reduce(
            operator.or_,
            (parse_yaml_file_as(cls, p) for p in yaml_paths),
            cls(root=frozenset()),
        )

    def to_record(self, station_id: StationId, program: Program) -> bool:
        for rule in self.root:
            if station_id not in rule.stations:
                continue

            for pattern in rule.title_patterns:
                if re.search(pattern, program.title):
                    return True

        return False
