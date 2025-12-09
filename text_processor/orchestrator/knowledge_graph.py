"""
Knowledge Graph для хранения извлечённых знаний Сарсекенова.

Граф состоит из:
- Узлов (nodes): концепты, паттерны, этапы процессов
- Рёбер (edges): связи между узлами
- Метаданных: confidence, tier, density
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Set, Any
from enum import Enum
import json


class NodeType(Enum):
    """Типы узлов в графе"""
    CONCEPT = "concept"              # Концепт из иерархии
    PATTERN = "pattern"              # Паттерн учения
    PROCESS_STAGE = "process_stage"  # Этап процесса
    PRACTICE = "practice"            # Практика
    TECHNIQUE = "technique"          # Техника
    EXERCISE = "exercise"            # Упражнение


class EdgeType(Enum):
    """Типы связей в графе"""
    # Иерархические (вертикальные)
    IS_CORE_COMPONENT_OF = "is_core_component_of"
    IS_PRACTICE_FOR = "is_practice_for"
    IS_TECHNIQUE_FOR = "is_technique_for"
    IS_EXERCISE_FOR = "is_exercise_for"
    
    # Процессуальные
    EMERGES_FROM = "emerges_from"
    ENABLES = "enables"
    REQUIRES = "requires"
    LEADS_TO = "leads_to"
    TRANSFORMS_INTO = "transforms_into"
    
    # Паттерны
    RELATED_TO = "related_to"
    PART_OF_PATTERN = "part_of_pattern"


@dataclass
class GraphNode:
    """Узел в графе знаний"""
    id: str                          # Уникальный ID
    name: str                        # Название
    node_type: NodeType              # Тип узла
    description: str                 # Описание
    sarsekenov_terms: List[str]      # Термины Сарсекенова
    tier: Optional[int] = None       # Tier (1-6) если применимо
    confidence: float = 1.0          # Уверенность (0.0-1.0)
    
    # Дополнительные атрибуты
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Сериализация в dict"""
        d = asdict(self)
        d['node_type'] = self.node_type.value
        return d


@dataclass
class GraphEdge:
    """Связь в графе знаний"""
    from_id: str                     # ID источника
    to_id: str                       # ID цели
    edge_type: EdgeType              # Тип связи
    explanation: str                 # Объяснение связи
    confidence: float = 1.0          # Уверенность в связи
    
    # Дополнительные атрибуты
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Сериализация в dict"""
        d = asdict(self)
        d['edge_type'] = self.edge_type.value
        return d


class KnowledgeGraph:
    """
    Граф знаний Сарсекенова.
    
    Хранит извлечённые знания в виде графа:
    - Узлы: концепты, паттерны, этапы
    - Рёбра: связи между ними
    
    Поддерживает:
    - Добавление узлов и связей
    - Поиск по графу
    - Построение путей (reasoning chains)
    - Экспорт для RAG
    """
    
    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}  # id -> node
        self.edges: List[GraphEdge] = []
        
        # Индексы для быстрого поиска
        self._edges_from: Dict[str, List[GraphEdge]] = {}  # from_id -> edges
        self._edges_to: Dict[str, List[GraphEdge]] = {}    # to_id -> edges
        self._nodes_by_type: Dict[NodeType, Set[str]] = {
            nt: set() for nt in NodeType
        }
        self._nodes_by_name: Dict[str, str] = {}  # name -> id
    
    def add_node(self, node: GraphNode) -> str:
        """
        Добавить узел в граф.
        
        Args:
            node: Узел для добавления
            
        Returns:
            ID добавленного узла
        """
        # Проверка дубликатов по имени
        if node.name in self._nodes_by_name:
            existing_id = self._nodes_by_name[node.name]
            # Обновить существующий узел (merge метаданных)
            existing_node = self.nodes[existing_id]
            existing_node.metadata.update(node.metadata)
            existing_node.confidence = max(
                existing_node.confidence,
                node.confidence
            )
            return existing_id
        
        # Добавить новый узел
        self.nodes[node.id] = node
        self._nodes_by_type[node.node_type].add(node.id)
        self._nodes_by_name[node.name] = node.id
        
        return node.id
    
    def add_edge(self, edge: GraphEdge) -> None:
        """
        Добавить связь в граф.
        
        Args:
            edge: Связь для добавления
        """
        # Проверка существования узлов
        if edge.from_id not in self.nodes:
            raise ValueError(f"Source node not found: {edge.from_id}")
        if edge.to_id not in self.nodes:
            raise ValueError(f"Target node not found: {edge.to_id}")
        
        # Проверка дубликатов
        for existing_edge in self.edges:
            if (existing_edge.from_id == edge.from_id and
                existing_edge.to_id == edge.to_id and
                existing_edge.edge_type == edge.edge_type):
                # Дубликат найден, не добавляем
                return
        
        # Добавить связь
        self.edges.append(edge)
        
        # Обновить индексы
        if edge.from_id not in self._edges_from:
            self._edges_from[edge.from_id] = []
        self._edges_from[edge.from_id].append(edge)
        
        if edge.to_id not in self._edges_to:
            self._edges_to[edge.to_id] = []
        self._edges_to[edge.to_id].append(edge)
    
    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Получить узел по ID"""
        return self.nodes.get(node_id)
    
    def get_node_by_name(self, name: str) -> Optional[GraphNode]:
        """Получить узел по имени"""
        node_id = self._nodes_by_name.get(name)
        return self.nodes.get(node_id) if node_id else None
    
    def get_nodes_by_type(self, node_type: NodeType) -> List[GraphNode]:
        """Получить все узлы определённого типа"""
        node_ids = self._nodes_by_type.get(node_type, set())
        return [self.nodes[nid] for nid in node_ids]
    
    def get_outgoing_edges(self, node_id: str) -> List[GraphEdge]:
        """Получить исходящие связи узла"""
        return self._edges_from.get(node_id, [])
    
    def get_incoming_edges(self, node_id: str) -> List[GraphEdge]:
        """Получить входящие связи узла"""
        return self._edges_to.get(node_id, [])
    
    def find_path(
        self,
        from_id: str,
        to_id: str,
        max_depth: int = 5
    ) -> Optional[List[str]]:
        """
        Найти путь между двумя узлами (BFS).
        
        Args:
            from_id: ID начального узла
            to_id: ID конечного узла
            max_depth: Максимальная глубина поиска
            
        Returns:
            Список ID узлов вдоль пути или None
        """
        if from_id == to_id:
            return [from_id]
        
        # BFS
        queue = [(from_id, [from_id])]
        visited = {from_id}
        
        while queue:
            current_id, path = queue.pop(0)
            
            if len(path) > max_depth:
                continue
            
            # Проверка исходящих связей
            for edge in self.get_outgoing_edges(current_id):
                next_id = edge.to_id
                
                if next_id == to_id:
                    return path + [next_id]
                
                if next_id not in visited:
                    visited.add(next_id)
                    queue.append((next_id, path + [next_id]))
        
        return None
    
    def build_reasoning_chain(
        self,
        from_concept: str,
        to_concept: str
    ) -> Optional[Dict]:
        """
        Построить reasoning chain от одного концепта к другому.
        
        Args:
            from_concept: Название начального концепта
            to_concept: Название конечного концепта
            
        Returns:
            Dict с цепочкой рассуждений или None
        """
        # Найти узлы
        from_node = self.get_node_by_name(from_concept)
        to_node = self.get_node_by_name(to_concept)
        
        if not from_node or not to_node:
            return None
        
        # Найти путь
        path = self.find_path(from_node.id, to_node.id)
        
        if not path:
            return None
        
        # Построить цепочку
        chain_steps = []
        for i in range(len(path) - 1):
            current_id = path[i]
            next_id = path[i + 1]
            
            # Найти связь
            edge = None
            for e in self.get_outgoing_edges(current_id):
                if e.to_id == next_id:
                    edge = e
                    break
            
            current_node = self.nodes[current_id]
            next_node = self.nodes[next_id]
            
            step = {
                "from": current_node.name,
                "to": next_node.name,
                "relation": edge.edge_type.value if edge else "unknown",
                "explanation": edge.explanation if edge else ""
            }
            chain_steps.append(step)
        
        return {
            "from_concept": from_concept,
            "to_concept": to_concept,
            "steps": chain_steps,
            "length": len(chain_steps)
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получить статистику графа"""
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "nodes_by_type": {
                nt.value: len(self._nodes_by_type[nt])
                for nt in NodeType
            },
            "avg_connections_per_node": (
                len(self.edges) / len(self.nodes) if self.nodes else 0
            )
        }
    
    def to_dict(self) -> Dict:
        """Сериализация графа в dict"""
        return {
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges],
            "statistics": self.get_statistics()
        }
    
    def to_json(self, filepath: str) -> None:
        """Сохранить граф в JSON файл"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'KnowledgeGraph':
        """Загрузить граф из dict"""
        graph = cls()
        
        # Загрузить узлы
        for node_data in data['nodes']:
            node_data['node_type'] = NodeType(node_data['node_type'])
            node = GraphNode(**node_data)
            graph.add_node(node)
        
        # Загрузить связи
        for edge_data in data['edges']:
            edge_data['edge_type'] = EdgeType(edge_data['edge_type'])
            edge = GraphEdge(**edge_data)
            graph.add_edge(edge)
        
        return graph
    
    @classmethod
    def from_json(cls, filepath: str) -> 'KnowledgeGraph':
        """Загрузить граф из JSON файла"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)