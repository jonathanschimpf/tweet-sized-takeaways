#!/bin/bash
python3 -m venv venv
source venv/bin/activate

# INSTALL backend DEPENDENCIES
pip install -r backend/requirements.txt

# RUN FastAPI FROM INSIDE backend
cd backend
uvicorn main:app --reload
