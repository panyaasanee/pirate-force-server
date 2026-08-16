param(
    [string]$Scenario = "scenarios\arena_v1.json",
    [string]$Database = "state\test_arena_v1.sqlite3"
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$clientRoot = Join-Path (Split-Path -Parent $root) 'GameClient'
$client = Join-Path $clientRoot 'GameClient.local.bin'
$scenarioPath = Join-Path $root $Scenario
$databasePath = Join-Path $root $Database
if (-not (Test-Path -LiteralPath $scenarioPath -PathType Leaf)) { throw "Scenario not found: $scenarioPath" }
if (-not (Test-Path -LiteralPath $client -PathType Leaf)) { throw "Client not found: $client" }
$scenarioId = (Get-Content -Raw -LiteralPath $scenarioPath | ConvertFrom-Json).id
$captureLabel = switch ($scenarioId) {
    'arena_v1_player_p30_target' { 'arena_v1' }
    'arena_v2_p30_basic_faction6_diagnostic' { 'arena_v2' }
    default { throw "Scenario id is not in the Arena launcher allowlist: $scenarioId" }
}

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$capture = Join-Path $clientRoot "capture_${captureLabel}_$stamp"
New-Item -ItemType Directory -Path $capture | Out-Null
$stdout = Join-Path $capture 'server_console_live.out.txt'
$stderr = Join-Path $capture 'server_console_live.err.txt'
$env:PYTHONPATH = Join-Path $root 'src'
$occupied = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object { $_.LocalPort -in 10188, 10189 }
if ($occupied) { throw 'Pirate Force login/game ports are already in use' }

$serverArgs = @(
    '-3', '-u', '-m', 'pirateforce_foundation.app',
    '--scenario', ('"' + $scenarioPath + '"'),
    '--db', ('"' + $databasePath + '"'),
    '--capture-root', ('"' + $capture + '"')
)
$server = Start-Process -FilePath 'py' -ArgumentList $serverArgs -WorkingDirectory $root `
    -WindowStyle Normal -PassThru
Set-Content -LiteralPath (Join-Path $capture 'server.pid') -Value $server.Id -Encoding ascii
$deadline = [DateTime]::UtcNow.AddSeconds(15)
do {
    if ($server.HasExited) { throw "Arena server exited before listening; inspect $stderr" }
    $loginReady = Get-NetTCPConnection -State Listen -LocalPort 10188 -ErrorAction SilentlyContinue
    $gameReady = Get-NetTCPConnection -State Listen -LocalPort 10189 -ErrorAction SilentlyContinue
    $ready = $loginReady -and $gameReady
    if (-not $ready) { Start-Sleep -Milliseconds 100 }
} while (-not $ready -and [DateTime]::UtcNow -lt $deadline)
if (-not $ready) { throw "Arena server did not listen within 15 seconds; inspect $stderr" }
Set-Content -LiteralPath (Join-Path $capture 'listener.pid') `
    -Value $loginReady[0].OwningProcess -Encoding ascii
$clientInfo = [Diagnostics.ProcessStartInfo]::new()
$clientInfo.FileName = $client
$clientInfo.WorkingDirectory = $clientRoot
$clientInfo.UseShellExecute = $false
$clientInfo.Arguments = '-launchbypatcher -subbuildversion 132 -acc test -pwd test'
$clientProcess = [Diagnostics.Process]::Start($clientInfo)
if (-not $clientProcess) { throw 'GameClient process could not be created' }
Set-Content -LiteralPath (Join-Path $capture 'client.pid') `
    -Value $clientProcess.Id -Encoding ascii
Write-Host "Test Arena capture: $capture"
Write-Host "Arena server PID: $($server.Id)"
Write-Host "GameClient PID: $($clientProcess.Id)"
