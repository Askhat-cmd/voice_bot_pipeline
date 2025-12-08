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
    """Тест: текст с запрещенными терминами отклоняется (в STRICT режиме)"""
    
    text = """
    Клиент испытывает стресс из-за активности эго.
    Подсознание формирует защитные механизмы.
    Рекомендуется медитация для работы с тревогой.
    """
    
    result = validator.validate_text(text, validation_mode="strict")
    
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
    """Тест: смешанный контент с достаточной плотностью проходит (SMART режим)"""
    
    text = """
    В процессе работы с человеком важно понимать, как работает метанаблюдение.
    Когда Ищущий начинает наблюдать за Я-образом, происходит разотождествление.
    Поле внимания расширяется, возникает свободное внимание и чистое осознавание.
    Этот путь ведет к пробуждению сознания через центрирование на присутствии.
    """
    
    result = validator.validate_text(text, validation_mode="smart")
    
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


# =============================================================
# НОВЫЕ ТЕСТЫ: SMART РЕЖИМ ВАЛИДАЦИИ
# =============================================================

def test_smart_mode_ignores_forbidden(validator):
    """
    SMART режим: Пропускает forbidden terms если плотность ≥15%
    
    Это ключевой тест - показывает, что SMART режим позволяет
    сохранить ~95% контента лекций вместо ~40% в strict режиме.
    """
    text = """
    Человек приходит с тревогой и говорит про эго и подсознание.
    Я объясняю: это не эго, это Я-образ. Метанаблюдение за Я-образом
    в поле внимания ведёт к разотождествлению. Ищущий замечает
    автоматизмы психики и захват внимания Я-образом.
    Через свободное внимание возникает чистое осознавание.
    """
    
    result = validator.validate_text(text, validation_mode="smart")
    
    assert result.is_valid == True
    assert len(result.forbidden_terms_found) > 0  # Найдены но не блокируют
    assert result.metrics['density'] >= 0.15
    
    print(f"✅ SMART: плотность {result.metrics['density']:.1%}, "
          f"forbidden найдено: {len(result.forbidden_terms_found)}, текст ПРОПУЩЕН")


def test_smart_mode_blocks_low_density(validator):
    """
    SMART режим: Блокирует низкую плотность <15%
    
    Даже в SMART режиме текст без достаточного количества
    терминов Сарсекенова будет отклонён.
    """
    text = """
    Эго, подсознание, тревога, стресс. Медитация помогает людям.
    Психотерапия работает хорошо. Клиент доволен результатами.
    Иногда упомяну метанаблюдение для полноты.
    """
    
    result = validator.validate_text(text, validation_mode="smart")
    
    assert result.is_valid == False
    assert result.metrics['density'] < 0.15
    
    print(f"❌ SMART: плотность {result.metrics['density']:.1%} < 15%, текст ЗАБЛОКИРОВАН")


def test_strict_mode_blocks_forbidden_even_with_high_density(validator):
    """
    STRICT режим: Блокирует forbidden terms даже при высокой плотности
    
    Демонстрирует разницу между SMART и STRICT режимами.
    """
    text = """
    Метанаблюдение за Я-образом через разотождествление.
    Поле внимания расширяется, свободное внимание возникает.
    Но люди говорят "эго" и "медитация" по привычке.
    Ищущий практикует центрирование на присутствии.
    """
    
    result = validator.validate_text(text, validation_mode="strict")
    
    assert result.is_valid == False  # Заблокировано из-за forbidden
    assert result.metrics['density'] >= 0.25
    assert len(result.forbidden_terms_found) > 0
    
    print(f"❌ STRICT: плотность {result.metrics['density']:.1%}, "
          f"но forbidden найдено → ЗАБЛОКИРОВАНО")


def test_soft_mode_contextual_usage(validator):
    """
    SOFT режим: Пропускает forbidden terms в объяснительном контексте
    
    Проверяет, что forbidden terms около терминов-замен проходят.
    """
    text = """
    Люди говорят "эго", но на самом деле это Я-образ.
    Метанаблюдение за Я-образом через разотождествление.
    Поле внимания расширяется, возникает чистое осознавание.
    Ищущий практикует центрирование на присутствии.
    """
    
    result = validator.validate_text(text, validation_mode="soft")
    
    # Высокая плотность + контекст объяснения = пропускаем
    assert result.metrics['density'] >= 0.25
    
    print(f"SOFT: плотность {result.metrics['density']:.1%}, "
          f"forbidden={len(result.forbidden_terms_found)}, "
          f"contextual={result.is_contextual}, valid={result.is_valid}")


def test_mode_comparison_same_text(validator):
    """
    Сравнение всех режимов на одном тексте
    
    Показывает, как один и тот же текст обрабатывается в разных режимах.
    """
    text = """
    Человек с тревогой говорит: "Моё эго меня разрушает."
    Я объясняю: это Я-образ. Метанаблюдение за Я-образом
    в поле внимания ведёт к разотождествлению. Ищущий видит
    автоматизмы психики и практикует центрирование на присутствии.
    """
    
    results = {
        "smart": validator.validate_text(text, validation_mode="smart"),
        "soft": validator.validate_text(text, validation_mode="soft"),
        "strict": validator.validate_text(text, validation_mode="strict"),
        "off": validator.validate_text(text, validation_mode="off")
    }
    
    print("\n" + "=" * 60)
    print("СРАВНЕНИЕ РЕЖИМОВ НА ОДНОМ ТЕКСТЕ")
    print("=" * 60)
    
    for mode, result in results.items():
        status = "✅ VALID" if result.is_valid else "❌ INVALID"
        print(f"{mode.upper():8} {status:12} density={result.metrics['density']:.1%} "
              f"forbidden={len(result.forbidden_terms_found)}")
    
    print("=" * 60)
    
    # SMART и OFF должны пропустить
    assert results["smart"].is_valid == True
    assert results["off"].is_valid == True
    # STRICT должен заблокировать (forbidden terms)
    assert results["strict"].is_valid == False


def test_validation_result_has_is_contextual(validator):
    """
    Тест: ValidationResult содержит поле is_contextual
    """
    text = """
    Метанаблюдение за Я-образом ведет к разотождествлению.
    Поле внимания расширяется, чистое осознавание возникает.
    """
    
    result = validator.validate_text(text)
    
    # Проверяем наличие нового поля
    assert hasattr(result, 'is_contextual')
    assert isinstance(result.is_contextual, bool)
    
    print(f"✅ ValidationResult.is_contextual = {result.is_contextual}")


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
    
    print("\n7. test_mixed_content")
    test_mixed_content(validator)
    
    print("\n8. test_utility_function")
    test_utility_function()
    
    # НОВЫЕ ТЕСТЫ SMART РЕЖИМА
    print("\n" + "=" * 60)
    print("НОВЫЕ ТЕСТЫ: SMART РЕЖИМ")
    print("=" * 60)
    
    print("\n9. test_smart_mode_ignores_forbidden")
    test_smart_mode_ignores_forbidden(validator)
    
    print("\n10. test_smart_mode_blocks_low_density")
    test_smart_mode_blocks_low_density(validator)
    
    print("\n11. test_strict_mode_blocks_forbidden_even_with_high_density")
    test_strict_mode_blocks_forbidden_even_with_high_density(validator)
    
    print("\n12. test_soft_mode_contextual_usage")
    test_soft_mode_contextual_usage(validator)
    
    print("\n13. test_mode_comparison_same_text")
    test_mode_comparison_same_text(validator)
    
    print("\n14. test_validation_result_has_is_contextual")
    test_validation_result_has_is_contextual(validator)
    
    print("\n" + "=" * 60)
    print("ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ!")
    print("=" * 60)
