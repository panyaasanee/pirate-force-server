$ErrorActionPreference = 'Stop'
py -3 -m py_compile current\pf_login_game_server_v141.py
py -3 current\pf_login_game_server_v141.py --self-test-only
py -3 -m unittest discover -s tests -v
$tracked = git ls-files
$bad = $tracked | Where-Object { $_ -match '^(references|evidence|backups|packages|derived|analysis|history|v77_video_frames|capture[^/]*)/' -or $_ -match '\.(zip|7z|rar|exe|dll|pyd|pyc|bin|db|sqlite|sqlite3|png|jpe?g|gif|mp4|pcap|cap)$' }
if ($bad) { $bad; throw 'FORBIDDEN TRACKED PATH' }
git diff --cached --check
Write-Host '[FOUNDATION] deterministic verification PASS'
