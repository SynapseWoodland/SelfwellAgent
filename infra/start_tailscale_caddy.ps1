# Selfwell Agent: one-shot startup for Tailscale Funnel + Caddy (port 8000)
# Steps:
#   1) Launch C:\Program Files\Tailscale\tailscale-ipn.exe
#   2) Enable public exposure: tailscale funnel --bg 8000
#   3) cd into D:\agent-project\SelfwellAgent\infra\caddy and run caddy with Caddyfile
#
# Usage (PowerShell 5.1 or 7+):
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\infra\start_tailscale_caddy.ps1
#
# Stop:
#   Ctrl+C to stop Caddy
#   tailscale funnel --bg off   (or: tailscale funnel off)
#   Task Manager -> tailscale-ipn.exe

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$TailscaleExe = "C:\Program Files\Tailscale\tailscale-ipn.exe"
$FunnelPort   = 8000
$CaddyDir     = "D:\agent-project\SelfwellAgent\infra\caddy"
$CaddyExe     = ".\caddy_windows_amd64.exe"
$CaddyCfg     = "D:\agent-project\SelfwellAgent\infra\caddy\Caddyfile"
$LogDir       = "$env:TEMP\selfwell_startup"
$LogFile      = "$LogDir\start_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

function Log([string]$Msg) {
    $Line = "[$(Get-Date -Format 'HH:mm:ss')] $Msg"
    Write-Output $Line
    Add-Content -Path $LogFile -Value $Line -Encoding UTF8
}

Log "================================================="
Log "Start: Tailscale Funnel + Caddy (port $FunnelPort)"
Log "Log:   $LogFile"
Log "================================================="

# ============================================
# Step 1: Launch Tailscale
# ============================================
Log ""
Log "-- Step 1: Launch Tailscale --"
if (-not (Test-Path $TailscaleExe)) {
    Log "[X] Tailscale not found: $TailscaleExe"
    Log "    Install from https://tailscale.com/download/windows"
    exit 1
}

# tailscale-ipn.exe is the tray/GUI process. Skip if already running.
$TailscaleProc = Get-Process -Name "tailscale-ipn" -ErrorAction SilentlyContinue
if ($TailscaleProc) {
    Log "[OK] Tailscale already running (PID=$($TailscaleProc.Id))"
}
if (-not $TailscaleProc) {
    Log "[..] Starting tailscale-ipn.exe ..."
    Start-Process -FilePath $TailscaleExe
    Start-Sleep -Seconds 3
    $TailscaleProc = Get-Process -Name "tailscale-ipn" -ErrorAction SilentlyContinue
    if ($TailscaleProc) {
        Log "[OK] Tailscale started (PID=$($TailscaleProc.Id))"
    }
    if (-not $TailscaleProc) {
        Log "[!] tailscale-ipn.exe did not start, continuing anyway"
    }
}

# ============================================
# Step 2: tailscale funnel --bg 8000
# ============================================
Log ""
Log "-- Step 2: tailscale funnel --bg $FunnelPort --"
$FunnelOk = $false
try {
    $FunnelOut = & "$TailscaleExe" funnel --bg $FunnelPort 2>&1
    $FunnelExit = $LASTEXITCODE
    Log "  exit=$FunnelExit"
    Log "  output: $($FunnelOut -join ' | ')"
    if ($FunnelExit -ne 0) {
        Log "[!] funnel returned non-zero, continuing (common causes: not logged in / HTTPS disabled / MagicDNS off)"
    }
    if ($FunnelExit -eq 0) {
        Log "[OK] Funnel configured"
        $FunnelOk = $true
    }
}
catch {
    Log "[X] funnel exception: $_"
    Log "    Debug: tailscale status  /  tailscale set --auto-update"
    exit 1
}

# ============================================
# Step 3: Start Caddy
# ============================================
Log ""
Log "-- Step 3: Start Caddy --"
if (-not (Test-Path $CaddyCfg)) {
    Log "[X] Caddyfile not found: $CaddyCfg"
    exit 1
}
$CaddyExeFull = Join-Path $CaddyDir "caddy_windows_amd64.exe"
if (-not (Test-Path $CaddyExeFull)) {
    Log "[X] Caddy binary not found: $CaddyExeFull"
    exit 1
}

Log "  cd $CaddyDir"
Log "  $CaddyExe run --config $CaddyCfg"
Log ""
Log "  >> Caddy runs in foreground. Ctrl+C to stop."
Log "  >> Log file: $LogFile"
Log "================================================="

Push-Location $CaddyDir
try {
    & $CaddyExe run --config $CaddyCfg
}
finally {
    Pop-Location
    Log ""
    Log "-- Caddy exited --"
}