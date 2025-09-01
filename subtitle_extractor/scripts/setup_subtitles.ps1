# PowerShell скрипт для настройки модуля YouTube Subtitles
# Запускать из корневой папки voice_bot_pipeline

Write-Host "🔧 Настройка модуля YouTube Subtitles..." -ForegroundColor Green

# Проверяем, что мы в правильной папке
if (-not (Test-Path "03_youtube_subtitles")) {
    Write-Host "❌ Ошибка: Запустите скрипт из папки voice_bot_pipeline" -ForegroundColor Red
    exit 1
}

# Активируем виртуальное окружение
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "📦 Активируем виртуальное окружение..." -ForegroundColor Yellow
    & .\.venv\Scripts\Activate.ps1
} else {
    Write-Host "❌ Виртуальное окружение не найдено. Сначала запустите setup_all.ps1" -ForegroundColor Red
    exit 1
}

# Устанавливаем зависимости
Write-Host "📥 Устанавливаем youtube-transcript-api..." -ForegroundColor Yellow
pip install youtube-transcript-api

# Создаем папку для данных
Write-Host "📁 Создаем папки для данных..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "data\subtitles" | Out-Null

# Тестируем установку
Write-Host "🧪 Тестируем установку..." -ForegroundColor Yellow
python -c "from youtube_transcript_api import YouTubeTranscriptApi; print('✅ youtube-transcript-api установлен успешно')"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Модуль YouTube Subtitles настроен успешно!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📖 Примеры использования:" -ForegroundColor Cyan
    Write-Host "  python 03_youtube_subtitles\get_subtitles.py --url 'URL_ВИДЕО'" -ForegroundColor White
    Write-Host "  python 03_youtube_subtitles\get_subtitles.py --file 'urls.txt'" -ForegroundColor White
    Write-Host "  python 03_youtube_subtitles\get_subtitles.py --url 'URL' --list-languages" -ForegroundColor White
} else {
    Write-Host "❌ Ошибка при установке модуля" -ForegroundColor Red
    exit 1
}
