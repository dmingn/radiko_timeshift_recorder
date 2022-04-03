from __future__ import annotations

import itertools
import operator
import re
from functools import reduce
from pathlib import Path

from pydantic import BaseModel
from pydantic_yaml import YamlModel

from radiko_timeshift_recorder.radiko import Program, StationId

PatternText = str


class Rule(BaseModel):
    class Config:
        frozen = True

    stations: frozenset[StationId]
    title_patterns: frozenset[PatternText]


class Rules(YamlModel):
    class Config:
        frozen = True

    __root__: frozenset[Rule]

    def __iter__(self):
        yield from self.__root__

    def __or__(self, other: Rules) -> Rules:
        return Rules(__root__=self.__root__ | other.__root__)

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> Rules:
        if yaml_path.is_dir():
            return reduce(
                operator.or_,
                (
                    cls.parse_file(p)
                    for p in itertools.chain(
                        yaml_path.glob("*.yaml"), yaml_path.glob("*.yml")
                    )
                ),
                cls(__root__=frozenset()),
            )
        else:
            return cls.parse_file(yaml_path)

    def to_record(self, program: Program) -> bool:
        for rule in self:
            if program.station_id not in rule.stations:
                continue

            for pattern in rule.title_patterns:
                if re.search(pattern, program.title):
                    return True

        return False
