[CmdletBinding()]
param([switch]$WithRenderer)
. (Join-Path $PSScriptRoot 'common.ps1')
Push-Location $ProjectRoot
try {
    if (-not (Test-Path -LiteralPath $PythonExe)) {
        python -m venv backend/.venv
        Assert-ExitCode 'Creating the Python environment'
    }
    $pythonVersion = & $PythonExe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    $constraints = @()
    if ($pythonVersion -eq '3.10') { $constraints = @('-c', 'backend/constraints-windows-py310.txt') }
    & $PythonExe -m pip install -r backend/requirements.txt @constraints
    Assert-ExitCode 'Installing backend dependencies'
    if ($WithRenderer) {
        & $PythonExe -m pip install -r backend/requirements-render.txt @constraints
        Assert-ExitCode 'Installing renderer dependencies'
    }
    Push-Location $FrontendRoot
    try { npm.cmd ci; Assert-ExitCode 'Installing frontend dependencies' } finally { Pop-Location }
    Import-LocalConfiguration
    Push-Location $BackendRoot
    try { & $PythonExe manage.py migrate; Assert-ExitCode 'Creating the local database' } finally { Pop-Location }
    Write-Host 'Setup complete. Run .\scripts\start.ps1. AI remains disabled until configured.'
} finally { Pop-Location }
