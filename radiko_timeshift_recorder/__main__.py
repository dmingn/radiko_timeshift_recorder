import typer

from radiko_timeshift_recorder.put_jobs_from_schedule import (
    typer_app as put_jobs_from_schedule_app,
)
from radiko_timeshift_recorder.server import typer_app as server_app

app = typer.Typer()
app.add_typer(put_jobs_from_schedule_app)
app.add_typer(server_app)

if __name__ == "__main__":
    app()
