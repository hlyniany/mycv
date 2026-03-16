# Extract CV data from HTML file and convert to JSONResume format
# Initial extraction - adds IT domain to all entries by default

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir

Push-Location $projectRoot

Write-Host "Running HTML to JSONResume extraction..." -ForegroundColor Cyan

# Use the configured Python path
$pythonCmd = "C:/Users/sk5091540/AppData/Local/Microsoft/WindowsApps/python3.11.exe"

& $pythonCmd scripts/read_html_initial.py

Write-Host ""
Write-Host "✓ Extraction complete!" -ForegroundColor Green
Write-Host "✓ Review the output in: review/cv.resume.json" -ForegroundColor Yellow
Write-Host "✓ Modify domains as needed, then use the data/cv.resume.json for generation" -ForegroundColor Yellow

Pop-Location
