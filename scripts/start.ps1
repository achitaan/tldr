[CmdletBinding()]
param()
. (Join-Path $PSScriptRoot 'common.ps1')
Import-LocalConfiguration
if (-not (Test-Path -LiteralPath $PythonExe)) { throw 'Run .\scripts\setup.ps1 -WithRenderer first.' }
$logDirectory = Join-Path $ProjectRoot 'artifacts\logs'
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
$processes = @()
try {
    Push-Location $BackendRoot
    try { & $PythonExe manage.py migrate --noinput; Assert-ExitCode 'Database migration' } finally { Pop-Location }
    $processes += Start-Process -FilePath $PythonExe -ArgumentList @('manage.py', 'runserver', '127.0.0.1:8765', '--noreload') -WorkingDirectory $BackendRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDirectory 'api.log') -RedirectStandardError (Join-Path $logDirectory 'api-error.log')
    $processes += Start-Process -FilePath $PythonExe -ArgumentList @('manage.py', 'study_worker') -WorkingDirectory $BackendRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDirectory 'worker.log') -RedirectStandardError (Join-Path $logDirectory 'worker-error.log')
    $nodeExe = (Get-Command node.exe).Source
    $viteEntry = Join-Path $FrontendRoot 'node_modules\vite\bin\vite.js'
    $processes += Start-Process -FilePath $nodeExe -ArgumentList @(('"' + $viteEntry + '"'), '--host', '127.0.0.1', '--port', '5173', '--strictPort') -WorkingDirectory $FrontendRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDirectory 'web.log') -RedirectStandardError (Join-Path $logDirectory 'web-error.log')
    Write-Host 'TLDR: http://127.0.0.1:5173  |  Static demo: http://127.0.0.1:5173/?demo=1'
    Write-Host 'Keep this terminal open. Ctrl+C stops these three processes. Logs: artifacts/logs'
    while ($true) {
        foreach ($child in $processes) {
            if ($child.HasExited) { throw "A TLDR process exited. See logs in $logDirectory." }
        }
        Start-Sleep -Seconds 1
    }
} finally {
    foreach ($child in $processes) {
        if (-not $child.HasExited) {
            # Stop only processes launched here, including an active Manim child.
            & taskkill.exe /PID $child.Id /T /F 2>$null | Out-Null
        }
    }
}
