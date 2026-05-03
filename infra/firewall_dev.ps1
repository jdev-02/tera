# TERA dev firewall helper — Windows only.
# Blocks all inbound TCP to port 8000 except from 127.0.0.1.
# Run BEFORE starting `make run` on a shared WiFi (hackathon venue, cafe, campus).
#
# Usage:
#   .\infra\firewall_dev.ps1          # add rule (default)
#   .\infra\firewall_dev.ps1 remove   # remove rule
#   .\infra\firewall_dev.ps1 status   # check if rule is active
#
# Requires: PowerShell running as Administrator

param(
    [ValidateSet("add", "remove", "status")]
    [string]$Action = "add"
)

$RULE_NAME = "TERA-block-8000"
$PORT      = 8000

function Test-Admin {
    $identity  = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal] $identity
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Admin)) {
    Write-Host ""
    Write-Host "  ERROR: Run this script as Administrator." -ForegroundColor Red
    Write-Host "  Right-click PowerShell -> 'Run as administrator'" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

switch ($Action) {

    "add" {
        $existing = Get-NetFirewallRule -DisplayName $RULE_NAME -ErrorAction SilentlyContinue
        if ($existing) {
            Write-Host ""
            Write-Host "  [OK] Rule '$RULE_NAME' already exists." -ForegroundColor Green
            Write-Host "       Port $PORT is already blocked from WiFi." -ForegroundColor Green
            Write-Host ""
            exit 0
        }

        New-NetFirewallRule `
            -DisplayName  $RULE_NAME `
            -Direction    Inbound `
            -Protocol     TCP `
            -LocalPort    $PORT `
            -RemoteAddress "0.0.0.0-126.255.255.255","128.0.0.0-255.255.255.255" `
            -Action       Block `
            -Profile      Any `
            -Enabled      True | Out-Null

        Write-Host ""
        Write-Host "  [ADDED] Rule '$RULE_NAME'" -ForegroundColor Green
        Write-Host "  Port $PORT now blocked for all remote IPs." -ForegroundColor Green
        Write-Host "  Only 127.0.0.1 (localhost) can reach the TERA server." -ForegroundColor Green
        Write-Host ""
        Write-Host "  Safe to run: uvicorn agent.app:app --host 127.0.0.1 --port $PORT" -ForegroundColor Cyan
        Write-Host ""
    }

    "remove" {
        $existing = Get-NetFirewallRule -DisplayName $RULE_NAME -ErrorAction SilentlyContinue
        if (-not $existing) {
            Write-Host ""
            Write-Host "  [INFO] Rule '$RULE_NAME' not found. Nothing to remove." -ForegroundColor Yellow
            Write-Host ""
            exit 0
        }

        Remove-NetFirewallRule -DisplayName $RULE_NAME
        Write-Host ""
        Write-Host "  [REMOVED] Rule '$RULE_NAME'" -ForegroundColor Yellow
        Write-Host "  Port $PORT is no longer firewall-blocked." -ForegroundColor Yellow
        Write-Host "  Remember: only use --host 127.0.0.1 on shared networks." -ForegroundColor Yellow
        Write-Host ""
    }

    "status" {
        $existing = Get-NetFirewallRule -DisplayName $RULE_NAME -ErrorAction SilentlyContinue
        Write-Host ""
        if ($existing) {
            $state = if ($existing.Enabled -eq "True") { "ACTIVE" } else { "DISABLED" }
            Write-Host "  [STATUS] Rule '$RULE_NAME': $state" -ForegroundColor Green
            Write-Host "  Port $PORT is protected from WiFi access." -ForegroundColor Green
        } else {
            Write-Host "  [STATUS] Rule '$RULE_NAME': NOT FOUND" -ForegroundColor Red
            Write-Host "  Port $PORT has no firewall block. Run: .\infra\firewall_dev.ps1 add" -ForegroundColor Red
        }
        Write-Host ""
    }
}
