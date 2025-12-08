#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для ручного тестирования CausalChainExtractor.

Запуск:
    cd voice_bot_pipeline
    .\.venv\Scripts\Activate.ps1
    python tests/extractors/run_causal_chain_tests.py
"""

import sys
from pathlib import Path

# Добавляем корневую директорию в путь
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

print("=" * 60)
print("ТЕСТИРОВАНИЕ CAUSALCHAINEXTRACTOR")
print("=" * 60)

# Импорт
try:
    from text_processor.extractors.causal_chain_extractor import (
        CausalChainExtractor,
        extract_causal_chains
    )
    print("[OK] Импорт успешен")
except Exception as e:
    print(f"[ERROR] Ошибка импорта: {e}")
    sys.exit(1)

# Создание экстрактора
try:
    extractor = CausalChainExtractor()
    print("[OK] Экстрактор создан")
except Exception as e:
    print(f"[ERROR] Ошибка создания: {e}")
    sys.exit(1)

# ============================================================
# ТЕСТЫ
# ============================================================

def test_triada_transformation():
    """Тест 1: Триада трансформации"""
    print("\n--- Тест 1: Триада трансформации ---")
    text = """
    Когда Ищущий практикует метанаблюдение, он сначала наблюдает за 
    мыслительным потоком. Затем происходит осознавание автоматизмов психики.
    Это ведет к трансформации через разотождествление с Я-образом.
    В результате возникает чистое осознавание и свободное внимание.
    """
    
    result = extractor.extract(text, specific_category="триада_трансформации")
    print(f"  Валиден: {result['valid']}")
    print(f"  Причина: {result.get('reason', 'N/A')}")
    print(f"  Цепочек: {len(result['chains'])}")
    
    if result['chains']:
        chain = result['chains'][0]
        print(f"  Категория: {chain['process_category']}")
        print(f"  Этапов: {len(chain['stages'])}")
        print(f"  Уверенность: {chain['confidence']:.2f}")
    
    assert result['valid'], "Текст должен быть валидным"
    assert len(result['chains']) >= 1, "Должна быть минимум 1 цепочка"
    print("  ✅ PASSED")


def test_smart_mode():
    """Тест 2: SMART режим (forbidden terms не блокируют)"""
    print("\n--- Тест 2: SMART режим ---")
    text = """
    Когда человек говорит об эго и медитации, я объясняю:
    это на самом деле Я-образ и метанаблюдение. Разотождествление
    с Я-образом ведёт к чистому осознаванию. В поле внимания 
    появляется свободное внимание и присутствие.
    Автоматизмы психики становятся видны наблюдающему сознанию.
    """
    
    result = extractor.extract(text)
    print(f"  Валиден: {result['valid']}")
    print(f"  Цепочек: {len(result['chains'])}")
    
    assert result['valid'], "SMART режим должен пропустить текст с forbidden terms"
    print("  ✅ PASSED (forbidden terms игнорируются)")


def test_low_density():
    """Тест 3: Низкая плотность отклоняется"""
    print("\n--- Тест 3: Низкая плотность ---")
    text = """
    Человек пришел на консультацию и рассказал о своих проблемах.
    Мы поговорили о его детстве и отношениях с родителями.
    """
    
    result = extractor.extract(text)
    print(f"  Валиден: {result['valid']} (ожидается False)")
    print(f"  Причина: {result.get('reason', 'N/A')}")
    
    assert not result['valid'], "Низкая плотность должна блокировать"
    print("  ✅ PASSED")


def test_cyclical_detection():
    """Тест 4: Определение цикличности"""
    print("\n--- Тест 4: Цикличность ---")
    text = """
    В практике нейро-сталкинга процесс осознавания снова и снова 
    возвращается к метанаблюдению. Ищущий периодически замечает 
    Я-образ и разотождествляется с ним. Это спираль развития,
    где каждый цикл приносит более глубокое чистое осознавание.
    Автоматизмы психики становятся всё более прозрачными.
    """
    
    result = extractor.extract(text)
    print(f"  Валиден: {result['valid']}")
    
    if result['chains']:
        chain = result['chains'][0]
        print(f"  Циклический: {chain['is_cyclical']}")
        print(f"  Маркеры целостности: {chain['wholeness_markers']}")
        
        assert chain['is_cyclical'], "Должен определить как циклический процесс"
    
    print("  ✅ PASSED")


def test_systemic_links():
    """Тест 5: Системные связи (emerges_from, enables)"""
    print("\n--- Тест 5: Системные связи ---")
    text = """
    Практика начинается с метанаблюдения за мыслительным потоком.
    Из этого возникает осознавание автоматизмов психики и Я-образа.
    Затем происходит разотождествление с ложной самостью.
    В результате появляется чистое осознавание и свободное внимание.
    """
    
    result = extractor.extract(text)
    print(f"  Валиден: {result['valid']}")
    
    if result['chains']:
        chain = result['chains'][0]
        stages = chain['stages']
        print(f"  Этапов: {len(stages)}")
        
        if len(stages) >= 2:
            second_stage = stages[1]
            print(f"  Stage 2 emerges_from: {second_stage.get('emerges_from')}")
            
            first_stage = stages[0]
            print(f"  Stage 1 enables: {first_stage.get('enables')}")
    
    print("  ✅ PASSED")


def test_utility_function():
    """Тест 6: Utility функция"""
    print("\n--- Тест 6: Utility функция ---")
    text = """
    Метанаблюдение за Я-образом в поле внимания ведёт к осознаванию.
    Разотождествление с автоматизмами психики открывает чистое осознавание.
    """
    
    result = extract_causal_chains(text)
    print(f"  Валиден: {result['valid']}")
    print(f"  Цепочек: {len(result['chains'])}")
    print("  ✅ PASSED")


# Запуск всех тестов
if __name__ == "__main__":
    tests = [
        test_triada_transformation,
        test_smart_mode,
        test_low_density,
        test_cyclical_detection,
        test_systemic_links,
        test_utility_function,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"РЕЗУЛЬТАТ: {passed} прошло, {failed} провалено")
    print("=" * 60)
    
    if failed == 0:
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    else:
        print("❌ ЕСТЬ ПРОВАЛЕННЫЕ ТЕСТЫ")
        sys.exit(1)
