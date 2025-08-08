#!/bin/bash

python3 -m uvicorn backend.main:app \
  --reload \
  --reload-dir backend \
  --reload-dir public \
  --reload-exclude .venv
