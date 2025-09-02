# 🧠 Voice Bot Pipeline - YouTube to Vector Database

Полнофункциональный пайплайн для подготовки данных из YouTube-лекций для AI-ботов с векторным поиском и граф-RAG системами.

## 📋 Оглавление

1. [Назначение проекта](#-назначение-проекта)
2. [Архитектура и компоненты](#-архитектура-и-компоненты)
3. [Структура проекта](#-структура-проекта)
4. [Быстрый старт](#-быстрый-старт)
5. [Детальная настройка](#-детальная-настройка)
6. [Доменные режимы обработки](#-доменные-режимы-обработки)
7. [Формат выходных данных](#-формат-выходных-данных)
8. [API и интеграция](#-api-и-интеграция)
9. [Мониторинг и отладка](#-мониторинг-и-отладка)
10. [Расширение функциональности](#-расширение-функциональности)
11. [Устранение неполадок](#-устранение-неполадок)
12. [Развертывание на GitHub](#-развертывание-на-github)

---

## 🎯 Назначение проекта

### Основная цель
Проект предназначен для **подготовки высококачественных данных** из YouTube-лекций для создания AI-ботов, использующих:
- **Векторный поиск** (semantic search)
- **Граф-RAG системы** (Graph Retrieval-Augmented Generation)
- **Гибридный поиск** (BM25 + векторы + граф знаний)

### Что делает система
1. **Извлекает субтитры** с YouTube (автоматически, высокое качество)
2. **Структурирует в семантические блоки** оптимального размера (4-8 минут, 300-500+ слов)
3. **Сохраняет с метаданными** для векторных БД и графов знаний
4. **Поддерживает доменную специализацию** (нейросталкинг/неосталкинг Саламата Сарсекенова)

### Для чего используются результаты
- **Семантический поиск** по содержанию лекций
- **RAG-системы** для ответов на вопросы с цитированием источников
- **Чат-боты** с контекстом из лекций
- **Граф знаний** для связывания концепций и терминов
- **Временные ссылки** на конкретные моменты в видео

---

## 🏗 Архитектура и компоненты

### Схема работы
```
YouTube URL → Субтитры → Семантические блоки → JSON для векторной БД
     ↓              ↓                ↓                    ↓
1. Извлечение    2. Чистка      3. Структура      4. Метаданные
   субтитров       текста         + таймкоды        + ID + ссылки
```

### Ключевые компоненты

#### 1. **Subtitle Extractor** (`subtitle_extractor/`)
- **Назначение**: Извлечение субтитров с YouTube
- **Технология**: `youtube-transcript-api`
- **Поддерживаемые форматы**:
  - Обычные видео: `youtube.com/watch?v=ID`
  - Короткие ссылки: `youtu.be/ID`
  - Live-трансляции: `youtube.com/live/ID`
- **Выходные форматы**: JSON (структурированный), SRT (стандартный), TXT (чистый текст)

#### 2. **Text Processor** (`text_processor/`)
- **Назначение**: Преобразование субтитров в семантические блоки
- **Доступные процессоры**:
  - `sarsekenov_processor.py` — доменный (нейросталкинг/неосталкинг)
  - `subtitles_to_blocks.py` — универсальный
- **ИИ-модели**: OpenAI GPT (настраиваемые через .env)

#### 3. **Pipeline Orchestrator** (`pipeline_orchestrator.py`)
- **Назначение**: Координация всего процесса
- **Функции**: Логирование, обработка ошибок, батч-режим
- **Конфигурация**: YAML-файл с настройками

---

## 📁 Структура проекта

```
voice_bot_pipeline/
├── 📁 subtitle_extractor/      # Модуль извлечения субтитров
│   ├── 🐍 get_subtitles.py     # Основной скрипт загрузки
│   ├── 📄 README.md            # Документация модуля
│   ├── 📦 requirements.txt     # Зависимости модуля
│   └── 📁 scripts/             # Скрипты настройки
│       └── 🔧 setup_subtitles.ps1
│
├── 📁 text_processor/          # Модуль обработки текста
│   ├── 🐍 sarsekenov_processor.py    # Доменный процессор (Сарсекенов)
│   ├── 🐍 subtitles_to_blocks.py     # Универсальный процессор
│   ├── 🐍 transcript_to_json_md.py   # Legacy процессор
│   └── 📁 scripts/             # Скрипты настройки
│       └── 🔧 setup_tp.ps1
│
├── 📁 data/                    # Данные проекта
│   ├── 📁 subtitles/           # Загруженные субтитры
│   │   ├── 📄 VIDEO_ID.json    # Структурированные данные
│   │   ├── 📄 VIDEO_ID.srt     # Стандартные субтитры
│   │   └── 📄 VIDEO_ID.txt     # Чистый текст
│   ├── 📁 vector_ready/        # Готовые для векторизации
│   │   ├── 📄 *.for_vector.json # Для векторной БД
│   │   └── 📄 *.for_review.md   # Для человеческого просмотра
│   └── 📁 pipeline_results/    # Логи выполнения
│
├── 📁 scripts/                 # Скрипты управления
│   ├── 🔧 setup_all.ps1        # Полная настройка окружения
│   └── 🔧 run_full_pipeline.ps1 # Быстрый запуск
│
├── ⚙️ config.yaml              # Конфигурация пайплайна
├── 🐍 pipeline_orchestrator.py # Главный оркестратор
├── 🐍 env_utils.py             # Утилиты окружения
├── 📦 requirements.txt         # Основные зависимости
├── 📄 urls.txt                 # Список URL для обработки
├── 🔐 .env                     # Переменные окружения (создать)
└── 📖 README.md               # Эта документация
```

---

## 🚀 Быстрый старт

### Шаг 1: Подготовка окружения

```powershell
# Автоматическая настройка (рекомендуется)
.\scripts\setup_all.ps1
```

**Что делает скрипт:**
- Проверяет наличие Python 3.8+
- Создает виртуальное окружение `.venv`
- Устанавливает все зависимости
- Создает необходимые папки
- Проверяет доступность FFmpeg (при необходимости)

### Шаг 2: Настройка API ключей

Создайте файл `.env` в корне проекта:

```env
# ========================================
# ОСНОВНЫЕ НАСТРОЙКИ
# ========================================

# Ключ OpenAI API (ОБЯЗАТЕЛЬНО)
OPENAI_API_KEY=sk-proj-ваш_ключ_здесь

# ========================================
# МОДЕЛИ ДЛЯ ОБРАБОТКИ ТЕКСТА
# ========================================

# Основная модель для разбивки на блоки
# Рекомендуется: gpt-4o-mini (быстро + дешево)
PRIMARY_MODEL=gpt-4o-mini

# Модель для полировки результатов (опционально)
# Рекомендуется: gpt-5-mini (дешевле чем gpt-4)
# Оставьте пустым для отключения
REFINE_MODEL=gpt-5-mini

# ========================================
# ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ (опционально)
# ========================================

# Для Neo4j (если планируете граф-БД)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Google Cloud (если нужно)
GOOGLE_CLOUD_PROJECT=your-project-id
```

### Шаг 3: Подготовка URL

Добавьте ссылки в файл `urls.txt` (по одной на строку):

```text
https://youtu.be/R39dqh5wA9U
https://youtube.com/watch?v=VIDEO_ID_2
https://youtube.com/live/LIVE_ID_3
```

### Шаг 4: Запуск

```powershell
# Активация окружения
.\.venv\Scripts\Activate.ps1

# Запуск полного пайплайна
python pipeline_orchestrator.py --config config.yaml
```

**Что происходит:**
1. Читает URL из `urls.txt`
2. Загружает субтитры с YouTube
3. Обрабатывает через доменный процессор (Сарсекенов по умолчанию)
4. Сохраняет результаты в `data/vector_ready/`

---

## ⚙️ Детальная настройка

### Конфигурация `config.yaml`

```yaml
# ========================================
# НАСТРОЙКИ ЛОГИРОВАНИЯ
# ========================================
logging:
  level: "INFO"          # DEBUG, INFO, WARNING, ERROR
  log_file: "pipeline.log"

# ========================================
# НАСТРОЙКИ ПАЙПЛАЙНА
# ========================================
pipeline:
  # Настройки извлечения субтитров
  subtitles:
    output_dir: "data/subtitles"
    language: "ru"         # Предпочитаемый язык
    
  # Настройки обработки текста  
  text_processing:
    output_dir: "data/vector_ready"
    
  # Папка для результатов выполнения
  results_dir: "data/pipeline_results"
```

### Переменные окружения (.env) - подробно

```env
# ========================================
# ОБЯЗАТЕЛЬНЫЕ НАСТРОЙКИ
# ========================================

# OpenAI API ключ - получить на https://platform.openai.com/
OPENAI_API_KEY=sk-proj-...

# ========================================
# МОДЕЛИ (настройка производительности/стоимости)
# ========================================

# Основная модель для структурирования текста
# Варианты:
# - gpt-4o-mini: быстро, дешево, хорошее качество (РЕКОМЕНДУЕТСЯ)
# - gpt-4o: медленно, дорого, отличное качество
# - gpt-4-turbo: компромисс скорость/качество
PRIMARY_MODEL=gpt-4o-mini

# Модель для финальной полировки (опционально)
# Варианты:
# - gpt-5-mini: дешево, хорошо для полировки (РЕКОМЕНДУЕТСЯ)
# - gpt-4: дорого, отлично для полировки
# - "" (пустая строка): отключить полировку
REFINE_MODEL=gpt-5-mini

# ========================================
# ПРОДВИНУТЫЕ НАСТРОЙКИ (опционально)
# ========================================

# Кастомные промпты (если нужна тонкая настройка)
MAIN_PROMPT="""Ты — редактор лекций. Разбей текст на крупные смысловые блоки..."""
REFINE_PROMPT="""Улучши заголовки и описания блоков..."""
FALLBACK_PROMPT="""Блок создан автоматически из-за ошибки обработки."""

# Настройки для граф-БД Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Google Cloud (для дополнительных сервисов)
GOOGLE_CLOUD_PROJECT=your-project-id
```

---

## 🧩 Доменные режимы обработки

### Что такое домен?

**Домен** — это специализированный профиль обработки текста, настроенный под конкретную тематику или автора.

### Доступные домены

#### 1. **sarsekenov** (по умолчанию)
- **Автор**: Саламат Сарсекенов
- **Тематика**: Нейросталкинг, неосталкинг
- **Особенности**:
  - Сохраняет авторскую терминологию
  - Правильно структурирует практики и упражнения
  - Выделяет вопросы из зала и разборы
  - Сохраняет стиль речи автора

**Ключевые термины, которые сохраняются:**
- нейросталкинг, неосталкинг
- поле внимания, наблюдение за умом
- метанаблюдение, осознавание
- паттерны, триггеры, автоматизмы
- исследование переживаний
- практика, упражнение, разбор

#### 2. **generic**
- **Назначение**: Универсальная обработка
- **Подходит для**: Любой контент без специфической терминологии
- **Особенности**: Стандартная структуризация без доменных правил

### Выбор домена при запуске

```powershell
# Доменный режим (по умолчанию)
python pipeline_orchestrator.py --config config.yaml --domain sarsekenov

# Универсальный режим
python pipeline_orchestrator.py --config config.yaml --domain generic
```

### Когда использовать какой домен

| Тип контента | Рекомендуемый домен | Причина |
|--------------|--------------------|---------| 
| Лекции Сарсекенова | `sarsekenov` | Сохранение терминологии |
| Психология, медитация | `sarsekenov` | Похожие концепции |
| Технические лекции | `generic` | Нет специфических терминов |
| Новости, интервью | `generic` | Универсальная структура |
| Образовательный контент | `generic` | Стандартная обработка |

---

## 📊 Формат выходных данных

### Структура JSON файла (для векторной БД)

```json
{
  "document_title": "Лекция Сарсекенова: Rxoj94WQpsQ",
  "document_summary": "Конспект лекции, структурированный по темам нейросталкинга/неосталкинга.",
  
  "document_metadata": {
    "total_blocks": 8,
    "language": "ru",
    "domain": "sarsekenov_neurostalking",
    "video_id": "Rxoj94WQpsQ",
    "source_url": "https://youtube.com/watch?v=Rxoj94WQpsQ",
    "schema_version": "1.0"
  },
  
  "overview_toc": "Исцеление и самопознание • Природа ума и осознавание • Преодоление через опыт",
  "overview_summary": "Лекция охватывает процесс исцеления через самопознание, работу с умом и важность интеграции опыта для обретения мудрости.",
  
  "blocks": [
    {
      "block_id": "Rxoj94WQpsQ_001",
      "video_id": "Rxoj94WQpsQ", 
      "start": "00:00:00",
      "end": "00:08:45",
      "source_url": "https://youtube.com/watch?v=Rxoj94WQpsQ",
      "youtube_link": "https://youtube.com/watch?v=Rxoj94WQpsQ&t=0s",
      
      "title": "Процесс исцеления через самопознание без героизма",
      "summary": "Обсуждается важность подлинного исцеления без позерства и героизма. Подчеркивается необходимость живого взаимодействия с людьми на их уровне понимания.",
      "keywords": ["исцеление", "самопознание", "взаимодействие", "осознавание"],
      
      "content": "Прямо сейчас уникальный момент исцеления, но без того я, позёра, который сказал: \"Ох, как я простил!\" Понимаете, как это тяжело в себе держать того, кто якобы кого-то простил, якобы кого-то полюбил... [ПОЛНЫЙ ТЕКСТ БЛОКА 300-500+ СЛОВ]"
    }
  ],
  
  "full_text": "Полный текст всех субтитров одной строкой..."
}
```

### Ключевые поля для RAG-системы

#### Идентификация и связи
- `block_id`: Уникальный ID блока (`VIDEO_ID_NNN`)
- `video_id`: ID исходного видео
- `source_url`: Ссылка на YouTube видео
- `youtube_link`: Прямая ссылка с временной меткой
- `schema_version`: Версия схемы данных

#### Временные метки
- `start`, `end`: Временные границы (HH:MM:SS)
- URL параметр `&t=Ns`: Прямой переход к моменту

#### Семантическое содержание
- `title`: Уникальный заголовок блока
- `summary`: Краткое описание (2-3 предложения)
- `keywords`: Массив ключевых терминов
- `content`: Полный текст блока (300-500+ слов)

#### Метаданные документа
- `domain`: Тип обработки
- `total_blocks`: Количество блоков
- `overview_toc`: Краткое оглавление
- `overview_summary`: Общее резюме

### Структура Markdown файла (для просмотра)

```markdown
# 🧭 Лекции С. Сарсекенова — конспект
## Лекция Сарсекенова: Rxoj94WQpsQ
*Конспект лекции, структурированный по темам нейросталкинга/неосталкинга.*

**Короткое оглавление:** Исцеление и самопознание • Природа ума • Преодоление опыта
**Общее резюме:** Лекция рассматривает процесс подлинного исцеления через самопознание...

---
## 📑 Оглавление
1. [Процесс исцеления через самопознание без героизма](#1-block)
2. [Природа ума и зеркальное отражение реальности](#2-block)
...

---

## <a id='1-block'></a> 1. Процесс исцеления через самопознание без героизма
**⏱ Время:** [00:00:00 - 00:08:45]
**📝 Краткое содержание:** Обсуждается важность подлинного исцеления...
**🏷 Ключевые слова:** исцеление, самопознание, взаимодействие

### Содержание:
Прямо сейчас уникальный момент исцеления, но без того я, позёра...
[ПОЛНЫЙ ТЕКСТ БЛОКА]

---
```

---

## 🔌 API и интеграция

### Командная строка

#### Основные команды

```powershell
# Полный пайплайн с автоматическим чтением urls.txt
python pipeline_orchestrator.py --config config.yaml

# Обработка одного URL
python pipeline_orchestrator.py --config config.yaml --url "https://youtu.be/VIDEO_ID"

# Обработка файла с URL
python pipeline_orchestrator.py --config config.yaml --urls-file custom_urls.txt

# Выбор домена
python pipeline_orchestrator.py --config config.yaml --domain generic

# Кастомное имя для результатов
python pipeline_orchestrator.py --config config.yaml --url "..." --name "Лекция_1"
```

#### Только извлечение субтитров

```powershell
# Из urls.txt
python subtitle_extractor\get_subtitles.py

# Один URL
python subtitle_extractor\get_subtitles.py --url "https://youtu.be/VIDEO_ID"

# Кастомный файл
python subtitle_extractor\get_subtitles.py --urls-file my_urls.txt

# Другой язык
python subtitle_extractor\get_subtitles.py --language en
```

#### Только обработка текста

```powershell
# Доменный процессор (Сарсекенов)
python text_processor\sarsekenov_processor.py --input data\subtitles --output data\vector_ready

# Универсальный процессор
python text_processor\subtitles_to_blocks.py --input data\subtitles --output data\vector_ready
```

### Программная интеграция

#### Python API

```python
from pathlib import Path
from text_processor.sarsekenov_processor import SarsekenovProcessor
from subtitle_extractor.get_subtitles import YouTubeSubtitlesExtractor

# Извлечение субтитров
extractor = YouTubeSubtitlesExtractor("data/subtitles")
extractor.process_url("https://youtu.be/VIDEO_ID")

# Обработка в блоки
processor = SarsekenovProcessor(
    primary_model="gpt-4o-mini",
    refine_model="gpt-5-mini"
)
result = processor.process_file(
    Path("data/subtitles/VIDEO_ID.json"),
    Path("data/vector_ready")
)

print(f"Создано блоков: {result['blocks']}")
print(f"JSON: {result['json_output']}")
print(f"MD: {result['md_output']}")
```

#### Батч-обработка

```python
from pipeline_orchestrator import PipelineOrchestrator

# Инициализация
orchestrator = PipelineOrchestrator("config.yaml", domain="sarsekenov")

# Обработка списка URL
urls = [
    "https://youtu.be/VIDEO_1",
    "https://youtu.be/VIDEO_2"
]

results = []
for url in urls:
    result = orchestrator.run_full_pipeline(url)
    results.append(result)
    
# Анализ результатов
successful = [r for r in results if r["status"] == "success"]
print(f"Успешно обработано: {len(successful)}/{len(results)}")
```

---

## 📈 Мониторинг и отладка

### Логирование

#### Основной лог: `pipeline.log`

```
2025-01-28 15:30:15,123 | INFO | pipeline | Starting pipeline for: https://youtu.be/VIDEO_ID
2025-01-28 15:30:15,124 | INFO | pipeline | Stage 1: Downloading subtitles from YouTube
2025-01-28 15:30:17,456 | INFO | pipeline | Stage 1 complete: data\subtitles\VIDEO_ID.json
2025-01-28 15:30:17,457 | INFO | pipeline | Stage 2: Processing text for vector database
2025-01-28 15:30:45,123 | INFO | pipeline | Stage 2 complete: 8 blocks created
2025-01-28 15:30:45,124 | INFO | pipeline | Pipeline complete! Total time: 30.0s
2025-01-28 15:30:45,125 | INFO | pipeline | Vector-ready JSON: data\vector_ready\VIDEO_ID.for_vector.json
```

#### Результаты выполнения: `data/pipeline_results/`

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
      "json_path": "data\\subtitles\\VIDEO_ID.json"
    },
    "text_processing": {
      "status": "success",
      "duration": 27.7,
      "blocks_created": 8
    }
  },
  "final_outputs": {
    "vector_json": "data\\vector_ready\\VIDEO_ID.for_vector.json",
    "review_markdown": "data\\vector_ready\\VIDEO_ID.for_review.md"
  }
}
```

**Батч-режим**: `batch_pipeline_results_YYYYMMDD_HHMMSS.json`
```json
[
  {
    "youtube_url": "https://youtu.be/VIDEO_1",
    "status": "success",
    "total_duration": 25.3,
    ...
  },
  {
    "youtube_url": "https://youtu.be/VIDEO_2", 
    "status": "failed",
    "error": "Could not extract video_id from URL",
    "total_duration": 0.1
  }
]
```

### Отладка и диагностика

#### Проверка окружения

```powershell
# Проверка Python и зависимостей
python --version
python -c "import openai, tiktoken, orjson; print('OK')"

# Проверка API ключа
python -c "import os; from env_utils import load_env; load_env(); print('API Key loaded:', bool(os.getenv('OPENAI_API_KEY')))"

# Тест OpenAI API
python -c "from openai import OpenAI; client = OpenAI(); print('API connection: OK')"
```

#### Проверка компонентов

```powershell
# Тест извлечения субтитров
python subtitle_extractor\get_subtitles.py --url "https://youtu.be/dQw4w9WgXcQ"

# Тест обработки (на готовых данных)
python text_processor\sarsekenov_processor.py --input data\subtitles\VIDEO_ID.json

# Полный тест пайплайна
python pipeline_orchestrator.py --config config.yaml --url "https://youtu.be/dQw4w9WgXcQ"
```

#### Анализ качества результатов

```powershell
# Статистика по блокам
python -c "
import json
from pathlib import Path

for f in Path('data/vector_ready').glob('*.for_vector.json'):
    with open(f) as file:
        data = json.load(file)
    blocks = data['blocks']
    words_per_block = [len(b['content'].split()) for b in blocks]
    print(f'{f.stem}: {len(blocks)} блоков, {min(words_per_block)}-{max(words_per_block)} слов')
"
```

---

## 🔧 Расширение функциональности

### Добавление нового домена

#### 1. Создание процессора

```python
# text_processor/my_domain_processor.py
from .sarsekenov_processor import SarsekenovProcessor

class MyDomainProcessor(SarsekenovProcessor):
    def __init__(self, primary_model="gpt-4o-mini", refine_model="gpt-5-mini"):
        super().__init__(primary_model, refine_model)
        
        # Доменные указания
        self.domain_context = (
            "Это лекция по [ВАШЕЙ ТЕМАТИКЕ]. "
            "Сохраняй терминологию: [ТЕРМИН1], [ТЕРМИН2], [ТЕРМИН3]. "
            "Особенности: [ОПИСАНИЕ ОСОБЕННОСТЕЙ]."
        )
```

#### 2. Регистрация в оркестраторе

```python
# pipeline_orchestrator.py
from text_processor.my_domain_processor import MyDomainProcessor

class PipelineOrchestrator:
    def __init__(self, config_path: str, domain: str = "sarsekenov"):
        # ...
        if domain.lower() == "sarsekenov":
            self.text_processor = SarsekenovProcessor()
        elif domain.lower() == "mydomain":
            self.text_processor = MyDomainProcessor()
        else:
            self.text_processor = SubtitlesProcessor()
```

#### 3. Использование

```powershell
python pipeline_orchestrator.py --config config.yaml --domain mydomain
```

### Интеграция с векторными БД

#### Пример для Qdrant

```python
# vector_indexer.py
from qdrant_client import QdrantClient
from qdrant_client.http import models
import json
from openai import OpenAI

class VectorIndexer:
    def __init__(self):
        self.qdrant = QdrantClient(host="localhost", port=6333)
        self.openai = OpenAI()
        
    def create_collection(self, collection_name: str):
        self.qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=1536,  # OpenAI embedding dimension
                distance=models.Distance.COSINE
            )
        )
    
    def index_document(self, json_path: str, collection_name: str):
        with open(json_path) as f:
            doc = json.load(f)
            
        points = []
        for block in doc['blocks']:
            # Создание эмбеддинга
            embedding = self.openai.embeddings.create(
                model="text-embedding-3-small",
                input=block['content']
            ).data[0].embedding
            
            # Подготовка точки для индексации
            point = models.PointStruct(
                id=block['block_id'],
                vector=embedding,
                payload={
                    "title": block['title'],
                    "summary": block['summary'],
                    "keywords": block['keywords'],
                    "content": block['content'],
                    "video_id": block['video_id'],
                    "youtube_link": block['youtube_link'],
                    "start_time": block['start'],
                    "end_time": block['end']
                }
            )
            points.append(point)
        
        # Загрузка в Qdrant
        self.qdrant.upsert(
            collection_name=collection_name,
            points=points
        )

# Использование
indexer = VectorIndexer()
indexer.create_collection("sarsekenov_lectures")
indexer.index_document("data/vector_ready/VIDEO_ID.for_vector.json", "sarsekenov_lectures")
```

### Интеграция с Neo4j (граф знаний)

```python
# graph_builder.py
from neo4j import GraphDatabase
import json
import re

class GraphBuilder:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def extract_entities(self, text: str):
        # Простое извлечение сущностей (можно заменить на NER)
        entities = []
        
        # Поиск терминов нейросталкинга
        neuro_terms = [
            "нейросталкинг", "неосталкинг", "поле внимания",
            "наблюдение за умом", "метанаблюдение", "осознавание"
        ]
        
        for term in neuro_terms:
            if term.lower() in text.lower():
                entities.append(("CONCEPT", term))
        
        return entities
    
    def create_graph_from_document(self, json_path: str):
        with open(json_path) as f:
            doc = json.load(f)
        
        with self.driver.session() as session:
            # Создание узла документа
            session.run(
                "CREATE (d:Document {id: $doc_id, title: $title, url: $url})",
                doc_id=doc['document_metadata']['video_id'],
                title=doc['document_title'],
                url=doc['document_metadata']['source_url']
            )
            
            # Обработка блоков
            for block in doc['blocks']:
                # Создание узла блока
                session.run(
                    """
                    CREATE (b:Block {
                        id: $block_id,
                        title: $title,
                        start_time: $start,
                        end_time: $end,
                        youtube_link: $youtube_link
                    })
                    """,
                    block_id=block['block_id'],
                    title=block['title'],
                    start=block['start'],
                    end=block['end'],
                    youtube_link=block['youtube_link']
                )
                
                # Связь блока с документом
                session.run(
                    """
                    MATCH (d:Document {id: $doc_id})
                    MATCH (b:Block {id: $block_id})
                    CREATE (d)-[:CONTAINS]->(b)
                    """,
                    doc_id=doc['document_metadata']['video_id'],
                    block_id=block['block_id']
                )
                
                # Извлечение и создание концептов
                entities = self.extract_entities(block['content'])
                for entity_type, entity_name in entities:
                    session.run(
                        f"MERGE (c:{entity_type} {{name: $name}})",
                        name=entity_name
                    )
                    
                    session.run(
                        f"""
                        MATCH (b:Block {{id: $block_id}})
                        MATCH (c:{entity_type} {{name: $name}})
                        CREATE (b)-[:MENTIONS]->(c)
                        """,
                        block_id=block['block_id'],
                        name=entity_name
                    )

# Использование
graph = GraphBuilder("bolt://localhost:7687", "neo4j", "password")
graph.create_graph_from_document("data/vector_ready/VIDEO_ID.for_vector.json")
```

---

## 🔍 Устранение неполадок

### Частые проблемы и решения

#### 1. **Ошибки API ключей**

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

**Возможные причины**:
- Файл `.env` отсутствует или в неправильном месте
- Неправильный формат ключа
- Проблемы с кодировкой файла

#### 2. **Проблемы с субтитрами**

**Проблема**: `[ERROR] Не удалось получить субтитры`

**Решение**:
```powershell
# Проверка URL вручную
python subtitle_extractor\get_subtitles.py --url "ВАША_ССЫЛКА"

# Попробовать другой язык
python subtitle_extractor\get_subtitles.py --url "ВАША_ССЫЛКА" --language en
```

**Возможные причины**:
- Видео не имеет субтитров
- Видео приватное или удаленное
- Неправильный формат URL
- Блокировка по региону

#### 3. **Ошибки обработки текста**

**Проблема**: `[INFO] Processing chunk X/Y` зависает

**Решение**:
```powershell
# Проверка баланса OpenAI
# Зайти на https://platform.openai.com/usage

# Снижение нагрузки
# В .env изменить:
PRIMARY_MODEL=gpt-4o-mini
REFINE_MODEL=

# Проверка отдельного блока
python text_processor\sarsekenov_processor.py --input data\subtitles\КОНКРЕТНЫЙ_ФАЙЛ.json
```

#### 4. **Проблемы с зависимостями**

**Проблема**: `ModuleNotFoundError: No module named 'XXX'`

**Решение**:
```powershell
# Переустановка окружения
Remove-Item -Recurse -Force .venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Проверка установки
pip list | Select-String "openai|tiktoken|orjson"
```

#### 5. **Проблемы с PowerShell**

**Проблема**: Ошибки выполнения скриптов

**Решение**:
```powershell
# Разрешение выполнения скриптов (от администратора)
Set-ExecutionPolicy RemoteSigned

# Альтернатива - прямые команды
python pipeline_orchestrator.py --config config.yaml
```

### Отладочные команды

```powershell
# Полная диагностика системы
python -c "
import sys
print('Python:', sys.version)
print('Path:', sys.executable)

try:
    import openai, tiktoken, orjson
    print('Dependencies: OK')
except Exception as e:
    print('Dependencies error:', e)

import os
from pathlib import Path
print('.env exists:', Path('.env').exists())
print('config.yaml exists:', Path('config.yaml').exists())
print('urls.txt exists:', Path('urls.txt').exists())

from env_utils import load_env
load_env()
print('API key loaded:', bool(os.getenv('OPENAI_API_KEY')))
"

# Проверка доступности YouTube
python -c "
from subtitle_extractor.get_subtitles import YouTubeSubtitlesExtractor
extractor = YouTubeSubtitlesExtractor('temp')
result = extractor.extract_video_id('https://youtu.be/dQw4w9WgXcQ')
print('YouTube parsing:', 'OK' if result else 'FAILED')
"

# Тест OpenAI API
python -c "
from openai import OpenAI
try:
    client = OpenAI()
    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[{'role': 'user', 'content': 'test'}],
        max_tokens=5
    )
    print('OpenAI API: OK')
except Exception as e:
    print('OpenAI API error:', e)
"
```

### Логи и мониторинг

```powershell
# Просмотр логов в реальном времени
Get-Content pipeline.log -Wait

# Анализ ошибок
Select-String "ERROR" pipeline.log | Select-Object -Last 10

# Статистика выполнения
Select-String "Pipeline complete" pipeline.log | Measure-Object

# Проверка размеров результатов
Get-ChildItem data\vector_ready\*.json | Select-Object Name, Length | Sort-Object Length
```

---

## 🚀 Развертывание на GitHub

### Подготовка к первому пушу

#### 1. **Создание репозитория**
```bash
# Создайте новый репозиторий на GitHub
# НЕ инициализируйте с README, .gitignore или лицензией
```

#### 2. **Инициализация Git в проекте**
```powershell
# В корне проекта voice_bot_pipeline
git init
git add .
git commit -m "Initial commit: Voice Bot Pipeline for YouTube to Vector DB"
```

#### 3. **Настройка удаленного репозитория**
```powershell
# Замените YOUR_USERNAME и YOUR_REPO на ваши данные
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
```

### ⚠️ **КРИТИЧЕСКИ ВАЖНО: Защита секретов**

#### **Проблема**: GitHub Push Protection блокирует пуши с секретами
```bash
# ❌ ОШИБКА: Push cannot contain secrets
# GitHub автоматически обнаруживает API ключи и блокирует пуш
```

#### **Решение**: Правильная настройка .gitignore и .env
```powershell
# 1. Убедитесь, что .env НЕ отслеживается Git
git status  # .env должен быть в "Untracked files"

# 2. Если .env уже в Git - удалите его из истории
git rm --cached .env
git commit -m "Remove .env from tracking"

# 3. Проверьте .gitignore содержит:
# .env
# .venv/
# __pycache__/
# *.log
# data/
```

#### **Создание .env.example (без секретов)**
```bash
# Создайте .env.example с примером структуры
OPENAI_API_KEY=your_openai_api_key_here
REFINE_MODEL=gpt-5-mini
PRIMARY_MODEL=gpt-4o-mini
```

### 🔐 **Аутентификация GitHub**

#### **Вариант A: Personal Access Token (рекомендуется)**
```powershell
# 1. Создайте PAT на GitHub: Settings → Developer settings → Personal access tokens
# 2. Выберите scopes: repo, workflow
# 3. Скопируйте токен

# 4. Настройте Git для использования токена
git config --global credential.helper store
# При следующем push введите username и токен как пароль
```

#### **Вариант B: SSH ключи**
```powershell
# 1. Генерация SSH ключа
ssh-keygen -t ed25519 -C "your_email@example.com"

# 2. Добавление в GitHub: Settings → SSH and GPG keys
# 3. Изменение remote URL
git remote set-url origin git@github.com:YOUR_USERNAME/YOUR_REPO.git
```

### 📤 **Первый пуш проекта**

#### **Безопасный пуш**
```powershell
# 1. Проверка статуса
git status

# 2. Добавление файлов (исключая секреты)
git add .

# 3. Проверка что .env НЕ добавлен
git status  # .env должен отсутствовать

# 4. Коммит
git commit -m "Initial commit: Complete Voice Bot Pipeline

- YouTube subtitle extraction
- Text processing with LLM
- Vector-ready JSON output
- Domain-specific processors
- Pipeline orchestration"

# 5. Пуш (GitHub запросит аутентификацию)
git push -u origin main
```

### 🔄 **Последующие обновления**

#### **Ежедневная работа**
```powershell
# 1. Проверка изменений
git status
git diff

# 2. Добавление и коммит
git add .
git commit -m "Update: [краткое описание изменений]"

# 3. Пуш
git push origin main
```

#### **Работа с ветками**
```powershell
# Создание feature ветки
git checkout -b feature/improve-text-processing

# Работа над изменениями...
git add .
git commit -m "Feature: Enhanced text cleaning and polishing"

# Слияние с main
git checkout main
git merge feature/improve-text-processing
git push origin main

# Удаление feature ветки
git branch -d feature/improve-text-processing
```

### 🚨 **Решение проблем с пушем**

#### **Ошибка: "Push cannot contain secrets"**
```powershell
# 1. Немедленно отмените последний коммит
git reset --soft HEAD~1

# 2. Удалите .env из Git
git rm --cached .env
git commit -m "Remove .env file"

# 3. Проверьте .gitignore
# 4. Повторите коммит и пуш
```

#### **Ошибка: "Authentication failed"**
```powershell
# 1. Проверьте токен/SSH ключ
# 2. Обновите credentials
git config --global credential.helper store

# 3. Или используйте SSH
git remote set-url origin git@github.com:YOUR_USERNAME/YOUR_REPO.git
```

#### **Ошибка: "Large file detected"**
```powershell
# 1. Проверьте размеры файлов
git status

# 2. Добавьте большие файлы в .gitignore
# 3. Удалите из Git если уже добавлены
git rm --cached large_file.mp4
```

### 📋 **Чек-лист перед пушем**

- [ ] `.env` файл НЕ отслеживается Git
- [ ] `.gitignore` настроен правильно
- [ ] Нет API ключей в коде
- [ ] Нет больших медиафайлов
- [ ] Все зависимости в `requirements.txt`
- [ ] README.md актуален
- [ ] Логи очищены от секретов

### 🌟 **Лучшие практики**

1. **Никогда не коммитьте `.env` файлы**
2. **Используйте `.env.example` для документации**
3. **Регулярно делайте коммиты с понятными сообщениями**
4. **Проверяйте статус перед каждым коммитом**
5. **Используйте feature ветки для крупных изменений**
6. **Держите main ветку стабильной**

---

## 📞 Поддержка и развитие

### Контакты
- **GitHub Issues**: [Создать issue](https://github.com/your-repo/issues)
- **Документация**: Этот README файл
- **Логи**: `pipeline.log` для диагностики

### Планы развития
- [ ] Автоматическое создание векторных индексов
- [ ] Интеграция с популярными векторными БД
- [ ] Веб-интерфейс для управления
- [ ] API для внешних приложений
- [ ] Поддержка дополнительных языков
- [ ] Улучшенное извлечение сущностей для графов

### Лицензия
Проект для образовательных целей. Используйте в соответствии с условиями YouTube API и OpenAI.

---

**🎉 Проект готов к использованию для создания AI-ботов с векторным поиском и граф-RAG системами!**

*Последнее обновление: 2025-01-28*
