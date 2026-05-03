@echo off
REM One-shot local setup script for MF Intelligence (Windows).
REM Usage: setup.bat

setlocal EnableDelayedExpansion
set ROOT=%~dp0

echo ==^> Project root: %ROOT%

REM --- Backend env ---
if not exist "%ROOT%backend\.env" (
    echo ==^> Creating backend\.env from template
    copy "%ROOT%backend\.env.example" "%ROOT%backend\.env" >nul
    for /f %%i in ('python -c "import secrets;print(secrets.token_hex(32))"') do set SECRET=%%i
    powershell -Command "(Get-Content '%ROOT%backend\.env') -replace 'replace-me-with-a-64-char-hex-secret', '!SECRET!' | Set-Content '%ROOT%backend\.env'"
    echo     JWT_SECRET generated automatically.
)

REM --- Frontend env ---
if not exist "%ROOT%frontend\.env" (
    echo ==^> Creating frontend\.env from template
    copy "%ROOT%frontend\.env.example" "%ROOT%frontend\.env" >nul
)

REM --- Backend deps ---
echo ==^> Installing backend Python deps...
cd /d "%ROOT%backend"
if not exist ".venv" (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ -r requirements.txt
call .venv\Scripts\deactivate.bat

REM --- Frontend deps ---
echo ==^> Installing frontend deps (yarn)...
cd /d "%ROOT%frontend"
where yarn >nul 2>nul
if errorlevel 1 (
    echo ERROR: yarn not found. Install with: npm install -g yarn
    exit /b 1
)
call yarn install

cd /d "%ROOT%"

echo.
echo ==^> Setup complete.
echo.
echo Next steps:
echo   1. (Optional) Edit backend\.env and add RESEND_API_KEY / EMERGENT_LLM_KEY
echo   2. Start MongoDB:  docker run -d -p 27017:27017 --name mongo mongo:7
echo   3. Start backend:
echo        cd backend ^&^& .venv\Scripts\activate ^&^& uvicorn server:app --reload --port 8001
echo   4. Start frontend (new terminal):
echo        cd frontend ^&^& yarn start
echo   5. Open http://localhost:3000   (admin@mfintel.com / Admin@12345)
echo.
echo Or:  docker compose up --build
endlocal
