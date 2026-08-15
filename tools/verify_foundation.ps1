$ErrorActionPreference = 'Stop'
function Assert-NativeSuccess {
    param([Parameter(Mandatory=$true)][int]$ExitCode,
          [Parameter(Mandatory=$true)][string]$Step)
    if ($ExitCode -ne 0) { throw "NATIVE STEP FAILED ($ExitCode): $Step" }
}

# Guard the verifier itself: a nonzero native exit must become a terminating error.
$failFastDetected = $false
try {
    py -3 -c "raise SystemExit(23)" 2>$null
    Assert-NativeSuccess -ExitCode $LASTEXITCODE -Step 'fail-fast self-check'
}
catch { $failFastDetected = $true }
if (-not $failFastDetected) { throw 'VERIFIER SELF-CHECK FAILED: native errors are not fatal' }

py -3 -m py_compile current\pf_login_game_server_v141.py
Assert-NativeSuccess -ExitCode $LASTEXITCODE -Step 'legacy py_compile'
py -3 -m compileall -q src tests tools\build_foundation_release.py
Assert-NativeSuccess -ExitCode $LASTEXITCODE -Step 'source/test compileall'
py -3 -m py_compile tools\wait_for_pf_stage.py
Assert-NativeSuccess -ExitCode $LASTEXITCODE -Step 'stage waiter py_compile'
py -3 -m py_compile tools\pf_relation_probe.py
Assert-NativeSuccess -ExitCode $LASTEXITCODE -Step 'relation probe py_compile'
py -3 -m py_compile tools\pf_relation_matrix_probe.py
Assert-NativeSuccess -ExitCode $LASTEXITCODE -Step 'relation matrix probe py_compile'
py -3 -m py_compile tools\pf_action_producer_probe.py
Assert-NativeSuccess -ExitCode $LASTEXITCODE -Step 'action producer probe py_compile'
py -3 -m py_compile tools\pf_action_consumer_probe.py
Assert-NativeSuccess -ExitCode $LASTEXITCODE -Step 'action consumer probe py_compile'
py -3 -m py_compile tools\pf_hit_result_probe.py
Assert-NativeSuccess -ExitCode $LASTEXITCODE -Step 'hit result probe py_compile'
py -3 -m py_compile tools\pf_behavior_lookup_probe.py
Assert-NativeSuccess -ExitCode $LASTEXITCODE -Step 'behavior lookup probe py_compile'
py -3 -m py_compile tools\pf_behavior_entry_probe.py
Assert-NativeSuccess -ExitCode $LASTEXITCODE -Step 'behavior entry probe py_compile'
py -3 -m py_compile tools\pf_behavior_range_gate_probe.py
Assert-NativeSuccess -ExitCode $LASTEXITCODE -Step 'behavior range gate probe py_compile'
py -3 -m py_compile tools\pf_structural_corpus_audit.py
Assert-NativeSuccess -ExitCode $LASTEXITCODE -Step 'structural corpus audit py_compile'
py -3 -m py_compile tools\scene_db_guard.py
Assert-NativeSuccess -ExitCode $LASTEXITCODE -Step 'database guard py_compile'
[void][scriptblock]::Create((Get-Content -Raw tools\run_test_arena.ps1))
[void][scriptblock]::Create((Get-Content -Raw tools\run_scene2_load_only.ps1))
py -3 current\pf_login_game_server_v141.py --self-test-only
Assert-NativeSuccess -ExitCode $LASTEXITCODE -Step 'legacy self-test'
py -3 -m unittest discover -s tests -v
Assert-NativeSuccess -ExitCode $LASTEXITCODE -Step 'Foundation unit tests'
$tracked = git ls-files
Assert-NativeSuccess -ExitCode $LASTEXITCODE -Step 'git ls-files'
$bad = $tracked | Where-Object { $_ -match '^(references|evidence|backups|packages|derived|analysis|history|v77_video_frames|capture[^/]*)/' -or $_ -match '\.(zip|7z|rar|exe|dll|pyd|pyc|bin|db|sqlite|sqlite3|png|jpe?g|gif|mp4|pcap|cap)$' }
if ($bad) { $bad; throw 'FORBIDDEN TRACKED PATH' }
foreach ($probe in @('src/__probe.exe','tests/__probe.png','docs/__probe.zip','src/__probe.bin')) {
    git check-ignore -q --no-index -- $probe
    if ($LASTEXITCODE -ne 0) { throw "GITIGNORE FAILED FOR $probe" }
}
git diff --cached --check
Assert-NativeSuccess -ExitCode $LASTEXITCODE -Step 'staged diff hygiene'
git diff --check
Assert-NativeSuccess -ExitCode $LASTEXITCODE -Step 'worktree diff hygiene'

$qaRoot = [IO.Path]::Combine([IO.Path]::GetTempPath(), 'pf-foundation-' + [Guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($qaRoot) | Out-Null
try {
    $releaseA = [IO.Path]::Combine($qaRoot, 'a.zip')
    $releaseB = [IO.Path]::Combine($qaRoot, 'b.zip')
    py -3 tools\build_foundation_release.py --output $releaseA | Out-Null
    Assert-NativeSuccess -ExitCode $LASTEXITCODE -Step 'release archive A'
    py -3 tools\build_foundation_release.py --output $releaseB | Out-Null
    Assert-NativeSuccess -ExitCode $LASTEXITCODE -Step 'release archive B'
    @'
import hashlib, sys, zipfile
expected = {
    'current/pf_login_game_server_v141.py',
    'migrations/001_initial.sql',
    'migrations/002_character_integrity.sql',
    'scenarios/arena_v1.json',
    'scenarios/arena_v2.json',
    'scenarios/scene2_load_only.json',
    'scenarios/scene2_fighting_fish_soldier.json',
    'scenarios/scene2_fighting_fish_soldier_hp3857.json',
    'scenarios/scene2_fighting_fish_soldier_hp3857_player_faction1.json',
    'scenarios/port_royal_fighting_fish_soldier_hp3857_player_faction1_ea7d_ack.json',
    'src/pirateforce_foundation/__init__.py',
    'src/pirateforce_foundation/action_ack.py',
    'src/pirateforce_foundation/actor_wire.py',
    'src/pirateforce_foundation/app.py',
    'src/pirateforce_foundation/legacy_bridge.py',
    'src/pirateforce_foundation/lifecycle.py',
    'src/pirateforce_foundation/model.py',
    'src/pirateforce_foundation/npc_wire.py',
    'src/pirateforce_foundation/player_wire.py',
    'src/pirateforce_foundation/repository.py',
    'src/pirateforce_foundation/runtime.py',
    'src/pirateforce_foundation/scenario.py',
    'src/pirateforce_foundation/scene_load.py',
    'src/pirateforce_foundation/scene_object.py',
    'src/pirateforce_foundation/session.py',
    'src/pirateforce_foundation/store.py',
    'tools/PF_FAST_ENTRY_AUTOMATION.md',
    'tools/pf_relation_probe.py',
    'tools/pf_relation_probe_config.json',
    'tools/pf_relation_matrix_probe.py',
    'tools/pf_action_producer_probe.py',
    'tools/pf_action_producer_probe_config.json',
    'tools/pf_action_producer_probe_local_config.json',
    'tools/pf_action_consumer_probe.py',
    'tools/pf_action_consumer_probe_config.json',
    'tools/pf_action_consumer_probe_local_config.json',
    'tools/pf_hit_result_probe.py',
    'tools/pf_hit_result_probe_config.json',
    'tools/pf_hit_result_probe_local_config.json',
    'tools/pf_behavior_lookup_probe.py',
    'tools/pf_behavior_lookup_probe_config.json',
    'tools/pf_behavior_lookup_probe_local_config.json',
    'tools/pf_behavior_entry_probe.py',
    'tools/pf_behavior_entry_probe_config.json',
    'tools/pf_behavior_entry_probe_local_config.json',
    'tools/pf_behavior_range_gate_probe.py',
    'tools/pf_behavior_range_gate_probe_config.json',
    'tools/pf_behavior_range_gate_probe_local_config.json',
    'tools/pf_structural_corpus_audit.py',
    'tools/pf_structural_corpus_audit_config.json',
    'tools/run_test_arena.ps1',
    'tools/run_scene2_load_only.ps1',
    'tools/scene_db_guard.py',
    'tools/wait_for_pf_stage.py',
}
a, b = map(__import__('pathlib').Path, sys.argv[1:])
assert hashlib.sha256(a.read_bytes()).digest() == hashlib.sha256(b.read_bytes()).digest()
with zipfile.ZipFile(a) as z:
    assert z.testzip() is None
    assert set(z.namelist()) == expected
'@ | py -3 - $releaseA $releaseB
    Assert-NativeSuccess -ExitCode $LASTEXITCODE -Step 'deterministic release/member verification'
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
