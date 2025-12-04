# Quick Pipeline Runner - Single Virtual Environment
param(
    [Parameter(Mandatory=$true)]
    [string]$Url,
    
    [string]$Name = "",
    [switch]$SkipSetup = $false
)

$ErrorActionPreference = "Stop"
Write-Host "=== Voice Bot Pipeline Runner ==="

# Check if setup is needed
if (-not $SkipSetup -and -not (Test-Path ".venv")) {
    Write-Host "[INFO] Running first-time setup..."
    & .\scripts\setup_all.ps1
}

# Check OpenAI API key
if (-not $env:OPENAI_API_KEY) {
    Write-Warning "[WARNING] OPENAI_API_KEY not set"
    $apiKey = Read-Host "Enter your OpenAI API key (or press Enter to skip)"
    if ($apiKey) {
        $env:OPENAI_API_KEY = $apiKey
    }
}

# Activate virtual environment
Write-Host "[INFO] Activating virtual environment..."
& .\.venv\Scripts\Activate.ps1

# Build command
$cmd = "python pipeline_orchestrator.py --url `"$Url`" --config config.yaml"
if ($Name) {
    $cmd += " --name `"$Name`""
}

Write-Host "[INFO] Running: $cmd"
Invoke-Expression $cmd

Write-Host "`n[INFO] Pipeline complete! Check data/sag_final/ for SAG v2.0 results."
