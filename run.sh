#!/bin/bash
set -e
echo '==================================='
echo ' KOHLER CONCORD - Starting...'
echo '==================================='

if [ ! -f .env ]; then
    echo 'ERROR: .env file not found!'
    echo 'Please copy .env.example to .env and add your API key.'
    echo '  cp .env.example .env'
    exit 1
fi

if [ ! -d venv ]; then
    echo 'Creating virtual environment...'
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt -q
streamlit run app.py
