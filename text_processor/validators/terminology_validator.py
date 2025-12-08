#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Терминологический валидатор для учения Саламата Сарсекенова.
Это ФУНДАМЕНТ всей системы - ни один текст не обрабатывается без валидации.

Поддерживает 4 режима валидации:
- smart (рекомендуемый): только проверка плотности ≥15%
- soft: пропускает forbidden terms в объяснительном контексте
- strict: блокирует любые forbidden terms
- off: только проверка плотности, никаких ограничений
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
import logging

# Загрузка переменных окружения
try:
    from dotenv import load_dotenv
    load_dotenv()
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

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
    is_contextual: bool = False  # True если forbidden terms в объяснительном контексте


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
        
        # Загрузка настроек режима валидации из .env
        self.validation_mode = os.getenv('VALIDATION_MODE', 'smart')
        self.min_density_smart = float(os.getenv('MIN_SARSEKENOV_DENSITY_SMART', '0.15'))
        self.min_density_strict = float(os.getenv('MIN_SARSEKENOV_DENSITY_STRICT', '0.25'))
        self.contextual_threshold = float(os.getenv('CONTEXTUAL_DENSITY_THRESHOLD', '0.35'))
        
        # Загрузка конфигурации терминологии
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
        logger.info(f"Validation mode: {self.validation_mode}")
        logger.info(f"Min density (smart): {self.min_density_smart:.0%}, (strict): {self.min_density_strict:.0%}")
        logger.info(f"Pymorphy available: {PYMORPHY_AVAILABLE}")
    
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
        min_density: Optional[float] = None,
        validation_mode: Optional[str] = None
    ) -> ValidationResult:
        """
        Валидация текста на соответствие стандартам Сарсекенова.
        
        Поддерживает 4 режима:
        - smart (рекомендуемый): только проверка плотности ≥15%, forbidden игнорируются
        - soft: пропускает forbidden в объяснительном контексте
        - strict: блокирует любые forbidden terms
        - off: только проверка плотности
        
        Args:
            text: Текст для валидации
            min_density: Минимальная плотность (None = автоопределение по режиму)
            validation_mode: Режим валидации (None = из настроек)
        
        Returns:
            ValidationResult с детальной информацией
        """
        
        # Определение режима валидации
        mode = validation_mode or self.validation_mode
        
        # Определение минимальной плотности в зависимости от режима
        if min_density is None:
            if mode in ["smart", "off"]:
                min_density = self.min_density_smart  # 0.15
            else:
                min_density = self.min_density_strict  # 0.25
        
        logger.debug(f"Validating text with mode={mode}, min_density={min_density:.0%}")
        
        # ШАГ 1: Расчёт плотности терминов Сарсекенова (ВСЕГДА)
        density_metrics = self._calculate_density(text)
        
        # ШАГ 2: Извлечение сущностей (ВСЕГДА)
        entities = self._extract_entities(text)
        
        # ШАГ 3: Поиск forbidden terms (ВСЕГДА - для статистики)
        forbidden_found = self._find_forbidden_terms(text)
        
        # ШАГ 4: В STRICT режиме сначала проверяем forbidden terms
        if mode == "strict" and forbidden_found:
            logger.warning(f"Text rejected (strict): forbidden terms found: {forbidden_found}")
            return ValidationResult(
                is_valid=False,
                reason=f"❌ Найдены запрещённые термины: {', '.join(forbidden_found)}",
                metrics=density_metrics,
                forbidden_terms_found=forbidden_found,
                sarsekenov_entities=entities,
                is_contextual=False
            )
        
        # ШАГ 5: Проверка минимальной плотности (ВСЕГДА)
        if density_metrics['density'] < min_density:
            logger.info(f"Text rejected: density {density_metrics['density']:.1%} < {min_density:.1%}")
            return ValidationResult(
                is_valid=False,
                reason=f"Недостаточная плотность терминов Сарсекенова: {density_metrics['density']:.1%} < {min_density:.1%}",
                metrics=density_metrics,
                forbidden_terms_found=forbidden_found,
                sarsekenov_entities=entities,
                is_contextual=False
            )
        
        # РЕЖИМ: SMART или OFF
        if mode in ["smart", "off"]:
            # SMART/OFF: Игнорируем forbidden terms полностью
            logger.info(f"Text accepted (mode={mode}): density {density_metrics['density']:.1%}, forbidden terms ignored")
            return ValidationResult(
                is_valid=True,
                reason=f"✅ Валидный текст Сарсекенова (плотность: {density_metrics['density']:.1%}, режим: {mode})",
                metrics=density_metrics,
                forbidden_terms_found=forbidden_found,  # Сохраняем для статистики
                sarsekenov_entities=entities,
                is_contextual=False
            )
        
        # РЕЖИМ: STRICT - уже проверен выше (шаг 4), если дошли сюда - forbidden не найдены
        elif mode == "strict":
            # Forbidden terms не найдены, плотность достаточная
            pass  # Переходим к успешной валидации
        
        # РЕЖИМ: SOFT
        elif mode == "soft":
            if forbidden_found:
                is_contextual = self._is_contextual_usage(
                    text,
                    forbidden_found,
                    density_metrics
                )
                
                if not is_contextual:
                    logger.warning(f"Text rejected (soft): forbidden terms without context")
                    return ValidationResult(
                        is_valid=False,
                        reason=f"❌ Найдены запрещённые термины вне контекста: {', '.join(forbidden_found)}",
                        metrics=density_metrics,
                        forbidden_terms_found=forbidden_found,
                        sarsekenov_entities=entities,
                        is_contextual=False
                    )
                else:
                    logger.info(f"Text accepted (soft): forbidden terms in explanatory context")
                    return ValidationResult(
                        is_valid=True,
                        reason=f"✅ Валидный текст (forbidden terms в контексте объяснения)",
                        metrics=density_metrics,
                        forbidden_terms_found=forbidden_found,
                        sarsekenov_entities=entities,
                        is_contextual=True
                    )
        
        # По умолчанию: Успешная валидация
        logger.info(f"Text accepted: density {density_metrics['density']:.1%}")
        return ValidationResult(
            is_valid=True,
            reason=f"✅ Валидный текст Сарсекенова (плотность: {density_metrics['density']:.1%})",
            metrics=density_metrics,
            forbidden_terms_found=forbidden_found,
            sarsekenov_entities=entities,
            is_contextual=False
        )
    
    def _is_contextual_usage(
        self,
        text: str,
        forbidden_terms: List[str],
        density_metrics: Dict
    ) -> bool:
        """
        Проверка, используются ли forbidden terms в объяснительном контексте.
        
        Критерии контекстного использования:
        1. Высокая плотность терминов Сарсекенова (≥35%)
        2. Рядом есть термины-замены
        3. Присутствуют маркеры объяснения
        
        Returns:
            True если использование контекстное/объяснительное
        """
        
        # Критерий 1: Высокая плотность = вероятно объяснительный контекст
        if density_metrics['density'] >= self.contextual_threshold:
            return True
        
        # Критерий 2: Термины-замены рядом с forbidden
        replacements = self.forbidden_config.get('replacements', {})
        
        for forbidden in forbidden_terms:
            replacement = replacements.get(forbidden)
            if replacement and replacement.lower() in text.lower():
                # Проверка близости (в пределах 100 символов)
                forbidden_pos = text.lower().find(forbidden.lower())
                replacement_pos = text.lower().find(replacement.lower())
                
                if abs(forbidden_pos - replacement_pos) < 100:
                    return True
        
        # Критерий 3: Маркеры объяснения
        explanation_markers = [
            "имею в виду", "на самом деле", "это называется",
            "вместо", "заменить на", "правильнее говорить",
            "не", "отличие", "разница", "объясняю"
        ]
        
        text_lower = text.lower()
        for marker in explanation_markers:
            if marker in text_lower:
                # Проверка близости маркера к forbidden term
                for forbidden in forbidden_terms:
                    marker_pos = text_lower.find(marker)
                    forbidden_pos = text_lower.find(forbidden.lower())
                    
                    if abs(marker_pos - forbidden_pos) < 50:
                        return True
        
        return False
    
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
