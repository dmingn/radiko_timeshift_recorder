import json

import typer
from pydantic.json_schema import model_json_schema

from radiko_timeshift_recorder.rules import Rules

app = typer.Typer()


@app.command()
def gen_json_schema_for_rules():
    print(json.dumps(model_json_schema(Rules), indent=2))
