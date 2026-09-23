Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "  Installing TraceX DVR Forensics Platform CLI        " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

if (Get-Command pipx -ErrorAction SilentlyContinue) {
    Write-Host "[+] Found pipx. Installing in an isolated environment..." -ForegroundColor Yellow
    pipx install git+https://github.com/byteforce101-ops/multi-vendor-dvr-forensics.git --force
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host "[+] Installing via Python pip..." -ForegroundColor Yellow
    python -m pip install --upgrade git+https://github.com/byteforce101-ops/multi-vendor-dvr-forensics.git
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    Write-Host "[+] Installing via Py launcher..." -ForegroundColor Yellow
    py -3 -m pip install --upgrade git+https://github.com/byteforce101-ops/multi-vendor-dvr-forensics.git
} else {
    Write-Host "[!] Error: Neither Python nor pipx was found on your system." -ForegroundColor Red
    Write-Host "    Please install Python 3.11+ and retry." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Green
Write-Host "  Installation Successful!                             " -ForegroundColor Green
Write-Host "  Run 'tracex' or 'dvrforensics' in PowerShell/CMD!   " -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Green
