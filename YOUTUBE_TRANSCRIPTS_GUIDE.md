# Загрузчик русских субтитров YouTube

Автономный CLI-модуль получает список роликов канала через официальный YouTube Data API v3, фильтрует ролики по включительному диапазону дат и сохраняет доступные русские субтитры в структурированные TXT-файлы.

Старый `pipeline_orchestrator.py`, SAG/RAG, ChromaDB и обработчики текста не используются.

## Установка

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-transcripts.txt
```

Добавьте ключ в существующий `.env`:

```dotenv
YOUTUBE_API_KEY=AIza...
```

## Проверка без скачивания

```powershell
python run_channel_transcripts.py --from-date 2025-01-01 --to-date 2025-01-31 --dry-run --verbose
```

## Скачивание

```powershell
python run_channel_transcripts.py --from-date 2025-01-01 --to-date 2025-12-31
```

Канал по умолчанию — `@Salsar`. Другой handle можно передать через `--channel`.

## Полезные параметры

```text
--output PATH       папка TXT, по умолчанию transcript_output
--registry PATH     JSON-реестр, по умолчанию data/transcript_registry.json
--limit N           обработать максимум N роликов
--force             перезаписать уже обработанные ролики
--retry-skipped     повторить ролики без русских субтитров
--retry-failed      повторить failed и unavailable
--dry-run           только показать найденные ролики
--verbose           подробный лог
```

## Результат

```text
transcript_output/YYYY/MM/YYYY-MM-DD_Название_VIDEOID.txt
```

В каждом TXT сохраняются название, дата публикации, ссылка, ID ролика, тип русских субтитров и полный очищенный текст без таймкодов.

Состояние записывается после каждого ролика в `data/transcript_registry.json`, поэтому обработка продолжается после остановки.

## Тесты

```powershell
python -m pytest tests/youtube_channel_transcripts -v
```

`youtube-transcript-api` использует недокументированный веб-интерфейс YouTube. При блокировке IP программа запишет ошибку в реестр и продолжит пакетную обработку.
