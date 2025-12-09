#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Case Study Extractor
Извлечение структурированных кейсов из текста.
"""

import json
from openai import OpenAI


class CaseStudyExtractor:
    """
    Извлечение структурированных кейсов (реальных случаев применения практик).
    """

    def __init__(self, client: OpenAI, model: str = "gpt-4o-mini"):
        self.client = client
        self.model = model

    def extract(self, block_content: str) -> dict:
        """
        Возвращает структуру вида:
        {
          "case_studies": [
            {
              "id": "case_local_1",
              "situation": "...",
              "root_cause": "...",
              "applied_practices": [...],
              "process": ["шаг 1", "шаг 2", ...],
              "outcome": "...",
              "lessons": "...",
              "related_concepts": [...]
            }
          ]
        }
        """

        prompt = f"""
Ты — эксперт по анализу психологических практик и их применению.

Проанализируй текст и найди РЕАЛЬНЫЕ КЕЙСЫ (примеры ситуаций, случаев применения практик, историй).

Для каждого кейса определи:
1. id: уникальный идентификатор (например, "case_local_1")
2. situation: описание ситуации/контекста
3. root_cause: корневая причина проблемы или исходное состояние
4. applied_practices: список примененных практик/техник
5. process: последовательность шагов процесса (массив строк)
6. outcome: результат/исход применения практик
7. lessons: выводы и уроки из этого кейса
8. related_concepts: связанные концепции из текста

Формат ответа (строгий JSON):
{{
  "case_studies": [
    {{
      "id": "case_local_1",
      "situation": "описание ситуации",
      "root_cause": "корневая причина",
      "applied_practices": ["практика1", "практика2"],
      "process": ["шаг 1", "шаг 2", "шаг 3"],
      "outcome": "результат",
      "lessons": "выводы и уроки",
      "related_concepts": ["концепт1", "концепт2"]
    }}
  ]
}}

Если явных кейсов нет — верни "case_studies": [].

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
            data = {"case_studies": []}

        data.setdefault("case_studies", [])
        return data


