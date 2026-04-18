@echo off
echo Starting Node.js Express server on port 8090...
cd /d "%~dp0server\node"
call npm install
call npm start
pause
