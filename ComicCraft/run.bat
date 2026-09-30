@echo off
setlocal
cd /d "%~dp0"

echo.
echo  ComicCraft - AI Comic Story Creator
echo  -----------------------------------
echo.

rem Reuse an existing virtual environment only when it is Python 3.11 or newer.
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -c "import sys; raise SystemExit(sys.version_info < (3, 11))" >nul 2>nul
    if errorlevel 1 (
        echo The existing .venv is not usable with Python 3.11 or newer. Recreating it...
        rmdir /s /q ".venv"
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo Looking for an installed Python 3.11 or newer runtime...
    rem Prefer the Windows Python launcher. -3 selects the installed default Python 3 runtime.
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -c "import sys; raise SystemExit(sys.version_info < (3, 11))" >nul 2>nul
        if not errorlevel 1 py -3 -m venv .venv
    )

    rem Fall back to the python command if the launcher has no usable runtime.
    if not exist ".venv\Scripts\python.exe" (
        if exist ".venv" rmdir /s /q ".venv"
        where python >nul 2>nul
        if not errorlevel 1 (
            python -c "import sys; raise SystemExit(sys.version_info < (3, 11))" >nul 2>nul
            if not errorlevel 1 python -m venv .venv
        )
    )
)

if not exist ".venv\Scripts\python.exe" goto :python_missing
.venv\Scripts\python.exe -c "import sys; raise SystemExit(sys.version_info < (3, 11))" >nul 2>nul
if errorlevel 1 goto :python_missing

if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo Created .env from .env.example. Add optional API keys there if desired.
)

echo Installing or updating project packages...
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto :failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :failed

echo.
echo Starting ComicCraft at http://127.0.0.1:8000
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
exit /b %errorlevel%

:python_missing
echo.
echo Python 3.11 or newer was not found, so the virtual environment was not created.
echo If you use the Windows Python Install Manager, open a terminal here and run: py install 3.11
echo Or install Python 3.11+ from https://www.python.org/downloads/ and reopen VS Code.
echo Then run run.bat again.
pause
exit /b 1

:failed
echo.
echo Package setup failed. Check your internet connection and Python installation.
pause
exit /b 1
