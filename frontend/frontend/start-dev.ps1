$ErrorActionPreference = 'Stop'

# Use a normal Node.js installation when available.
$nodeCommand = Get-Command node -ErrorAction SilentlyContinue
if ($nodeCommand) {
  npm install
  npm run dev
  exit $LASTEXITCODE
}

# Fallback for the Codex desktop bundled runtime.
$bundledNode = 'C:\Users\LOQ\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin'
$bundledPnpm = 'C:\Users\LOQ\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\fallback\pnpm.cmd'

if (-not (Test-Path (Join-Path $bundledNode 'node.exe')) -or -not (Test-Path $bundledPnpm)) {
  Write-Host 'Node.js was not found.' -ForegroundColor Yellow
  Write-Host 'Install Node.js LTS, reopen PowerShell, and run this script again.'
  exit 1
}

$env:PATH = "$bundledNode;$env:PATH"
& $bundledPnpm install
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $bundledPnpm dev --host 127.0.0.1
