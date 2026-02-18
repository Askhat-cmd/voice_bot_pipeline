"""
SD Labeler - автоматическая SD-разметка чанков при подготовке БД.
Вызывается в pipeline_orchestrator.py после нарезки текста на блоки.
Каждый блок получает sd_metadata: уровень СД, сложность, тон.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from openai import OpenAI

logger = logging.getLogger(__name__)


SD_LABELER_SYSTEM_PROMPT = """
Ты - эксперт по теории Спиральной Динамики Клэра Грейвза.
Тебе дан фрагмент психологического или развивающего текста.

Определи, к какому уровню сознания ОБРАЩАЕТСЯ этот текст
(не какой уровень описывает, а какому читателю он подходит).

КРИТЕРИИ УРОВНЕЙ:
- BEIGE: выживание, базовые страхи, физическая безопасность
- PURPLE: традиции, семья важнее личного, магическое мышление, коллектив
- RED: сила, власть, немедленное действие, ego-центризм
- BLUE: правила, долг, вина, дисциплина, иерархия
- ORANGE: успех, цели, эффективность, логика, рациональность
- GREEN: чувства, эмпатия, принятие, сообщество, диалог
- YELLOW: паттерны, системы, метанаблюдение, интеграция противоречий
- TURQUOISE: единство всего, трансличностное, холизм

ПРАВИЛО: при неуверенности - выбери уровень НИЖЕ (безопаснее).

Верни ТОЛЬКО JSON без пояснений:
{
  "sd_level": "GREEN",
  "sd_secondary": "YELLOW",
  "complexity_score": 4,
  "emotional_tone": "validating",
  "requires_prior_concepts": false,
  "reasoning": "краткое объяснение в 1 предложении"
}

emotional_tone: validating / challenging / educational / neutral / grounding
complexity_score: 1 (очень просто) - 10 (требует глубокой подготовки)
"""


class SDLabeler:
    """Автоматическая SD-разметка блоков через LLM."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.1,
        max_tokens: int = 200,
        max_chars: int = 1500,
    ) -> None:
        self.client = OpenAI()
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_chars = max_chars

    def label_block(self, block_content: str, block_id: str = "") -> Dict[str, Any]:
        """Разметить один блок по уровню СД."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "system", "content": SD_LABELER_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Текст блока:\n\n{(block_content or '')[: self.max_chars]}"},
                ],
            )
            raw = (response.choices[0].message.content or "").strip()
            result = json.loads(raw)
            logger.info(
                f"[SD_LABELER] block_id={block_id} -> {result.get('sd_level')} "
                f"(complexity={result.get('complexity_score')})"
            )
            return result
        except json.JSONDecodeError as exc:
            logger.warning(f"[SD_LABELER] JSON parse error for block {block_id}: {exc}")
            return self._default_label()
        except Exception as exc:
            logger.error(f"[SD_LABELER] error for block {block_id}: {exc}")
            return self._default_label()

    def label_blocks_batch(self, blocks: List[Dict[str, Any]], author_id: str = "") -> List[Dict[str, Any]]:
        """
        Разметить список блоков. Добавляет поле sd_metadata к каждому блоку.

        Args:
            blocks: список dict с полями block_id, content
            author_id: ID автора из конфига authors/
        Returns:
            blocks с добавленным полем sd_metadata
        """
        labeled: List[Dict[str, Any]] = []
        for i, block in enumerate(blocks):
            sd_data = self.label_block(
                block_content=block.get("content", ""),
                block_id=block.get("block_id", str(i)),
            )
            block["sd_metadata"] = {
                **sd_data,
                "author_id": author_id,
                "labeled_by": "sd_labeler_v1",
            }
            labeled.append(block)
            if (i + 1) % 10 == 0:
                logger.info(f"[SD_LABELER] Progress: {i + 1}/{len(blocks)} blocks labeled")
        return labeled

    @staticmethod
    def _default_label() -> Dict[str, Any]:
        """Безопасное значение при ошибке."""
        return {
            "sd_level": "GREEN",
            "sd_secondary": None,
            "complexity_score": 5,
            "emotional_tone": "neutral",
            "requires_prior_concepts": False,
            "reasoning": "default fallback on error",
        }
