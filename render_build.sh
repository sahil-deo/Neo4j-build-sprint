#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install Python dependencies
pip install -e .
pip install uvicorn fastapi
