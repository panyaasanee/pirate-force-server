$ErrorActionPreference = 'Stop'
py -3 -m py_compile current\pf_login_game_server_v141.py
py -3 -m compileall -q src tests tools\build_foundation_release.py
py -3 -m py_compile tools\wait_for_pf_stage.py
[void][scriptblock]::Create((Get-Content -Raw tools\run_test_arena.ps1))
py -3 current\pf_login_game_server_v141.py --self-test-only
py -3 -m unittest discover -s tests -v
$tracked = git ls-files
$bad = $tracked | Where-Object { $_ -match '^(references|evidence|backups|packages|derived|analysis|history|v77_video_frames|capture[^/]*)/' -or $_ -match '\.(zip|7z|rar|exe|dll|pyd|pyc|bin|db|sqlite|sqlite3|png|jpe?g|gif|mp4|pcap|cap)$' }
if ($bad) { $bad; throw 'FORBIDDEN TRACKED PATH' }
foreach ($probe in @('src/__probe.exe','tests/__probe.png','docs/__probe.zip','src/__probe.bin')) {
    git check-ignore -q --no-index -- $probe
    if ($LASTEXITCODE -ne 0) { throw "GITIGNORE FAILED FOR $probe" }
}
git diff --cached --check
git diff --check

$qaRoot = [IO.Path]::Combine([IO.Path]::GetTempPath(), 'pf-foundation-' + [Guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($qaRoot) | Out-Null
try {
    $releaseA = [IO.Path]::Combine($qaRoot, 'a.zip')
    $releaseB = [IO.Path]::Combine($qaRoot, 'b.zip')
    py -3 tools\build_foundation_release.py --output $releaseA | Out-Null
    py -3 tools\build_foundation_release.py --output $releaseB | Out-Null
    @'
import hashlib, sys, zipfile
expected = {
    'current/pf_login_game_server_v141.py',
    'migrations/001_initial.sql',
    'migrations/002_character_integrity.sql',
    'scenarios/arena_v1.json',
    'src/pirateforce_foundation/__init__.py',
    'src/pirateforce_foundation/actor_wire.py',
    'src/pirateforce_foundation/app.py',
    'src/pirateforce_foundation/legacy_bridge.py',
    'src/pirateforce_foundation/lifecycle.py',
    'src/pirateforce_foundation/model.py',
    'src/pirateforce_foundation/repository.py',
    'src/pirateforce_foundation/runtime.py',
    'src/pirateforce_foundation/scenario.py',
    'src/pirateforce_foundation/session.py',
    'src/pirateforce_foundation/store.py',
    'tools/PF_FAST_ENTRY_AUTOMATION.md',
    'tools/run_test_arena.ps1',
    'tools/wait_for_pf_stage.py',
}
a, b = map(__import__('pathlib').Path, sys.argv[1:])
assert hashlib.sha256(a.read_bytes()).digest() == hashlib.sha256(b.read_bytes()).digest()
with zipfile.ZipFile(a) as z:
    assert z.testzip() is None
    assert set(z.namelist()) == expected
'@ | py -3 - $releaseA $releaseB
}
finally {
    $fullQaRoot = [IO.Path]::GetFullPath($qaRoot)
    $fullTemp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    if (-not $fullQaRoot.StartsWith($fullTemp, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Unsafe QA temp path'
    }
    [IO.Directory]::Delete($fullQaRoot, $true)
}
Write-Host '[FOUNDATION] deterministic verification PASS'
