FROM python:3.10-slim AS builder

WORKDIR /radiko_timeshift_recorder

RUN apt-get update && \
    apt-get install -y build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install poetry

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false && \
    poetry install --no-dev

FROM python:3.10-slim

WORKDIR /radiko_timeshift_recorder

# TODO: reduce image size
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages

COPY radiko_timeshift_recorder ./radiko_timeshift_recorder

ENTRYPOINT ["python", "-m", "radiko_timeshift_recorder"]
