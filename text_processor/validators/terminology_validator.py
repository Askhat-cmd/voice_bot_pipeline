#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Терминологический валидатор для учения Саламата Сарсекенова.
Это ФУНДАМЕНТ всей системы - ни один текст не обрабатывается без валидации.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
import logging

try:
    import pymorphy3 as pymorphy2  # pymorphy3 - форк для Python 3.11+
    PYMORPHY_AVAILABLE = True
except ImportError:
    try:
        import pymorphy2  # Fallback для старых версий Python
        PYMORPHY_AVAILABLE = True
    except ImportError:
        PYMORPHY_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Результат валидации текста"""
    is_valid: bool
    reason: str
    metrics: Dict
    forbidden_terms_found: List[str]
    sarsekenov_entities: List[str]


class TerminologyValidator:
    """
    Валидатор терминологии Сарсекенова.
    
    Гарантирует, что обрабатываются только тексты с достаточной плотностью
    специфической терминологии и без запрещенной общепсихологической лексики.
    """
    
    def __init__(self, config_dir: str = None):
        """
        Инициализация валидатора.
        
        Args:
            config_dir: Путь к директории с конфигурацией терминологии
        """
        if config_dir is None:
            # Определяем путь относительно файла
            self.config_dir = Path(__file__).resolve().parents[2] / "config" / "terminology"
        else:
            self.config_dir = Path(config_dir)
        
        # Загрузка конфигурации
        self.sarsekenov_terms = self._load_sarsekenov_terms()
        self.forbidden_config = self._load_forbidden_terms()
        self.term_categories = self._load_term_categories()
        
        # Обработанные структуры для быстрого поиска
        self.all_sarsekenov_terms = self._flatten_sarsekenov_terms()
        self.forbidden_terms = set(self.forbidden_config['forbidden_terms'])
        self.allowed_general_terms = set(self.forbidden_config.get('allowed_general_terms', []))
        
        # Инициализация морфологического анализатора для лемматизации
        if PYMORPHY_AVAILABLE:
            self.morph = pymorphy2.MorphAnalyzer()
            # Создаём набор лемм терминов для быстрого поиска
            self.sarsekenov_lemmas = self._build_lemma_index()
            self.forbidden_lemmas = {self._lemmatize(t) for t in self.forbidden_terms}
        else:
            self.morph = None
            self.sarsekenov_lemmas = {}
            self.forbidden_lemmas = set()
            logger.warning("pymorphy2 not installed. Lemmatization disabled. Install with: pip install pymorphy2")
        
        logger.info(f"Initialized TerminologyValidator with {len(self.all_sarsekenov_terms)} Sarsekenov terms")
        logger.info(f"Forbidden terms: {len(self.forbidden_terms)}")
        logger.info(f"Pymorphy2 available: {PYMORPHY_AVAILABLE}")
    
    def _load_sarsekenov_terms(self) -> Dict:
        """Загрузка терминов Сарсекенова из JSON"""
        path = self.config_dir / "sarsekenov_terms.json"
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_forbidden_terms(self) -> Dict:
        """Загрузка запрещенных терминов из JSON"""
        path = self.config_dir / "forbidden_terms.json"
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_term_categories(self) -> Dict:
        """Загрузка категорий терминов"""
        path = self.config_dir / "term_categories.json"
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _flatten_sarsekenov_terms(self) -> Set[str]:
        """
        Извлечь все термины Сарсекенова в единый set для быстрого поиска.
        """
        terms = set()
        for tier_key, tier_data in self.sarsekenov_terms.items():
            if 'terms' in tier_data:
                terms.update(tier_data['terms'])
        return terms
    
    def _lemmatize(self, word: str) -> str:
        """Привести слово к начальной форме (лемме)."""
        if not self.morph:
            return word.lower()
        
        # Для составных терминов - лемматизируем каждое слово
        if ' ' in word:
            parts = word.split()
            lemmas = [self._lemmatize(p) for p in parts]
            return ' '.join(lemmas)
        
        # Для терминов с дефисом - лемматизируем каждую часть
        if '-' in word:
            parts = word.split('-')
            lemmas = [self._lemmatize(p) for p in parts]
            return '-'.join(lemmas)
        
        # Простое слово
        parsed = self.morph.parse(word.lower())
        if parsed:
            return parsed[0].normal_form
        return word.lower()
    
    def _build_lemma_index(self) -> Dict[str, str]:
        """Построить индекс: лемма -> оригинальный термин."""
        index = {}
        for term in self.all_sarsekenov_terms:
            lemma = self._lemmatize(term)
            index[lemma] = term
        return index
    
    def _lemmatize_text_words(self, text: str) -> List[str]:
        """Лемматизировать все слова в тексте."""
        words = re.findall(r'[а-яёА-ЯЁ-]+', text.lower())
        if not self.morph:
            return words
        return [self._lemmatize(w) for w in words]
    
    def validate_text(
        self, 
        text: str, 
        min_density: float = 0.25,
        strict_mode: bool = True
    ) -> ValidationResult:
        """
        Валидация текста на соответствие стандартам Сарсекенова.
        
        Args:
            text: Текст для валидации
            min_density: Минимальная плотность терминов Сарсекенова (0.25 = 25%)
            strict_mode: Строгий режим (отклонять при наличии запрещенных терминов)
        
        Returns:
            ValidationResult с детальной информацией
        """
        
        # Шаг 1: Проверка на запрещенные термины
        forbidden_found = self._find_forbidden_terms(text)
        
        if strict_mode and forbidden_found:
            return ValidationResult(
                is_valid=False,
                reason=f"Найдены запрещенные термины: {', '.join(forbidden_found)}",
                metrics={},
                forbidden_terms_found=forbidden_found,
                sarsekenov_entities=[]
            )
        
        # Шаг 2: Расчет плотности терминов Сарсекенова
        density_metrics = self._calculate_density(text)
        
        # Шаг 3: Извлечение сущностей
        entities = self._extract_entities(text)
        
        # Шаг 4: Проверка минимальной плотности
        if density_metrics['density'] < min_density:
            return ValidationResult(
                is_valid=False,
                reason=f"Недостаточная плотность терминов Сарсекенова: {density_metrics['density']:.1%} < {min_density:.1%}",
                metrics=density_metrics,
                forbidden_terms_found=forbidden_found,
                sarsekenov_entities=entities
            )
        
        # Шаг 5: Успешная валидация
        return ValidationResult(
            is_valid=True,
            reason=f"Валидный текст Сарсекенова (плотность: {density_metrics['density']:.1%})",
            metrics=density_metrics,
            forbidden_terms_found=forbidden_found,
            sarsekenov_entities=entities
        )
    
    def _find_forbidden_terms(self, text: str) -> List[str]:
        """Найти запрещенные термины в тексте."""
        found = []
        
        if self.morph and PYMORPHY_AVAILABLE:
            # С лемматизацией - ищем по леммам
            text_lemmas = set(self._lemmatize_text_words(text))
            for term in self.forbidden_terms:
                term_lemma = self._lemmatize(term)
                if term_lemma in text_lemmas:
                    if term not in self.allowed_general_terms:
                        found.append(term)
        else:
            # Без лемматизации - старый метод
            text_lower = text.lower()
            for term in self.forbidden_terms:
                pattern = r'\b' + re.escape(term.lower()) + r'\b'
                if re.search(pattern, text_lower):
                    if term not in self.allowed_general_terms:
                        found.append(term)
        
        return found
    
    def _calculate_density(self, text: str) -> Dict:
        """Рассчитать плотность терминов Сарсекенова в тексте."""
        
        words = re.findall(r'[а-яёА-ЯЁ]+', text.lower())
        
        stop_words = {
            'и', 'в', 'не', 'на', 'с', 'что', 'а', 'это', 'как', 'по', 
            'для', 'но', 'от', 'к', 'за', 'из', 'или', 'то', 'же', 'так',
            'вы', 'он', 'она', 'они', 'мы', 'весь', 'уже', 'еще', 'бы',
            'вот', 'когда', 'может', 'быть', 'есть', 'был', 'была', 'были'
        }
        
        significant_words = [w for w in words if w not in stop_words and len(w) > 2]
        
        sarsekenov_occurrences = 0
        found_terms_details = []
        
        if self.morph and PYMORPHY_AVAILABLE:
            # С лемматизацией
            text_lemmas = self._lemmatize_text_words(text)
            
            for lemma, original_term in self.sarsekenov_lemmas.items():
                if ' ' in lemma or '-' in lemma:
                    # Составной термин - ищем в строке лемм
                    lemma_text = ' '.join(text_lemmas)
                    count = lemma_text.count(lemma)
                else:
                    # Простое слово - считаем вхождения
                    count = text_lemmas.count(lemma)
                
                if count > 0:
                    sarsekenov_occurrences += count
                    found_terms_details.append({
                        'term': original_term,
                        'count': count,
                        'tier': self._get_term_tier(original_term)
                    })
        else:
            # Без лемматизации - старый метод
            text_lower = text.lower()
            
            for term in self.all_sarsekenov_terms:
                term_lower = term.lower()
                
                if ' ' in term_lower or '-' in term_lower:
                    count = text_lower.count(term_lower)
                else:
                    pattern = r'(?<![а-яёА-ЯЁ])' + re.escape(term_lower) + r'(?![а-яёА-ЯЁ])'
                    count = len(re.findall(pattern, text_lower))
                
                if count > 0:
                    sarsekenov_occurrences += count
                    found_terms_details.append({
                        'term': term,
                        'count': count,
                        'tier': self._get_term_tier(term)
                    })
        
        total_significant = len(significant_words)
        density = sarsekenov_occurrences / total_significant if total_significant > 0 else 0
        
        return {
            'density': density,
            'sarsekenov_occurrences': sarsekenov_occurrences,
            'total_significant_words': total_significant,
            'found_terms': found_terms_details,
            'text_length_chars': len(text),
            'text_length_words': len(words)
        }
    
    def _get_term_tier(self, term: str) -> Optional[str]:
        """Определить уровень (tier) термина"""
        for tier_key, tier_data in self.sarsekenov_terms.items():
            if term in tier_data.get('terms', []):
                return tier_key
        return None
    
    def _extract_entities(self, text: str) -> List[str]:
        """Извлечь только термины Сарсекенова как сущности."""
        entities = []
        
        if self.morph and PYMORPHY_AVAILABLE:
            # С лемматизацией - ищем по леммам
            text_lemmas = self._lemmatize_text_words(text)
            text_lemmas_set = set(text_lemmas)
            
            for lemma, original_term in self.sarsekenov_lemmas.items():
                # Для составных терминов - проверяем подстроку в лемматизированном тексте
                if ' ' in lemma or '-' in lemma:
                    lemma_text = ' '.join(text_lemmas)
                    if lemma in lemma_text:
                        entities.append(original_term)
                else:
                    # Для простых слов - проверяем наличие в множестве
                    if lemma in text_lemmas_set:
                        entities.append(original_term)
        else:
            # Без лемматизации - старый метод
            text_lower = text.lower()
            sorted_terms = sorted(self.all_sarsekenov_terms, key=len, reverse=True)
            
            for term in sorted_terms:
                term_lower = term.lower()
                
                if ' ' in term_lower or '-' in term_lower:
                    if term_lower in text_lower:
                        entities.append(term)
                else:
                    pattern = r'(?<![а-яёА-ЯЁ])' + re.escape(term_lower) + r'(?![а-яёА-ЯЁ])'
                    if re.search(pattern, text_lower):
                        entities.append(term)
        
        # Удаление дубликатов с сохранением порядка
        seen = set()
        unique_entities = []
        for entity in entities:
            entity_lower = entity.lower()
            if entity_lower not in seen:
                seen.add(entity_lower)
                unique_entities.append(entity)
        
        return unique_entities
    
    def get_term_info(self, term: str) -> Optional[Dict]:
        """Получить информацию о термине."""
        for tier_key, tier_data in self.sarsekenov_terms.items():
            if term in tier_data.get('terms', []):
                return {
                    'term': term,
                    'tier': tier_key,
                    'level': tier_data.get('level'),
                    'description': tier_data.get('description')
                }
        return None
    
    def replace_forbidden_terms(self, text: str) -> str:
        """Заменить запрещенные термины на эквиваленты Сарсекенова."""
        replacements = self.forbidden_config.get('replacements', {})
        
        result = text
        for forbidden, replacement in replacements.items():
            pattern = r'\b' + re.escape(forbidden) + r'\b'
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        return result


def validate_block(text: str, validator: Optional[TerminologyValidator] = None) -> ValidationResult:
    """
    Utility функция для быстрой валидации блока текста.
    """
    if validator is None:
        validator = TerminologyValidator()
    
    return validator.validate_text(text)
