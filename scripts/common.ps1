$ErrorActionPreference = 'Stop'
$script:ProjectRoot = Split-Path $PSScriptRoot -Parent
$script:BackendRoot = Join-Path $script:ProjectRoot 'backend\tldr_backend'
$script:FrontendRoot = Join-Path $script:ProjectRoot 'frontend\tldr-frontend'
$script:PythonExe = Join-Path $script:ProjectRoot 'backend\.venv\Scripts\python.exe'
function Import-LocalConfiguration {
    $config = Join-Path $script:ProjectRoot '.env.local'
    if (-not (Test-Path -LiteralPath $config)) { return }
    $allowed = @('GEMINI_API_KEY', 'TLDR_GEMINI_MODEL', 'TLDR_FREE_PROJECT_ACK', 'TLDR_DATA_TERMS_ACK', 'TLDR_OLLAMA_EMBEDDINGS', 'OLLAMA_NO_CLOUD', 'TESSERACT_CMD', 'TLDR_DATA_DIR', 'DJANGO_SECRET_KEY')
    foreach ($line in Get-Content -LiteralPath $config) {
        if ($line -match '^\s*(#|$)') { continue }
        if ($line -notmatch '^([A-Z_][A-Z_0-9]*)=(.*)$') { throw 'Invalid .env.local entry. Use NAME=value without shell commands.' }
        $configName = $Matches[1]
        $configValue = $Matches[2].Trim()
        if ($configName -notin $allowed) { throw "Unknown local configuration name: $configName" }
        [Environment]::SetEnvironmentVariable($configName, $configValue, 'Process')
    }
}
function Assert-ExitCode([string]$operation) {
    if ($LASTEXITCODE -ne 0) { throw "$operation failed (exit $LASTEXITCODE)." }
}
