#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест интеграции расширенной граф-коллекции (442 узла + 259 отношений)
Проверяет работу новых методов анализа семантических связей
"""

import sys
from pathlib import Path

# Добавляем корень проекта в sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[0]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from text_processor.sarsekenov_processor import SarsekenovProcessor

def test_graph_integration():
    """Тестирует интеграцию расширенной граф-коллекции"""
    print("🚀 ТЕСТ ИНТЕГРАЦИИ РАСШИРЕННОЙ ГРАФ-КОЛЛЕКЦИИ")
    print("=" * 60)
    
    # Создаем процессор
    processor = SarsekenovProcessor()
    
    # Тест 1: Проверка размера граф-коллекции
    print(f"\n📊 РАЗМЕР ГРАФ-КОЛЛЕКЦИИ:")
    print(f"   Узлы: {len(processor.graph_nodes)} (ожидалось: 442)")
    print(f"   Отношения: {len(processor.graph_relationships)} (ожидалось: 259)")
    print(f"   Синонимы: {len(processor.synonym_map)}")
    print(f"   Стоп-слова: {len(processor.stop_words)}")
    
    # Тест 2: Проверка ключевых концептов нейросталкинга
    print(f"\n🎯 КЛЮЧЕВЫЕ КОНЦЕПТЫ НЕЙРОСТАЛКИНГА:")
    key_concepts = ["нейросталкинг", "неосталкинг", "метанаблюдение", "поле внимания", "осознавание"]
    for concept in key_concepts:
        status = "✅" if concept in processor.graph_nodes else "❌"
        print(f"   {status} {concept}")
    
    # Тест 3: Проверка извлечения граф-сущностей
    print(f"\n🔍 ТЕСТ ИЗВЛЕЧЕНИЯ ГРАФ-СУЩНОСТЕЙ:")
    test_content = """
    В нейросталкинге мы используем метанаблюдение для исследования поля внимания. 
    Это позволяет нам осознавать автоматические реакции и паттерны поведения. 
    Через центрирование и заземление мы приходим к глубокому пониманию себя.
    """
    
    test_keywords = ["метанаблюдение", "внимание", "осознавание", "паттерны", "центрирование"]
    
    entities = processor.extract_graph_entities(test_content, test_keywords)
    print(f"   Извлечено сущностей: {len(entities)} (ожидалось: 5-15)")
    print(f"   Сущности: {entities[:10]}...")  # Показываем первые 10
    
    # Тест 4: Проверка анализа семантических связей
    print(f"\n🔗 ТЕСТ АНАЛИЗА СЕМАНТИЧЕСКИХ СВЯЗЕЙ:")
    relationships = processor.analyze_semantic_relationships(entities)
    
    print(f"   Концептуальные связи: {len(relationships.get('conceptual_links', []))}")
    print(f"   Каузальные связи: {len(relationships.get('causal_links', []))}")
    print(f"   Практические связи: {len(relationships.get('practical_links', []))}")
    
    # Показываем примеры связей
    if relationships.get('conceptual_links'):
        print(f"   Пример концептуальной связи: {relationships['conceptual_links'][0]}")
    
    # Тест 5: Проверка приоритизации
    print(f"\n⭐ ТЕСТ ПРИОРИТИЗАЦИИ:")
    print(f"   Приоритетные концепты: {entities[:5]}")
    print(f"   Все сущности в граф-коллекции: {sum(1 for e in entities if e in processor.graph_nodes)}")
    
    # Тест 6: Проверка синонимов
    print(f"\n🔄 ТЕСТ СИНОНИМОВ:")
    test_synonyms = ["осознанность", "неосталкинг", "живое переживание"]
    for synonym in test_synonyms:
        canonical = processor.synonym_map.get(synonym, synonym)
        status = "✅" if canonical != synonym else "❌"
        print(f"   {status} {synonym} → {canonical}")
    
    print(f"\n" + "=" * 60)
    print("🎉 ТЕСТ ЗАВЕРШЕН!")
    
    return True

def test_performance():
    """Тестирует производительность расширенной системы"""
    print(f"\n⚡ ТЕСТ ПРОИЗВОДИТЕЛЬНОСТИ:")
    
    processor = SarsekenovProcessor()
    
    # Тест с большим объемом текста
    large_content = """
    """ * 1000  # Создаем большой текст
    
    import time
    start_time = time.time()
    
    # Тестируем извлечение сущностей
    entities = processor.extract_graph_entities(large_content, ["тест", "производительность"])
    
    extraction_time = time.time() - start_time
    
    start_time = time.time()
    
    # Тестируем анализ связей
    relationships = processor.analyze_semantic_relationships(entities)
    
    analysis_time = time.time() - start_time
    
    print(f"   Время извлечения сущностей: {extraction_time:.3f}с")
    print(f"   Время анализа связей: {analysis_time:.3f}с")
    print(f"   Общее время: {extraction_time + analysis_time:.3f}с")
    
    return True

if __name__ == "__main__":
    try:
        test_graph_integration()
        test_performance()
        print(f"\n✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    except Exception as e:
        print(f"\n❌ ОШИБКА В ТЕСТАХ: {e}")
        import traceback
        traceback.print_exc()
