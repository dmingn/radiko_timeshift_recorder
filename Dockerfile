FROM python:3.12-slim AS base


FROM base AS install-ffmpeg

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


FROM base AS export-requirements-txt

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR="off"

WORKDIR /export-requirements-txt

RUN pip install pipenv

COPY Pipfile Pipfile.lock ./

RUN pipenv requirements --hash > requirements.txt


FROM base AS install-requirements

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR="off"

WORKDIR /install-requirements

# for aarch64
RUN apt-get update && \
    apt-get install -y build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY --from=export-requirements-txt /export-requirements-txt/requirements.txt .

RUN pip install -r requirements.txt

# patch streamlink
RUN sed -i 's/tf-rpaa/tf-f-rpaa-radiko/' /usr/local/lib/python3.12/site-packages/streamlink/plugins/radiko.py

FROM install-ffmpeg

WORKDIR /radiko_timeshift_recorder

COPY --from=install-requirements /usr/local/bin /usr/local/bin
COPY --from=install-requirements /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

COPY radiko_timeshift_recorder ./radiko_timeshift_recorder

ENTRYPOINT ["python", "-m", "radiko_timeshift_recorder"]
