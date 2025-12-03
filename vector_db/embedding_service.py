#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Embedding Service for creating vector embeddings using OpenAI API
"""

import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

import tiktoken
from openai import OpenAI
from env_utils import load_env

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Сервис для создания эмбеддингов через OpenAI API с поддержкой rate limiting"""
    
    def __init__(
        self, 
        model: str = "text-embedding-3-small", 
        api_key: Optional[str] = None,
        chunk_size: int = 2048,  # OpenAI лимит: до 2048 текстов в одном запросе
        delay_between_requests: float = 15.0,  # Задержка для соблюдения RPM лимитов
        max_retries: int = 5,
        retry_delay: float = 2.0,
        max_retry_delay: float = 60.0,
        max_tokens_per_text: int = 8000,
        chunk_overlap: int = 100,
        max_workers: int = 1  # Последовательная обработка для избежания rate limits
    ):
        """
        Инициализация сервиса эмбеддингов
        
        Args:
            model: Модель OpenAI для эмбеддингов (по умолчанию text-embedding-3-small)
            api_key: API ключ OpenAI (если не указан, загружается из .env)
            chunk_size: Максимальный размер чанка для одного запроса (OpenAI лимит: до 2048 текстов)
            delay_between_requests: Задержка между запросами в секундах (уменьшено для ускорения)
            max_retries: Максимальное количество попыток при ошибке rate limit
            retry_delay: Начальная задержка при retry в секундах
            max_retry_delay: Максимальная задержка при retry в секундах
            max_tokens_per_text: Максимальное количество токенов на один текст (лимит OpenAI: 8192)
            chunk_overlap: Перекрытие между чанками при разбиении длинных текстов (в токенах)
            max_workers: Количество параллельных запросов (1 для базовых планов, 2-3 для платных)
        """
        # Загружаем окружение ПЕРЕД созданием клиента (как в sarsekenov_processor)
        load_env()
        self.model = model
        
        # Настройки rate limiting
        self.chunk_size = min(chunk_size, 2048)  # OpenAI лимит: максимум 2048 текстов
        self.delay_between_requests = delay_between_requests
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_retry_delay = max_retry_delay
        self.max_workers = max_workers  # Параллельная обработка
        
        # Настройки для обработки длинных текстов
        self.max_tokens_per_text = max_tokens_per_text
        self.chunk_overlap = chunk_overlap
        
        # Инициализация tiktoken для подсчета токенов (cl100k_base для text-embedding-3-small)
        self.encoding = tiktoken.get_encoding("cl100k_base")
        
        # Используем точно такой же подход, как в sarsekenov_processor.py:55
        # Если явно передан api_key, используем его, иначе OpenAI() автоматически берет из окружения
        if api_key:
            self.client = OpenAI(api_key=api_key)
            logger.debug("Используется явно переданный API ключ")
        else:
            # Проверяем наличие ключа в окружении для отладки
            env_key = os.getenv("OPENAI_API_KEY")
            if not env_key:
                logger.warning("⚠️ OPENAI_API_KEY не найден в окружении, но продолжаем (OpenAI клиент попытается найти его сам)")
            else:
                logger.debug(f"✅ OPENAI_API_KEY найден в окружении (длина: {len(env_key)} символов)")
            # Точно так же, как в sarsekenov_processor.py строка 55
            self.client = OpenAI()  # Автоматически использует OPENAI_API_KEY из окружения
        
        self.embedding_dim = 1536  # Размерность для text-embedding-3-small
        
        logger.info(f"✅ EmbeddingService инициализирован с моделью: {model}, chunk_size: {self.chunk_size}, delay: {delay_between_requests}s, max_tokens: {max_tokens_per_text}, max_workers: {max_workers}")
    
    def _count_tokens(self, text: str) -> int:
        """
        Подсчитывает количество токенов в тексте
        
        Args:
            text: Текст для подсчета
            
        Returns:
            Количество токенов
        """
        return len(self.encoding.encode(text))
    
    def _truncate_or_chunk_text(self, text: str) -> List[str]:
        """
        Разбивает длинный текст на чанки по предложениям, если превышает лимит токенов
        
        Args:
            text: Текст для обработки
            
        Returns:
            Список текстовых чанков (если текст короткий - список с одним элементом)
        """
        token_count = self._count_tokens(text)
        
        # Если текст в пределах лимита - возвращаем как есть
        if token_count <= self.max_tokens_per_text:
            return [text]
        
        logger.warning(f"⚠️ Текст превышает лимит токенов ({token_count} > {self.max_tokens_per_text}). Разбиваю на чанки...")
        
        # Разбиваем текст на предложения (учитываем точки, восклицательные и вопросительные знаки)
        # Используем более надежное регулярное выражение
        sentence_endings = re.compile(r'([.!?]+\s+|\.\n+|\.$|\n\n)')
        parts = sentence_endings.split(text)
        
        # Объединяем разделители с предложениями
        sentences = []
        for i in range(0, len(parts), 2):
            if i < len(parts):
                sentence = parts[i]
                if i + 1 < len(parts):
                    sentence += parts[i + 1]
                if sentence.strip():
                    sentences.append(sentence.strip())
        
        if not sentences:
            # Если не удалось разбить по предложениям, разбиваем по абзацам
            sentences = [s.strip() for s in text.split('\n\n') if s.strip()]
        
        if not sentences:
            # Если и это не помогло, разбиваем по строкам
            sentences = [s.strip() for s in text.split('\n') if s.strip()]
        
        if not sentences:
            # Последний вариант - разбиваем по словам
            words = text.split()
            sentences = [' '.join(words[i:i+100]) for i in range(0, len(words), 100)]
        
        chunks = []
        current_chunk = ""
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self._count_tokens(sentence)
            
            # Если одно предложение превышает лимит - обрезаем его
            if sentence_tokens > self.max_tokens_per_text:
                # Разбиваем на слова и создаем чанки
                words = sentence.split()
                word_chunk = ""
                for word in words:
                    word_with_space = word + " "
                    word_tokens = self._count_tokens(word_with_space)
                    
                    if current_tokens + word_tokens > self.max_tokens_per_text:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                            # Начинаем новый чанк с перекрытием (последние слова)
                            overlap_count = min(self.chunk_overlap // 10, len(current_chunk.split()))
                            overlap_words = current_chunk.split()[-overlap_count:] if overlap_count > 0 else []
                            current_chunk = " ".join(overlap_words) + " " + word
                            current_tokens = self._count_tokens(current_chunk)
                        else:
                            # Даже одно слово слишком длинное - обрезаем по символам
                            max_chars = self.max_tokens_per_text * 4  # Примерно 4 символа на токен
                            current_chunk = word[:max_chars]
                            current_tokens = self._count_tokens(current_chunk)
                    else:
                        current_chunk += word_with_space
                        current_tokens += word_tokens
                continue
            
            # Если добавление предложения превысит лимит - сохраняем текущий чанк
            if current_tokens + sentence_tokens > self.max_tokens_per_text:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    # Начинаем новый чанк с перекрытием (последние предложения)
                    # Берем последние предложения для перекрытия
                    prev_sentences = current_chunk.split('.')
                    overlap_sentences = prev_sentences[-2:] if len(prev_sentences) >= 2 else [current_chunk]
                    overlap_text = '. '.join([s.strip() for s in overlap_sentences if s.strip()])
                    current_chunk = overlap_text + '. ' + sentence if overlap_text else sentence
                    current_tokens = self._count_tokens(current_chunk)
                else:
                    current_chunk = sentence
                    current_tokens = sentence_tokens
            else:
                # Добавляем предложение к текущему чанку
                separator = " " if current_chunk and not current_chunk.endswith(('.', '!', '?')) else ""
                current_chunk += separator + sentence
                current_tokens += sentence_tokens
        
        # Добавляем последний чанк
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # Проверяем, что все чанки в пределах лимита
        valid_chunks = []
        for chunk in chunks:
            chunk_tokens = self._count_tokens(chunk)
            if chunk_tokens > self.max_tokens_per_text:
                logger.warning(f"⚠️ Чанк все еще превышает лимит ({chunk_tokens} токенов), обрезаю...")
                # Обрезаем по токенам
                tokens = self.encoding.encode(chunk)
                truncated_tokens = tokens[:self.max_tokens_per_text]
                chunk = self.encoding.decode(truncated_tokens)
            valid_chunks.append(chunk)
        
        logger.info(f"📝 Текст разбит на {len(valid_chunks)} чанков (токены: {[self._count_tokens(c) for c in valid_chunks]})")
        return valid_chunks
    
    def _average_embeddings(self, embeddings: List[List[float]]) -> List[float]:
        """
        Усредняет несколько эмбеддингов в один вектор
        
        Args:
            embeddings: Список векторов эмбеддингов
            
        Returns:
            Усредненный вектор
        """
        if not embeddings:
            return [0.0] * self.embedding_dim
        
        if len(embeddings) == 1:
            return embeddings[0]
        
        # Усредняем по каждому измерению
        averaged = []
        for i in range(self.embedding_dim):
            avg_value = sum(emb[i] for emb in embeddings) / len(embeddings)
            averaged.append(avg_value)
        
        return averaged
    
    def _make_request_with_retry(self, texts: List[str], attempt: int = 0) -> List[List[float]]:
        """
        Выполняет запрос к API с retry логикой
        
        Args:
            texts: Список текстов для векторизации
            attempt: Номер текущей попытки
            
        Returns:
            Список векторов эмбеддингов
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            error_msg = str(e)
            
            # Обработка недостаточной квоты (insufficient_quota) - проверяем ПЕРВЫМ
            # так как это критическая ошибка, которую нельзя решить retry
            if "insufficient_quota" in error_msg.lower() or "quota" in error_msg.lower():
                logger.error(f"❌ Превышена квота OpenAI API. Проверьте биллинг: https://platform.openai.com/account/billing")
                logger.error(f"   Детали ошибки: {error_msg}")
                raise RuntimeError("Превышена квота OpenAI API. Проверьте биллинг и попробуйте позже.") from e
            
            # Обработка rate limit (429) - повторяем с задержкой
            elif "429" in error_msg or "rate_limit" in error_msg.lower():
                if attempt < self.max_retries:
                    delay = min(self.retry_delay * (2 ** attempt), self.max_retry_delay)
                    logger.warning(f"⚠️ Rate limit достигнут. Попытка {attempt + 1}/{self.max_retries}. Ожидание {delay:.1f}s...")
                    time.sleep(delay)
                    return self._make_request_with_retry(texts, attempt + 1)
                else:
                    logger.error(f"❌ Превышено максимальное количество попыток ({self.max_retries}). Rate limit не снят.")
                    raise RuntimeError(f"Rate limit не снят после {self.max_retries} попыток. Попробуйте позже.") from e
            
            # Обработка неверного ключа (401)
            elif "401" in error_msg or "invalid_api_key" in error_msg.lower():
                logger.error(f"❌ Неверный API ключ OpenAI. Проверьте OPENAI_API_KEY в .env")
                raise ValueError("Неверный API ключ OpenAI") from e
            
            # Другие ошибки
            else:
                logger.error(f"Ошибка при создании эмбеддингов: {e}")
                raise
    
    def create_embedding(self, text: str) -> List[float]:
        """
        Создает эмбеддинг для одного текста с автоматическим разбиением длинных текстов
        
        Args:
            text: Текст для векторизации
            
        Returns:
            Список чисел (вектор эмбеддинга)
        """
        if not text or not text.strip():
            logger.warning("Пустой текст передан для создания эмбеддинга")
            return [0.0] * self.embedding_dim
        
        text = text.strip()
        
        # Проверяем длину и разбиваем на чанки при необходимости
        text_chunks = self._truncate_or_chunk_text(text)
        
        # Если текст разбит на несколько чанков - создаем эмбеддинги для каждого и усредняем
        if len(text_chunks) > 1:
            chunk_embeddings = []
            for i, chunk in enumerate(text_chunks):
                logger.debug(f"  Создание эмбеддинга для чанка {i+1}/{len(text_chunks)} ({self._count_tokens(chunk)} токенов)")
                chunk_emb = self._make_request_with_retry([chunk])
                chunk_embeddings.append(chunk_emb[0])
                # Небольшая задержка между чанками одного текста
                if i < len(text_chunks) - 1:
                    time.sleep(0.1)
            
            # Усредняем эмбеддинги всех чанков
            averaged_embedding = self._average_embeddings(chunk_embeddings)
            logger.debug(f"✅ Эмбеддинг создан из {len(text_chunks)} чанков (усреднен)")
            return averaged_embedding
        else:
            # Обычный случай - один чанк
            embeddings = self._make_request_with_retry([text_chunks[0]])
            return embeddings[0]
    
    def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Создает эмбеддинги для списка текстов (эффективная батч-обработка)
        
        Оптимизированный подход:
        1. Группирует короткие тексты в батчи для эффективной обработки
        2. Длинные тексты разбивает на чанки и обрабатывает отдельно
        3. Использует батч-запросы к API для ускорения
        
        Args:
            texts: Список текстов для векторизации
            
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
        
        logger.info(f"📦 Обработка {len(valid_texts)} текстов (батч-режим, размер батча: {self.chunk_size})...")
        
        # Разделяем тексты на короткие (для батч-обработки) и длинные (для разбиения)
        short_texts = []  # Тексты, которые можно обработать батчами
        short_indices = []  # Индексы коротких текстов
        long_texts = []  # Тексты, которые нужно разбить
        long_indices = []  # Индексы длинных текстов
        
        for i, text in enumerate(valid_texts):
            token_count = self._count_tokens(text)
            if token_count > self.max_tokens_per_text:
                long_texts.append(text)
                long_indices.append(i)
            else:
                short_texts.append(text)
                short_indices.append(i)
        
        all_embeddings = [None] * len(valid_texts)
        
        # Обрабатываем короткие тексты батчами с параллелизмом (оптимизировано!)
        if short_texts:
            logger.info(f"  📊 Короткие тексты ({len(short_texts)}): обработка батчами (размер: {self.chunk_size}, параллельно: {self.max_workers})...")
            
            # Подготовка батчей
            batches = []
            batch_indices = []
            for batch_idx in range(0, len(short_texts), self.chunk_size):
                batch = short_texts[batch_idx:batch_idx + self.chunk_size]
                batch_start_idx = batch_idx
                batches.append(batch)
                batch_indices.append(batch_start_idx)
            
            total_batches = len(batches)
            
            # Функция для обработки одного батча
            def process_batch(batch_data):
                batch_idx, batch = batch_data
                batch_num = batch_idx + 1
                try:
                    logger.debug(f"    Батч {batch_num}/{total_batches}: {len(batch)} текстов (обработка...)")
                    batch_embeddings = self._make_request_with_retry(batch)
                    logger.debug(f"    ✅ Батч {batch_num}/{total_batches} обработан")
                    return batch_idx, batch_embeddings, None
                except Exception as e:
                    logger.error(f"    ❌ Ошибка при обработке батча {batch_num}/{total_batches}: {e}")
                    return batch_idx, None, e
            
            # Параллельная обработка батчей
            if self.max_workers > 1 and total_batches > 1:
                # Используем ThreadPoolExecutor для параллельной обработки
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    # Запускаем все батчи параллельно
                    future_to_batch = {
                        executor.submit(process_batch, (idx, batch)): idx 
                        for idx, batch in enumerate(batches)
                    }
                    
                    # Собираем результаты по мере завершения
                    completed = 0
                    for future in as_completed(future_to_batch):
                        batch_idx, batch_embeddings, error = future.result()
                        completed += 1
                        
                        if batch_embeddings:
                            # Сохраняем результаты
                            start_idx = batch_indices[batch_idx]
                            for j, embedding in enumerate(batch_embeddings):
                                original_idx = short_indices[start_idx + j]
                                all_embeddings[original_idx] = embedding
                        else:
                            # В случае ошибки НЕ добавляем нулевые векторы - это приведет к неправильной индексации
                            # Оставляем None, чтобы индексатор понял что произошла ошибка
                            start_idx = batch_indices[batch_idx]
                            batch = batches[batch_idx]
                            for j in range(len(batch)):
                                original_idx = short_indices[start_idx + j]
                                all_embeddings[original_idx] = None  # None вместо нулевых векторов
                        
                        # Небольшая задержка для rate limiting (только между завершениями)
                        if completed < total_batches:
                            time.sleep(self.delay_between_requests)
            else:
                # Последовательная обработка (если max_workers=1 или один батч)
                for batch_idx, batch in enumerate(batches):
                    batch_num = batch_idx + 1
                    logger.debug(f"    Батч {batch_num}/{total_batches}: {len(batch)} текстов")
                    
                    # Задержка между батчами (кроме первого)
                    if batch_idx > 0:
                        time.sleep(self.delay_between_requests)
                    
                    try:
                        batch_embeddings = self._make_request_with_retry(batch)
                        start_idx = batch_indices[batch_idx]
                        for j, embedding in enumerate(batch_embeddings):
                            original_idx = short_indices[start_idx + j]
                            all_embeddings[original_idx] = embedding
                        logger.debug(f"    ✅ Батч {batch_num}/{total_batches} обработан")
                    except Exception as e:
                        logger.error(f"    ❌ Ошибка при обработке батча {batch_num}/{total_batches}: {e}")
                        # При ошибке НЕ добавляем нулевые векторы - это приведет к неправильной индексации
                        # Выбрасываем исключение, чтобы индексатор понял что произошла ошибка
                        raise RuntimeError(f"Не удалось создать эмбеддинги для батча {batch_num}/{total_batches}: {e}") from e
        
        # Обрабатываем длинные тексты отдельно (с разбиением на чанки)
        if long_texts:
            logger.info(f"  📏 Длинные тексты ({len(long_texts)}): разбиение на чанки...")
            for i, text in enumerate(long_texts):
                original_idx = long_indices[i]
                token_count = self._count_tokens(text)
                logger.debug(f"    Текст {i+1}/{len(long_texts)}: {token_count} токенов (будет разбит)")
                
                # Задержка между запросами
                if i > 0 or short_texts:  # Задержка если не первый или были короткие тексты
                    time.sleep(self.delay_between_requests)
                
                try:
                    # Используем create_embedding, который сам разобьет текст
                    embedding = self.create_embedding(text)
                    all_embeddings[original_idx] = embedding
                except Exception as e:
                    logger.error(f"    ❌ Ошибка при обработке длинного текста {i+1}/{len(long_texts)}: {e}")
                    # При ошибке выбрасываем исключение вместо нулевых векторов
                    raise RuntimeError(f"Не удалось создать эмбеддинг для длинного текста {i+1}/{len(long_texts)}: {e}") from e
        
        # Проверяем что все эмбеддинги созданы успешно
        failed_count = sum(1 for emb in all_embeddings if emb is None)
        if failed_count > 0:
            raise RuntimeError(f"Не удалось создать {failed_count} из {len(valid_texts)} эмбеддингов. Проверьте логи для деталей.")
        
        # Восстанавливаем порядок с учетом пустых текстов
        result = []
        embedding_idx = 0
        for i, original_text in enumerate(texts):
            if i in valid_indices:
                result.append(all_embeddings[embedding_idx])
                embedding_idx += 1
            else:
                result.append([0.0] * self.embedding_dim)  # Пустые тексты получают нулевые векторы
        
        processed_count = sum(1 for emb in all_embeddings if emb is not None)
        logger.info(f"✅ Обработано {processed_count}/{len(valid_texts)} текстов (батчами: {len(short_texts)}, отдельно: {len(long_texts)})")
        return result
    
    @property
    def dimension(self) -> int:
        """Возвращает размерность эмбеддингов"""
        return self.embedding_dim

