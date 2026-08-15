@echo off
cd /d "%~dp0"
if not exist "capture_v141" mkdir "capture_v141"
echo [1/2] Starting PF v141 destination population continuity...
start "" /b py -3 -u "%~dp0pf_login_game_server_v141.py" 1>"%~dp0capture_v141\server_console_live.out.txt" 2>"%~dp0capture_v141\server_console_live.err.txt"
ping 127.0.0.1 -n 1 >nul
echo [2/2] Starting local GameClient...
start "" "%~dp0GameClient.local.bin" -launchbypatcher -subbuildversion 132 -acc test -pwd test
exit /b
