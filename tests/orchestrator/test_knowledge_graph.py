"""
Тесты для KnowledgeGraph.

Проверяют:
- Добавление узлов и связей
- Поиск по графу
- Построение путей
- Сериализацию
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from voice_bot_pipeline.text_processor.orchestrator.knowledge_graph import (
    KnowledgeGraph,
    GraphNode,
    GraphEdge,
    NodeType,
    EdgeType
)


@pytest.fixture
def empty_graph():
    """Пустой граф"""
    return KnowledgeGraph()


@pytest.fixture
def sample_graph():
    """Граф с примером данных"""
    graph = KnowledgeGraph()
    
    # Создать узлы
    root = GraphNode(
        id="root_1",
        name="нейро-сталкинг",
        node_type=NodeType.CONCEPT,
        description="Корень учения",
        sarsekenov_terms=["нейро-сталкинг"],
        tier=1
    )
    
    domain = GraphNode(
        id="domain_1",
        name="поле внимания",
        node_type=NodeType.CONCEPT,
        description="Доменная область",
        sarsekenov_terms=["поле внимания"],
        tier=2
    )
    
    practice = GraphNode(
        id="practice_1",
        name="метанаблюдение",
        node_type=NodeType.PRACTICE,
        description="Практика наблюдения",
        sarsekenov_terms=["метанаблюдение"],
        tier=3
    )
    
    # Добавить узлы
    graph.add_node(root)
    graph.add_node(domain)
    graph.add_node(practice)
    
    # Создать связи
    edge1 = GraphEdge(
        from_id="domain_1",
        to_id="root_1",
        edge_type=EdgeType.IS_CORE_COMPONENT_OF,
        explanation="Domain is core component of root"
    )
    
    edge2 = GraphEdge(
        from_id="practice_1",
        to_id="domain_1",
        edge_type=EdgeType.IS_PRACTICE_FOR,
        explanation="Practice is for domain"
    )
    
    graph.add_edge(edge1)
    graph.add_edge(edge2)
    
    return graph


class TestGraphConstruction:
    """Тесты построения графа"""
    
    def test_add_node(self, empty_graph):
        """Тест добавления узла"""
        node = GraphNode(
            id="test_1",
            name="тестовый концепт",
            node_type=NodeType.CONCEPT,
            description="Описание",
            sarsekenov_terms=["термин1"]
        )
        
        node_id = empty_graph.add_node(node)
        
        assert node_id == "test_1"
        assert len(empty_graph.nodes) == 1
        assert empty_graph.get_node("test_1") is not None
    
    def test_add_duplicate_node_merges(self, empty_graph):
        """Тест что дубликаты объединяются"""
        node1 = GraphNode(
            id="dup_1",
            name="концепт",
            node_type=NodeType.CONCEPT,
            description="Первое описание",
            sarsekenov_terms=["термин1"]
        )
        
        node2 = GraphNode(
            id="dup_2",
            name="концепт",  # То же имя!
            node_type=NodeType.CONCEPT,
            description="Второе описание",
            sarsekenov_terms=["термин2"],
            confidence=0.9
        )
        
        id1 = empty_graph.add_node(node1)
        id2 = empty_graph.add_node(node2)
        
        # Должен быть тот же ID (merge)
        assert id1 == id2
        assert len(empty_graph.nodes) == 1
        
        # Confidence должна быть максимальной
        merged_node = empty_graph.get_node(id1)
        assert merged_node.confidence == max(1.0, 0.9)
    
    def test_add_edge(self, sample_graph):
        """Тест добавления связи"""
        assert len(sample_graph.edges) == 2
        
        # Проверка индексов
        outgoing = sample_graph.get_outgoing_edges("domain_1")
        assert len(outgoing) == 1
        assert outgoing[0].to_id == "root_1"
        
        incoming = sample_graph.get_incoming_edges("root_1")
        assert len(incoming) == 1
        assert incoming[0].from_id == "domain_1"
    
    def test_add_edge_invalid_nodes_raises(self, empty_graph):
        """Тест что связь с несуществующими узлами вызывает ошибку"""
        edge = GraphEdge(
            from_id="nonexistent_1",
            to_id="nonexistent_2",
            edge_type=EdgeType.ENABLES,
            explanation="Test"
        )
        
        with pytest.raises(ValueError):
            empty_graph.add_edge(edge)


class TestGraphQueries:
    """Тесты запросов к графу"""
    
    def test_get_node_by_name(self, sample_graph):
        """Тест поиска по имени"""
        node = sample_graph.get_node_by_name("метанаблюдение")
        
        assert node is not None
        assert node.id == "practice_1"
        assert node.node_type == NodeType.PRACTICE
    
    def test_get_nodes_by_type(self, sample_graph):
        """Тест поиска по типу"""
        concepts = sample_graph.get_nodes_by_type(NodeType.CONCEPT)
        practices = sample_graph.get_nodes_by_type(NodeType.PRACTICE)
        
        assert len(concepts) == 2  # root + domain
        assert len(practices) == 1
    
    def test_find_path(self, sample_graph):
        """Тест поиска пути"""
        path = sample_graph.find_path("practice_1", "root_1")
        
        assert path is not None
        assert len(path) == 3  # practice -> domain -> root
        assert path == ["practice_1", "domain_1", "root_1"]
    
    def test_find_path_no_connection(self, sample_graph):
        """Тест что путь не найден если нет связи"""
        # Добавить несвязанный узел
        isolated = GraphNode(
            id="isolated_1",
            name="изолированный",
            node_type=NodeType.CONCEPT,
            description="Без связей",
            sarsekenov_terms=[]
        )
        sample_graph.add_node(isolated)
        
        path = sample_graph.find_path("practice_1", "isolated_1")
        
        assert path is None
    
    def test_build_reasoning_chain(self, sample_graph):
        """Тест построения reasoning chain"""
        chain = sample_graph.build_reasoning_chain(
            "метанаблюдение",
            "нейро-сталкинг"
        )
        
        assert chain is not None
        assert chain['from_concept'] == "метанаблюдение"
        assert chain['to_concept'] == "нейро-сталкинг"
        assert chain['length'] == 2  # practice -> domain -> root
        assert len(chain['steps']) == 2


class TestGraphSerialization:
    """Тесты сериализации графа"""
    
    def test_to_dict(self, sample_graph):
        """Тест сериализации в dict"""
        data = sample_graph.to_dict()
        
        assert 'nodes' in data
        assert 'edges' in data
        assert 'statistics' in data
        
        assert len(data['nodes']) == 3
        assert len(data['edges']) == 2
    
    def test_to_json_and_back(self, sample_graph):
        """Тест сохранения в JSON и загрузки"""
        # Создать временный файл
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            delete=False
        ) as f:
            filepath = f.name
        
        try:
            # Сохранить
            sample_graph.to_json(filepath)
            
            # Загрузить
            loaded_graph = KnowledgeGraph.from_json(filepath)
            
            # Проверка что данные совпадают
            assert len(loaded_graph.nodes) == len(sample_graph.nodes)
            assert len(loaded_graph.edges) == len(sample_graph.edges)
            
        finally:
            # Удалить временный файл
            if os.path.exists(filepath):
                os.remove(filepath)
    
    def test_get_statistics(self, sample_graph):
        """Тест получения статистики"""
        stats = sample_graph.get_statistics()
        
        assert stats['total_nodes'] == 3
        assert stats['total_edges'] == 2
        assert 'nodes_by_type' in stats
        assert stats['nodes_by_type']['concept'] == 2
        assert stats['nodes_by_type']['practice'] == 1