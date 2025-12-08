#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Экстрактор паттернов нейро-сталкинга Саламата Сарсекенова.

Извлекает уникальные паттерны учения из валидированного текста.
"""

import json
import logging
import re
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from text_processor.validators.terminology_validator import (
    TerminologyValidator,
    ValidationResult
)

logger = logging.getLogger(__name__)


@dataclass
class NeurostalkingPattern:
    """Структура паттерна нейро-сталкинга"""
    pattern_category: str  # триада_трансформации, работа_с_вниманием, и т.д.
    pattern_name: str
    description: str
    key_terms: List[str]
    typical_context: str
    recognition_markers: List[str]
    related_practices: List[str]
    source_quote: str
    confidence: float  # 0.0 - 1.0


class NeurostalkingPatternExtractor:
    """
    Экстрактор уникальных паттернов учения Сарсекенова.
    
    Находит и структурирует паттерны четырех категорий:
    1. Триада трансформации (наблюдение → осознавание → трансформация)
    2. Работа с вниманием (захват, освобождение, расширение поля)
    3. Разотождествление (отделение от Я-образа)
    4. Состояния сознания (чистое осознавание, присутствие)
    """
    
    # Категории паттернов с ключевыми терминами
    PATTERN_CATEGORIES = {
        "триада_трансформации": {
            "key_terms": ["наблюдение", "осознавание", "трансформация", "метанаблюдение"],
            "description": "Процесс: наблюдение → осознавание → трансформация"
        },
        "работа_с_вниманием": {
            "key_terms": ["поле внимания", "свободное внимание", "захват внимания", 
                         "расширение поля", "поле восприятия"],
            "description": "Процессы работы с полем внимания"
        },
        "разотождествление": {
            "key_terms": ["разотождествление", "Я-образ", "идентификация", 
                         "наблюдающее сознание", "ложная самость"],
            "description": "Процессы отделения от ложной самости"
        },
        "состояния_сознания": {
            "key_terms": ["чистое осознавание", "присутствие", "живое переживание", 
                         "здесь-и-сейчас", "пробуждение", "прояснение"],
            "description": "Состояния чистого осознавания"
        }
    }
    
    def __init__(
        self,
        terminology_validator: Optional[TerminologyValidator] = None,
        use_llm: bool = False,
        llm_client = None
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
        
        logger.info(f"Initialized NeurostalkingPatternExtractor (LLM: {use_llm})")
    
    def extract(
        self, 
        text: str,
        min_density: float = 0.25,
        categories: Optional[List[str]] = None
    ) -> Dict:
        """
        Извлечь паттерны нейро-сталкинга из текста.
        
        Args:
            text: Текст для обработки
            min_density: Минимальная плотность терминов Сарсекенова
            categories: Список категорий для извлечения (None = все)
        
        Returns:
            Словарь с найденными паттернами
        """
        
        # Шаг 1: Валидация текста
        validation = self.validator.validate_text(text, min_density=min_density)
        
        if not validation.is_valid:
            logger.warning(f"Text validation failed: {validation.reason}")
            return {
                "valid": False,
                "reason": validation.reason,
                "patterns": []
            }
        
        logger.info(f"Text validated successfully (density: {validation.metrics['density']:.1%})")
        
        # Шаг 2: Определение релевантных категорий
        relevant_categories = self._identify_relevant_categories(
            validation.sarsekenov_entities,
            categories
        )
        
        if not relevant_categories:
            logger.info("No relevant pattern categories found")
            return {
                "valid": True,
                "patterns": [],
                "metrics": validation.metrics
            }
        
        # Шаг 3: Извлечение паттернов
        if self.use_llm and self.llm_client:
            patterns = self._extract_with_llm(text, relevant_categories, validation)
        else:
            patterns = self._extract_rule_based(text, relevant_categories, validation)
        
        return {
            "valid": True,
            "patterns": [asdict(p) for p in patterns],
            "metrics": validation.metrics,
            "categories_found": list(set(p.pattern_category for p in patterns))
        }
    
    def _identify_relevant_categories(
        self,
        entities: List[str],
        requested_categories: Optional[List[str]] = None
    ) -> List[str]:
        """
        Определить релевантные категории паттернов на основе найденных сущностей.
        
        Args:
            entities: Список найденных терминов Сарсекенова
            requested_categories: Запрошенные категории (None = все)
        
        Returns:
            Список релевантных категорий
        """
        relevant = []
        entities_lower = [e.lower() for e in entities]
        
        for category, info in self.PATTERN_CATEGORIES.items():
            # Проверка запрошенных категорий
            if requested_categories and category not in requested_categories:
                continue
            
            # Проверка наличия ключевых терминов категории
            key_terms_lower = [t.lower() for t in info['key_terms']]
            
            if any(term in entities_lower for term in key_terms_lower):
                relevant.append(category)
                logger.debug(f"Category '{category}' is relevant")
        
        return relevant
    
    def _extract_rule_based(
        self,
        text: str,
        categories: List[str],
        validation: ValidationResult
    ) -> List[NeurostalkingPattern]:
        """
        Извлечение паттернов на основе правил (без LLM).
        
        Использует эвристики для определения паттернов.
        """
        patterns = []
        
        for category in categories:
            category_info = self.PATTERN_CATEGORIES[category]
            
            # Поиск предложений с ключевыми терминами категории
            sentences = self._split_into_sentences(text)
            
            for sentence in sentences:
                sentence_lower = sentence.lower()
                
                # Проверка наличия ключевых терминов категории в предложении
                matching_terms = [
                    term for term in category_info['key_terms']
                    if term.lower() in sentence_lower
                ]
                
                if len(matching_terms) >= 2:  # Минимум 2 термина категории
                    # Создание паттерна
                    pattern = self._create_pattern_from_sentence(
                        sentence,
                        category,
                        matching_terms,
                        validation.sarsekenov_entities
                    )
                    
                    if pattern:
                        patterns.append(pattern)
        
        return patterns
    
    def _create_pattern_from_sentence(
        self,
        sentence: str,
        category: str,
        matching_terms: List[str],
        all_entities: List[str]
    ) -> Optional[NeurostalkingPattern]:
        """
        Создать паттерн из предложения на основе эвристик.
        """
        
        # Извлечение всех терминов Сарсекенова из предложения
        sentence_entities = [
            e for e in all_entities
            if e.lower() in sentence.lower()
        ]
        
        if len(sentence_entities) < 2:
            return None
        
        # Определение типичного контекста на основе категории
        typical_contexts = {
            "триада_трансформации": "В процессе практики метанаблюдения",
            "работа_с_вниманием": "При работе с полем внимания",
            "разотождествление": "В процессе разотождествления с Я-образом",
            "состояния_сознания": "В состоянии чистого присутствия"
        }
        
        # Определение маркеров распознавания
        recognition_markers = self._extract_recognition_markers(sentence, category)
        
        # Определение связанных практик
        related_practices = self._identify_related_practices(sentence_entities)
        
        pattern = NeurostalkingPattern(
            pattern_category=category,
            pattern_name=self._generate_pattern_name(sentence, matching_terms),
            description=sentence.strip(),
            key_terms=sentence_entities,
            typical_context=typical_contexts.get(category, "В практике нейро-сталкинга"),
            recognition_markers=recognition_markers,
            related_practices=related_practices,
            source_quote=sentence.strip(),
            confidence=self._calculate_confidence(sentence_entities, matching_terms)
        )
        
        return pattern
    
    def _generate_pattern_name(self, sentence: str, key_terms: List[str]) -> str:
        """Генерация названия паттерна"""
        # Упрощенная версия: используем первые ключевые термины
        if len(key_terms) >= 2:
            return f"{key_terms[0]} и {key_terms[1]}"
        elif key_terms:
            return key_terms[0]
        else:
            return "Паттерн нейро-сталкинга"
    
    def _extract_recognition_markers(self, sentence: str, category: str) -> List[str]:
        """Извлечение маркеров распознавания паттерна"""
        markers = []
        
        # Ключевые слова для каждой категории
        marker_keywords = {
            "триада_трансформации": ["наблюдать", "осознавать", "замечать", "видеть"],
            "работа_с_вниманием": ["внимание", "поле", "расширяется", "сужается"],
            "разотождествление": ["отделение", "дистанция", "наблюдатель"],
            "состояния_сознания": ["присутствие", "ясность", "пробуждение"]
        }
        
        sentence_lower = sentence.lower()
        category_keywords = marker_keywords.get(category, [])
        
        for keyword in category_keywords:
            if keyword in sentence_lower:
                markers.append(f"Присутствует '{keyword}'")
        
        return markers if markers else ["Прямое описание процесса"]
    
    def _identify_related_practices(self, entities: List[str]) -> List[str]:
        """Определение связанных практик"""
        practices = []
        
        practice_terms = {
            "метанаблюдение", "разотождествление", "центрирование", 
            "интеграция опыта", "центрирование на присутствии"
        }
        
        for entity in entities:
            if entity.lower() in [p.lower() for p in practice_terms]:
                practices.append(entity)
        
        return practices if practices else ["метанаблюдение"]
    
    def _calculate_confidence(
        self,
        sentence_entities: List[str],
        matching_terms: List[str]
    ) -> float:
        """
        Рассчитать уверенность в паттерне.
        
        Основано на количестве терминов и их релевантности.
        """
        # Базовая уверенность на основе количества терминов
        base_confidence = min(len(sentence_entities) * 0.15, 0.7)
        
        # Бонус за совпадение с ключевыми терминами категории
        category_bonus = min(len(matching_terms) * 0.1, 0.3)
        
        return min(base_confidence + category_bonus, 1.0)
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Разделить текст на предложения"""
        # Простое разделение по точкам, восклицательным и вопросительным знакам
        sentences = re.split(r'[.!?]+', text)
        
        # Очистка и фильтрация
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _extract_with_llm(
        self,
        text: str,
        categories: List[str],
        validation: ValidationResult
    ) -> List[NeurostalkingPattern]:
        """
        Извлечение паттернов с использованием LLM.
        
        TODO: Реализовать после настройки LLM клиента
        """
        logger.warning("LLM extraction not yet implemented, falling back to rule-based")
        return self._extract_rule_based(text, categories, validation)


# Utility функции

def extract_patterns(
    text: str,
    validator: Optional[TerminologyValidator] = None
) -> Dict:
    """
    Utility функция для быстрого извлечения паттернов.
    
    Args:
        text: Текст для обработки
        validator: Валидатор (создается если не передан)
    
    Returns:
        Словарь с паттернами
    """
    extractor = NeurostalkingPatternExtractor(terminology_validator=validator)
    return extractor.extract(text)
