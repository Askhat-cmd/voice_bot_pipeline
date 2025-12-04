# Complete Pipeline Setup - Single Virtual Environment
$ErrorActionPreference = "Stop"
Write-Host "=== Voice Bot Pipeline Setup ==="

# Check Python
try {
    $pythonVersion = python --version
    Write-Host "[OK] Python found: $pythonVersion"
} catch {
    Write-Error "Python not found. Install Python 3.10+ and restart terminal."
    exit 1
}

# Check/Install winget
try {
    winget --version | Out-Null
    Write-Host "[OK] winget found"
} catch {
    Write-Warning "winget not found. Some dependencies may need manual installation"
}

# Check/Install FFmpeg
try {
    ffmpeg -version | Out-Null
    Write-Host "[OK] FFmpeg found"
} catch {
    Write-Host "[INFO] Installing FFmpeg..."
    winget install -e --id Gyan.FFmpeg -h --accept-source-agreements --accept-package-agreements
}

# Check NVIDIA GPU
try {
    nvidia-smi | Out-Null
    Write-Host "[OK] NVIDIA GPU detected"
} catch {
    Write-Warning "nvidia-smi not found. GPU acceleration may not work"
}

# Create main directory structure
$directories = @(
    "data/raw_subtitles",
    "data/sag_final",
    "data/chromadb"
)

foreach ($dir in $directories) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    Write-Host "[INFO] Created directory: $dir"
}

# Create SINGLE virtual environment in the main directory
Write-Host "`n=== Creating Virtual Environment ==="
if (!(Test-Path ".venv")) {
    Write-Host "[INFO] Creating virtual environment..."
    python -m venv .venv
    Write-Host "[OK] Virtual environment created"
} else {
    Write-Host "[INFO] Virtual environment already exists"
}

# Activate and install ALL dependencies
Write-Host "`n=== Installing Dependencies ==="
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

# Test installation
Write-Host "`n=== Testing Installation ==="
python -c "import yt_dlp; print('✓ yt-dlp:', yt_dlp.__version__)"
python -c "from faster_whisper import WhisperModel; print('✓ faster-whisper: OK')"
python -c "from openai import OpenAI; print('✓ openai: OK')"
python -c "import orjson, tiktoken, yaml; print('✓ All modules: OK')"

# Create sample URLs file
$sampleUrls = @"
# Sample YouTube URLs (one per line)
# Lines starting with # are comments
https://www.youtube.com/watch?v=dQw4w9WgXcQ
# https://www.youtube.com/watch?v=another_video_id
"@
Set-Content -Path "sample_urls.txt" -Value $sampleUrls

Write-Host "`n=== Setup Complete! ==="
Write-Host "Virtual environment: .venv"
Write-Host "Dependencies: requirements.txt"
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Set OpenAI API key: `$env:OPENAI_API_KEY = 'your-key-here'"
Write-Host "2. Activate environment: .\.venv\Scripts\Activate.ps1"
Write-Host "3. Single video: python pipeline_orchestrator.py --url 'https://youtube.com/...'"
Write-Host "4. Batch process: python pipeline_orchestrator.py --urls-file sample_urls.txt"
Write-Host "5. Check results in data/sag_final/ folder"
