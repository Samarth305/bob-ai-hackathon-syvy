@echo off
:: run.bat — Windows shortcut for the Drug Safety app launcher
:: Double-click this file, or run:  .\run.bat  from a terminal

:: Activate venv if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

python run.py %*
