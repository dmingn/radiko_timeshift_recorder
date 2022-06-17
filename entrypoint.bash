#!/bin/bash

set -euo pipefail

source .venv/bin/activate
python -m radiko_timeshift_recorder "$@"
