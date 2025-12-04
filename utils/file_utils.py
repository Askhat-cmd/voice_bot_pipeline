#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилиты для работы с именами файлов и путями
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Tuple


def create_safe_filename(title: str, max_length: int = 50) -> str:
    """
    Создает безопасное имя файла из названия видео.
    
    Args:
        title: Оригинальное название
        max_length: Максимальная длина
    
    Returns:
        Безопасное имя без спецсимволов
    """
    # Убираем спецсимволы и лишние пробелы
    safe = re.sub(r'[^\w\s-]', '', title)
    safe = re.sub(r'[-\s]+', '_', safe)
    
    # Ограничиваем длину
    if len(safe) > max_length:
        safe = safe[:max_length].rsplit('_', 1)[0]
    
    return safe.strip('_')


def create_filename(video_id: str, title: str, published_date: str, ext: str = "json") -> str:
    """
    Создает полное имя файла.
    
    Args:
        video_id: YouTube video ID
        title: Название видео
        published_date: ISO дата публикации
        ext: Расширение файла
    
    Returns:
        Имя файла в формате: 2024-03-15_HndVzdJuAz0_Название.json
    """
    # Парсим дату из ISO формата
    try:
        if published_date.endswith('Z'):
            date_obj = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
        else:
            date_obj = datetime.fromisoformat(published_date)
        date_str = date_obj.strftime('%Y-%m-%d')
    except (ValueError, AttributeError):
        # Если не удалось распарсить, используем текущую дату
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    safe_title = create_safe_filename(title)
    
    return f"{date_str}_{video_id}_{safe_title}.{ext}"


def get_date_paths(base_dir: Path, published_date: str) -> Tuple[Path, str, str]:
    """
    Создает пути по датам для организации файлов.
    
    Args:
        base_dir: Базовая директория
        published_date: ISO дата публикации
    
    Returns:
        Tuple (полный путь, год, месяц)
    """
    try:
        if published_date.endswith('Z'):
            date_obj = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
        else:
            date_obj = datetime.fromisoformat(published_date)
        year = date_obj.strftime('%Y')
        month = date_obj.strftime('%m')
    except (ValueError, AttributeError):
        # Если не удалось распарсить, используем текущую дату
        now = datetime.now()
        year = now.strftime('%Y')
        month = now.strftime('%m')
    
    full_path = base_dir / year / month
    return full_path, year, month

