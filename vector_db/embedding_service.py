#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Embedding Service for creating vector embeddings using Sentence-Transformers
"""

import logging
import os
from typing import List, Optional

from sentence_transformers import SentenceTransformer
from env_utils import load_env

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Сервис для создания эмбеддингов через Sentence-Transformers"""
    
    def __init__(self, model: Optional[str] = None, device: Optional[str] = None):
        """
        Инициализация сервиса эмбеддингов
        
        Args:
            model: Модель Sentence-Transformers (если не указана, берется из SENTENCE_TRANSFORMERS_MODEL в .env, иначе intfloat/multilingual-e5-large)
            device: Устройство для выполнения ('cuda', 'cpu', 'mps' или None для автоматического выбора)
        """
        # Загружаем окружение
        load_env()
        
        # Определяем модель: сначала из параметра, потом из env, потом дефолт
        if model is None:
            model = os.getenv("SENTENCE_TRANSFORMERS_MODEL", "intfloat/multilingual-e5-large")
        
        # Определяем устройство: сначала из параметра, потом из env, потом автоматически
        if device is None:
            device = os.getenv("SENTENCE_TRANSFORMERS_DEVICE", None)  # None = автоматический выбор
        
        logger.info(f"⏳ Загрузка модели Sentence-Transformers: {model}")
        if device:
            logger.info(f"   Устройство: {device} (явно указано)")
        else:
            logger.info(f"   Устройство: автоматический выбор (GPU если доступен, иначе CPU)")
        
        try:
            self.model = SentenceTransformer(model, device=device)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            actual_device = str(next(self.model.parameters()).device)
            logger.info(f"✅ EmbeddingService инициализирован с моделью: {model}, размерность: {self.embedding_dim}, устройство: {actual_device}")
        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке модели {model}: {e}")
            raise RuntimeError(f"Не удалось загрузить модель Sentence-Transformers: {e}") from e
    
    def create_embedding(self, text: str) -> List[float]:
        """
        Создает эмбеддинг для одного текста
        
        Args:
            text: Текст для векторизации
            
        Returns:
            Список чисел (вектор эмбеддинга)
        """
        if not text or not text.strip():
            logger.warning("Пустой текст передан для создания эмбеддинга")
            return [0.0] * self.embedding_dim
        
        text = text.strip()
        
        try:
            # Sentence-Transformers автоматически обрабатывает длинные тексты
            # Модель сама обрезает текст если он слишком длинный (обычно до 512 токенов)
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Ошибка при создании эмбеддинга: {e}")
            raise RuntimeError(f"Не удалось создать эмбеддинг: {e}") from e
    
    def create_embeddings_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Создает эмбеддинги для списка текстов (эффективная батч-обработка)
        
        Args:
            texts: Список текстов для векторизации
            batch_size: Размер батча для обработки (по умолчанию 32)
            
        Returns:
            Список векторов эмбеддингов
        """
        if not texts:
            return []
        
        # Фильтруем пустые тексты и сохраняем индексы
        valid_texts = []
        valid_indices = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text.strip())
                valid_indices.append(i)
        
        if not valid_texts:
            logger.warning("Все тексты пустые")
            return [[0.0] * self.embedding_dim] * len(texts)
        
        logger.info(f"📦 Обработка {len(valid_texts)} текстов (батч-режим, batch_size={batch_size})")
        
        try:
            # Sentence-Transformers эффективно обрабатывает батчи локально
            embeddings = self.model.encode(
                valid_texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            
            # Восстанавливаем порядок с учетом пустых текстов
            result = []
            embedding_idx = 0
            for i, original_text in enumerate(texts):
                if i in valid_indices:
                    result.append(embeddings[embedding_idx].tolist())
                    embedding_idx += 1
                else:
                    result.append([0.0] * self.embedding_dim)  # Пустые тексты получают нулевые векторы
            
            logger.info(f"✅ Обработано {len(valid_texts)} текстов")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при создании эмбеддингов батчем: {e}")
            raise RuntimeError(f"Не удалось создать эмбеддинги: {e}") from e
    
    @property
    def dimension(self) -> int:
        """Возвращает размерность эмбеддингов"""
        return self.embedding_dim
