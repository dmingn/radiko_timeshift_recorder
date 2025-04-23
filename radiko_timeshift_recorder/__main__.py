import typer

from radiko_timeshift_recorder.commands.put_job_from_url import (
    app as put_job_from_url_app,
)
from radiko_timeshift_recorder.commands.put_jobs_from_schedule import (
    app as put_jobs_from_schedule_app,
)
from radiko_timeshift_recorder.commands.run_server import app as run_server_app

app = typer.Typer()
app.add_typer(put_job_from_url_app)
app.add_typer(put_jobs_from_schedule_app)
app.add_typer(run_server_app)

if __name__ == "__main__":
    app()
