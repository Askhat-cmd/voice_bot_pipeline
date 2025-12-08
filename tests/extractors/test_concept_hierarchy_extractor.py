# -*- coding: utf-8 -*-
import pytest
from voice_bot_pipeline.text_processor.extractors.concept_hierarchy_extractor import ConceptHierarchyExtractor, extract_concept_hierarchy

@pytest.fixture
def extractor():
    return ConceptHierarchyExtractor()

def test_strict_5_level_hierarchy(extractor):
    """Проверка строгой 5-уровневой структуры"""
    # Текст должен быть достаточно насыщенным для прохождения валидатора
    text = """
    Нейро-сталкинг (корневой концепт) включает поле внимания как core component.
    Для работы с полем внимания применяется метанаблюдение (практика).
    Метанаблюдение реализуется через технику "наблюдение мыслительного потока".
    Это позволяет достичь разотождествления и чистого осознавания.
    """
    
    result = extractor.extract(text)
    
    assert result['valid'] is True, f"Validation failed: {result['reason']}"
    hierarchy = result['hierarchy']
    
    assert hierarchy['root']['level'] == "root"
    assert hierarchy['root']['name'] in ["нейро-сталкинг", "нео-сталкинг", "сталкинг ума"]
    
    # Проверяем наличие уровней
    assert len(hierarchy['domains']) > 0
    assert len(hierarchy['practices']) > 0
    assert len(hierarchy['techniques']) > 0

def test_root_must_be_allowed(extractor):
    """Root может быть только из ALLOWED_ROOTS"""
    # Текст насыщен терминами, но не содержит правильного корня
    text = """
    Психотерапия работает с полем внимания и использует метанаблюдение.
    Разотождествление помогает в работе с автоматизмами.
    Чистое осознавание — цель практики.
    """
    
    result = extractor.extract(text)
    
    # Должно быть отклонено (нет нейро-сталкинга)
    assert result['valid'] is False
    # Причина может быть в валидаторе (если плотность мала) или в отсутствии корня
    # В данном случае терминов много, так что скорее всего "Не найден корневой концепт"
    assert "корневой" in result['reason'].lower() or "root" in result['reason'].lower()

def test_parent_child_relationships(extractor):
    """Каждый узел имеет родителя"""
    text = """
    Нейро-сталкинг работает с полем внимания.
    Метанаблюдение — это практика для поля внимания.
    """
    
    result = extractor.extract(text)
    
    assert result['valid'] is True
    hierarchy = result['hierarchy']
    
    # Проверка что practices имеют родителей из domains
    domain_names = [d['name'] for d in hierarchy['domains']]
    for practice in hierarchy['practices']:
        assert practice['parent'] in domain_names

def test_cross_connections_extracted(extractor):
    """Извлечение горизонтальных связей"""
    text = """
    Нейро-сталкинг.
    Поле внимания — важный элемент.
    Метанаблюдение делает возможным разотождествление.
    Разотождествление ведёт к чистому осознаванию.
    """
    
    result = extractor.extract(text)
    
    assert result['valid'] is True
    assert len(result['hierarchy']['cross_connections']) > 0
    
    conn = result['hierarchy']['cross_connections'][0]
    assert conn['relation'] in ['enables', 'leads_to', 'requires', 'transforms_into']

def test_exercises_with_duration_frequency(extractor):
    """Извлечение упражнений с параметрами"""
    text = """
    Нейро-сталкинг. Поле внимания. Метанаблюдение.
    Техника: наблюдение мыслительного потока.
    Практикуй наблюдение мыслительного потока 5 минут,
    3 раза в день для развития осознанности.
    """
    
    result = extractor.extract(text)
    
    assert result['valid'] is True, f"Failed: {result.get('reason')}"
    exercises = result['hierarchy']['exercises']
    assert len(exercises) > 0
    
    exercise = exercises[0]
    assert exercise['duration'] is not None
    assert exercise['frequency'] is not None
    assert "5 минут" in exercise['duration']
    assert "3 раза в день" in exercise['frequency']

def test_minimum_sarsekenov_terms(extractor):
    """Минимум 3 термина Сарсекенова в иерархии"""
    text = """
    Нейро-сталкинг — это учение.
    """
    
    result = extractor.extract(text)
    
    # Может быть отклонено из-за недостатка терминов или валидатором
    assert result['valid'] is False
    reason = result['reason'].lower()
    assert "плотность" in reason or "термин" in reason or "enough" in reason

def test_utility_function():
    """Тест utility функции"""
    text = """
    Нейро-сталкинг включает работу с полем внимания
    через практику метанаблюдения и разотождествления.
    """
    
    result = extract_concept_hierarchy(text, expected_root="нейро-сталкинг")
    
    assert result['valid'] is True
    assert result['hierarchy']['root']['name'] == "нейро-сталкинг"

def test_smart_mode_validation(extractor):
    """SMART режим: forbidden terms не блокируют"""
    text = """
    Нейро-сталкинг отличается от медитации и работы с эго.
    Основа — поле внимания, метанаблюдение и разотождествление.
    """
    
    result = extractor.extract(text)
    
    # Должно быть принято (плотность достаточная, режим smart)
    assert result['valid'] is True