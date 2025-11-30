# Schwab OAuth Authentication Script
# Run this in PowerShell from the project directory

$clientId = "npcUbrvmFA1x3c8KdahWTIvMv1VrWTkF"
$redirectUri = "https://127.0.0.1"
$authUrl = "https://api.schwabapi.com/v1/oauth/authorize?client_id=$clientId&redirect_uri=$redirectUri"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Schwab OAuth Token Generator" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Opening browser for authorization..." -ForegroundColor Yellow
Write-Host ""

Start-Process $authUrl

Write-Host "1. Log in to Schwab if prompted" -ForegroundColor White
Write-Host "2. Click 'Allow' to authorize the app" -ForegroundColor White
Write-Host "3. You'll be redirected to a page that won't load (that's OK!)" -ForegroundColor White
Write-Host "4. Copy the ENTIRE URL from your browser address bar" -ForegroundColor White
Write-Host ""
Write-Host "Paste the redirect URL here and press Enter:" -ForegroundColor Green

$redirectUrl = Read-Host

if ([string]::IsNullOrWhiteSpace($redirectUrl)) {
    Write-Host "No URL provided. Exiting." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Exchanging code for tokens..." -ForegroundColor Yellow

& .\venv\Scripts\python.exe exchange_code.py $redirectUrl

Write-Host ""
Write-Host "Done! If successful, you can now test with:" -ForegroundColor Cyan
Write-Host "  .\venv\Scripts\python.exe -m schwab_mcp.server" -ForegroundColor White
Write-Host ""
