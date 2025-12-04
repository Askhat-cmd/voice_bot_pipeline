#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Safety Information Extractor
Извлечение информации о безопасности, ограничениях и противопоказаниях
для практик и концепций.
"""

import json
from openai import OpenAI


class SafetyInformationExtractor:
    """
    Извлечение информации о безопасности, ограничениях и противопоказаниях
    для практик и концепций.
    """

    def __init__(self, client: OpenAI, model: str = "gpt-4o-mini"):
        self.client = client
        self.model = model

    def extract(self, block_content: str, practice_or_concept_name: str) -> dict:
        """
        Анализирует текст блока и извлекает safety-информацию.

        Возвращает словарь структуры:
        {
          "contraindications": [...],
          "limitations": [...],
          "when_to_stop": [...],
          "when_to_seek_professional_help": [...],
          "notes": [...]
        }
        """
        prompt = f"""
Ты — эксперт по психологии и безопасности психопрактик.

Проанализируй текст ниже, который относится к практике/концепции: "{practice_or_concept_name}".

Тебе нужно извлечь ИСКЛЮЧИТЕЛЬНО информацию о безопасности, если она там есть 
(либо явно, либо по смыслу, даже если не проговорена дословно).

Структура ответа (строгий JSON):

{{
  "contraindications": [
    {{
      "condition": "краткое название состояния, при котором практика противопоказана",
      "reason": "почему эта практика может быть вредна при этом состоянии",
      "alternative": "какие более мягкие или безопасные подходы можно использовать"
    }}
  ],
  "limitations": [
    "ограничение или то, чего практика делать не должна/не может"
  ],
  "when_to_stop": [
    "симптомы или состояния, при которых практику нужно прекратить немедленно"
  ],
  "when_to_seek_professional_help": [
    "описания ситуаций, когда явно нужна помощь психотерапевта/психиатра/специалиста"
  ],
  "notes": [
    "любые дополнительные замечания по безопасности, если есть"
  ]
}}

Если в тексте НЕТ информации по какому-то разделу — верни для него пустой список.

Текст для анализа:
\"\"\"{block_content}\"\"\"        
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )

            data = json.loads(response.choices[0].message.content)
        except Exception:
            # На всякий случай защита от невалидного JSON
            data = {
                "contraindications": [],
                "limitations": [],
                "when_to_stop": [],
                "when_to_seek_professional_help": [],
                "notes": [],
            }

        # Гарантия наличия всех ключей
        for key in [
            "contraindications",
            "limitations",
            "when_to_stop",
            "when_to_seek_professional_help",
            "notes",
        ]:
            data.setdefault(key, [])

        return data


