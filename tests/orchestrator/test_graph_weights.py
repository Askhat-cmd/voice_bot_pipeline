"""
Тесты для GraphWeightCalculator и проверки весов в Knowledge Graph.
"""

import pytest
import math
from voice_bot_pipeline.text_processor.orchestrator.graph_weight_calculator import GraphWeightCalculator


class TestGraphWeightCalculator:
    """Тесты для GraphWeightCalculator"""
    
    def test_analyze_block(self):
        """Проверка анализа блока"""
        calculator = GraphWeightCalculator()
        
        block_content = "Осознанность и присутствие важны для практики нейросталкинга. Осознанность помогает развивать присутствие."
        entities = ["осознанность", "присутствие", "нейросталкинг"]
        
        calculator.analyze_block(block_content, entities, block_idx=0)
        
        # Проверяем, что позиции сохранены
        assert "осознанность" in calculator.concept_positions
        assert "присутствие" in calculator.concept_positions
        
        # Проверяем co-occurrence
        pair = tuple(sorted(["осознанность", "присутствие"]))
        assert pair in calculator.cooccurrence_matrix
        assert calculator.cooccurrence_matrix[pair] >= 1
    
    def test_calculate_pmi(self):
        """Проверка вычисления PMI"""
        calculator = GraphWeightCalculator()
        
        # Анализируем несколько блоков
        calculator.analyze_block(
            "Осознанность и присутствие важны.",
            ["осознанность", "присутствие"],
            block_idx=0
        )
        calculator.analyze_block(
            "Осознанность помогает.",
            ["осознанность"],
            block_idx=1
        )
        calculator.analyze_block(
            "Присутствие и осознанность связаны.",
            ["присутствие", "осознанность"],
            block_idx=2
        )
        
        total_blocks = 3
        
        # PMI для часто встречающихся вместе концептов должен быть высоким
        pmi = calculator.calculate_pmi("осознанность", "присутствие", total_blocks)
        assert 0.0 <= pmi <= 1.0
        
        # PMI для невстречающихся вместе должен быть низким
        calculator.analyze_block("Дыхание важно.", ["дыхание"], block_idx=3)
        pmi_low = calculator.calculate_pmi("осознанность", "дыхание", total_blocks + 1)
        assert pmi_low == 0.0 or pmi_low < pmi
    
    def test_calculate_distance_weight(self):
        """Проверка вычисления веса на основе расстояния"""
        calculator = GraphWeightCalculator()
        
        # Блок где концепты близко друг к другу
        block_content = "Осознанность присутствие важны для практики."
        calculator.analyze_block(block_content, ["осознанность", "присутствие"], block_idx=0)
        
        weight_close = calculator.calculate_distance_weight("осознанность", "присутствие")
        assert 0.0 <= weight_close <= 1.0
        
        # Блок где концепты далеко друг от друга
        block_content_far = "Осознанность это важное качество. Присутствие также важно для практики нейросталкинга."
        calculator.analyze_block(block_content_far, ["осознанность", "присутствие"], block_idx=1)
        
        weight_far = calculator.calculate_distance_weight("осознанность", "присутствие")
        # Близкие концепты должны иметь больший вес
        assert weight_close >= weight_far or weight_far < 0.3
    
    def test_calculate_combined_weight(self):
        """Проверка комбинированного веса"""
        calculator = GraphWeightCalculator()
        
        # Анализируем блоки с частыми co-occurrence
        for i in range(3):
            calculator.analyze_block(
                f"Осознанность и присутствие важны для практики {i}.",
                ["осознанность", "присутствие"],
                block_idx=i
            )
        
        total_blocks = 3
        weight = calculator.calculate_combined_weight("осознанность", "присутствие", total_blocks)
        
        # Вес должен быть в диапазоне [0.1, 1.0]
        assert 0.1 <= weight <= 1.0
        
        # Для часто встречающихся вместе концептов вес должен быть высоким
        assert weight > 0.3
    
    def test_combined_weight_no_cooccurrence(self):
        """Проверка веса для концептов без co-occurrence"""
        calculator = GraphWeightCalculator()
        
        calculator.analyze_block("Осознанность важна.", ["осознанность"], block_idx=0)
        calculator.analyze_block("Дыхание важно.", ["дыхание"], block_idx=1)
        
        total_blocks = 2
        weight = calculator.calculate_combined_weight("осознанность", "дыхание", total_blocks)
        
        # Минимальный вес для связей без co-occurrence
        assert weight == 0.1
    
    def test_edge_case_empty_blocks(self):
        """Проверка обработки пустых блоков"""
        calculator = GraphWeightCalculator()
        
        calculator.analyze_block("", [], block_idx=0)
        
        total_blocks = 1
        weight = calculator.calculate_combined_weight("концепт1", "концепт2", total_blocks)
        
        # Должен вернуть минимальный вес
        assert weight == 0.1
    
    def test_weight_range(self):
        """Проверка что все веса в допустимом диапазоне"""
        calculator = GraphWeightCalculator()
        
        # Различные сценарии
        test_cases = [
            (["осознанность", "присутствие"], "Осознанность и присутствие важны."),
            (["дыхание"], "Дыхание важно."),
            (["метанаблюдение", "наблюдение"], "Метанаблюдение включает наблюдение."),
        ]
        
        for i, (entities, content) in enumerate(test_cases):
            calculator.analyze_block(content, entities, block_idx=i)
        
        total_blocks = len(test_cases)
        
        # Проверяем различные пары
        pairs = [
            ("осознанность", "присутствие"),
            ("осознанность", "дыхание"),
            ("метанаблюдение", "наблюдение"),
        ]
        
        for entity1, entity2 in pairs:
            weight = calculator.calculate_combined_weight(entity1, entity2, total_blocks)
            assert 0.1 <= weight <= 1.0, f"Weight для ({entity1}, {entity2}) = {weight} вне диапазона"


class TestKnowledgeGraphWeights:
    """Тесты для проверки весов в Knowledge Graph"""
    
    def test_weights_variance(self, sample_processed_data):
        """Веса должны варьироваться (не все 1.0)"""
        if not sample_processed_data:
            pytest.skip("Нет тестовых данных")
        
        kg = sample_processed_data.get('knowledge_graph', {})
        edges = kg.get('edges', [])
        
        if not edges:
            pytest.skip("Нет связей в графе")
        
        weights = [edge.get('confidence', 1.0) for edge in edges]
        
        # Проверяем, что веса варьируются
        unique_weights = set(weights)
        assert len(unique_weights) > 1, f"Все веса одинаковые: {unique_weights}"
        
        # Проверяем диапазон
        assert min(weights) >= 0.1, f"Минимальный вес слишком низкий: {min(weights)}"
        assert max(weights) <= 1.0, f"Максимальный вес слишком высокий: {max(weights)}"
    
    def test_weight_statistics(self, sample_processed_data):
        """Метаданные должны содержать статистику весов"""
        if not sample_processed_data:
            pytest.skip("Нет тестовых данных")
        
        kg = sample_processed_data.get('knowledge_graph', {})
        metadata = kg.get('metadata', {})
        stats = metadata.get('weight_statistics')
        
        assert stats is not None, "Нет статистики весов в метаданных!"
        assert 'min_weight' in stats
        assert 'max_weight' in stats
        assert 'avg_weight' in stats
        assert 'median_weight' in stats
        
        # Проверяем что статистика разумная
        assert stats['min_weight'] >= 0
        assert stats['max_weight'] <= 1.0
        assert stats['avg_weight'] > 0
        assert stats['min_weight'] <= stats['avg_weight'] <= stats['max_weight']
    
    def test_weight_range(self, sample_processed_data):
        """Все веса должны быть в диапазоне [0.1, 1.0]"""
        if not sample_processed_data:
            pytest.skip("Нет тестовых данных")
        
        kg = sample_processed_data.get('knowledge_graph', {})
        edges = kg.get('edges', [])
        
        for edge in edges:
            weight = edge.get('confidence', 1.0)
            assert 0.1 <= weight <= 1.0, f"Вес {weight} вне допустимого диапазона для связи {edge.get('from_name')} -> {edge.get('to_name')}"


@pytest.fixture
def sample_processed_data():
    """
    Фикстура с обработанными данными для тестирования.
    В реальном использовании загружает данные из обработанного видео.
    """
    # Для unit-тестов возвращаем None
    # В интеграционных тестах можно загрузить реальные данные
    return None


class TestIntegration:
    """Интеграционные тесты"""
    
    def test_calculator_integration(self):
        """Проверка интеграции калькулятора с реальными данными"""
        calculator = GraphWeightCalculator()
        
        # Симулируем обработку нескольких блоков
        blocks_data = [
            {
                "content": "Осознанность и присутствие являются ключевыми концептами нейросталкинга. Осознанность помогает развивать присутствие.",
                "graph_entities": ["осознанность", "присутствие", "нейросталкинг"]
            },
            {
                "content": "Метанаблюдение включает наблюдение за процессом мышления. Это важная практика.",
                "graph_entities": ["метанаблюдение", "наблюдение", "практика"]
            },
            {
                "content": "Осознанность и метанаблюдение связаны между собой.",
                "graph_entities": ["осознанность", "метанаблюдение"]
            }
        ]
        
        # Анализируем блоки
        for idx, block in enumerate(blocks_data):
            calculator.analyze_block(
                block["content"],
                block["graph_entities"],
                block_idx=idx
            )
        
        total_blocks = len(blocks_data)
        
        # Проверяем веса для различных пар
        weight1 = calculator.calculate_combined_weight("осознанность", "присутствие", total_blocks)
        weight2 = calculator.calculate_combined_weight("метанаблюдение", "наблюдение", total_blocks)
        weight3 = calculator.calculate_combined_weight("осознанность", "метанаблюдение", total_blocks)
        
        # Все веса должны быть в допустимом диапазоне
        assert 0.1 <= weight1 <= 1.0
        assert 0.1 <= weight2 <= 1.0
        assert 0.1 <= weight3 <= 1.0
        
        # Часто встречающиеся вместе должны иметь больший вес
        assert weight1 > 0.3  # осознанность и присутствие встречаются часто
        assert weight2 > 0.3  # метанаблюдение и наблюдение связаны




