#!/usr/bin/env bash

set -e

cd "$(dirname "$0")/.."

# Start Home Assistant
poetry run hass -c . --debug
