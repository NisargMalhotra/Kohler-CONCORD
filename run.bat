@echo off
echo ===================================
echo  KOHLER CONCORD - Starting...
echo ===================================

if not exist .env (
    echo ERROR: .env file not found!
    echo Please copy .env.example to .env and add your API key.
    echo   copy .env.example .env
    pause
    exit /b 1
)

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate
pip install -r requirements.txt -q
streamlit run app.py
