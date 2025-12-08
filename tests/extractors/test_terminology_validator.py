#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для терминологического валидатора
"""

import sys
from pathlib import Path

# Добавляем корень проекта в путь
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from text_processor.validators.terminology_validator import (
    TerminologyValidator,
    ValidationResult,
    validate_block
)


@pytest.fixture
def validator():
    """Fixture для создания валидатора"""
    return TerminologyValidator()


def test_valid_sarsekenov_text(validator):
    """Тест: валидный текст Сарсекенова проходит валидацию"""
    
    text = """
    Когда Ищущий практикует метанаблюдение, он начинает замечать 
    появление Я-образа в поле внимания. Через разотождествление 
    возникает свободное внимание, и Ищущий открывает чистое осознавание.
    Процесс центрирования на присутствии ведет к прозрению.
    """
    
    result = validator.validate_text(text)
    
    assert result.is_valid == True
    assert result.metrics['density'] >= 0.25
    assert len(result.sarsekenov_entities) >= 5
    assert len(result.forbidden_terms_found) == 0
    
    print(f"Плотность: {result.metrics['density']:.1%}")
    print(f"Найдено терминов: {len(result.sarsekenov_entities)}")
    print(f"Термины: {result.sarsekenov_entities}")


def test_invalid_forbidden_terms(validator):
    """Тест: текст с запрещенными терминами отклоняется"""
    
    text = """
    Клиент испытывает стресс из-за активности эго.
    Подсознание формирует защитные механизмы.
    Рекомендуется медитация для работы с тревогой.
    """
    
    result = validator.validate_text(text, strict_mode=True)
    
    assert result.is_valid == False
    assert len(result.forbidden_terms_found) > 0
    
    print(f"Найдены запрещенные термины: {result.forbidden_terms_found}")
    print(f"Причина отклонения: {result.reason}")


def test_low_density_text(validator):
    """Тест: текст с низкой плотностью терминов отклоняется"""
    
    text = """
    Человек пришел на консультацию и рассказал о своих проблемах.
    Он чувствует неудовлетворенность жизнью и ищет перемены.
    Возможно, метанаблюдение поможет, но это только одна практика среди многих.
    """
    
    result = validator.validate_text(text, min_density=0.25)
    
    assert result.is_valid == False
    assert result.metrics['density'] < 0.25
    
    print(f"Плотность слишком низкая: {result.metrics['density']:.1%}")


def test_mixed_content(validator):
    """Тест: смешанный контент с достаточной плотностью проходит"""
    
    text = """
    В процессе работы с человеком важно понимать, как работает метанаблюдение.
    Когда Ищущий начинает наблюдать за Я-образом, происходит разотождествление.
    Поле внимания расширяется, возникает свободное внимание и чистое осознавание.
    Этот путь ведет к пробуждению сознания через центрирование на присутствии.
    """
    
    result = validator.validate_text(text, min_density=0.25, strict_mode=False)
    
    assert result.is_valid == True
    
    print(f"Смешанный контент прошел: плотность {result.metrics['density']:.1%}")


def test_entity_extraction(validator):
    """Тест: корректное извлечение сущностей (с лемматизацией - любые падежи)"""
    
    text = """
    Метанаблюдение за Я-образом в поле внимания ведет к разотождествлению.
    Ищущий практикует центрирование на присутствии.
    """
    
    result = validator.validate_text(text)
    
    expected_entities = [
        "метанаблюдение",
        "Я-образ", 
        "поле внимания",
        "разотождествление",
        "Ищущий",
        "центрирование на присутствии",
    ]
    
    for entity in expected_entities:
        found = any(e.lower() == entity.lower() for e in result.sarsekenov_entities)
        assert found, f"Отсутствует: {entity}"
    
    print(f"Извлечено сущностей: {result.sarsekenov_entities}")


def test_term_replacement(validator):
    """Тест: замена запрещенных терминов"""
    
    text = "Эго создает защиты через подсознание. Медитация помогает с тревогой."
    
    replaced = validator.replace_forbidden_terms(text)
    
    assert "эго" not in replaced.lower()
    assert "подсознание" not in replaced.lower()
    assert "медитация" not in replaced.lower()
    assert "Я-образ" in replaced
    assert "автоматизмы психики" in replaced
    assert "метанаблюдение" in replaced
    
    print(f"Исходный: {text}")
    print(f"Заменен: {replaced}")


def test_get_term_info(validator):
    """Тест: получение информации о термине"""
    
    term_info = validator.get_term_info("метанаблюдение")
    
    assert term_info is not None
    assert term_info['term'] == "метанаблюдение"
    assert term_info['tier'].startswith('tier_')
    assert term_info['level'] is not None
    
    print(f"Информация о термине: {term_info}")


def test_utility_function():
    """Тест: utility функция validate_block"""
    
    text = "Метанаблюдение за Я-образом ведет к разотождествлению в поле внимания."
    
    result = validate_block(text)
    
    assert isinstance(result, ValidationResult)
    
    print(f"Utility функция работает, is_valid={result.is_valid}")


if __name__ == "__main__":
    # Запуск тестов вручную
    validator = TerminologyValidator()
    
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ТЕРМИНОЛОГИЧЕСКОГО ВАЛИДАТОРА")
    print("=" * 60)
    
    print("\n1. test_valid_sarsekenov_text")
    test_valid_sarsekenov_text(validator)
    
    print("\n2. test_invalid_forbidden_terms")
    test_invalid_forbidden_terms(validator)
    
    print("\n3. test_low_density_text")
    test_low_density_text(validator)
    
    print("\n4. test_entity_extraction")
    test_entity_extraction(validator)
    
    print("\n5. test_term_replacement")
    test_term_replacement(validator)
    
    print("\n6. test_get_term_info")
    test_get_term_info(validator)
    
    print("\n" + "=" * 60)
    print("ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    print("=" * 60)
