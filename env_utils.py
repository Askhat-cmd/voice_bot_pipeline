#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from pathlib import Path
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # fallback if python-dotenv не установлен
    def load_dotenv(*args, **kwargs):  # type: ignore
        return False

def load_env() -> None:
    """
    Единая загрузка .env:
    1) Сначала пытаемся загрузить через python-dotenv (наиболее надежный способ)
    2) Затем вручную парсим .env для поддержки простых многострочных значений
    
    Ищет .env файл в нескольких местах:
    - Текущая рабочая директория
    - Директория скрипта (где находится env_utils.py)
    - Родительские директории
    """
    # Получаем директорию, где находится env_utils.py
    script_dir = Path(__file__).resolve().parent
    
    # Список возможных путей к .env файлу (в порядке приоритета)
    possible_paths = [
        Path.cwd() / ".env",  # Текущая рабочая директория (абсолютный путь)
        Path(".env"),  # Текущая рабочая директория (относительный)
        script_dir / ".env",  # Рядом с env_utils.py
        script_dir.parent / ".env",  # Родительская директория
    ]
    
    # Сначала пробуем загрузить через python-dotenv (наиболее надежный способ)
    loaded = False
    for env_path in possible_paths:
        if env_path.exists():
            try:
                # Используем dotenv для загрузки (он правильно обрабатывает BOM и кодировки)
                result = load_dotenv(dotenv_path=str(env_path.resolve()), override=True)
                if result:
                    loaded = True
                    break
            except Exception:
                continue
    
    # Если dotenv не сработал, пробуем стандартный поиск
    if not loaded:
        try:
            load_dotenv(override=True)
        except Exception:
            pass
    
    # Дополнительно: вручную парсим для поддержки многострочных значений
    for env_path in possible_paths:
        if env_path.exists():
            try:
                # Читаем с обработкой BOM
                with open(env_path, "r", encoding="utf-8-sig") as f:  # utf-8-sig автоматически убирает BOM
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            # Убираем кавычки и пробелы
                            v = v.strip().strip('"').strip("'")
                            # Устанавливаем только если еще не установлено (dotenv имеет приоритет)
                            if k.strip() not in os.environ:
                                os.environ[k.strip()] = v
                break
            except Exception:
                continue
