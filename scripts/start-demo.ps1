param([string]$DemoPassword)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
if (-not $DemoPassword) {
    $securePassword = Read-Host 'Demo password (at least 8 characters)' -AsSecureString
    $DemoPassword = [System.Net.NetworkCredential]::new('', $securePassword).Password
}
$env:DEMO_PASSWORD = $DemoPassword
$env:DEMO_MODE = 'true'
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) { python -m venv .venv }
& '.venv/Scripts/python.exe' -m pip install -r backend/requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed' }
& '.venv/Scripts/python.exe' backend/manage.py init
& '.venv/Scripts/python.exe' backend/manage.py seed
if ($LASTEXITCODE -ne 0) { throw 'Database initialization failed' }
$backendProcess = Start-Process -FilePath "$projectRoot/.venv/Scripts/python.exe" -ArgumentList 'backend/run.py' -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru
try {
    Set-Location -LiteralPath "$projectRoot/frontend"
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        if (-not (Test-Path -LiteralPath node_modules)) { npm install }
        Write-Host 'Open http://127.0.0.1:5173. Accounts: analyst, reviewer, admin. Ctrl+C stops the frontend.'
        npm run dev
    } else {
        $nodeDirectory = Split-Path (Get-Command node).Source -Parent
        $bundledPnpm = Join-Path (Split-Path $nodeDirectory -Parent) 'node_modules/pnpm/bin/pnpm.cjs'
        if (-not (Test-Path -LiteralPath $bundledPnpm)) { throw 'Install Node.js with npm, or provide pnpm' }
        if (-not (Test-Path -LiteralPath node_modules)) { node $bundledPnpm install }
        Write-Host 'Open http://127.0.0.1:5173. Accounts: analyst, reviewer, admin. Ctrl+C stops the frontend.'
        node node_modules/vite/bin/vite.js --host 127.0.0.1
    }
} finally {
    Stop-Process -Id $backendProcess.Id -ErrorAction SilentlyContinue
}
