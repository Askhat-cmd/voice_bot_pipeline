# text_processor/extractors/__init__.py

# Относительные импорты (правильно)
from .safety_extractor import SafetyInformationExtractor
from .causal_chain_extractor import CausalChainExtractor
from .concept_hierarchy_extractor import ConceptHierarchyExtractor
from .case_study_extractor import CaseStudyExtractor
from .prerequisite_extractor import PrerequisiteExtractor
from .neurostalking_pattern_extractor import NeurostalkingPatternExtractor

__all__ = [
    'SafetyInformationExtractor',
    'CausalChainExtractor',
    'ConceptHierarchyExtractor',
    'CaseStudyExtractor',
    'PrerequisiteExtractor',
    'NeurostalkingPatternExtractor'
]