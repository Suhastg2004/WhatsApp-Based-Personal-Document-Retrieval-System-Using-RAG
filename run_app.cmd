@echo off
setlocal
set ROOT=%~dp0

if not exist "%ROOT%major_project\Scripts\python.exe" (
  echo Virtual environment not found at major_project\Scripts\python.exe
  echo Create it first: python -m venv major_project
  exit /b 1
)

if not exist "%ROOT%.env" (
  if exist "%ROOT%.env.example" (
    copy /Y "%ROOT%.env.example" "%ROOT%.env" >nul
    echo Created .env from .env.example
  ) else (
    echo .env not found, and .env.example is missing.
    exit /b 1
  )
)

"%ROOT%major_project\Scripts\python.exe" -m pip install -r "%ROOT%requirements.txt"
"%ROOT%major_project\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
