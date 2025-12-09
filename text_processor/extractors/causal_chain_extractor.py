#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Экстрактор причинно-следственных цепочек трансформации сознания.

Извлекает системные процессы трансформации в терминологии Саламата Сарсекенова.
Полностью совместим с SMART режимом валидации.

ФИЛОСОФИЯ:
НЕ линейная причинность (A→B→C), А СИСТЕМНАЯ трансформация:
- Каждый этап возникает из целостности процесса (эмерджентность)
- Этапы связаны через emerges_from и enables
- Поддержка циклических/спиральных процессов
- Маркеры целостности системы
"""

import json
import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from pathlib import Path

from voice_bot_pipeline.text_processor.validators.terminology_validator import (
    TerminologyValidator,
    ValidationResult
)

logger = logging.getLogger(__name__)


@dataclass
class InterventionPoint:
    """Точка возможного вмешательства в процесс"""
    at_stage: int                    # На каком этапе
    practice: str                    # Какая практика применяется
    triggers: List[str]              # Что запускает практику
    expected_outcome: str            # Ожидаемый результат


@dataclass
class CausalChainStage:
    """Этап в процессе трансформации"""
    stage: int                       # Номер этапа
    stage_name: str                  # Название (из терминов)
    description: str                 # Описание (из текста)
    sarsekenov_terms: List[str]      # Термины Сарсекенова
    # СИСТЕМНЫЕ связи (не линейные):
    emerges_from: Optional[List[int]] = None  # Из каких этапов возникает
    enables: Optional[List[int]] = None       # Какие этапы делает возможными


@dataclass
class CausalChain:
    """Причинно-следственная цепочка (системная трансформация)"""
    process_name: str                # Название процесса
    process_category: str            # Категория (из 5 типов)
    stages: List[CausalChainStage]   # Этапы процесса
    intervention_points: List[InterventionPoint]
    context: str                     # Контекст (200 символов)
    source_quote: str                # Исходная цитата
    confidence: float                # Уверенность (0.0-1.0)
    
    # Метаданные системности:
    is_cyclical: bool = False        # Циклический процесс?
    wholeness_markers: List[str] = field(default_factory=list)  # Маркеры целостности
    sarsekenov_density: float = 0.0  # Плотность терминов


class CausalChainExtractor:
    """
    Экстрактор причинно-следственных цепочек трансформации сознания.
    
    ФИЛОСОФИЯ SMART РЕЖИМА:
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    1. Forbidden terms НЕ блокируют текст
    2. Минимум 15% плотности (не 25%)
    3. Фокус на системности, не линейности
    4. LLM на выходе сам фильтрует стиль
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    
    MIN_SARSEKENOV_TERMS = 3  # Минимум терминов в цепочке
    
    # Категории процессов (5 типов)
    PROCESS_CATEGORIES = {
        "триада_трансформации": [
            "метанаблюдение", "наблюдение", "осознавание", "трансформация",
            "чистое осознавание", "свидетельствование"
        ],
        "работа_с_вниманием": [
            "поле внимания", "свободное внимание", "захват внимания",
            "центрирование", "присутствие", "расширение поля", "поле восприятия"
        ],
        "разотождествление": [
            "разотождествление", "Я-образ", "идентификация",
            "ложная самость", "автоматизмы психики", "наблюдающее сознание"
        ],
        "пробуждение_сознания": [
            "пробуждение", "реализация", "прозрение", "ясность",
            "живое переживание", "бытие"
        ],
        "интеграция_целостности": [
            "интеграция", "целостность", "самодостаточность",
            "гомеостаз", "эмерджентность", "интеграция опыта"
        ]
    }
    
    # Практики для точек вмешательства
    PRACTICES = {
        "метанаблюдение": {
            "triggers": ["автоматическая реакция", "захват внимания", "отождествление"],
            "outcome": "выход из автоматизма в осознанность"
        },
        "центрирование": {
            "triggers": ["потеря присутствия", "рассеянность", "захваченность"],
            "outcome": "возвращение к центру, стабилизация внимания"
        },
        "разотождествление": {
            "triggers": ["отождествление с Я-образом", "эмоциональная захваченность"],
            "outcome": "свобода от ложной идентификации"
        },
        "интеграция опыта": {
            "triggers": ["инсайт", "новое осознание", "трансформативный опыт"],
            "outcome": "укоренение нового понимания в практике"
        },
        "свидетельствование": {
            "triggers": ["внутренний процесс", "эмоция", "мысль"],
            "outcome": "непривязанное наблюдение, ясность"
        }
    }
    
    # Маркеры цикличности
    CYCLICAL_MARKERS = [
        "снова", "возвращается", "спираль", "цикл", "вновь",
        "повторяется", "периодически", "раз за разом", "каждый раз"
    ]
    
    # Маркеры целостности
    WHOLENESS_MARKERS = [
        "целостность", "интеграция", "эмерджентность", "единство",
        "всё вместе", "как одно", "нераздельность", "полнота"
    ]
    
    def __init__(
        self,
        terminology_validator: Optional[TerminologyValidator] = None,
        use_llm: bool = False,
        llm_client: Optional[Any] = None
    ):
        """
        Инициализация экстрактора.
        
        Args:
            terminology_validator: Валидатор терминологии (создается если не передан)
            use_llm: Использовать LLM для извлечения (иначе rule-based)
            llm_client: Клиент LLM (OpenAI, Anthropic и т.д.)
        """
        self.validator = terminology_validator or TerminologyValidator()
        self.use_llm = use_llm
        self.llm_client = llm_client
        
        # Строим плоский список всех терминов категорий
        self._all_category_terms = {}
        for category, terms in self.PROCESS_CATEGORIES.items():
            self._all_category_terms[category] = set(t.lower() for t in terms)
        
        logger.info(f"Initialized CausalChainExtractor (LLM: {use_llm})")
    
    def extract(
        self,
        text: str,
        specific_category: Optional[str] = None,
        min_stages: int = 2,
        max_stages: int = 10
    ) -> Dict[str, Any]:
        """
        Извлечение причинно-следственных цепочек.
        
        Args:
            text: Текст для обработки
            specific_category: Конкретная категория для извлечения (None = все)
            min_stages: Минимальное количество этапов
            max_stages: Максимальное количество этапов
        
        Returns:
            {
                "valid": bool,
                "reason": str,
                "chains": List[Dict],  # Сериализованные CausalChain
                "metrics": Dict
            }
        """
        
        # 1. ВАЛИДАЦИЯ через TerminologyValidator (SMART режим)
        # НЕ указываем min_density - берётся из .env (SMART = 0.15)
        validation = self.validator.validate_text(text)
        
        if not validation.is_valid:
            logger.warning(f"Text validation failed: {validation.reason}")
            return {
                "valid": False,
                "reason": validation.reason,
                "chains": [],
                "metrics": validation.metrics
            }
        
        logger.info(f"Text validated successfully (density: {validation.metrics['density']:.1%})")
        
        # 2. ИЗВЛЕЧЕНИЕ цепочек (rule-based или LLM)
        if self.use_llm and self.llm_client:
            chains = self._extract_with_llm(
                text, 
                validation.sarsekenov_entities,
                specific_category,
                min_stages,
                max_stages
            )
        else:
            chains = self._extract_rule_based(
                text,
                validation.sarsekenov_entities,
                specific_category,
                min_stages,
                max_stages
            )
        
        # 3. ВАЛИДАЦИЯ каждой цепочки
        validated_chains = [c for c in chains if self._validate_chain(c)]
        
        # Добавляем плотность к каждой цепочке
        for chain in validated_chains:
            chain.sarsekenov_density = validation.metrics['density']
        
        return {
            "valid": True,
            "reason": f"Извлечено {len(validated_chains)} цепочек",
            "chains": [asdict(c) for c in validated_chains],
            "metrics": {
                "density": validation.metrics['density'],
                "total_chains": len(validated_chains),
                "categories": list(set(c.process_category for c in validated_chains)),
                "sarsekenov_entities": validation.sarsekenov_entities
            }
        }
    
    def _extract_rule_based(
        self,
        text: str,
        entities: List[str],
        specific_category: Optional[str],
        min_stages: int,
        max_stages: int
    ) -> List[CausalChain]:
        """
        Rule-based извлечение цепочек.
        
        Алгоритм:
        1. Определить категории в тексте
        2. Разбить на предложения
        3. Найти предложения релевантные категории
        4. Построить этапы процесса
        5. Определить точки вмешательства
        6. Создать цепочку
        """
        chains = []
        
        # 1. Определение категорий
        relevant_categories = self._identify_categories(entities, specific_category)
        
        if not relevant_categories:
            logger.info("No relevant categories found in text")
            return []
        
        logger.debug(f"Found relevant categories: {relevant_categories}")
        
        # 2. Разбиение на предложения
        sentences = self._split_sentences(text)
        
        for category in relevant_categories:
            # 3. Фильтрация предложений по категории
            category_sentences = self._filter_by_category(sentences, category, entities)
            
            if len(category_sentences) < min_stages:
                logger.debug(f"Category {category}: not enough sentences ({len(category_sentences)} < {min_stages})")
                continue
            
            # 4. Построение цепочки
            chain = self._build_chain_from_sentences(
                category_sentences[:max_stages],
                category,
                text,
                entities
            )
            
            if chain and len(chain.stages) >= min_stages:
                chains.append(chain)
                logger.debug(f"Built chain for category {category} with {len(chain.stages)} stages")
        
        return chains
    
    def _identify_categories(
        self,
        entities: List[str],
        specific_category: Optional[str]
    ) -> List[str]:
        """
        Определить релевантные категории на основе найденных сущностей.
        
        Категория считается релевантной если найдено минимум 2 её термина.
        """
        relevant = []
        entities_lower = set(e.lower() for e in entities)
        
        for category, terms in self.PROCESS_CATEGORIES.items():
            # Проверка запрошенной категории
            if specific_category and category != specific_category:
                continue
            
            # Подсчёт совпадений
            terms_lower = set(t.lower() for t in terms)
            matches = entities_lower.intersection(terms_lower)
            
            if len(matches) >= 2:
                relevant.append(category)
                logger.debug(f"Category '{category}' is relevant (matches: {matches})")
        
        return relevant
    
    def _split_sentences(self, text: str) -> List[str]:
        """Разбить текст на предложения по [.!?]"""
        sentences = re.split(r'[.!?]+', text)
        # Очистка и фильтрация
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        return sentences
    
    def _filter_by_category(
        self,
        sentences: List[str],
        category: str,
        all_entities: List[str]
    ) -> List[str]:
        """Оставить предложения с терминами категории"""
        category_terms = self._all_category_terms.get(category, set())
        
        filtered = []
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            # Проверяем наличие терминов категории
            has_category_term = any(term in sentence_lower for term in category_terms)
            
            # Или любых терминов Сарсекенова
            has_sarsekenov = any(e.lower() in sentence_lower for e in all_entities)
            
            if has_category_term or has_sarsekenov:
                filtered.append(sentence)
        
        return filtered
    
    def _build_chain_from_sentences(
        self,
        sentences: List[str],
        category: str,
        full_text: str,
        all_entities: List[str]
    ) -> Optional[CausalChain]:
        """
        Построить CausalChain из предложений:
        - Создать stages из предложений
        - Определить emerges_from/enables (системность)
        - Найти intervention_points
        - Определить is_cyclical
        - Извлечь wholeness_markers
        """
        if not sentences:
            return None
        
        # Создание этапов
        stages = []
        all_terms = []
        
        for i, sentence in enumerate(sentences, start=1):
            # Найти термины Сарсекенова в предложении
            sentence_terms = [
                e for e in all_entities
                if e.lower() in sentence.lower()
            ]
            all_terms.extend(sentence_terms)
            
            # Определить название этапа
            stage_name = self._determine_stage_name(sentence, sentence_terms, category)
            
            # Создать системные связи
            emerges_from = [i - 1] if i > 1 else None
            enables = [i + 1] if i < len(sentences) else None
            
            stage = CausalChainStage(
                stage=i,
                stage_name=stage_name,
                description=sentence.strip(),
                sarsekenov_terms=sentence_terms,
                emerges_from=emerges_from,
                enables=enables
            )
            stages.append(stage)
        
        if not stages:
            return None
        
        # Определение точек вмешательства
        intervention_points = self._find_intervention_points(stages, all_terms)
        
        # Определение цикличности
        is_cyclical = self._detect_cyclical(sentences)
        
        # Извлечение маркеров целостности
        wholeness_markers = self._extract_wholeness_markers(sentences)
        
        # Генерация названия процесса
        process_name = self._generate_process_name(stages, category)
        
        # Расчёт уверенности
        confidence = self._calculate_confidence(stages, all_terms)
        
        # Контекст (первые 200 символов)
        context = full_text[:200].strip()
        
        # Исходная цитата (объединение предложений)
        source_quote = " ".join(sentences)[:500]
        
        chain = CausalChain(
            process_name=process_name,
            process_category=category,
            stages=stages,
            intervention_points=intervention_points,
            context=context,
            source_quote=source_quote,
            confidence=confidence,
            is_cyclical=is_cyclical,
            wholeness_markers=wholeness_markers
        )
        
        return chain
    
    def _determine_stage_name(
        self,
        sentence: str,
        terms: List[str],
        category: str
    ) -> str:
        """Определить название этапа на основе терминов"""
        # Приоритет: термины категории
        category_terms = self.PROCESS_CATEGORIES.get(category, [])
        
        for term in terms:
            if term.lower() in [t.lower() for t in category_terms]:
                return term
        
        # Если нет терминов категории, берём первый термин
        if terms:
            return terms[0]
        
        # Если терминов нет, генерируем из предложения
        return f"Этап процесса"
    
    def _find_intervention_points(
        self,
        stages: List[CausalChainStage],
        all_terms: List[str]
    ) -> List[InterventionPoint]:
        """Найти точки вмешательства на основе практик"""
        points = []
        all_terms_lower = set(t.lower() for t in all_terms)
        
        for practice_name, practice_info in self.PRACTICES.items():
            if practice_name.lower() in all_terms_lower:
                # Найти этап, на котором применяется практика
                for stage in stages:
                    stage_terms_lower = [t.lower() for t in stage.sarsekenov_terms]
                    if practice_name.lower() in stage_terms_lower:
                        point = InterventionPoint(
                            at_stage=stage.stage,
                            practice=practice_name,
                            triggers=practice_info["triggers"],
                            expected_outcome=practice_info["outcome"]
                        )
                        points.append(point)
                        break
        
        return points
    
    def _detect_cyclical(self, sentences: List[str]) -> bool:
        """Поиск маркеров цикличности"""
        full_text = " ".join(sentences).lower()
        
        for marker in self.CYCLICAL_MARKERS:
            if marker in full_text:
                return True
        
        return False
    
    def _extract_wholeness_markers(self, sentences: List[str]) -> List[str]:
        """Извлечь маркеры целостности"""
        markers_found = []
        full_text = " ".join(sentences).lower()
        
        for marker in self.WHOLENESS_MARKERS:
            if marker in full_text:
                markers_found.append(marker)
        
        return markers_found
    
    def _generate_process_name(
        self,
        stages: List[CausalChainStage],
        category: str
    ) -> str:
        """Генерация названия процесса"""
        # Собираем названия первых 2-3 этапов
        stage_names = [s.stage_name for s in stages[:3] if s.stage_name]
        
        if len(stage_names) >= 2:
            return f"{stage_names[0]} → {stage_names[1]}"
        elif stage_names:
            return f"Процесс: {stage_names[0]}"
        else:
            category_display = category.replace("_", " ")
            return f"Процесс {category_display}"
    
    def _calculate_confidence(
        self,
        stages: List[CausalChainStage],
        all_terms: List[str]
    ) -> float:
        """
        Расчёт уверенности:
        - Базовая: 0.5
        - +0.05 за каждый этап (макс 0.2)
        - +0.02 за каждый термин (макс 0.2)
        - +0.05 за каждую системную связь (макс 0.1)
        """
        base = 0.5
        
        # Бонус за этапы
        stages_bonus = min(len(stages) * 0.05, 0.2)
        
        # Бонус за термины
        terms_bonus = min(len(all_terms) * 0.02, 0.2)
        
        # Бонус за системные связи
        systemic_links = sum(
            1 for s in stages 
            if s.emerges_from or s.enables
        )
        systemic_bonus = min(systemic_links * 0.05, 0.1)
        
        confidence = base + stages_bonus + terms_bonus + systemic_bonus
        
        return min(confidence, 1.0)
    
    def _validate_chain(self, chain: CausalChain) -> bool:
        """
        Валидация цепочки:
        1. Минимум 3 термина Сарсекенова
        2. Проверка НЕ НУЖНА для forbidden terms (SMART режим)
        """
        all_terms = []
        for stage in chain.stages:
            all_terms.extend(stage.sarsekenov_terms)
        
        is_valid = len(all_terms) >= self.MIN_SARSEKENOV_TERMS
        
        if not is_valid:
            logger.debug(f"Chain rejected: only {len(all_terms)} terms (min: {self.MIN_SARSEKENOV_TERMS})")
        
        return is_valid
    
    def _extract_with_llm(
        self,
        text: str,
        entities: List[str],
        specific_category: Optional[str],
        min_stages: int,
        max_stages: int
    ) -> List[CausalChain]:
        """
        Извлечение цепочек с использованием LLM.
        
        TODO: Реализовать после настройки LLM клиента
        """
        logger.warning("LLM extraction not yet implemented, falling back to rule-based")
        return self._extract_rule_based(
            text, entities, specific_category, min_stages, max_stages
        )


# Utility функции

def extract_causal_chains(
    text: str,
    specific_category: Optional[str] = None,
    min_stages: int = 2,
    max_stages: int = 10,
    use_llm: bool = False,
    validator: Optional[TerminologyValidator] = None
) -> Dict[str, Any]:
    """
    Быстрое извлечение причинно-следственных цепочек.
    
    Args:
        text: Текст для обработки
        specific_category: Конкретная категория (None = все)
        min_stages: Минимум этапов
        max_stages: Максимум этапов
        use_llm: Использовать LLM
        validator: Валидатор (создается если не передан)
    
    Returns:
        Словарь с цепочками и метриками
    
    Example:
        >>> result = extract_causal_chains(text, specific_category="триада_трансформации")
        >>> print(f"Найдено цепочек: {len(result['chains'])}")
    """
    extractor = CausalChainExtractor(
        terminology_validator=validator,
        use_llm=use_llm
    )
    return extractor.extract(text, specific_category, min_stages, max_stages)
