#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для экстрактора паттернов нейро-сталкинга.
"""

import sys
from pathlib import Path

# Добавляем корень проекта в sys.path
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
from text_processor.extractors.neurostalking_pattern_extractor import (
    NeurostalkingPatternExtractor,
    NeurostalkingPattern,
    extract_patterns
)
from text_processor.validators.terminology_validator import TerminologyValidator


@pytest.fixture
def extractor():
    """Fixture для создания экстрактора"""
    return NeurostalkingPatternExtractor()


def test_extract_triada_pattern(extractor):
    """Тест: извлечение паттерна триады трансформации"""
    
    text = """
    Когда Ищущий практикует метанаблюдение, он сначала наблюдает за 
    мыслительным потоком. Затем происходит осознавание автоматизмов психики.
    Это ведет к трансформации через разотождествление с Я-образом.
    """
    
    result = extractor.extract(text)
    
    assert result['valid'] == True
    assert len(result['patterns']) > 0
    
    # Проверка, что найден паттерн категории триада_трансформации
    triada_patterns = [
        p for p in result['patterns']
        if p['pattern_category'] == 'триада_трансформации'
    ]
    
    assert len(triada_patterns) > 0
    
    pattern = triada_patterns[0]
    assert 'метанаблюдение' in [t.lower() for t in pattern['key_terms']]
    
    print(f"✅ Найден паттерн триады: {pattern['pattern_name']}")
    print(f"   Ключевые термины: {pattern['key_terms']}")


def test_extract_attention_field_pattern(extractor):
    """Тест: извлечение паттерна работы с вниманием"""
    
    text = """
    Поле внимания захватывается Я-образом, когда Ищущий погружается 
    во внутренний диалог. Свободное внимание теряется, поле восприятия 
    сужается. Через метанаблюдение происходит расширение поля внимания.
    """
    
    result = extractor.extract(text)
    
    assert result['valid'] == True
    
    attention_patterns = [
        p for p in result['patterns']
        if p['pattern_category'] == 'работа_с_вниманием'
    ]
    
    assert len(attention_patterns) > 0
    
    pattern = attention_patterns[0]
    attention_terms = ['поле внимания', 'свободное внимание', 'захват внимания']
    
    found_attention_terms = [
        term for term in attention_terms
        if any(term.lower() in kt.lower() for kt in pattern['key_terms'])
    ]
    
    assert len(found_attention_terms) > 0
    
    print(f"✅ Найден паттерн внимания: {pattern['pattern_name']}")


def test_extract_disidentification_pattern(extractor):
    """Тест: извлечение паттерна разотождествления"""
    
    text = """
    Разотождествление с Я-образом происходит через наблюдающее сознание.
    Ищущий замечает идентификацию с мыслями и начинает видеть ложную самость.
    Возникает пространство между наблюдателем и наблюдаемым.
    """
    
    result = extractor.extract(text)
    
    assert result['valid'] == True
    
    disid_patterns = [
        p for p in result['patterns']
        if p['pattern_category'] == 'разотождествление'
    ]
    
    assert len(disid_patterns) > 0
    
    print(f"✅ Найден паттерн разотождествления")
    print(f"   Описание: {disid_patterns[0]['description'][:100]}...")


def test_extract_consciousness_state_pattern(extractor):
    """Тест: извлечение паттерна состояния сознания"""
    
    text = """
    В чистом осознавании Ищущий пребывает в присутствии здесь-и-сейчас.
    Живое переживание настоящего момента раскрывает пробуждение сознания.
    Возникает ясность и прояснение природы сознания.
    """
    
    result = extractor.extract(text)
    
    assert result['valid'] == True
    
    state_patterns = [
        p for p in result['patterns']
        if p['pattern_category'] == 'состояния_сознания'
    ]
    
    assert len(state_patterns) > 0
    
    print(f"✅ Найден паттерн состояния сознания")


def test_invalid_text_rejected(extractor):
    """Тест: невалидный текст отклоняется"""
    
    text = """
    Клиент испытывает стресс и тревогу. Его эго защищается.
    Рекомендуется медитация и работа с подсознанием.
    """
    
    result = extractor.extract(text)
    
    assert result['valid'] == False
    assert len(result['patterns']) == 0
    
    print(f"❌ Невалидный текст корректно отклонен: {result['reason']}")


def test_low_density_text_rejected(extractor):
    """Тест: текст с низкой плотностью отклоняется"""
    
    text = """
    Человек пришел на встречу и рассказал о своих переживаниях.
    Он чувствует дискомфорт и ищет решение своих проблем.
    Может быть полезно попробовать метанаблюдение.
    """
    
    result = extractor.extract(text, min_density=0.25)
    
    assert result['valid'] == False
    
    print(f"❌ Низкая плотность: {result['reason']}")


def test_specific_category_extraction(extractor):
    """Тест: извлечение только определенной категории"""
    
    text = """
    Метанаблюдение за Я-образом ведет к разотождествлению.
    Поле внимания расширяется, возникает свободное внимание.
    Чистое осознавание раскрывает присутствие.
    """
    
    # Извлечение только паттернов работы с вниманием
    result = extractor.extract(text, categories=['работа_с_вниманием'])
    
    assert result['valid'] == True
    
    # Все паттерны должны быть только этой категории
    for pattern in result['patterns']:
        assert pattern['pattern_category'] == 'работа_с_вниманием'
    
    print(f"✅ Извлечена только категория 'работа_с_вниманием'")


def test_confidence_calculation(extractor):
    """Тест: расчет уверенности в паттерне"""
    
    text = """
    Метанаблюдение за Я-образом через наблюдающее сознание ведет к 
    разотождествлению, расширению поля внимания и чистому осознаванию.
    """
    
    result = extractor.extract(text)
    
    assert result['valid'] == True
    assert len(result['patterns']) > 0
    
    # Паттерны с большим количеством терминов должны иметь высокую уверенность
    high_confidence_patterns = [
        p for p in result['patterns']
        if p['confidence'] > 0.5
    ]
    
    assert len(high_confidence_patterns) > 0
    
    print(f"✅ Найдено {len(high_confidence_patterns)} паттернов с высокой уверенностью")
    for p in high_confidence_patterns:
        print(f"   {p['pattern_name']}: {p['confidence']:.2f}")


def test_related_practices_identified(extractor):
    """Тест: определение связанных практик"""
    
    text = """
    Метанаблюдение и разотождествление работают совместно.
    Центрирование на присутствии усиливает интеграцию опыта.
    """
    
    result = extractor.extract(text)
    
    assert result['valid'] == True
    
    # Проверка, что связанные практики определены
    for pattern in result['patterns']:
        assert len(pattern['related_practices']) > 0
    
    print(f"✅ Связанные практики определены")


def test_utility_function():
    """Тест: utility функция extract_patterns"""
    
    text = """
    Метанаблюдение за Я-образом ведет к разотождествлению 
    и расширению поля внимания.
    """
    
    result = extract_patterns(text)
    
    assert result['valid'] == True
    assert len(result['patterns']) > 0
    
    print(f"✅ Utility функция работает")


def test_pattern_structure(extractor):
    """Тест: структура паттерна корректна"""
    
    text = """
    Метанаблюдение за Я-образом ведет к разотождествлению.
    """
    
    result = extractor.extract(text)
    
    assert len(result['patterns']) > 0
    
    pattern = result['patterns'][0]
    
    # Проверка обязательных полей
    required_fields = [
        'pattern_category',
        'pattern_name',
        'description',
        'key_terms',
        'typical_context',
        'recognition_markers',
        'related_practices',
        'source_quote',
        'confidence'
    ]
    
    for field in required_fields:
        assert field in pattern, f"Отсутствует поле: {field}"
    
    # Проверка типов
    assert isinstance(pattern['key_terms'], list)
    assert isinstance(pattern['recognition_markers'], list)
    assert isinstance(pattern['related_practices'], list)
    assert isinstance(pattern['confidence'], (int, float))
    assert 0 <= pattern['confidence'] <= 1
    
    print(f"✅ Структура паттерна корректна")


if __name__ == "__main__":
    # Запуск тестов вручную
    extractor = NeurostalkingPatternExtractor()
    
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ NEUROSTALKING PATTERN EXTRACTOR")
    print("=" * 60)
    print()
    
    test_extract_triada_pattern(extractor)
    print()
    test_extract_attention_field_pattern(extractor)
    print()
    test_extract_disidentification_pattern(extractor)
    print()
    test_extract_consciousness_state_pattern(extractor)
    print()
    test_invalid_text_rejected(extractor)
    print()
    test_low_density_text_rejected(extractor)
    print()
    test_specific_category_extraction(extractor)
    print()
    test_confidence_calculation(extractor)
    print()
    test_related_practices_identified(extractor)
    print()
    test_utility_function()
    print()
    test_pattern_structure(extractor)
    print()
    
    print("=" * 60)
    print("ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ!")
    print("=" * 60)
