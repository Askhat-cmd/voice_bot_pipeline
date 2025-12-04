#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Causal Chain Extractor
Извлечение причинно-следственных цепочек психологических процессов
и точек вмешательства.
"""

import json
from openai import OpenAI


class CausalChainExtractor:
    """
    Извлечение причинно-следственных цепочек психологических процессов
    и точек вмешательства.
    """

    def __init__(self, client: OpenAI, model: str = "gpt-4o-mini"):
        self.client = client
        self.model = model

    def extract(self, block_content: str) -> dict:
        """
        Возвращает структуру вида:
        {
          "processes": [
            {
              "name": "короткое название процесса",
              "steps": [
                {"step": 1, "event": "...", "description": "..."},
                ...
              ],
              "intervention_points": [
                {
                  "after_step": 2,
                  "practice": "метанаблюдение",
                  "effect": "что меняется",
                  "related_concepts": ["осознавание", "паттерны"]
                }
              ]
            }
          ]
        }
        """

        prompt = f"""
Ты — специалист по когнитивно-поведенческим и процессуально-ориентированным подходам.

Проанализируй текст и найди ПСИХОЛОГИЧЕСКИЕ ПРОЦЕССЫ в формате причинно-следственных цепочек.

Для каждого процесса определи:
1. Краткое название процесса (name).
2. Последовательность шагов (steps):
   - step: номер шага (1, 2, 3, ...)
   - event: краткое событие/этап
   - description: более подробное описание
3. Точки вмешательства (intervention_points):
   - after_step: после какого шага можно вмешаться
   - practice: какая практика/инструмент может быть применена (из текста, если упоминается)
   - effect: в чем суть влияния этой практики
   - related_concepts: какие концепции из текста связаны с этой точкой

Формат ответа (строгий JSON):
{{
  "processes": [
    {{
      "name": "краткое название процесса",
      "steps": [
        {{"step": 1, "event": "событие", "description": "описание"}},
        {{"step": 2, "event": "событие", "description": "описание"}}
      ],
      "intervention_points": [
        {{
          "after_step": 1,
          "practice": "название практики",
          "effect": "результат применения",
          "related_concepts": ["концепт1", "концепт2"]
        }}
      ]
    }}
  ]
}}

Если явных процессов нет — верни "processes": [].

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
            data = {"processes": []}

        data.setdefault("processes", [])
        return data

