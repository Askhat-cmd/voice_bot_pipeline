# 🔌 API и интеграция

## Навигация

- [Назад к README](../README.md)
- [Быстрый старт](./getting-started.md)
- [Knowledge Graph](./knowledge-graph.md)
- [Векторная база данных](./vector-database.md)

---

## 📖 Описание и назначение

**Назначение документа**: Это полная документация по API методам и интеграции Voice Bot Pipeline в другие системы. Документ содержит примеры использования всех API методов, интеграцию в AI-ботов и расширение функциональности.

**Для кого**: Документ предназначен для разработчиков AI-ботов, которые хотят интегрировать систему в свои приложения, для разработчиков, создающих API на основе системы, и для исследователей, использующих систему программно.

**Что содержит**:
- API методы (все методы с примерами: обработка текстов, поиск практик, рекомендации упражнений)
- Интеграция в AI-бота (детальные примеры интеграции Knowledge Graph, векторного поиска)
- Примеры использования (полные примеры кода для всех сценариев)
- Расширение функциональности (инструкции по созданию новых экстракторов, интеграций)
- CLI команды (все команды командной строки с параметрами)
- Программный интерфейс (Python API, использование классов и функций)
- Best practices (лучшие практики интеграции, обработка ошибок, оптимизация)

**Когда использовать**: Используйте этот документ при разработке интеграций, при создании AI-ботов на основе системы, при расширении функциональности, или когда нужно понять программный интерфейс системы.

---

## Командная строка

### Основные команды

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

# 🆕 SAG v2.0 Прямая обработка с доменным процессором
python -m text_processor.sarsekenov_processor --input data/subtitles/VIDEO_ID.json --output data/sag_final --primary-model gpt-4o-mini --refine-model gpt-5-mini
```

### Только извлечение субтитров

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

### Только обработка текста

```powershell
# 🆕 SAG v2.0 Доменный процессор (Сарсекенов)
python -m text_processor.sarsekenov_processor --input data/subtitles/VIDEO_ID.json --output data/sag_final --primary-model gpt-4o-mini --refine-model gpt-5-mini

# 🆕 SAG v2.0 с кастомными настройками
python -m text_processor.sarsekenov_processor --input data/subtitles --output data/sag_final --primary-model gpt-4o-mini --refine-model gpt-5-mini

# Универсальный процессор (базовая схема v1.0)
python text_processor\subtitles_to_blocks.py --input data\subtitles --output data\vector_ready
```

**🆕 Новые возможности SAG v2.0:**
- **Автоматическая классификация**: Типы блоков, эмоциональные тона, сложность
- **🎯 Граф-сущности**: 442 узла + 259 отношений с нормализацией и агрегацией
- **🔗 Семантический анализ**: Автоматическое выявление связей между концептами
- **Морфологическая обработка**: Русский язык с правильными грамматическими формами
- **Умная маршрутизация**: Классификация по коллекциям с метрикой уверенности
- **Расширенные метаданные**: Схема v2.0 для современных векторных БД

---

## Программная интеграция

### Python API

```python
from pathlib import Path
from text_processor.sarsekenov_processor import SarsekenovProcessor
from subtitle_extractor.get_subtitles import YouTubeSubtitlesExtractor

# Извлечение субтитров
extractor = YouTubeSubtitlesExtractor("data/subtitles")
extractor.process_url("https://youtu.be/VIDEO_ID")

# 🆕 SAG v2.0 Обработка в блоки
processor = SarsekenovProcessor(
    primary_model="gpt-4o-mini",
    refine_model="gpt-5-mini"
)
result = processor.process_file(
    Path("data/subtitles/VIDEO_ID.json"),
    Path("data/sag_final")
)

# 🆕 Новые возможности SAG v2.0
print(f"Создано блоков: {len(result['blocks'])}")
print(f"SAG Schema: {result['document_metadata']['schema_version']}")
print(f"Collection Target: {result['document_metadata']['collection_target']}")
print(f"Routing Confidence: {result['document_metadata']['routing_confidence']}")
print(f"Graph Entities: {len(result['graph_entities'])}")
print(f"JSON: {result['json_output']}")
print(f"MD: {result['md_output']}")

# 🆕 Анализ классификации блоков
block_types = [b['block_type'] for b in result['blocks']]
emotional_tones = [b['emotional_tone'] for b in result['blocks']]
complexity_scores = [b['complexity_score'] for b in result['blocks']]

print(f"Block Types: {set(block_types)}")
print(f"Emotional Tones: {set(emotional_tones)}")
print(f"Avg Complexity: {sum(complexity_scores)/len(complexity_scores):.1f}")
```

### Батч-обработка

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

# 🆕 SAG v2.0 Анализ качества
for result in successful:
    if "document_metadata" in result:
        metadata = result["document_metadata"]
        print(f"Video: {metadata.get('video_id', 'Unknown')}")
        print(f"  SAG Schema: {metadata.get('schema_version', 'Unknown')}")
        print(f"  Collection: {metadata.get('collection_target', 'Unknown')}")
        print(f"  Confidence: {metadata.get('routing_confidence', 'Unknown')}")
        print(f"  Graph Entities: {len(result.get('graph_entities', []))}")
        print(f"  Overview Length: {len(result.get('overview_summary', ''))}")
```

---

## Knowledge Graph API

### Поиск практик для концепта/симптома

```python
from text_processor.sarsekenov_processor import SarsekenovProcessor
import json

processor = SarsekenovProcessor()

# Загрузить граф
with open("data/sag_final/2025/06/video.for_vector.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    kg = data["knowledge_graph"]

# Поиск практик
practices = processor.find_practices_for_concept("обида", kg)
for p in practices:
    print(f"Практика: {p['practice']}")
    print(f"Связь: {p['relation']}")
    print(f"Объяснение: {p.get('explanation', '')}")
```

### Получение цепочки между концептами

```python
# Получение цепочки между концептами
chain = processor.get_concept_chain("страдание", "освобождение", kg)
if chain:
    print(f"Путь от '{chain['from_concept']}' к '{chain['to_concept']}':")
    for step in chain['steps']:
        print(f"  {step['from']} --[{step['relation']}]--> {step['to']}")
```

### Рекомендация упражнения

```python
# Рекомендация упражнения для практики
exercise = processor.recommend_exercise_for_practice("метанаблюдение", kg, "5 минут")
if exercise:
    print(f"Упражнение: {exercise['exercise']}")
    print(f"Длительность: {exercise['duration']}")
    print(f"Инструкции: {exercise['instructions']}")
```

---

## Интеграция в AI-бота

```python
def get_recommendations_for_symptom(symptom: str, knowledge_graph: Dict):
    """
    Получить рекомендации для работы с симптомом.
    
    Args:
        symptom: Описание симптома (напр. "захват внимания", "обида")
        knowledge_graph: Данные Knowledge Graph
        
    Returns:
        Dict с практиками, упражнениями и reasoning chains
    """
    processor = SarsekenovProcessor()
    
    # Найти практики
    practices = processor.find_practices_for_concept(symptom, knowledge_graph)
    
    # Для каждой практики найти упражнения
    recommendations = []
    for practice_info in practices:
        practice_name = practice_info['practice']
        exercise = processor.recommend_exercise_for_practice(
            practice_name, 
            knowledge_graph
        )
        
        recommendations.append({
            "symptom": symptom,
            "practice": practice_name,
            "relation": practice_info['relation'],
            "explanation": practice_info.get('explanation', ''),
            "exercise": exercise
        })
    
    return recommendations
```

---

## Расширение функциональности

### Добавление нового домена

1. Создание процессора в `text_processor/my_domain_processor.py`
2. Настройка терминологии в `config/terminology/`
3. Интеграция в `pipeline_orchestrator.py`

---

## Навигация

- [Назад к README](../README.md)
- [Knowledge Graph](./knowledge-graph.md)
- [Векторная база данных](./vector-database.md)
- [Быстрый старт](./getting-started.md)

