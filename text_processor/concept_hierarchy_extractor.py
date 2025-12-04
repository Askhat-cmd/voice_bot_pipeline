#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Concept Hierarchy Extractor
Извлечение иерархии концептов (root/domain/practice/technique/exercise)
и их отношений.
"""

import json
from openai import OpenAI


class ConceptHierarchyExtractor:
    """
    Извлечение иерархии концептов (root/domain/practice/technique/exercise)
    и их отношений.
    """

    def __init__(self, client: OpenAI, model: str = "gpt-4o-mini"):
        self.client = client
        self.model = model

    def extract(self, block_content: str, known_entities: list[str]) -> dict:
        """
        known_entities — список graph_entities уже извлеченных для блока.

        Возвращает:
        {
          "concepts": [
            {
              "name": "осознавание",
              "level": "domain",
              "parent": "нейросталкинг",
              "relationship": "is_core_component_of"
            },
            ...
          ]
        }
        """

        entities_str = ", ".join(known_entities) if known_entities else "нет"

        prompt = f"""
Ты — эксперт по систематизации знаний.

У тебя есть список концептов (graph_entities): [{entities_str}].

Твоя задача — определить ИЕРАРХИЮ этих концептов в контексте текста.

Уровни:
- "root": корневые учения/подходы (например, "нейросталкинг")
- "domain": доменные понятия (например, "осознавание", "трансформация")
- "practice": практики и методы (например, "метанаблюдение")
- "technique": конкретные техники (например, "наблюдение за умом", "ведение дневника")
- "exercise": отдельные упражнения (например, "5 минут наблюдения утром")

Для каждого концепта определи:
- name: название (как в graph_entities или из текста)
- level: один из [root, domain, practice, technique, exercise]
- parent: родительский концепт (или null, если root)
- relationship: тип связи с родителем
    - "is_core_component_of"
    - "is_part_of"
    - "is_technique_for"
    - "enables"
    - "requires"

Формат ответа (строгий JSON):

{{
  "concepts": [
    {{
      "name": "осознавание",
      "level": "domain",
      "parent": "нейросталкинг",
      "relationship": "is_core_component_of"
    }}
  ]
}}

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
            data = {"concepts": []}

        data.setdefault("concepts", [])
        return data

