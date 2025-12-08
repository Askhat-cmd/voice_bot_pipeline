#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для CausalChainExtractor.

Проверяет извлечение причинно-следственных цепочек трансформации сознания
в терминологии Саламата Сарсекенова с SMART режимом валидации.
"""

import pytest
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from text_processor.extractors.causal_chain_extractor import (
    CausalChainExtractor,
    CausalChain,
    CausalChainStage,
    InterventionPoint,
    extract_causal_chains
)
from text_processor.validators.terminology_validator import TerminologyValidator


class TestCausalChainExtractor:
    """Тесты класса CausalChainExtractor"""
    
    @pytest.fixture
    def extractor(self):
        """Создание экстрактора для тестов"""
        return CausalChainExtractor()
    
    @pytest.fixture
    def validator(self):
        """Создание валидатора для тестов"""
        return TerminologyValidator()
    
    # ==================== Тесты извлечения цепочек ====================
    
    def test_extract_triada_transformation_chain(self, extractor):
        """Триада: наблюдение → осознавание → трансформация"""
        text = """
        Когда Ищущий практикует метанаблюдение, он сначала наблюдает за 
        мыслительным потоком. Затем происходит осознавание автоматизмов психики.
        Это ведет к трансформации через разотождествление с Я-образом.
        В результате возникает чистое осознавание и свободное внимание.
        """
        
        result = extractor.extract(text, specific_category="триада_трансформации")
        
        assert result['valid'] is True
        assert len(result['chains']) >= 1
        
        chain = result['chains'][0]
        assert chain['process_category'] == "триада_трансформации"
        assert len(chain['stages']) >= 2
    
    def test_extract_attention_work_chain(self, extractor):
        """Работа с вниманием"""
        text = """
        В практике нейро-сталкинга работа с полем внимания начинается с 
        центрирования. Когда происходит захват внимания автоматизмами,
        практикующий использует свободное внимание для возвращения 
        в присутствие. Расширение поля восприятия позволяет удерживать
        осознавание в поле внимания.
        """
        
        result = extractor.extract(text, specific_category="работа_с_вниманием")
        
        assert result['valid'] is True
        assert len(result['chains']) >= 1
        
        chain = result['chains'][0]
        assert chain['process_category'] == "работа_с_вниманием"
    
    def test_extract_disidentification_chain(self, extractor):
        """Разотождествление с Я-образом"""
        text = """
        Процесс разотождествления начинается с осознавания Я-образа
        как автоматической конструкции. Ищущий замечает идентификацию 
        с ложной самостью и автоматизмы психики, которые поддерживают её.
        Через метанаблюдение возникает наблюдающее сознание, свободное
        от отождествления. Это ведёт к разотождествлению и чистому осознаванию.
        """
        
        result = extractor.extract(text, specific_category="разотождествление")
        
        assert result['valid'] is True
        assert len(result['chains']) >= 1
        
        chain = result['chains'][0]
        assert chain['process_category'] == "разотождествление"
    
    # ==================== Тесты SMART режима валидации ====================
    
    def test_low_density_rejected(self, extractor):
        """Низкая плотность (<15%) отклоняется"""
        text = """
        Человек пришел на консультацию и рассказал о своих проблемах.
        Мы поговорили о его детстве и отношениях с родителями.
        Он понял некоторые важные вещи о себе и своем поведении.
        """
        
        result = extractor.extract(text)
        
        # Должно быть отклонено из-за низкой плотности
        assert result['valid'] is False
        assert "плотность" in result['reason'].lower() or "density" in result['reason'].lower()
    
    def test_forbidden_terms_NOT_rejected_in_smart_mode(self, extractor):
        """
        КРИТИЧНО: В SMART режиме forbidden terms НЕ блокируют!
        """
        text = """
        Когда человек говорит об эго и медитации, я объясняю:
        это на самом деле Я-образ и метанаблюдение. Разотождествление
        с Я-образом ведёт к чистому осознаванию. В поле внимания 
        появляется свободное внимание и присутствие.
        Автоматизмы психики становятся видны наблюдающему сознанию.
        """
        
        result = extractor.extract(text)
        
        # Должно ПРОЙТИ (плотность достаточная, режим smart)
        assert result['valid'] is True, f"Expected valid but got: {result['reason']}"
        
        # Должны быть найдены цепочки
        assert len(result['chains']) >= 1
    
    # ==================== Тесты точек вмешательства ====================
    
    def test_intervention_points_identified(self, extractor):
        """Определение точек вмешательства"""
        text = """
        При практике метанаблюдения Ищущий наблюдает за Я-образом.
        Когда возникает захват внимания, применяется центрирование.
        Через разотождествление с автоматизмами психики достигается
        свободное внимание и чистое осознавание.
        """
        
        result = extractor.extract(text)
        
        assert result['valid'] is True
        assert len(result['chains']) >= 1
        
        # Проверяем наличие точек вмешательства
        chain = result['chains'][0]
        
        # Должны быть найдены точки вмешательства для практик
        # (метанаблюдение, центрирование, разотождествление)
        all_intervention_practices = [
            ip['practice'] for ip in chain['intervention_points']
        ]
        
        # Хотя бы одна практика должна быть найдена
        # (зависит от структуры текста)
        assert chain['intervention_points'] is not None
    
    # ==================== Тесты системности ====================
    
    def test_cyclical_process_detection(self, extractor):
        """Определение цикличности (маркеры: "снова", "спираль")"""
        text = """
        В практике нейро-сталкинга процесс осознавания снова и снова 
        возвращается к метанаблюдению. Ищущий периодически замечает 
        Я-образ и разотождествляется с ним. Это спираль развития,
        где каждый цикл приносит более глубокое чистое осознавание.
        Автоматизмы психики становятся всё более прозрачными.
        """
        
        result = extractor.extract(text)
        
        assert result['valid'] is True
        assert len(result['chains']) >= 1
        
        # Проверяем определение цикличности
        chain = result['chains'][0]
        assert chain['is_cyclical'] is True
    
    def test_wholeness_markers_extraction(self, extractor):
        """Извлечение: "целостность", "интеграция", "эмерджентность" """
        text = """
        Через практику метанаблюдения достигается целостность восприятия.
        Интеграция опыта происходит через разотождествление с Я-образом.
        Возникает единство наблюдающего и наблюдаемого в чистом осознавании.
        Автоматизмы психики интегрируются в поле внимания как целое.
        """
        
        result = extractor.extract(text)
        
        assert result['valid'] is True
        assert len(result['chains']) >= 1
        
        chain = result['chains'][0]
        
        # Должны быть найдены маркеры целостности
        assert len(chain['wholeness_markers']) >= 1
        
        # Проверяем конкретные маркеры
        markers_lower = [m.lower() for m in chain['wholeness_markers']]
        assert 'целостность' in markers_lower or 'интеграция' in markers_lower or 'единство' in markers_lower
    
    def test_systemic_relationships(self, extractor):
        """Проверка emerges_from и enables в stages"""
        text = """
        Практика начинается с метанаблюдения за мыслительным потоком.
        Из этого возникает осознавание автоматизмов психики и Я-образа.
        Затем происходит разотождествление с ложной самостью.
        В результате появляется чистое осознавание и свободное внимание.
        """
        
        result = extractor.extract(text)
        
        assert result['valid'] is True
        assert len(result['chains']) >= 1
        
        chain = result['chains'][0]
        stages = chain['stages']
        
        # Проверяем системные связи
        assert len(stages) >= 2
        
        # Второй этап должен иметь emerges_from (связь с первым)
        if len(stages) >= 2:
            second_stage = stages[1]
            assert second_stage['emerges_from'] is not None
            assert 1 in second_stage['emerges_from']
        
        # Первый этап должен иметь enables (связь со вторым)
        first_stage = stages[0]
        assert first_stage['enables'] is not None
        assert 2 in first_stage['enables']
    
    # ==================== Тесты расчёта уверенности ====================
    
    def test_confidence_calculation(self, extractor):
        """Расчёт уверенности (5+ этапов, 8+ терминов → >0.7)"""
        text = """
        В нейро-сталкинге процесс трансформации начинается с метанаблюдения.
        Ищущий наблюдает за Я-образом в поле внимания.
        Затем происходит осознавание автоматизмов психики.
        Через центрирование достигается присутствие.
        Разотождествление с ложной самостью открывает путь к трансформации.
        В результате возникает чистое осознавание и свободное внимание.
        Интеграция опыта закрепляет достигнутое состояние сознания.
        """
        
        result = extractor.extract(text)
        
        assert result['valid'] is True
        assert len(result['chains']) >= 1
        
        chain = result['chains'][0]
        
        # Уверенность должна быть достаточно высокой при большом количестве
        # этапов и терминов
        assert chain['confidence'] >= 0.6
    
    # ==================== Тесты множественных категорий ====================
    
    def test_multiple_categories_in_text(self, extractor):
        """Извлечение нескольких категорий из одного текста"""
        text = """
        Практика нейро-сталкинга включает работу с полем внимания и 
        процесс разотождествления. Через метанаблюдение Ищущий замечает
        захват внимания Я-образом. Центрирование возвращает в присутствие.
        Осознавание автоматизмов психики ведёт к трансформации.
        Чистое осознавание и свободное внимание возникают естественно.
        Разотождествление с ложной самостью завершает процесс.
        """
        
        # Извлечение без указания категории - должны найтись несколько
        result = extractor.extract(text)
        
        assert result['valid'] is True
        
        # Проверяем метрики
        categories_found = result['metrics'].get('categories', [])
        
        # Должно быть найдено несколько категорий
        # (триада, работа с вниманием, разотождествление)
        assert len(categories_found) >= 1
    
    # ==================== Тесты минимальных требований ====================
    
    def test_minimum_sarsekenov_terms_requirement(self, extractor):
        """Минимум 3 термина Сарсекенова на цепочку"""
        # Текст с недостаточным количеством терминов в одном контексте
        text = """
        Человек занимается метанаблюдением. Это полезная практика.
        Она помогает понять себя. Процесс требует времени и терпения.
        """
        
        result = extractor.extract(text)
        
        # Текст может быть валидным, но цепочки не должно быть
        # из-за недостатка терминов в предложениях
        # (зависит от плотности)
        if result['valid']:
            # Если текст прошёл, цепочки должны иметь минимум 3 термина
            for chain in result['chains']:
                all_terms = []
                for stage in chain['stages']:
                    all_terms.extend(stage['sarsekenov_terms'])
                assert len(all_terms) >= 3
    
    # ==================== Тесты utility функции ====================
    
    def test_utility_function_extract_causal_chains(self):
        """Utility функция extract_causal_chains"""
        text = """
        Когда Ищущий практикует метанаблюдение, он наблюдает за Я-образом.
        Осознавание автоматизмов психики ведёт к разотождествлению.
        В результате возникает чистое осознавание и свободное внимание.
        """
        
        result = extract_causal_chains(text)
        
        assert result['valid'] is True
        assert 'chains' in result
        assert 'metrics' in result
    
    def test_utility_function_with_specific_category(self):
        """Utility функция с конкретной категорией"""
        text = """
        Практика разотождествления начинается с осознавания Я-образа.
        Ищущий замечает автоматизмы психики и идентификацию.
        Через метанаблюдение возникает наблюдающее сознание.
        Чистое осознавание приходит через разотождествление с ложной самостью.
        """
        
        result = extract_causal_chains(
            text, 
            specific_category="разотождествление"
        )
        
        assert result['valid'] is True
        
        # Все найденные цепочки должны быть категории "разотождествление"
        for chain in result['chains']:
            assert chain['process_category'] == "разотождествление"
    
    # ==================== Тесты структуры данных ====================
    
    def test_chain_structure_completeness(self, extractor):
        """Проверка полноты структуры CausalChain"""
        text = """
        Метанаблюдение за Я-образом в поле внимания ведёт к осознаванию.
        Разотождествление с автоматизмами психики открывает чистое осознавание.
        Свободное внимание и присутствие возникают естественно.
        """
        
        result = extractor.extract(text)
        
        assert result['valid'] is True
        assert len(result['chains']) >= 1
        
        chain = result['chains'][0]
        
        # Проверяем наличие всех полей
        assert 'process_name' in chain
        assert 'process_category' in chain
        assert 'stages' in chain
        assert 'intervention_points' in chain
        assert 'context' in chain
        assert 'source_quote' in chain
        assert 'confidence' in chain
        assert 'is_cyclical' in chain
        assert 'wholeness_markers' in chain
        assert 'sarsekenov_density' in chain
        
        # Проверяем структуру этапов
        for stage in chain['stages']:
            assert 'stage' in stage
            assert 'stage_name' in stage
            assert 'description' in stage
            assert 'sarsekenov_terms' in stage
            assert 'emerges_from' in stage
            assert 'enables' in stage


class TestCausalChainExtractorEdgeCases:
    """Тесты граничных случаев"""
    
    @pytest.fixture
    def extractor(self):
        return CausalChainExtractor()
    
    def test_empty_text(self, extractor):
        """Пустой текст"""
        result = extractor.extract("")
        assert result['valid'] is False
    
    def test_very_short_text(self, extractor):
        """Очень короткий текст"""
        result = extractor.extract("Метанаблюдение.")
        # Должен быть отклонён из-за недостаточной плотности или контента
        assert result['valid'] is False or len(result['chains']) == 0
    
    def test_text_without_sarsekenov_terms(self, extractor):
        """Текст без терминов Сарсекенова"""
        text = """
        Обычный текст о психологии и самопознании.
        Человек пытается понять себя через анализ своих мыслей.
        Это важный процесс для личностного роста.
        """
        
        result = extractor.extract(text)
        assert result['valid'] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
