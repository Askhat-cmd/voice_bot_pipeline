#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prerequisite Extractor
Извлечение предпосылок и последовательности обучения.
"""

import json
from openai import OpenAI


class PrerequisiteExtractor:
    """
    Извлечение предпосылок и последовательности обучения для практик и концепций.
    """

    def __init__(self, client: OpenAI, model: str = "gpt-4o-mini"):
        self.client = client
        self.model = model

    def extract(self, block_content: str) -> dict:
        """
        Возвращает структуру вида:
        {
          "prerequisites": [
            {
              "concept": "основа осознавания",
              "level": "beginner",
              "why_needed": "..."
            }
          ],
          "recommended_sequence": [
            "осознавание → метанаблюдение → распознавание паттернов → работа с паттернами"
          ],
          "common_mistakes": ["..."]
        }
        """

        prompt = f"""
Ты — эксперт по структурированию обучения и педагогике.

Проанализируй текст и найди информацию о ПРЕДПОСЫЛКАХ и ПОСЛЕДОВАТЕЛЬНОСТИ ОБУЧЕНИЯ.

Определи:
1. prerequisites: что нужно освоить ДО сложных практик
   - concept: название концепта/практики-предпосылки
   - level: уровень сложности (beginner, intermediate, advanced)
   - why_needed: почему это необходимо
2. recommended_sequence: рекомендуемая последовательность обучения (массив строк)
3. common_mistakes: типичные ошибки при изучении/применении

Формат ответа (строгий JSON):
{{
  "prerequisites": [
    {{
      "concept": "основа осознавания",
      "level": "beginner",
      "why_needed": "описание почему это нужно"
    }}
  ],
  "recommended_sequence": [
    "осознавание → метанаблюдение → распознавание паттернов → работа с паттернами"
  ],
  "common_mistakes": [
    "описание типичной ошибки"
  ]
}}

Если информации нет — верни пустые списки.

Текст:
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
            data = {
                "prerequisites": [],
                "recommended_sequence": [],
                "common_mistakes": []
            }

        # Гарантия наличия всех ключей
        for key in ["prerequisites", "recommended_sequence", "common_mistakes"]:
            data.setdefault(key, [])

        return data


