#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилита для обновления Markdown файла со списком видео канала
Добавляет отметки о статусе обработки видео
"""

import re
from pathlib import Path
from typing import Optional
from datetime import datetime

from .video_registry import VideoRegistry


class MarkdownUpdater:
    """Класс для обновления Markdown файла со статусами обработки"""
    
    def __init__(self, markdown_path: str, registry_path: str = "data/video_registry.json"):
        """
        Инициализация обновлятеля Markdown.
        
        Args:
            markdown_path: Путь к Markdown файлу со списком видео
            registry_path: Путь к файлу реестра видео
        """
        self.markdown_path = Path(markdown_path)
        self.registry = VideoRegistry(registry_path)
    
    def update_status_columns(self) -> bool:
        """
        Обновление колонок "Статус" и "Дата обработки" в Markdown файле.
        
        Returns:
            True если обновление прошло успешно, False в противном случае
        """
        if not self.markdown_path.exists():
            return False
        
        try:
            # Читаем файл
            with open(self.markdown_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Ищем начало таблицы
            header_line_idx = None
            separator_line_idx = None
            
            for i, line in enumerate(lines):
                if '| № |' in line and 'Дата публикации' in line:
                    header_line_idx = i
                elif header_line_idx is not None and '|---' in line:
                    separator_line_idx = i
                    break
            
            if header_line_idx is None:
                return False
            
            # Проверяем, есть ли уже колонки статуса
            header = lines[header_line_idx]
            has_status_column = 'Статус' in header
            
            # Если колонок нет - добавляем их в заголовок и разделитель
            if not has_status_column:
                lines[header_line_idx] = header.replace(
                    '| Ссылка |', 
                    '| Статус | Дата обработки | Ссылка |'
                )
                if separator_line_idx is not None:
                    separator = lines[separator_line_idx]
                    lines[separator_line_idx] = separator.replace(
                        '|--------|',
                        '|--------|----------------|--------|'
                    )
            
            # Обновляем строки таблицы
            updated_lines = []
            for i, line in enumerate(lines):
                if i <= (separator_line_idx or header_line_idx):
                    # Заголовок и разделитель - оставляем как есть (уже обновлены)
                    updated_lines.append(line)
                elif line.strip().startswith('|') and line.count('|') >= 7:
                    # Строка таблицы - обновляем
                    updated_line = self._update_table_row(line)
                    updated_lines.append(updated_line)
                else:
                    # Обычная строка - оставляем как есть
                    updated_lines.append(line)
            
            # Сохраняем обновленный файл
            with open(self.markdown_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(updated_lines))
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Ошибка обновления Markdown: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _update_table_row(self, line: str) -> str:
        """
        Обновление строки таблицы со статусом обработки.
        
        Args:
            line: Строка таблицы
        
        Returns:
            Обновленная строка
        """
        # Парсим строку таблицы
        parts = [p.strip() for p in line.rstrip().split('|')]
        
        # Убираем пустые элементы в начале и конце
        while parts and not parts[0]:
            parts.pop(0)
        while parts and not parts[-1]:
            parts.pop()
        
        if len(parts) < 7:
            # Недостаточно колонок - возвращаем как есть
            return line
        
        # Извлекаем video_id из ссылки (последняя колонка)
        video_id = None
        for part in reversed(parts):
            if 'youtube.com/watch?v=' in part or 'youtu.be/' in part:
                # Извлекаем video_id
                match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', part)
                if match:
                    video_id = match.group(1)
                    break
        
        if not video_id:
            return line
        
        # Проверяем статус в реестре
        status_symbol = '[ ]'  # Не обработано
        processed_date = ''
        
        if self.registry.video_exists(video_id):
            video_data = self.registry.data["videos"].get(video_id, {})
            video_status = video_data.get("status", "pending")
            
            if video_status == "processed":
                status_symbol = '[x]'  # Обработано
                # Получаем дату последней обработки
                history = video_data.get("processing_history", [])
                if history:
                    last_record = history[-1]
                    processed_at = last_record.get("processed_at", "")
                    if processed_at:
                        try:
                            dt = datetime.fromisoformat(processed_at.replace('Z', '+00:00'))
                            processed_date = dt.strftime('%d.%m.%Y')
                        except:
                            processed_date = processed_at[:10] if len(processed_at) >= 10 else ''
            elif video_status == "failed":
                status_symbol = '[!]'  # Ошибка
        
        # Обновляем колонки статуса
        # Формат: | № | Дата | Название | Плейлист | Просмотры | Длительность | Статус | Дата обработки | Ссылка |
        if len(parts) >= 9:
            # Колонки уже есть - обновляем предпоследние две
            parts[-3] = status_symbol  # Статус
            parts[-2] = processed_date  # Дата обработки
        elif len(parts) == 7:
            # Колонок нет - добавляем перед последней (Ссылка)
            parts.insert(-1, status_symbol)
            parts.insert(-1, processed_date)
        
        # Формируем строку обратно
        return '| ' + ' | '.join(parts) + ' |\n'
    
    def update_after_processing(self, video_id: str) -> bool:
        """
        Обновление Markdown файла после обработки конкретного видео.
        
        Args:
            video_id: ID обработанного видео
        
        Returns:
            True если обновление прошло успешно
        """
        return self.update_status_columns()

