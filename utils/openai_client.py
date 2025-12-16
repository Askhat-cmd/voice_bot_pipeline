#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI Client Wrapper с retry логикой, таймаутами и единообразной обработкой ошибок
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional

from openai import OpenAI
from openai._exceptions import APIError, APITimeoutError, RateLimitError

from env_utils import load_env

logger = logging.getLogger(__name__)


class OpenAIClientWrapper:
    """
    Обертка над OpenAI клиентом с автоматической обработкой:
    - Таймаутов запросов
    - Retry логики с экспоненциальным backoff
    - Единообразных задержек между запросами
    - Обработки специфичных ошибок (429, 500, 503)
    """

    def __init__(self):
        """Инициализация wrapper с настройками из переменных окружения"""
        load_env()

        # Таймаут ожидания ответа от API (по умолчанию 30 секунд)
        timeout = float(os.getenv("OPENAI_API_TIMEOUT", "30.0"))
        self.client = OpenAI(timeout=timeout)

        # Задержка между запросами для избежания rate limit
        self.api_delay = float(os.getenv("OPENAI_API_DELAY", "1.0"))

        # Настройки retry логики
        self.max_retries = int(os.getenv("OPENAI_API_MAX_RETRIES", "3"))
        self.backoff_base = float(os.getenv("OPENAI_API_RETRY_BACKOFF_BASE", "2.0"))

        logger.info(
            f"OpenAIClientWrapper инициализирован: timeout={timeout}s, "
            f"delay={self.api_delay}s, max_retries={self.max_retries}"
        )

    def _should_retry(self, error: Exception) -> bool:
        """
        Определяет, нужно ли повторять запрос при данной ошибке.

        Args:
            error: Исключение от OpenAI API

        Returns:
            True если нужно retry, False если нет
        """
        # Rate limit ошибки - всегда retry
        if isinstance(error, RateLimitError):
            return True

        # API ошибки с определенными статус-кодами
        if isinstance(error, APIError):
            status_code = getattr(error, "status_code", None)
            if status_code in (429, 500, 503, 502, 504):
                return True
            # 401, 400, 403 - клиентские ошибки, не retry
            if status_code in (401, 400, 403, 404):
                return False

        # Timeout ошибки - retry
        if isinstance(error, APITimeoutError):
            return True

        # Неизвестные ошибки - не retry
        return False

    def _get_retry_delay(self, attempt: int) -> float:
        """
        Вычисляет задержку перед следующей попыткой с экспоненциальным backoff.

        Args:
            attempt: Номер попытки (начинается с 1)

        Returns:
            Задержка в секундах
        """
        return self.backoff_base ** attempt

    def chat_completions_create(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Any:
        """
        Создает chat completion с автоматической retry логикой и задержками.

        Args:
            model: Модель для использования
            messages: Список сообщений
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов
            response_format: Формат ответа (например, {"type": "json_object"})
            **kwargs: Дополнительные параметры для API

        Returns:
            Ответ от OpenAI API

        Raises:
            APIError: Если все попытки исчерпаны или ошибка не требует retry
        """
        # Задержка перед запросом для избежания rate limit
        time.sleep(self.api_delay)

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                # Формируем параметры запроса
                params: Dict[str, Any] = {
                    "model": model,
                    "messages": messages,
                    **kwargs
                }

                if temperature is not None:
                    params["temperature"] = temperature
                if max_tokens is not None:
                    params["max_tokens"] = max_tokens
                if response_format is not None:
                    params["response_format"] = response_format

                # Выполняем запрос
                response = self.client.chat.completions.create(**params)

                # Если это retry после ошибки, логируем успех
                if attempt > 0:
                    logger.info(
                        f"✅ Успешный retry после {attempt} попыток для модели {model}"
                    )

                return response

            except Exception as e:
                last_error = e

                # Проверяем, нужно ли retry
                if not self._should_retry(e) or attempt >= self.max_retries:
                    # Не retry или исчерпаны попытки
                    if attempt >= self.max_retries:
                        logger.error(
                            f"❌ Исчерпаны все {self.max_retries} попытки для модели {model}. "
                            f"Последняя ошибка: {type(e).__name__}: {str(e)}"
                        )
                    else:
                        logger.error(
                            f"❌ Ошибка не требует retry для модели {model}: "
                            f"{type(e).__name__}: {str(e)}"
                        )
                    raise

                # Вычисляем задержку перед следующей попыткой
                delay = self._get_retry_delay(attempt + 1)
                logger.warning(
                    f"⚠️ Попытка {attempt + 1}/{self.max_retries + 1} не удалась для модели {model}. "
                    f"Ошибка: {type(e).__name__}: {str(e)}. "
                    f"Повтор через {delay:.1f} секунд..."
                )

                time.sleep(delay)

        # Если дошли сюда, значит все попытки исчерпаны
        if last_error:
            raise last_error
        raise RuntimeError("Неожиданная ошибка: все попытки исчерпаны без исключения")

    def embeddings_create(
        self,
        model: str,
        input: str | List[str],
        **kwargs
    ) -> Any:
        """
        Создает embeddings с автоматической retry логикой и задержками.

        Args:
            model: Модель для embeddings
            input: Текст или список текстов для векторизации
            **kwargs: Дополнительные параметры для API

        Returns:
            Ответ от OpenAI API с embeddings

        Raises:
            APIError: Если все попытки исчерпаны или ошибка не требует retry
        """
        # Задержка перед запросом для избежания rate limit
        time.sleep(self.api_delay)

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                params: Dict[str, Any] = {
                    "model": model,
                    "input": input,
                    **kwargs
                }

                # Выполняем запрос
                response = self.client.embeddings.create(**params)

                # Если это retry после ошибки, логируем успех
                if attempt > 0:
                    logger.info(
                        f"✅ Успешный retry после {attempt} попыток для embeddings модели {model}"
                    )

                return response

            except Exception as e:
                last_error = e

                # Проверяем, нужно ли retry
                if not self._should_retry(e) or attempt >= self.max_retries:
                    # Не retry или исчерпаны попытки
                    if attempt >= self.max_retries:
                        logger.error(
                            f"❌ Исчерпаны все {self.max_retries} попытки для embeddings модели {model}. "
                            f"Последняя ошибка: {type(e).__name__}: {str(e)}"
                        )
                    else:
                        logger.error(
                            f"❌ Ошибка не требует retry для embeddings модели {model}: "
                            f"{type(e).__name__}: {str(e)}"
                        )
                    raise

                # Вычисляем задержку перед следующей попыткой
                delay = self._get_retry_delay(attempt + 1)
                logger.warning(
                    f"⚠️ Попытка {attempt + 1}/{self.max_retries + 1} не удалась для embeddings модели {model}. "
                    f"Ошибка: {type(e).__name__}: {str(e)}. "
                    f"Повтор через {delay:.1f} секунд..."
                )

                time.sleep(delay)

        # Если дошли сюда, значит все попытки исчерпаны
        if last_error:
            raise last_error
        raise RuntimeError("Неожиданная ошибка: все попытки исчерпаны без исключения")

