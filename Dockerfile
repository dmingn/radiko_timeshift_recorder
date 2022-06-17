FROM python:3.10 AS builder

WORKDIR /radiko_timeshift_recorder

RUN pip install poetry

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.in-project true && \
    poetry install --no-dev

FROM python:3.10-slim

WORKDIR /radiko_timeshift_recorder

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY entrypoint.bash ./

COPY --from=builder /radiko_timeshift_recorder/.venv /radiko_timeshift_recorder/.venv

COPY radiko_timeshift_recorder ./radiko_timeshift_recorder

ENTRYPOINT ["bash", "entrypoint.bash"]
