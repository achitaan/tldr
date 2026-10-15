. (Join-Path $PSScriptRoot 'common.ps1')
# Deliberately do not load AI credentials for verification.
Push-Location $BackendRoot
try {
    & $PythonExe manage.py check
    Assert-ExitCode 'Django checks'
    & $PythonExe manage.py test study
    Assert-ExitCode 'Backend tests'
} finally { Pop-Location }
Push-Location $FrontendRoot
try {
    npm.cmd run build
    Assert-ExitCode 'Frontend build'
    npm.cmd run lint
    Assert-ExitCode 'Frontend lint'
    npm.cmd test
    Assert-ExitCode 'Frontend tests'
} finally { Pop-Location }
