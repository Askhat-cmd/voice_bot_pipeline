import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
import pytest

from text_processor.components.cleaner import Cleaner
from text_processor.components.classifier import Classifier
from text_processor.components.metadata_calculator import MetadataCalculator

def test_cleaner_pipeline():
    cleaner = Cleaner()
    text = "Ээ, привет  ,  вот вот это это текст."
    cleaned = cleaner.clean(text)
    assert "Ээ" not in cleaned
    assert "вот" in cleaned
    assert "это" in cleaned


def test_classifier_dialogue_detection():
    classifier = Classifier()
    blocks = [{"content": ">> Привет", "block_type": "dialogue"}]
    assert classifier.detect_has_dialogue(blocks, ">> Привет")
    assert classifier.detect_speaker("понимаете, вот смотрите") == "sarsekenov"


def test_metadata_calculation():
    classifier = Classifier()
    calculator = MetadataCalculator(classifier)
    blocks = [
        {"content": ">> вопрос?", "block_type": "dialogue", "keywords": ["нейросталкинг"], "complexity_score": 5.0},
        {"content": "ответ", "block_type": "monologue", "keywords": ["нейросталкинг"], "complexity_score": 5.0}
    ]
    metadata = calculator.calculate_document_metadata(blocks, ">> вопрос? ответ")
    assert metadata["has_dialogue"] is True
    assert metadata["participant_count"] == 1
    assert metadata["duration_minutes"] == 0
