"""
SarsekenovProcessor - главный оркестратор всех экстракторов.

Координирует работу:
- TerminologyValidator
- NeurostalkingPatternExtractor
- CausalChainExtractor
- ConceptHierarchyExtractor

Объединяет результаты в Knowledge Graph.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import uuid

from ..validators import TerminologyValidator
from ..extractors import (
    NeurostalkingPatternExtractor,
    CausalChainExtractor,
    ConceptHierarchyExtractor
)
from .knowledge_graph import (
    KnowledgeGraph,
    GraphNode,
    GraphEdge,
    NodeType,
    EdgeType
)


@dataclass
class ProcessingResult:
    """Результат обработки текста"""
    text_id: str                     # Уникальный ID текста
    is_valid: bool                   # Прошёл ли валидацию
    validation_reason: str           # Причина валидации
    
    # Результаты экстракторов
    validation_metrics: Dict
    patterns_extracted: List[Dict]
    chains_extracted: List[Dict]
    hierarchy_extracted: Optional[Dict]
    
    # Статистика
    total_concepts: int
    total_patterns: int
    total_chains: int
    sarsekenov_density: float
    
    # Метаданные
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        """Сериализация в dict"""
        return asdict(self)


class SarsekenovProcessor:
    """
    Главный оркестратор для обработки текстов Сарсекенова.
    
    Workflow:
    1. Валидация текста (TerminologyValidator)
    2. Параллельное извлечение:
       - Паттерны (NeurostalkingPatternExtractor)
       - Цепочки (CausalChainExtractor)
       - Иерархия (ConceptHierarchyExtractor)
    3. Построение Knowledge Graph
    4. Подготовка для экспорта в RAG
    
    ФИЛОСОФИЯ:
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    - Единая точка входа для обработки
    - Автоматическая координация экстракторов
    - Объединение результатов в граф
    - Готовый API для AI-бота
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    
    def __init__(
        self,
        validator: Optional[TerminologyValidator] = None,
        pattern_extractor: Optional[NeurostalkingPatternExtractor] = None,
        causal_chain_extractor: Optional[CausalChainExtractor] = None,
        hierarchy_extractor: Optional[ConceptHierarchyExtractor] = None
    ):
        """
        Инициализация оркестратора.
        
        Args:
            validator: Валидатор (создаётся если не передан)
            pattern_extractor: Экстрактор паттернов
            causal_chain_extractor: Экстрактор цепочек
            hierarchy_extractor: Экстрактор иерархии
        """
        # Создать экстракторы если не переданы
        self.validator = validator or TerminologyValidator()
        
        self.pattern_extractor = pattern_extractor or \
            NeurostalkingPatternExtractor(terminology_validator=self.validator)
        
        self.causal_chain_extractor = causal_chain_extractor or \
            CausalChainExtractor(terminology_validator=self.validator)
        
        self.hierarchy_extractor = hierarchy_extractor or \
            ConceptHierarchyExtractor(terminology_validator=self.validator)
        
        # Knowledge Graph
        self.knowledge_graph = KnowledgeGraph()
    
    def process_text(
        self,
        text: str,
        text_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> ProcessingResult:
        """
        Обработать текст всеми экстракторами.
        
        Args:
            text: Текст для обработки
            text_id: ID текста (генерируется если не передан)
            metadata: Дополнительные метаданные
            
        Returns:
            ProcessingResult с результатами всех экстракторов
        """
        text_id = text_id or str(uuid.uuid4())
        metadata = metadata or {}
        
        # ШАГ 1: ВАЛИДАЦИЯ
        validation = self.validator.validate_text(text)
        
        if not validation.is_valid:
            return ProcessingResult(
                text_id=text_id,
                is_valid=False,
                validation_reason=validation.reason,
                validation_metrics=validation.metrics,
                patterns_extracted=[],
                chains_extracted=[],
                hierarchy_extracted=None,
                total_concepts=0,
                total_patterns=0,
                total_chains=0,
                sarsekenov_density=validation.metrics.get('density', 0.0),
                metadata=metadata
            )
        
        # ШАГ 2: ИЗВЛЕЧЕНИЕ (параллельно)
        patterns_result = self.pattern_extractor.extract(text)
        chains_result = self.causal_chain_extractor.extract(text)
        hierarchy_result = self.hierarchy_extractor.extract(text)
        
        # ШАГ 3: ПОСТРОЕНИЕ KNOWLEDGE GRAPH
        self._build_graph_from_results(
            text_id=text_id,
            validation=validation,
            patterns_result=patterns_result,
            chains_result=chains_result,
            hierarchy_result=hierarchy_result
        )
        
        # ШАГ 4: СОЗДАНИЕ РЕЗУЛЬТАТА
        result = ProcessingResult(
            text_id=text_id,
            is_valid=True,
            validation_reason=validation.reason,
            validation_metrics=validation.metrics,
            patterns_extracted=patterns_result.get('patterns', []),
            chains_extracted=chains_result.get('chains', []),
            hierarchy_extracted=hierarchy_result.get('hierarchy') if hierarchy_result['valid'] else None,
            total_concepts=self._count_concepts(hierarchy_result),
            total_patterns=len(patterns_result.get('patterns', [])),
            total_chains=len(chains_result.get('chains', [])),
            sarsekenov_density=validation.metrics['density'],
            metadata=metadata
        )
        
        return result
    
    def _build_graph_from_results(
        self,
        text_id: str,
        validation: Any,
        patterns_result: Dict,
        chains_result: Dict,
        hierarchy_result: Dict
    ) -> None:
        """
        Построить Knowledge Graph из результатов экстракторов.
        
        Args:
            text_id: ID текста
            validation: Результат валидации
            patterns_result: Результат извлечения паттернов
            chains_result: Результат извлечения цепочек
            hierarchy_result: Результат извлечения иерархии
        """
        
        # 1. ДОБАВИТЬ УЗЛЫ ИЗ ИЕРАРХИИ
        if hierarchy_result['valid']:
            self._add_hierarchy_to_graph(hierarchy_result['hierarchy'], text_id)
        
        # 2. ДОБАВИТЬ ПАТТЕРНЫ
        self._add_patterns_to_graph(patterns_result.get('patterns', []), text_id)
        
        # 3. ДОБАВИТЬ ЦЕПОЧКИ
        self._add_chains_to_graph(chains_result.get('chains', []), text_id)
    
    def _add_hierarchy_to_graph(self, hierarchy: Dict, text_id: str) -> None:
        """Добавить иерархию в граф"""
        
        # Root
        root = hierarchy['root']
        root_node = GraphNode(
            id=f"{text_id}_root_{root['name']}",
            name=root['name'],
            node_type=NodeType.CONCEPT,
            description=root.get('description', ''),
            sarsekenov_terms=root.get('sarsekenov_terms', []),
            tier=1,
            metadata={"source": text_id, "level": "root"}
        )
        root_id = self.knowledge_graph.add_node(root_node)
        
        # Domains
        for domain in hierarchy.get('domains', []):
            domain_node = GraphNode(
                id=f"{text_id}_domain_{domain['name']}",
                name=domain['name'],
                node_type=NodeType.CONCEPT,
                description=domain.get('description', ''),
                sarsekenov_terms=domain.get('sarsekenov_terms', []),
                tier=2,
                metadata={"source": text_id, "level": "domain"}
            )
            domain_id = self.knowledge_graph.add_node(domain_node)
            
            # Связь domain -> root
            edge = GraphEdge(
                from_id=domain_id,
                to_id=root_id,
                edge_type=EdgeType.IS_CORE_COMPONENT_OF,
                explanation=f"{domain['name']} is core component of {root['name']}"
            )
            self.knowledge_graph.add_edge(edge)
        
        # Practices
        for practice in hierarchy.get('practices', []):
            practice_node = GraphNode(
                id=f"{text_id}_practice_{practice['name']}",
                name=practice['name'],
                node_type=NodeType.PRACTICE,
                description=practice.get('description', ''),
                sarsekenov_terms=practice.get('sarsekenov_terms', []),
                tier=3,
                metadata={"source": text_id, "level": "practice"}
            )
            practice_id = self.knowledge_graph.add_node(practice_node)
            
            # Связь practice -> domain (parent)
            parent_node = self.knowledge_graph.get_node_by_name(practice['parent'])
            if parent_node:
                edge = GraphEdge(
                    from_id=practice_id,
                    to_id=parent_node.id,
                    edge_type=EdgeType.IS_PRACTICE_FOR,
                    explanation=f"{practice['name']} is practice for {practice['parent']}"
                )
                self.knowledge_graph.add_edge(edge)
        
        # Techniques
        for technique in hierarchy.get('techniques', []):
            technique_node = GraphNode(
                id=f"{text_id}_technique_{technique['name']}",
                name=technique['name'],
                node_type=NodeType.TECHNIQUE,
                description=technique.get('description', ''),
                sarsekenov_terms=technique.get('sarsekenov_terms', []),
                tier=4,
                metadata={"source": text_id, "level": "technique"}
            )
            technique_id = self.knowledge_graph.add_node(technique_node)
            
            # Связь technique -> practice (parent)
            parent_node = self.knowledge_graph.get_node_by_name(technique['parent'])
            if parent_node:
                edge = GraphEdge(
                    from_id=technique_id,
                    to_id=parent_node.id,
                    edge_type=EdgeType.IS_TECHNIQUE_FOR,
                    explanation=f"{technique['name']} is technique for {technique['parent']}"
                )
                self.knowledge_graph.add_edge(edge)
        
        # Exercises
        for exercise in hierarchy.get('exercises', []):
            exercise_node = GraphNode(
                id=f"{text_id}_exercise_{exercise['name']}",
                name=exercise['name'],
                node_type=NodeType.EXERCISE,
                description=exercise.get('description', ''),
                sarsekenov_terms=[],
                metadata={
                    "source": text_id,
                    "level": "exercise",
                    "duration": exercise.get('duration'),
                    "frequency": exercise.get('frequency'),
                    "instructions": exercise.get('instructions')
                }
            )
            exercise_id = self.knowledge_graph.add_node(exercise_node)
            
            # Связь exercise -> technique (parent)
            parent_node = self.knowledge_graph.get_node_by_name(exercise['parent'])
            if parent_node:
                edge = GraphEdge(
                    from_id=exercise_id,
                    to_id=parent_node.id,
                    edge_type=EdgeType.IS_EXERCISE_FOR,
                    explanation=f"{exercise['name']} is exercise for {exercise['parent']}"
                )
                self.knowledge_graph.add_edge(edge)
        
        # Cross-connections
        for conn in hierarchy.get('cross_connections', []):
            from_concept = self.knowledge_graph.get_node_by_name(conn['from_concept'])
            to_concept = self.knowledge_graph.get_node_by_name(conn['to_concept'])
            
            if from_concept and to_concept:
                edge_type_map = {
                    "enables": EdgeType.ENABLES,
                    "requires": EdgeType.REQUIRES,
                    "leads_to": EdgeType.LEADS_TO,
                    "transforms_into": EdgeType.TRANSFORMS_INTO
                }
                
                edge = GraphEdge(
                    from_id=from_concept.id,
                    to_id=to_concept.id,
                    edge_type=edge_type_map.get(conn['relation'], EdgeType.RELATED_TO),
                    explanation=conn.get('explanation', '')
                )
                self.knowledge_graph.add_edge(edge)
    
    def _add_patterns_to_graph(self, patterns: List[Dict], text_id: str) -> None:
        """Добавить паттерны в граф"""
        
        for pattern in patterns:
            pattern_node = GraphNode(
                id=f"{text_id}_pattern_{pattern['pattern_name']}",
                name=pattern['pattern_name'],
                node_type=NodeType.PATTERN,
                description=pattern.get('description', ''),
                sarsekenov_terms=pattern.get('key_terms', []),
                confidence=pattern.get('confidence', 1.0),
                metadata={
                    "source": text_id,
                    "category": pattern['pattern_category'],
                    "typical_context": pattern.get('typical_context', ''),
                    "related_practices": pattern.get('related_practices', [])
                }
            )
            pattern_id = self.knowledge_graph.add_node(pattern_node)
            
            # Связать с практиками
            for practice_name in pattern.get('related_practices', []):
                practice_node = self.knowledge_graph.get_node_by_name(practice_name)
                if practice_node:
                    edge = GraphEdge(
                        from_id=pattern_id,
                        to_id=practice_node.id,
                        edge_type=EdgeType.RELATED_TO,
                        explanation=f"Pattern {pattern['pattern_name']} relates to {practice_name}"
                    )
                    self.knowledge_graph.add_edge(edge)
    
    def _add_chains_to_graph(self, chains: List[Dict], text_id: str) -> None:
        """Добавить цепочки в граф"""
        
        for chain_idx, chain in enumerate(chains):
            # Создать узлы для каждого этапа
            stage_ids = []
            
            for stage in chain['stages']:
                stage_node = GraphNode(
                    id=f"{text_id}_chain{chain_idx}_stage{stage['stage']}",
                    name=stage['stage_name'],
                    node_type=NodeType.PROCESS_STAGE,
                    description=stage.get('description', ''),
                    sarsekenov_terms=stage.get('sarsekenov_terms', []),
                    metadata={
                        "source": text_id,
                        "chain_category": chain['process_category'],
                        "stage_number": stage['stage']
                    }
                )
                stage_id = self.knowledge_graph.add_node(stage_node)
                stage_ids.append((stage['stage'], stage_id))
            
            # Создать связи между этапами
            for i in range(len(stage_ids) - 1):
                current_stage_num, current_id = stage_ids[i]
                next_stage_num, next_id = stage_ids[i + 1]
                
                edge = GraphEdge(
                    from_id=current_id,
                    to_id=next_id,
                    edge_type=EdgeType.EMERGES_FROM,
                    explanation=f"Stage {next_stage_num} emerges from stage {current_stage_num}",
                    confidence=chain.get('confidence', 1.0)
                )
                self.knowledge_graph.add_edge(edge)
    
    def _count_concepts(self, hierarchy_result: Dict) -> int:
        """Подсчитать количество концептов в иерархии"""
        if not hierarchy_result.get('valid'):
            return 0
        
        hierarchy = hierarchy_result['hierarchy']
        return (
            1 +  # root
            len(hierarchy.get('domains', [])) +
            len(hierarchy.get('practices', [])) +
            len(hierarchy.get('techniques', [])) +
            len(hierarchy.get('exercises', []))
        )
    
    def get_knowledge_graph(self) -> KnowledgeGraph:
        """Получить Knowledge Graph"""
        return self.knowledge_graph
    
    def find_practices_for_symptom(self, symptom: str) -> List[Dict]:
        """
        Найти практики для работы с симптомом.
        
        Args:
            symptom: Описание симптома (напр. "захват внимания")
            
        Returns:
            Список практик с reasoning chains
        """
        # Найти узел симптома
        symptom_node = self.knowledge_graph.get_node_by_name(symptom)
        
        if not symptom_node:
            return []
        
        # Найти связанные практики
        practices = []
        for edge in self.knowledge_graph.get_outgoing_edges(symptom_node.id):
            if edge.edge_type in [EdgeType.REQUIRES, EdgeType.ENABLES]:
                target_node = self.knowledge_graph.get_node(edge.to_id)
                if target_node and target_node.node_type == NodeType.PRACTICE:
                    practices.append({
                        "practice": target_node.name,
                        "relation": edge.edge_type.value,
                        "explanation": edge.explanation,
                        "confidence": edge.confidence
                    })
        
        return practices
    
    def recommend_exercise(
        self,
        practice: str,
        duration: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Рекомендовать упражнение для практики.
        
        Args:
            practice: Название практики
            duration: Желаемая длительность (напр. "5-10 минут")
            
        Returns:
            Dict с упражнением или None
        """
        practice_node = self.knowledge_graph.get_node_by_name(practice)
        
        if not practice_node:
            return None
        
        # Найти technique для этой практики
        techniques = []
        for edge in self.knowledge_graph.get_incoming_edges(practice_node.id):
            if edge.edge_type == EdgeType.IS_TECHNIQUE_FOR:
                source_node = self.knowledge_graph.get_node(edge.from_id)
                if source_node:
                    techniques.append(source_node)
        
        if not techniques:
            return None
        
        # Найти exercises для первой техники
        technique = techniques[0]
        for edge in self.knowledge_graph.get_incoming_edges(technique.id):
            if edge.edge_type == EdgeType.IS_EXERCISE_FOR:
                exercise_node = self.knowledge_graph.get_node(edge.from_id)
                if exercise_node:
                    exercise_duration = exercise_node.metadata.get('duration')
                    
                    # Проверка длительности если указана
                    if duration and exercise_duration and duration not in exercise_duration:
                        continue
                    
                    return {
                        "exercise": exercise_node.name,
                        "technique": technique.name,
                        "practice": practice,
                        "duration": exercise_duration,
                        "frequency": exercise_node.metadata.get('frequency'),
                        "instructions": exercise_node.metadata.get('instructions')
                    }
        
        return None