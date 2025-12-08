"""
Extractors for Sarsekenov knowledge extraction system.

Этот модуль содержит экстракторы для извлечения структурированных знаний
из лекций Саламата Сарсекенова.
"""

from text_processor.extractors.neurostalking_pattern_extractor import (
    NeurostalkingPatternExtractor,
    NeurostalkingPattern,
    extract_patterns
)

__all__ = [
    'NeurostalkingPatternExtractor',
    'NeurostalkingPattern',
    'extract_patterns',
]
