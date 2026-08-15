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

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$capture = Join-Path $clientRoot "capture_arena_v1_$stamp"
New-Item -ItemType Directory -Path $capture | Out-Null
$stdout = Join-Path $capture 'server_console_live.out.txt'
$stderr = Join-Path $capture 'server_console_live.err.txt'
$env:PYTHONPATH = Join-Path $root 'src'
$occupied = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object { $_.LocalPort -in 10001, 10189 }
if ($occupied) { throw 'Pirate Force login/game ports are already in use' }

$serverArgs = @(
    '-3', '-u', '-m', 'pirateforce_foundation.app',
    '--scenario', ('"' + $scenarioPath + '"'),
    '--db', ('"' + $databasePath + '"'),
    '--capture-root', ('"' + $capture + '"')
)
$server = Start-Process -FilePath 'py' -ArgumentList $serverArgs -WorkingDirectory $root `
    -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
Set-Content -LiteralPath (Join-Path $capture 'server.pid') -Value $server.Id -Encoding ascii
$deadline = [DateTime]::UtcNow.AddSeconds(15)
do {
    if ($server.HasExited) { throw "Arena server exited before listening; inspect $stderr" }
    $ready = Get-NetTCPConnection -State Listen -LocalPort 10001 -ErrorAction SilentlyContinue
    if (-not $ready) { Start-Sleep -Milliseconds 100 }
} while (-not $ready -and [DateTime]::UtcNow -lt $deadline)
if (-not $ready) { throw "Arena server did not listen within 15 seconds; inspect $stderr" }
Set-Content -LiteralPath (Join-Path $capture 'listener.pid') `
    -Value $ready[0].OwningProcess -Encoding ascii
Start-Process -FilePath $client -WorkingDirectory $clientRoot `
    -ArgumentList @('-launchbypatcher','-subbuildversion','132','-acc','test','-pwd','test')
Write-Host "Test Arena capture: $capture"
Write-Host "Arena server PID: $($server.Id)"
