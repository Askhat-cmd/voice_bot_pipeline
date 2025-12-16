#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилита для парсинга номеров видео из channel_videos_list.json
и преобразования их в URL для использования в pipeline_orchestrator
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple


class ChannelListParser:
    """Парсер для работы со списком видео канала"""
    
    def __init__(self, json_path: str):
        """
        Инициализация парсера.
        
        Args:
            json_path: Путь к JSON файлу со списком видео
        """
        self.json_path = Path(json_path)
        self.channel_list = None
        self._load_list()
    
    def _load_list(self) -> None:
        """Загрузка списка видео из JSON файла"""
        if not self.json_path.exists():
            raise FileNotFoundError(f"Файл списка видео не найден: {self.json_path}")
        
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.channel_list = data.get('videos', [])
        except json.JSONDecodeError as e:
            raise ValueError(f"Ошибка парсинга JSON файла: {e}")
        except Exception as e:
            raise RuntimeError(f"Ошибка загрузки списка видео: {e}")
    
    def get_video_by_number(self, number: int) -> Optional[Dict]:
        """
        Получение видео по номеру.
        
        Args:
            number: Порядковый номер видео (начиная с 1)
        
        Returns:
            Словарь с данными видео или None если не найдено
        """
        if not self.channel_list:
            return None
        
        # Номера начинаются с 1, индексы с 0
        if 1 <= number <= len(self.channel_list):
            return self.channel_list[number - 1]
        return None
    
    def get_url_by_number(self, number: int) -> Optional[str]:
        """
        Получение URL видео по номеру.
        
        Args:
            number: Порядковый номер видео
        
        Returns:
            URL видео или None если не найдено
        """
        video = self.get_video_by_number(number)
        return video.get('url') if video else None
    
    @staticmethod
    def parse_number_spec(spec: str) -> Set[int]:
        """
        Парсинг спецификации номера с поддержкой диапазонов.
        
        Args:
            spec: Строка с номерами (например: "4, 8, 15, 34-56")
        
        Returns:
            Множество номеров (включительно для диапазонов)
        
        Примеры:
            "4" → {4}
            "34-56" → {34, 35, 36, ..., 56}
            "4, 8, 15, 34-56" → {4, 8, 15, 34, 35, ..., 56}
        """
        numbers = set()
        spec = spec.strip()
        
        # Разделяем по запятым
        parts = [p.strip() for p in spec.split(',')]
        
        for part in parts:
            if not part:
                continue
            
            # Проверяем диапазон (формат: "start-end")
            if '-' in part:
                try:
                    start_str, end_str = part.split('-', 1)
                    start = int(start_str.strip())
                    end = int(end_str.strip())
                    
                    # Диапазон включительно
                    if start <= end:
                        numbers.update(range(start, end + 1))
                    else:
                        # Если start > end, меняем местами
                        numbers.update(range(end, start + 1))
                except ValueError:
                    # Некорректный формат диапазона - пропускаем
                    continue
            else:
                # Одиночный номер
                try:
                    number = int(part)
                    numbers.add(number)
                except ValueError:
                    # Не число - пропускаем
                    continue
        
        return numbers
    
    def resolve_numbers_to_urls(self, numbers: Set[int]) -> List[str]:
        """
        Преобразование множества номеров в список URL.
        
        Args:
            numbers: Множество номеров видео
        
        Returns:
            Список URL (только для найденных номеров)
        """
        urls = []
        for number in sorted(numbers):
            url = self.get_url_by_number(number)
            if url:
                urls.append(url)
        
        return urls
    
    def parse_urls_file(self, urls_file: str) -> Tuple[List[str], List[str]]:
        """
        Парсинг файла urls.txt с поддержкой номеров и обычных URL.
        
        Args:
            urls_file: Путь к файлу urls.txt
        
        Returns:
            Кортеж (список URL для обработки, список предупреждений)
        """
        urls_file_path = Path(urls_file)
        if not urls_file_path.exists():
            raise FileNotFoundError(f"Файл urls.txt не найден: {urls_file_path}")
        
        all_urls = []
        all_numbers = set()
        warnings = []
        
        # Паттерн для определения URL
        url_pattern = re.compile(
            r'https?://(?:www\.)?(?:youtube\.com|youtu\.be)/.*',
            re.IGNORECASE
        )
        
        with open(urls_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Пропускаем пустые строки и комментарии
                if not line or line.startswith('#'):
                    continue
                
                # Проверяем, является ли строка URL
                if url_pattern.match(line):
                    all_urls.append(line)
                else:
                    # Пытаемся распарсить как номера
                    try:
                        numbers = self.parse_number_spec(line)
                        if numbers:
                            all_numbers.update(numbers)
                        else:
                            warnings.append(f"Строка {line_num}: '{line}' - не распознано как номер или URL")
                    except Exception as e:
                        warnings.append(f"Строка {line_num}: '{line}' - ошибка парсинга: {e}")
        
        # Преобразуем номера в URL
        resolved_urls = self.resolve_numbers_to_urls(all_numbers)
        all_urls.extend(resolved_urls)
        
        # Проверяем отсутствующие номера
        found_numbers = set()
        for number in all_numbers:
            video = self.get_video_by_number(number)
            if video:
                found_numbers.add(number)
        
        missing_numbers = all_numbers - found_numbers
        if missing_numbers:
            warnings.append(
                f"Номера не найдены в списке: {sorted(missing_numbers)} "
                f"(всего видео в списке: {len(self.channel_list) if self.channel_list else 0})"
            )
        
        return all_urls, warnings
    
    def get_total_videos(self) -> int:
        """Получение общего количества видео в списке"""
        return len(self.channel_list) if self.channel_list else 0


def load_channel_list(json_path: str) -> ChannelListParser:
    """
    Удобная функция для загрузки списка видео.
    
    Args:
        json_path: Путь к JSON файлу
    
    Returns:
        Экземпляр ChannelListParser
    """
    return ChannelListParser(json_path)

