from __future__ import annotations

from typing import List

from .classifier import Classifier


class MetadataCalculator:
    """Utility responsible for aggregating document level metadata."""

    def __init__(self, classifier: Classifier):
        self.classifier = classifier

    def calculate_document_metadata(self, blocks: List[dict], full_text: str) -> dict:
        """Compute high level metadata for the provided blocks."""
        has_dialogue = self.classifier.detect_has_dialogue(blocks, full_text)
        main_topics = self._extract_main_topics(blocks)
        all_keywords = self._get_all_keywords(blocks)
        collection_target, routing_confidence = self.classifier.determine_collection_target(
            main_topics, all_keywords, has_dialogue, blocks
        )
        return {
            "recording_date": None,
            "lecture_type": "seminar" if has_dialogue else "lecture",
            "has_dialogue": has_dialogue,
            "main_topics": main_topics,
            "difficulty_level": self._calculate_difficulty_level(blocks),
            "collection_target": collection_target,
            "routing_confidence": routing_confidence,
            "participant_count": self._estimate_participant_count(blocks),
            "duration_minutes": self._calculate_duration_minutes(blocks),
        }

    def _extract_main_topics(self, blocks: List[dict]) -> List[str]:
        all_keywords = []
        for block in blocks:
            all_keywords.extend(block.get("keywords", []))
        keyword_counts = {}
        for keyword in all_keywords:
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
        return [kw[0] for kw in sorted_keywords[:5]]

    def _get_all_keywords(self, blocks: List[dict]) -> List[str]:
        all_keywords = []
        for block in blocks:
            all_keywords.extend(block.get("keywords", []))
        return list(set(all_keywords))

    def _calculate_difficulty_level(self, blocks: List[dict]) -> str:
        complexity_scores = [block.get("complexity_score", 5.0) for block in blocks]
        avg_complexity = sum(complexity_scores) / len(complexity_scores) if complexity_scores else 5.0
        if avg_complexity < 4.0:
            return "beginner"
        elif avg_complexity < 7.0:
            return "intermediate"
        else:
            return "advanced"

    def _estimate_participant_count(self, blocks: List[dict]) -> int | None:
        dialogue_blocks = [b for b in blocks if b.get("block_type") == "dialogue"]
        if not dialogue_blocks:
            return None
        return max(1, len(dialogue_blocks) // 2)

    def _calculate_duration_minutes(self, blocks: List[dict]) -> int | None:
        if not blocks:
            return None
        try:
            last_block = blocks[-1]
            end_time = last_block.get("end", "00:00:00")
            h, m, s = map(int, end_time.split(":"))
            return h * 60 + m + (1 if s > 0 else 0)
        except Exception:
            return None
