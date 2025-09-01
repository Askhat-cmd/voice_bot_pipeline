# Text Processing Setup
$ErrorActionPreference = "Stop"
Write-Host "=== Setting up Text Processing ==="

# Virtual environment
if (!(Test-Path ".venv")) {
    Write-Host "[INFO] Creating virtual environment..."
    python -m venv .venv
}

Write-Host "[INFO] Installing dependencies..."
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

# Create directories
New-Item -ItemType Directory -Force -Path "../data/structured"
New-Item -ItemType Directory -Force -Path "../data/vector_ready"

# Check OpenAI API key
if (-not $env:OPENAI_API_KEY) {
    Write-Warning "[WARNING] OPENAI_API_KEY environment variable not set"
    Write-Host "[INFO] Set it with: `$env:OPENAI_API_KEY = 'your-key-here'"
}

Write-Host "[OK] Text processing setup complete!"
Write-Host "Usage: python transcript_to_json_md.py --input '../data/transcripts' --output '../data/structured'"
