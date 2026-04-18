@echo off
chcp 65001 >nul
title Классификация текстов — сервер
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  set "PY=%~dp0.venv\Scripts\python.exe"
) else if exist "venv\Scripts\python.exe" (
  set "PY=%~dp0venv\Scripts\python.exe"
) else (
  set "PY=python"
)

where %PY% >nul 2>&1
if errorlevel 1 (
  where python >nul 2>&1
  if errorlevel 1 (
    echo Не найден Python. Установите Python 3.10+ или создайте виртуальное окружение:
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
  )
  set "PY=python"
)

echo.
echo  Сервер: http://127.0.0.1:8000/
echo  Остановка: закройте это окно или нажмите Ctrl+C
echo.

REM Браузер через несколько секунд (пока поднимается Django и ML)
start "" cmd /c "timeout /t 5 /nobreak >nul 2>&1 && start "" http://127.0.0.1:8000/"

"%PY%" manage.py runserver 127.0.0.1:8000
echo.
pause
