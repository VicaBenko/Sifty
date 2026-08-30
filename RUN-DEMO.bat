@echo off
title Sift - Demo Server
cd /d "%USERPROFILE%\Sift"

rem --- optional: needed only for NEW queries that are not in the cache ---
rem set ANTHROPIC_API_KEY=sk-ant-...

echo.
echo   Restoring the photo set...
python demo\reset.py
echo.
echo   Sift demo starting...
echo   Browser will open in a moment.
echo.
echo   KEEP THIS WINDOW OPEN while you use the demo.
echo   Close it to stop the server.
echo.

start "" /b cmd /c "timeout /t 3 /nobreak >nul & start "" http://127.0.0.1:8091"

python demo\serve.py --port 8091

echo.
echo   Server stopped.
pause
