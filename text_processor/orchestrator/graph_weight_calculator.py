"""
GraphWeightCalculator - вычисление весов связей в графе знаний.

Вычисляет веса связей между концептами на основе:
- Co-occurrence frequency (частота совместной встречаемости)
- Расстояние между концептами в тексте
- PMI (Pointwise Mutual Information)
"""

import math
from typing import List, Dict, Tuple
from collections import defaultdict


class GraphWeightCalculator:
    """
    Вычисляет веса связей между концептами в графе знаний.
    """
    
    def __init__(self):
        self.concept_positions = {}  # {concept: [(block_idx, word_idx)]}
        self.cooccurrence_matrix = {}  # {(concept1, concept2): count}
        
    def analyze_block(self, block_content: str, entities: List[str], block_idx: int):
        """
        Анализирует блок текста и сохраняет позиции концептов.
        
        Args:
            block_content: Текст блока
            entities: Список сущностей (концептов) в блоке
            block_idx: Индекс блока
        """
        words = block_content.lower().split()
        
        # Найти позиции каждого концепта
        for entity in entities:
            entity_lower = entity.lower()
            positions = []
            
            # Ищем концепт в словах (частичное совпадение)
            for i, word in enumerate(words):
                if entity_lower in word or word in entity_lower:
                    positions.append((block_idx, i))
            
            if entity not in self.concept_positions:
                self.concept_positions[entity] = []
            self.concept_positions[entity].extend(positions)
        
        # Подсчитать co-occurrence (концепты в одном блоке)
        unique_entities = list(set(entities))
        for i, entity1 in enumerate(unique_entities):
            for entity2 in unique_entities[i+1:]:
                pair = tuple(sorted([entity1, entity2]))
                self.cooccurrence_matrix[pair] = self.cooccurrence_matrix.get(pair, 0) + 1
    
    def calculate_pmi(self, entity1: str, entity2: str, total_blocks: int) -> float:
        """
        Вычисляет Pointwise Mutual Information между двумя концептами.
        
        Args:
            entity1: Первый концепт
            entity2: Второй концепт
            total_blocks: Общее количество блоков
            
        Returns:
            PMI score (0.0 - 1.0, нормализованный)
        """
        if total_blocks == 0:
            return 0.0
        
        pair = tuple(sorted([entity1, entity2]))
        cooccur = self.cooccurrence_matrix.get(pair, 0)
        
        if cooccur == 0:
            return 0.0
        
        # Количество блоков, где встречается каждый концепт
        blocks_with_entity1 = len(set(
            pos[0] for pos in self.concept_positions.get(entity1, [])
        ))
        blocks_with_entity2 = len(set(
            pos[0] for pos in self.concept_positions.get(entity2, [])
        ))
        
        if blocks_with_entity1 == 0 or blocks_with_entity2 == 0:
            return 0.0
        
        # Вероятности
        p_xy = cooccur / total_blocks  # Совместная вероятность
        p_x = blocks_with_entity1 / total_blocks  # Вероятность entity1
        p_y = blocks_with_entity2 / total_blocks  # Вероятность entity2
        
        if p_x * p_y == 0:
            return 0.0
        
        # PMI = log2(P(x,y) / (P(x) * P(y)))
        pmi = math.log2(p_xy / (p_x * p_y))
        
        # Нормализация от 0 до 1
        # PMI может быть отрицательным (независимость) или положительным (зависимость)
        # Используем сигмоидную нормализацию для диапазона [-10, 10] -> [0, 1]
        normalized_pmi = 1 / (1 + math.exp(-pmi / 2))
        
        return normalized_pmi
    
    def calculate_distance_weight(self, entity1: str, entity2: str) -> float:
        """
        Вычисляет вес на основе среднего расстояния между концептами.
        Чем ближе концепты встречаются в тексте, тем выше вес.
        
        Args:
            entity1: Первый концепт
            entity2: Второй концепт
            
        Returns:
            Weight (0.0 - 1.0)
        """
        positions1 = self.concept_positions.get(entity1, [])
        positions2 = self.concept_positions.get(entity2, [])
        
        if not positions1 or not positions2:
            return 0.0
        
        min_distances = []
        for pos1 in positions1:
            for pos2 in positions2:
                # Только если в одном блоке
                if pos1[0] == pos2[0]:  # Один и тот же блок
                    # Расстояние в словах (исправление ошибки из гайда)
                    distance = abs(pos1[1] - pos2[1])
                    min_distances.append(distance)
        
        if not min_distances:
            return 0.3  # Базовый вес для концептов из разных блоков
        
        avg_distance = sum(min_distances) / len(min_distances)
        
        # Чем меньше расстояние, тем выше вес
        # Используем экспоненциальное затухание
        # 50 слов - характерная длина для близости концептов
        weight = math.exp(-avg_distance / 50)
        
        return min(weight, 1.0)  # Ограничиваем максимум 1.0
    
    def calculate_combined_weight(self, entity1: str, entity2: str, total_blocks: int) -> float:
        """
        Вычисляет итоговый вес связи как комбинацию метрик.
        
        Args:
            entity1: Первый концепт
            entity2: Второй концепт
            total_blocks: Общее количество блоков
            
        Returns:
            Combined weight (0.0 - 1.0)
        """
        pair = tuple(sorted([entity1, entity2]))
        cooccur_count = self.cooccurrence_matrix.get(pair, 0)
        
        if cooccur_count == 0:
            return 0.1  # Минимальный вес для связей без co-occurrence
        
        # Нормализованная частота co-occurrence
        max_cooccur = max(self.cooccurrence_matrix.values()) if self.cooccurrence_matrix else 1
        freq_weight = cooccur_count / max_cooccur
        
        # PMI
        pmi_weight = self.calculate_pmi(entity1, entity2, total_blocks)
        
        # Distance weight
        dist_weight = self.calculate_distance_weight(entity1, entity2)
        
        # Комбинированный вес (взвешенная сумма)
        combined = (
            0.4 * freq_weight +  # 40% - частота
            0.3 * pmi_weight +   # 30% - PMI
            0.3 * dist_weight    # 30% - расстояние
        )
        
        # Ограничиваем диапазон [0.1, 1.0]
        combined = max(0.1, min(1.0, combined))
        
        return round(combined, 3)

