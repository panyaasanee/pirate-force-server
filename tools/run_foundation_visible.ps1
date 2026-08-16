param(
    [string]$Database = "state\pirateforce.sqlite3",
    [ValidateSet('required','bypass')]
    [string]$SecondPasswordMode = 'required',
    [string]$CaptureRoot = ''
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$clientRoot = Join-Path (Split-Path -Parent $root) 'GameClient'
$databasePath = [IO.Path]::GetFullPath((Join-Path $root $Database))
if (-not (Test-Path -LiteralPath $databasePath -PathType Leaf)) {
    throw "Existing database not found: $databasePath"
}
$occupied = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object { $_.LocalPort -in 10188, 10189 }
if ($occupied) { throw 'Pirate Force login/game ports are already in use' }
if (-not $CaptureRoot) {
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $CaptureRoot = Join-Path $clientRoot "capture_foundation_manual_$stamp"
}
$capturePath = [IO.Path]::GetFullPath($CaptureRoot)
New-Item -ItemType Directory -Path $capturePath -ErrorAction Stop | Out-Null
$env:PYTHONPATH = Join-Path $root 'src'
$serverArgs = @(
    '-3', '-u', '-m', 'pirateforce_foundation.app',
    '--db', ('"' + $databasePath + '"'),
    '--capture-root', ('"' + $capturePath + '"'),
    '--second-password-mode', $SecondPasswordMode
)
$server = Start-Process -FilePath 'py' -ArgumentList $serverArgs `
    -WorkingDirectory $root -WindowStyle Normal -PassThru
Write-Host "Visible Foundation console PID: $($server.Id)"
Write-Host "Summary/raw capture root: $capturePath"
Write-Host 'Stop the server with Ctrl+C in its visible console.'
