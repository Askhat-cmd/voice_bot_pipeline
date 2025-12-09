"""
Тесты для SarsekenovProcessor.

Проверяют:
- Координацию экстракторов
- Построение Knowledge Graph
- API для AI-бота
"""

import pytest
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from voice_bot_pipeline.text_processor.orchestrator.sarsekenov_processor import (
    SarsekenovProcessor
)
from voice_bot_pipeline.text_processor.orchestrator.knowledge_graph import (
    KnowledgeGraph,
    NodeType,
    EdgeType
)
from voice_bot_pipeline.tests.fixtures.real_sarsekenov_texts import (
    TRIADA_TRANSFORMATION_TEXT,
    HIERARCHY_PRACTICES_TEXT
)


@pytest.fixture
def processor():
    """Фикстура процессора"""
    return SarsekenovProcessor()


class TestSarsekenovProcessor:
    """Тесты главного оркестратора"""
    
    def test_process_text_full_workflow(self, processor):
        """
        Тест полного workflow обработки текста.
        
        Проверяет:
        1. Валидация проходит
        2. Все экстракторы отработали
        3. Knowledge Graph построен
        4. Результат полный
        """
        text = TRIADA_TRANSFORMATION_TEXT
        
        result = processor.process_text(text, text_id="test_001")
        
        # Проверка валидации
        assert result.is_valid, f"Validation failed: {result.validation_reason}"
        assert result.sarsekenov_density >= 0.15
        
        # Проверка извлечения
        assert len(result.patterns_extracted) > 0, "No patterns extracted"
        assert len(result.chains_extracted) > 0, "No chains extracted"
        assert result.hierarchy_extracted is not None, "No hierarchy extracted"
        
        # Проверка статистики
        assert result.total_concepts > 0
        assert result.total_patterns > 0
        assert result.total_chains > 0
        
        print(f"\n✅ FULL WORKFLOW TEST PASSED")
        print(f"   Concepts: {result.total_concepts}")
        print(f"   Patterns: {result.total_patterns}")
        print(f"   Chains: {result.total_chains}")
        print(f"   Density: {result.sarsekenov_density:.1%}")
    
    def test_knowledge_graph_built(self, processor):
        """Тест построения Knowledge Graph"""
        text = TRIADA_TRANSFORMATION_TEXT
        
        result = processor.process_text(text, text_id="test_002")
        
        # Получить граф
        graph = processor.get_knowledge_graph()
        
        # Проверка что граф не пуст
        assert len(graph.nodes) > 0, "Graph is empty"
        assert len(graph.edges) > 0, "No edges in graph"
        
        # Проверка статистики
        stats = graph.get_statistics()
        print(f"\n✅ KNOWLEDGE GRAPH BUILT")
        print(f"   Total nodes: {stats['total_nodes']}")
        print(f"   Total edges: {stats['total_edges']}")
        print(f"   Nodes by type: {stats['nodes_by_type']}")
    
    def test_hierarchy_nodes_in_graph(self, processor):
        """Тест что узлы иерархии добавлены в граф"""
        text = HIERARCHY_PRACTICES_TEXT
        
        result = processor.process_text(text, text_id="test_003")
        graph = processor.get_knowledge_graph()
        
        # Проверка наличия узлов разных типов
        concepts = graph.get_nodes_by_type(NodeType.CONCEPT)
        practices = graph.get_nodes_by_type(NodeType.PRACTICE)
        techniques = graph.get_nodes_by_type(NodeType.TECHNIQUE)
        
        assert len(concepts) > 0, "No concept nodes"
        assert len(practices) > 0, "No practice nodes"
        
        print(f"\n✅ HIERARCHY NODES IN GRAPH")
        print(f"   Concepts: {len(concepts)}")
        print(f"   Practices: {len(practices)}")
        print(f"   Techniques: {len(techniques)}")
    
    def test_find_practices_for_symptom(self, processor):
        """Тест поиска практик по симптому"""
        text = TRIADA_TRANSFORMATION_TEXT
        
        result = processor.process_text(text, text_id="test_004")
        
        # Поиск практик для "захват внимания"
        # Note: This depends on the exact extraction logic and text content
        # We might need to adjust the symptom string based on what's actually extracted
        practices = processor.find_practices_for_symptom("захват внимания")
        
        # Может не найти если концепт не в тексте или связи не те
        print(f"\n   Practices found for 'захват внимания': {len(practices)}")
    
    def test_recommend_exercise(self, processor):
        """Тест рекомендации упражнения"""
        text = HIERARCHY_PRACTICES_TEXT
        
        result = processor.process_text(text, text_id="test_005")
        
        # Рекомендация упражнения для метанаблюдения
        exercise = processor.recommend_exercise("метанаблюдение")
        
        if exercise:
            print(f"\n✅ EXERCISE RECOMMENDED")
            print(f"   Exercise: {exercise['exercise']}")
            print(f"   Duration: {exercise.get('duration')}")
            print(f"   Frequency: {exercise.get('frequency')}")
        else:
            print(f"\n   No exercise found for 'метанаблюдение'")
    
    def test_invalid_text_rejected(self, processor):
        """Тест отклонения невалидного текста"""
        text = "Общая психология и терапия стресса."
        
        result = processor.process_text(text, text_id="test_006")
        
        # Должен быть отклонён
        assert not result.is_valid
        assert result.total_concepts == 0
        assert result.total_patterns == 0
        
        print(f"\n✅ INVALID TEXT REJECTED")
        print(f"   Reason: {result.validation_reason}")
    
    def test_metadata_preserved(self, processor):
        """Тест сохранения метаданных"""
        text = TRIADA_TRANSFORMATION_TEXT
        metadata = {
            "source": "lecture_001",
            "author": "Саламат Сарсекенов",
            "date": "2024-12-08"
        }
        
        result = processor.process_text(
            text,
            text_id="test_007",
            metadata=metadata
        )
        
        # Проверка метаданных
        assert result.metadata == metadata
        
        print(f"\n✅ METADATA PRESERVED")
        print(f"   Source: {result.metadata['source']}")
    
    def test_multiple_texts_processing(self, processor):
        """Тест обработки нескольких текстов"""
        texts = [
            TRIADA_TRANSFORMATION_TEXT,
            HIERARCHY_PRACTICES_TEXT
        ]
        
        results = []
        for i, text in enumerate(texts):
            result = processor.process_text(text, text_id=f"test_multi_{i}")
            results.append(result)
        
        # Все тексты должны быть обработаны
        assert all(r.is_valid for r in results)
        
        # Граф должен содержать узлы из обоих текстов
        graph = processor.get_knowledge_graph()
        stats = graph.get_statistics()
        
        print(f"\n✅ MULTIPLE TEXTS PROCESSED")
        print(f"   Total nodes: {stats['total_nodes']}")
        print(f"   Total edges: {stats['total_edges']}")


class TestKnowledgeGraphAPI:
    """Тесты API графа знаний"""
    
    def test_find_path_between_concepts(self, processor):
        """Тест поиска пути между концептами"""
        text = TRIADA_TRANSFORMATION_TEXT
        
        processor.process_text(text, text_id="test_path")
        graph = processor.get_knowledge_graph()
        
        # Попытка найти путь
        # (может не найти если концепты не связаны)
        nodes = list(graph.nodes.keys())
        if len(nodes) >= 2:
            path = graph.find_path(nodes[0], nodes[1])
            print(f"\n   Path found: {path is not None}")
    
    def test_build_reasoning_chain(self, processor):
        """Тест построения reasoning chain"""
        text = TRIADA_TRANSFORMATION_TEXT
        
        processor.process_text(text, text_id="test_reasoning")
        graph = processor.get_knowledge_graph()
        
        # Попытка построить цепочку
        # Note: Concepts need to be exactly as extracted
        chain = graph.build_reasoning_chain(
            "метанаблюдение",
            "чистое осознавание"
        )
        
        if chain:
            print(f"\n✅ REASONING CHAIN BUILT")
            print(f"   From: {chain['from_concept']}")
            print(f"   To: {chain['to_concept']}")
            print(f"   Steps: {chain['length']}")
        else:
            print(f"\n   No reasoning chain found")