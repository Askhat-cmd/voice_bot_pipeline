#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Concept Hierarchy Extractor
Экстрактор иерархии концептов Сарсекенова со строгой 5-уровневой структурой.
"""

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from ..validators.terminology_validator import TerminologyValidator, ValidationResult

@dataclass
class ConceptNode:
    """Узел в иерархии концептов"""
    name: str                    # Название концепта
    level: str                   # root/domain/practice/technique/exercise
    parent: Optional[str]        # Родительский концепт
    relation_type: str           # Тип связи с родителем
    description: str             # Описание из текста
    sarsekenov_terms: List[str]  # Термины Сарсекенова в описании
    tier: int                    # Tier из sarsekenov_terms.json (1-6)
    
    # Для EXERCISE:
    duration: Optional[str] = None      # "5 минут", "10-15 минут"
    frequency: Optional[str] = None     # "3 раза в день", "ежедневно"
    instructions: Optional[str] = None  # Пошаговая инструкция

@dataclass
class CrossConnection:
    """Горизонтальная связь между концептами"""
    from_concept: str
    to_concept: str
    relation: str          # enables/requires/leads_to/transforms_into
    explanation: str       # Объяснение связи
    context: str           # Контекст из текста

@dataclass
class ConceptHierarchy:
    """Полная иерархия концептов"""
    root: ConceptNode              # Корень (всегда 1)
    domains: List[ConceptNode]     # Домены (могут быть несколько)
    practices: List[ConceptNode]   # Практики
    techniques: List[ConceptNode]  # Техники
    exercises: List[ConceptNode]   # Упражнения
    cross_connections: List[CrossConnection]  # Горизонтальные связи
    confidence: float              # Уверенность в иерархии
    sarsekenov_density: float      # Плотность терминов

class ConceptHierarchyExtractor:
    """
    Экстрактор иерархии концептов Сарсекенова.
    
    ФИЛОСОФИЯ:
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    1. СТРОГАЯ 5-уровневая структура (без исключений)
    2. ROOT может быть только: нейро-сталкинг/нео-сталкинг/сталкинг ума
    3. Каждый концепт имеет РОВНО ОДНОГО родителя (дерево, не граф)
    4. Горизонтальные связи — отдельно (cross_connections)
    5. SMART режим валидации (15%, forbidden игнорируются)
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    
    # Разрешённые корневые концепты
    ALLOWED_ROOTS = ["нейро-сталкинг", "нео-сталкинг", "сталкинг ума"]
    
    # Минимальное количество терминов Сарсекенова
    MIN_SARSEKENOV_TERMS = 3
    
    # Уровни иерархии (СТРОГО в таком порядке)
    HIERARCHY_LEVELS = ["root", "domain", "practice", "technique", "exercise"]

    # Hardcoded techniques from specification (since they are missing in JSON)
    TECHNIQUE_CONCEPTS = [
        "наблюдение мыслительного потока",
        "наблюдение за мыслительным потоком",
        "отслеживание автоматизмов",
        "остановка внутреннего диалога",
        "центрирование на дыхании",
        "сканирование телесных ощущений"
    ]
    
    def __init__(
        self,
        terminology_validator: Optional[TerminologyValidator] = None,
        use_llm: bool = False,
        llm_client: Optional[Any] = None
    ):
        self.validator = terminology_validator or TerminologyValidator()
        self.use_llm = use_llm
        self.llm_client = llm_client
        self._load_sarsekenov_terms()
        self._build_level_term_mapping()
    
    def _load_sarsekenov_terms(self):
        """Загрузка терминов из config/terminology/sarsekenov_terms.json"""
        # Path logic: extractors -> text_processor -> voice_bot_pipeline -> config
        config_path = Path(__file__).parent.parent.parent / "config" / "terminology" / "sarsekenov_terms.json"
        with open(config_path, 'r', encoding='utf-8') as f:
            self.sarsekenov_terms_config = json.load(f)
    
    def _build_level_term_mapping(self):
        """
        Построить маппинг: термин → уровень иерархии
        
        Используем tier из sarsekenov_terms.json:
        - tier_1_root → root
        - tier_2_domain → domain
        - tier_3_practice → practice
        - tier_4_diagnostic → может быть в любом контексте
        - tier_5_agents → может быть в любом контексте
        - tier_6_states → может быть в любом контексте
        """
        self.term_to_level = {}
        self.term_to_tier = {}
        
        for tier_key, tier_data in self.sarsekenov_terms_config.items():
            level = tier_data.get('level', 'unknown')
            terms = tier_data.get('terms', [])
            try:
                tier_num = int(tier_key.split('_')[1])
            except (IndexError, ValueError):
                tier_num = 0
            
            for term in terms:
                self.term_to_level[term] = level
                self.term_to_tier[term] = tier_num
        
        # Manually add techniques
        for term in self.TECHNIQUE_CONCEPTS:
            self.term_to_level[term] = "technique"
            self.term_to_tier[term] = 4  # Assigning arbitrary tier for techniques
            
            # Also add lowercase version for easier matching
            self.term_to_level[term.lower()] = "technique"
            self.term_to_tier[term.lower()] = 4
    
    def extract(
        self,
        text: str,
        expected_root: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Извлечь иерархию концептов из текста.
        
        Args:
            text: Текст для анализа
            expected_root: Ожидаемый root (None = автоопределение)
        
        Returns:
            {
                "valid": bool,
                "reason": str,
                "hierarchy": Dict,  # Сериализованная ConceptHierarchy
                "metrics": Dict
            }
        """
        
        # 1. ВАЛИДАЦИЯ через TerminologyValidator (SMART режим)
        validation = self.validator.validate_text(text)
        
        if not validation.is_valid:
            return {
                "valid": False,
                "reason": validation.reason,
                "hierarchy": None,
                "metrics": validation.metrics
            }
        
        # 2. ОПРЕДЕЛЕНИЕ ROOT
        root_node = self._identify_root(text, validation.sarsekenov_entities, expected_root)
        
        if not root_node:
            return {
                "valid": False,
                "reason": "Не найден корневой концепт (нейро-сталкинг/нео-сталкинг/сталкинг ума)",
                "hierarchy": None,
                "metrics": validation.metrics
            }
        
        # 3. ИЗВЛЕЧЕНИЕ уровней (rule-based или LLM)
        
        # HACK: Добавляем hardcoded техники в entities, если они найдены в тексте
        # (так как их может не быть в sarsekenov_terms.json)
        text_lower = text.lower()
        for tech in self.TECHNIQUE_CONCEPTS:
            if tech.lower() in text_lower:
                # Проверяем, нет ли уже этого термина (case-insensitive)
                # TerminologyValidator возвращает сущности, найденные в тексте.
                # Если техника есть в тексте, но не в JSON конфиге, она не попадет в sarsekenov_entities.
                # Мы должны добавить её вручную.
                
                # Note: validation.sarsekenov_entities is a list of strings
                if not any(e.lower() == tech.lower() for e in validation.sarsekenov_entities):
                    validation.sarsekenov_entities.append(tech)

        # Force lower case matching for entities in _extract_level_nodes
        # by ensuring we can look them up in term_to_level
        
        if self.use_llm and self.llm_client:
            # Placeholder for LLM extraction if implemented
            hierarchy = self._extract_rule_based(text, root_node, validation)
        else:
            hierarchy = self._extract_rule_based(text, root_node, validation)
        
        # 4. ВАЛИДАЦИЯ иерархии
        is_valid_hierarchy, hierarchy_reason = self._validate_hierarchy(hierarchy)
        if not is_valid_hierarchy:
            return {
                "valid": False,
                "reason": f"Иерархия не прошла валидацию: {hierarchy_reason}",
                "hierarchy": None,
                "metrics": validation.metrics
            }
        
        return {
            "valid": True,
            "reason": f"Извлечена иерархия с {len(hierarchy.domains)} доменами",
            "hierarchy": asdict(hierarchy),
            "metrics": {
                "density": validation.metrics['density'],
                "total_nodes": (
                    1 +  # root
                    len(hierarchy.domains) +
                    len(hierarchy.practices) +
                    len(hierarchy.techniques) +
                    len(hierarchy.exercises)
                ),
                "levels": {
                    "domains": len(hierarchy.domains),
                    "practices": len(hierarchy.practices),
                    "techniques": len(hierarchy.techniques),
                    "exercises": len(hierarchy.exercises)
                },
                "cross_connections": len(hierarchy.cross_connections)
            }
        }

    def _identify_root(
        self,
        text: str,
        entities: List[str],
        expected_root: Optional[str]
    ) -> Optional[ConceptNode]:
        """
        Определить корневой концепт.
        
        Алгоритм:
        1. Если expected_root указан и найден в тексте → использовать
        2. Иначе искать любой из ALLOWED_ROOTS в entities
        3. Если найдено несколько → выбрать первый по встречаемости в тексте
        """
        text_lower = text.lower()
        
        if expected_root:
            if expected_root in self.ALLOWED_ROOTS and expected_root.lower() in text_lower:
                return ConceptNode(
                    name=expected_root,
                    level="root",
                    parent=None,
                    relation_type="",
                    description=self._extract_root_description(text, expected_root),
                    sarsekenov_terms=[expected_root],
                    tier=1
                )
        
        # Поиск любого корня
        for root_term in self.ALLOWED_ROOTS:
            if root_term.lower() in text_lower or root_term in entities:
                return ConceptNode(
                    name=root_term,
                    level="root",
                    parent=None,
                    relation_type="",
                    description=self._extract_root_description(text, root_term),
                    sarsekenov_terms=[root_term],
                    tier=1
                )
        
        return None

    def _extract_root_description(self, text: str, root_term: str) -> str:
        """Извлечь описание для корневого концепта"""
        sentences = self._split_sentences(text)
        for sentence in sentences:
            if root_term.lower() in sentence.lower():
                return sentence
        return root_term

    def _extract_rule_based(
        self,
        text: str,
        root_node: ConceptNode,
        validation: ValidationResult
    ) -> ConceptHierarchy:
        """
        Rule-based извлечение иерархии.
        
        Алгоритм:
        1. Разбить текст на предложения
        2. Для каждого уровня (domain→practice→technique→exercise):
           - Найти термины этого уровня в entities
           - Создать узлы с родителями
        3. Определить cross-connections между узлами
        """
        
        sentences = self._split_sentences(text)
        entities = validation.sarsekenov_entities
        
        # УРОВЕНЬ 2: DOMAINS
        domains = self._extract_level_nodes(
            sentences,
            entities,
            level="domain",
            parent_node=root_node,
            relation_type="is_core_component_of"
        )
        
        # УРОВЕНЬ 3: PRACTICES
        practices = []
        for domain in domains:
            domain_practices = self._extract_level_nodes(
                sentences,
                entities,
                level="practice",
                parent_node=domain,
                relation_type="is_practice_for"
            )
            practices.extend(domain_practices)
        
        # Если нет доменов, пробуем привязать практики к root (нестандартно, но для робастности)
        # Но по спецификации "Строгая структура", поэтому если нет доменов, практики не найдутся как дети доменов.
        # Однако, если в тексте упомянуты практики, но не упомянуты домены, они потеряются.
        # В рамках "Строгой структуры" это, возможно, правильно. Оставим как есть.
        
        # УРОВЕНЬ 4: TECHNIQUES
        techniques = []
        if practices:
            # First, try to find techniques linked to specific practices
            for practice in practices:
                practice_techniques = self._extract_level_nodes(
                    sentences,
                    entities,
                    level="technique",
                    parent_node=practice,
                    relation_type="is_technique_for"
                )
                techniques.extend(practice_techniques)
            
            # If no techniques found yet, try to find ANY techniques mentioned in text
            # and link them to the most relevant practice (or first one)
            if not techniques:
                # Find all potential technique terms in entities
                tech_terms = [e for e in entities if self.term_to_level.get(e) == "technique" or self.term_to_level.get(e.lower()) == "technique"]
                
                if tech_terms:
                    # Use the first practice as default parent if we can't determine better
                    default_parent = practices[0]
                    
                    # Extract these techniques
                    found_techniques = self._extract_level_nodes(
                        sentences,
                        tech_terms, # Pass only tech terms to force extraction
                        level="technique",
                        parent_node=default_parent,
                        relation_type="is_technique_for"
                    )
                    techniques.extend(found_techniques)
        
        # УРОВЕНЬ 5: EXERCISES
        exercises = []
        for technique in techniques:
            technique_exercises = self._extract_exercises(
                sentences,
                technique
            )
            exercises.extend(technique_exercises)
        
        # Горизонтальные связи
        cross_connections = self._extract_cross_connections(
            sentences,
            domains + practices + techniques
        )
        
        hierarchy = ConceptHierarchy(
            root=root_node,
            domains=domains,
            practices=practices,
            techniques=techniques,
            exercises=exercises,
            cross_connections=cross_connections,
            confidence=self._calculate_hierarchy_confidence(domains, practices, techniques),
            sarsekenov_density=validation.metrics['density']
        )
        
        return hierarchy

    def _extract_level_nodes(
        self,
        sentences: List[str],
        entities: List[str],
        level: str,
        parent_node: ConceptNode,
        relation_type: str
    ) -> List[ConceptNode]:
        """
        Извлечь узлы определённого уровня.
        
        Алгоритм:
        1. Найти все термины этого уровня в entities
        2. Для каждого термина найти предложение с описанием
        3. Создать ConceptNode
        """
        level_nodes = []
        
        # Найти термины этого уровня
        # We need to handle case sensitivity here. entities might be mixed case,
        # but term_to_level keys might be specific.
        level_terms = []
        for e in entities:
             # Try exact match
            if self.term_to_level.get(e) == level:
                level_terms.append(e)
            # Try lower match
            elif self.term_to_level.get(e.lower()) == level:
                level_terms.append(e)
        
        # Удаляем дубликаты
        level_terms = list(set(level_terms))
        
        for term in level_terms:
            # Найти предложение с этим термином
            description = self._find_description_for_term(sentences, term)
            
            # Извлечь термины Сарсекенова из описания
            desc_terms = [e for e in entities if e.lower() in description.lower()]
            
            node = ConceptNode(
                name=term,
                level=level,
                parent=parent_node.name,
                relation_type=relation_type,
                description=description,
                sarsekenov_terms=desc_terms,
                tier=self.term_to_tier.get(term, 0)
            )
            
            level_nodes.append(node)
        
        return level_nodes

    def _extract_exercises(
        self,
        sentences: List[str],
        parent_technique: ConceptNode
    ) -> List[ConceptNode]:
        """
        Извлечь упражнения для техники.
        
        Упражнения редко явно названы в тексте, поэтому:
        1. Ищем маркеры упражнений: "практикуй", "делай", "попробуй", "упражнение"
        2. Извлекаем duration, frequency, instructions
        """
        exercises = []
        
        exercise_markers = ["практикуй", "делай", "попробуй", "упражнение", "тренируй", "выполняй", "наблюдай"]
        
        for i, sentence in enumerate(sentences):
            sentence_lower = sentence.lower()
            
            # Проверка наличия маркера И термина родителя
            if any(marker in sentence_lower for marker in exercise_markers):
                # Check current sentence OR previous sentence for technique name
                is_related = parent_technique.name.lower() in sentence_lower
                if not is_related and i > 0:
                    is_related = parent_technique.name.lower() in sentences[i-1].lower()
                
                if is_related:
                    
                    # Генерация имени упражнения
                    exercise_name = f"Упражнение для {parent_technique.name}"
                    
                    # Попытка извлечь duration
                    duration = self._extract_duration(sentence)
                    
                    # Попытка извлечь frequency
                    frequency = self._extract_frequency(sentence)
                    
                    exercise = ConceptNode(
                        name=exercise_name,
                        level="exercise",
                        parent=parent_technique.name,
                        relation_type="is_exercise_for",
                        description=sentence,
                        sarsekenov_terms=[],
                        tier=5,
                        duration=duration,
                        frequency=frequency,
                        instructions=sentence
                    )
                    
                    exercises.append(exercise)
        
        return exercises

    def _extract_cross_connections(
        self,
        sentences: List[str],
        all_nodes: List[ConceptNode]
    ) -> List[CrossConnection]:
        """
        Извлечь горизонтальные связи между концептами.
        
        Маркеры связей:
        - "enables": "делает возможным", "позволяет", "открывает путь к"
        - "requires": "требует", "необходимо", "нужно сначала"
        - "leads_to": "ведёт к", "приводит к", "результат"
        - "transforms_into": "трансформируется в", "переходит в"
        """
        connections = []
        
        relation_markers = {
            "enables": ["делает возможным", "позволяет", "открывает путь к"],
            "requires": ["требует", "необходимо", "нужно сначала"],
            "leads_to": ["ведёт к", "приводит к", "результат"],
            "transforms_into": ["трансформируется в", "переходит в", "становится"]
        }
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            # Найти концепты в предложении
            concepts_in_sentence = [
                node for node in all_nodes 
                if node.name.lower() in sentence_lower
            ]
            
            if len(concepts_in_sentence) >= 2:
                # Определить тип связи
                for relation, markers in relation_markers.items():
                    if any(marker in sentence_lower for marker in markers):
                        # Simple heuristic: first concept -> second concept
                        # In reality, syntax analysis would be better, but this is rule-based
                        connection = CrossConnection(
                            from_concept=concepts_in_sentence[0].name,
                            to_concept=concepts_in_sentence[1].name,
                            relation=relation,
                            explanation=sentence,
                            context=sentence
                        )
                        connections.append(connection)
                        break
        
        return connections

    def _calculate_hierarchy_confidence(
        self,
        domains: List[ConceptNode],
        practices: List[ConceptNode],
        techniques: List[ConceptNode]
    ) -> float:
        """
        Расчёт уверенности в иерархии.
        
        Факторы:
        - Базовая уверенность: 0.5
        - +0.1 за каждый domain (макс 0.2)
        - +0.05 за каждую practice (макс 0.15)
        - +0.02 за каждую technique (макс 0.1)
        - +0.05 если есть все 5 уровней
        """
        confidence = 0.5
        
        confidence += min(len(domains) * 0.1, 0.2)
        confidence += min(len(practices) * 0.05, 0.15)
        confidence += min(len(techniques) * 0.02, 0.1)
        
        # Бонус за полноту иерархии (хотя бы один элемент на каждом уровне)
        if domains and practices and techniques:
            confidence += 0.05
        
        return min(confidence, 1.0)

    def _validate_hierarchy(self, hierarchy: ConceptHierarchy) -> tuple[bool, str]:
        """
        Валидация иерархии.
        
        Returns:
            (valid, reason)
        """
        
        # 1. Проверка root
        if hierarchy.root.name not in self.ALLOWED_ROOTS:
            return False, f"Invalid root: {hierarchy.root.name}"
        
        # 2. Проверка родителей
        all_nodes = (
            [hierarchy.root] +
            hierarchy.domains +
            hierarchy.practices +
            hierarchy.techniques +
            hierarchy.exercises
        )
        
        for node in all_nodes:
            if node.level != "root":
                if not node.parent:
                    return False, f"Node {node.name} has no parent"
                
                # Проверка что родитель существует
                parent_exists = any(n.name == node.parent for n in all_nodes)
                if not parent_exists:
                    return False, f"Parent {node.parent} for node {node.name} not found"
        
        # 3. Подсчёт терминов
        all_terms = []
        for node in all_nodes:
            all_terms.extend(node.sarsekenov_terms)
        
        unique_terms_count = len(set(all_terms))
        if unique_terms_count < self.MIN_SARSEKENOV_TERMS:
            return False, f"Not enough Sarsekenov terms: {unique_terms_count} < {self.MIN_SARSEKENOV_TERMS}"
        
        return True, "OK"

    def _split_sentences(self, text: str) -> List[str]:
        """Simple sentence splitter"""
        # Replace common abbreviations to avoid false splits if needed, but for now simple split
        return re.split(r'(?<=[.!?])\s+', text)

    def _find_description_for_term(self, sentences: List[str], term: str) -> str:
        """Find the most relevant sentence describing the term"""
        for sentence in sentences:
            if term.lower() in sentence.lower():
                return sentence
        return term  # Fallback

    def _extract_duration(self, text: str) -> Optional[str]:
        """Extract duration string like '5 минут'"""
        match = re.search(r'(\d+[\d\-\.]*\s*(?:минут|час|секунд)[а-я]*)', text.lower())
        if match:
            return match.group(1)
        return None

    def _extract_frequency(self, text: str) -> Optional[str]:
        """Extract frequency string like '3 раза в день'"""
        match = re.search(r'(\d+\s*раз[а]?\s*(?:в|на)\s*(?:день|неделю|месяц))', text.lower())
        if match:
            return match.group(1)
        # Check for words like "ежедневно"
        if "ежедневно" in text.lower():
            return "ежедневно"
        return None

def extract_concept_hierarchy(
    text: str,
    expected_root: Optional[str] = None,
    use_llm: bool = False
) -> Dict[str, Any]:
    """
    Быстрое извлечение иерархии концептов.
    
    Args:
        text: Текст для анализа
        expected_root: Ожидаемый корень (None = автоопределение)
        use_llm: Использовать LLM
    
    Returns:
        Dict с иерархией
    """
    extractor = ConceptHierarchyExtractor(use_llm=use_llm)
    return extractor.extract(text, expected_root)