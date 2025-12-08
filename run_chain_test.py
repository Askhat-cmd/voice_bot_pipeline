#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Тестовый скрипт для проверки CausalChainExtractor"""

import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("Тестирование CausalChainExtractor")
print("=" * 60)

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
    print(f"[ERROR] Ошибка создания экстрактора: {e}")
    sys.exit(1)

# Тест 1: Триада трансформации
print("\n--- Тест 1: Триада трансформации ---")
text1 = """
Когда Ищущий практикует метанаблюдение, он сначала наблюдает за 
мыслительным потоком. Затем происходит осознавание автоматизмов психики.
Это ведет к трансформации через разотождествление с Я-образом.
В результате возникает чистое осознавание и свободное внимание.
"""

result = extractor.extract(text1, specific_category="триада_трансформации")
print(f"  Валиден: {result['valid']}")
print(f"  Причина: {result.get('reason', 'N/A')}")
print(f"  Цепочек: {len(result['chains'])}")

if result['chains']:
    chain = result['chains'][0]
    print(f"  Категория: {chain['process_category']}")
    print(f"  Этапов: {len(chain['stages'])}")
    print(f"  Уверенность: {chain['confidence']:.2f}")

# Тест 2: SMART режим (forbidden terms не блокируют)
print("\n--- Тест 2: SMART режим ---")
text2 = """
Когда человек говорит об эго и медитации, я объясняю:
это на самом деле Я-образ и метанаблюдение. Разотождествление
с Я-образом ведёт к чистому осознаванию. В поле внимания 
появляется свободное внимание и присутствие.
Автоматизмы психики становятся видны наблюдающему сознанию.
"""

result = extractor.extract(text2)
print(f"  Валиден: {result['valid']}")
print(f"  Причина: {result.get('reason', 'N/A')}")
print(f"  Цепочек: {len(result['chains'])}")

# Тест 3: Низкая плотность отклоняется
print("\n--- Тест 3: Низкая плотность ---")
text3 = """
Человек пришел на консультацию и рассказал о своих проблемах.
Мы поговорили о его детстве и отношениях с родителями.
"""

result = extractor.extract(text3)
print(f"  Валиден: {result['valid']} (ожидается False)")
print(f"  Причина: {result.get('reason', 'N/A')}")

# Тест 4: Цикличность
print("\n--- Тест 4: Определение цикличности ---")
text4 = """
В практике нейро-сталкинга процесс осознавания снова и снова 
возвращается к метанаблюдению. Ищущий периодически замечает 
Я-образ и разотождествляется с ним. Это спираль развития,
где каждый цикл приносит более глубокое чистое осознавание.
Автоматизмы психики становятся всё более прозрачными.
"""

result = extractor.extract(text4)
print(f"  Валиден: {result['valid']}")
if result['chains']:
    chain = result['chains'][0]
    print(f"  Циклический: {chain['is_cyclical']}")
    print(f"  Маркеры целостности: {chain['wholeness_markers']}")

# Тест 5: Utility функция
print("\n--- Тест 5: Utility функция ---")
result = extract_causal_chains(text1)
print(f"  Валиден: {result['valid']}")
print(f"  Цепочек: {len(result['chains'])}")

print("\n" + "=" * 60)
print("Тестирование завершено успешно!")
print("=" * 60)
