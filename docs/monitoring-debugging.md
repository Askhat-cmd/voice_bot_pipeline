# 📈 Мониторинг и отладка

## Навигация

- [Назад к README](../README.md)
- [Быстрый старт](./getting-started.md)
- [Устранение неполадок](#устранение-неполадок)

---

## Логирование

### Основной лог: `pipeline.log`

```
2025-01-28 15:30:15,123 | INFO | pipeline | Starting pipeline for: https://youtu.be/VIDEO_ID
2025-01-28 15:30:15,124 | INFO | pipeline | Stage 1: Downloading subtitles from YouTube
2025-01-28 15:30:17,456 | INFO | pipeline | Stage 1 complete: data\raw_subtitles\VIDEO_ID.json
2025-01-28 15:30:17,457 | INFO | pipeline | Stage 2: Processing text for SAG v2.0
2025-01-28 15:30:45,123 | INFO | pipeline | Stage 2 complete: 8 SAG v2.0 blocks created
2025-01-28 15:30:45,124 | INFO | pipeline | Pipeline complete! Total time: 30.0s
2025-01-28 15:30:45,125 | INFO | pipeline | SAG v2.0 JSON: data\sag_final\VIDEO_ID.for_vector.json
```

### 🆕 SAG v2.0 Логи с расширенной информацией

```
2025-01-28 15:30:17,458 | INFO | sarsekenov_processor | SAG v2.0: Processing with schema version 2.0
2025-01-28 15:30:17,459 | INFO | sarsekenov_processor | Detecting dialogue patterns in full_text
2025-01-28 15:30:17,460 | INFO | sarsekenov_processor | Dialogue detected: True (confidence: 0.85)
2025-01-28 15:30:17,461 | INFO | sarsekenov_processor | Extracting graph entities: 12 entities found
2025-01-28 15:30:17,462 | INFO | sarsekenov_processor | Collection target: dialogue_sessions (confidence: 0.7)
2025-01-28 15:30:17,463 | INFO | sarsekenov_processor | Overview length: 573 chars (validation: PASSED)
2025-01-28 15:30:17,464 | INFO | sarsekenov_processor | Morphological improvements: 2/9 applied
2025-01-28 15:30:45,125 | INFO | sarsekenov_processor | SAG v2.0 complete: 90% readiness score
```

### Результаты выполнения: `data/raw_subtitles/`

**Одиночный запуск**: `pipeline_result_YYYYMMDD_HHMMSS.json`

```json
{
  "youtube_url": "https://youtu.be/VIDEO_ID",
  "status": "success",
  "pipeline_start": "2025-01-28 15:30:15",
  "pipeline_end": "2025-01-28 15:30:45", 
  "total_duration": 30.0,
  "stages": {
    "subtitles": {
      "status": "success",
      "duration": 2.3,
      "json_path": "data\\raw_subtitles\\VIDEO_ID.json"
    },
    "text_processing": {
      "status": "success",
      "duration": 27.7,
      "blocks_created": 8
    }
  },
  "final_outputs": {
    "sag_v2_json": "data\\sag_final\\VIDEO_ID.for_vector.json",
    "review_markdown": "data\\sag_final\\VIDEO_ID.for_review.md"
  }
}
```

**🆕 SAG v2.0 Результаты с расширенными метаданными:**

```json
{
  "sag_metadata": {
    "schema_version": "2.0",
    "processing_version": "v2.1",
    "sag_readiness_score": 90.0,
    "collection_target": "dialogue_sessions",
    "routing_confidence": 0.7,
    "has_dialogue": true,
    "difficulty_level": "intermediate",
    "graph_entities_count": 12,
    "overview_length": 573,
    "morphological_improvements": 2
  }
}
```

---

## Отладка и диагностика

### Проверка окружения

```powershell
# Проверка Python и зависимостей
python --version
python -c "import openai, tiktoken, orjson; print('OK')"

# Проверка API ключа
python -c "import os; from env_utils import load_env; load_env(); print('API Key loaded:', bool(os.getenv('OPENAI_API_KEY')))"

# Тест OpenAI API
python -c "from openai import OpenAI; client = OpenAI(); print('API connection: OK')"
```

### Проверка компонентов

```powershell
# Тест извлечения субтитров
python subtitle_extractor\get_subtitles.py --url "https://youtu.be/dQw4w9WgXcQ"

# Тест обработки (на готовых данных)
python text_processor\sarsekenov_processor.py --input data\subtitles\VIDEO_ID.json

# Полный тест пайплайна
python pipeline_orchestrator.py --config config.yaml --url "https://youtu.be/dQw4w9WgXcQ"
```

### Анализ качества результатов

```powershell
# Статистика по блокам
python -c "
import json
from pathlib import Path

for f in Path('data/sag_final').glob('*.for_vector.json'):
    with open(f) as file:
        data = json.load(file)
    blocks = data['blocks']
    words_per_block = [len(b['content'].split()) for b in blocks]
    print(f'{f.stem}: {len(blocks)} блоков, {min(words_per_block)}-{max(words_per_block)} слов')
"
```

---

## Устранение неполадок

### Частые проблемы и решения

#### 1. Ошибки API ключей

**Проблема**: `[ERROR] OPENAI_API_KEY не установлен`

**Решение**:
```powershell
# Проверка наличия файла .env
ls .env

# Проверка содержимого
Get-Content .env

# Проверка загрузки в Python
python -c "import os; from env_utils import load_env; load_env(); print(os.getenv('OPENAI_API_KEY'))"
```

#### 2. Проблемы с субтитрами

**Проблема**: `[ERROR] Не удалось получить субтитры`

**Решение**:
```powershell
# Проверка URL вручную
python subtitle_extractor\get_subtitles.py --url "ВАША_ССЫЛКА"

# Попробовать другой язык
python subtitle_extractor\get_subtitles.py --url "ВАША_ССЫЛКА" --language en
```

#### 3. Ошибки обработки текста

**Проблема**: `[INFO] Processing chunk X/Y` зависает или много ошибок `429 Too Many Requests`

**Решение**:
```powershell
# Увеличение задержки между запросами к API
# Добавьте в .env:
OPENAI_API_DELAY=2.0  # Увеличьте до 2-3 секунд при частых ошибках 429

# Снижение нагрузки
# В .env изменить:
PRIMARY_MODEL=gpt-4o-mini
REFINE_MODEL=
```

#### 4. SAG v2.0 Специфические проблемы

**Проблема**: `overview_summary слишком короткий`

**Решение**: В ETAP 5 добавлена валидация длины. Автоматический fallback на морфологию. Минимум 200 символов гарантирован.

**Проблема**: Граф-сущности не извлекаются

**Решение**: В ETAP 5 добавлена агрегация на уровне документа. Проверьте поле graph_entities в JSON. Должно быть 12+ сущностей для качественных данных.

---

## Логи и мониторинг

```powershell
# Просмотр логов в реальном времени
Get-Content pipeline.log -Wait

# Анализ ошибок
Select-String "ERROR" pipeline.log | Select-Object -Last 10

# Статистика выполнения
Select-String "Pipeline complete" pipeline.log | Measure-Object

# Проверка размеров результатов
Get-ChildItem data\sag_final\*.json | Select-Object Name, Length | Sort-Object Length
```

---

## Навигация

- [Назад к README](../README.md)
- [Быстрый старт](./getting-started.md)
- [Тестирование](./testing.md)
- [Развертывание](./deployment.md)

