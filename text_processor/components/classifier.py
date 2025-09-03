from __future__ import annotations

from typing import List, Tuple


class Classifier:
    """Collection of classification utilities."""

    def detect_speaker(self, content: str) -> str:
        """Determine the speaker of the block based on heuristics."""
        if ">>" in content:
            return "mixed"
        sarsekenov_markers = [
            "понимаете", "заметили", "чувствуете", "прямо сейчас",
            "повторяюсь", "вот смотрите", "штрих-код бросаю",
            "к примеру", "мало того", "опять же", "видите ли"
        ]
        content_lower = content.lower()
        marker_count = sum(1 for marker in sarsekenov_markers if marker in content_lower)
        return "sarsekenov" if marker_count >= 2 else "participant"

    def detect_has_dialogue(self, blocks: List[dict], full_text: str | None = None) -> bool:
        """Return True if document appears to contain dialogue."""
        if full_text:
            if ">>" in full_text:
                return True
            import re
            if re.search(r"\?\s*$", full_text, re.MULTILINE):
                return True
            dialogue_markers = [
                "можете спросить", "да, вопрос", "вопрос есть",
                "спрашива", "отвеча", "а если", "можно ли",
                "как же", "что делать", "почему так"
            ]
            full_text_lower = full_text.lower()
            for marker in dialogue_markers:
                if marker in full_text_lower:
                    return True
        for block in blocks:
            content = block.get("content", "")
            block_type = block.get("block_type", "")
            if ">>" in content:
                return True
            if block_type in ["dialogue", "question"]:
                return True
            if content.strip().endswith("?"):
                return True
            if any(marker in content.lower() for marker in [
                "можете спросить", "вопрос", "спрашива", "отвеча"
            ]):
                return True
        return False

    def determine_collection_target(self, main_topics: List[str], keywords: List[str],
                                    has_dialogue: bool, blocks: List[dict]) -> Tuple[str, float]:
        """Classify collection target for the document."""
        all_keywords = main_topics + keywords
        keywords_str = " ".join(all_keywords).lower()
        all_content = " ".join([block.get("content", "") for block in blocks]).lower()
        if has_dialogue:
            return "dialogue_sessions", 0.95
        collection_markers = {
            "neurostalking_basics": [
                "нейросталкинг", "неосталкинг", "основы", "концепция",
                "определение", "терминология", "система", "метанаблюдение",
                "поле внимания", "свободное внимание", "сталкинг ума"
            ],
            "meditation_practices": [
                "медитация", "практика", "упражнение", "дыхание", "пранаяма",
                "центрирование", "заземление", "техника", "випашьяна", "шаматха",
                "наблюдение за наблюдающим", "исследование поля внимания"
            ],
            "healing_transformation": [
                "исцеление", "трансформация", "преодоление", "боль", "страдание",
                "обида", "прощение", "принятие", "интеграция", "освобождение",
                "отпускание", "сдача", "капитуляция", "смирение"
            ],
            "advanced_concepts": [
                "пробуждение", "просветление", "сознание", "абсолют", "бытие",
                "сущность", "божественность", "мудрость", "единство", "недуальность",
                "чистое сознание", "присутствие бытия", "истина"
            ],
            "psychological_states": [
                "состояние", "эмоция", "чувство", "переживание", "настроение",
                "радость", "счастье", "печаль", "гнев", "страх", "тревога",
                "покой", "умиротворение", "блаженство", "экстаз"
            ],
            "spiritual_development": [
                "развитие", "эволюция", "рост", "созревание", "прогресс",
                "самопознание", "самоисследование", "самореализация",
                "духовность", "духовный путь", "путь", "практикующий"
            ]
        }
        keyword_scores = {}
        for collection, markers in collection_markers.items():
            score = sum(1 for marker in markers if marker in keywords_str)
            keyword_scores[collection] = score
        content_scores = {}
        for collection, markers in collection_markers.items():
            score = sum(1 for marker in markers if marker in all_content)
            content_scores[collection] = score * 0.5
        total_scores = {}
        for collection in collection_markers.keys():
            total_scores[collection] = keyword_scores[collection] + content_scores[collection]
        practice_terms = ["упражнение", "техника", "метод", "способ", "практика"]
        practice_count = sum(1 for term in practice_terms if term in keywords_str)
        if practice_count >= 2:
            total_scores["meditation_practices"] += 2.0
        emotion_terms = ["чувство", "эмоция", "переживание", "состояние"]
        emotion_count = sum(1 for term in emotion_terms if term in keywords_str)
        if emotion_count >= 2:
            total_scores["psychological_states"] += 2.0
        deep_terms = ["сущность", "абсолют", "бытие", "истина", "божественность"]
        deep_count = sum(1 for term in deep_terms if term in keywords_str)
        if deep_count >= 1:
            total_scores["advanced_concepts"] += 2.0
        if max(total_scores.values()) > 0:
            best_collection = max(total_scores.keys(), key=lambda k: total_scores[k])
            best_score = total_scores[best_collection]
            total_possible_score = sum(total_scores.values())
            if has_dialogue:
                confidence = 0.95
            elif total_possible_score == 0:
                confidence = 0.3
            else:
                confidence = min(0.95, max(0.4, best_score / total_possible_score))
                if best_score >= 5:
                    confidence = min(0.95, confidence + 0.1)
                elif best_score >= 3:
                    confidence = min(0.9, confidence + 0.05)
            return best_collection, round(confidence, 2)
        return "neurostalking_basics", 0.3
