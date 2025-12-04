#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Управление реестром видео.
Обеспечивает проверку дубликатов, индексацию, историю обработки.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class VideoMetadata:
    """Метаданные одного видео"""
    video_id: str
    title: str
    channel: str
    published_date: str
    duration_seconds: int
    url: str
    status: str = "pending"
    language: str = "ru"
    has_subtitles: bool = True
    subtitle_type: str = "auto-generated"
    description: str = ""
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class ProcessingRecord:
    """Запись о процессе обработки"""
    processed_at: str
    pipeline_version: str
    stage_completed: str
    blocks_created: int
    entities_extracted: int
    processing_time_seconds: float
    api_cost_estimate: float
    error_message: Optional[str] = None


class VideoRegistry:
    """
    Управление реестром видео.
    Обеспечивает проверку дубликатов, индексацию, историю обработки.
    """
    
    def __init__(self, registry_path: str = "data/video_registry.json"):
        self.registry_path = Path(registry_path)
        self.data = self._load()
    
    def _load(self) -> dict:
        """Загрузка реестра из файла"""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARNING] Ошибка загрузки реестра: {e}. Создаю новый.")
        
        # Создаем новый реестр
        return {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "total_videos": 0,
            "processed": 0,
            "failed": 0,
            "pending": 0,
            "videos": {}
        }
    
    def save(self):
        """Сохранение реестра"""
        self.data["last_updated"] = datetime.now().isoformat()
        
        # Обновляем счетчики
        self.data["total_videos"] = len(self.data["videos"])
        self.data["processed"] = sum(
            1 for v in self.data["videos"].values() 
            if v["status"] == "processed"
        )
        self.data["failed"] = sum(
            1 for v in self.data["videos"].values() 
            if v["status"] == "failed"
        )
        self.data["pending"] = sum(
            1 for v in self.data["videos"].values() 
            if v["status"] == "pending"
        )
        
        # Создаем директорию если нужно
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.registry_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
    
    def video_exists(self, video_id: str) -> bool:
        """Проверка: существует ли видео в реестре"""
        return video_id in self.data["videos"]
    
    def is_processed(self, video_id: str) -> bool:
        """Проверка: обработано ли видео"""
        if not self.video_exists(video_id):
            return False
        return self.data["videos"][video_id]["status"] == "processed"
    
    def add_video(self, metadata: VideoMetadata):
        """
        Добавление нового видео в реестр.
        
        Args:
            metadata: Метаданные видео
        
        Returns:
            bool: True если добавлено, False если уже существует
        """
        if self.video_exists(metadata.video_id):
            print(f"⚠️ Видео {metadata.video_id} уже в реестре")
            return False
        
        self.data["videos"][metadata.video_id] = {
            **asdict(metadata),
            "processing_history": [],
            "files": {},
            "metadata": {
                "language": metadata.language,
                "has_subtitles": metadata.has_subtitles,
                "subtitle_type": metadata.subtitle_type,
                "description": metadata.description,
                "tags": metadata.tags
            }
        }
        
        self.save()
        print(f"✅ Видео {metadata.video_id} добавлено в реестр")
        return True
    
    def update_status(self, video_id: str, status: str):
        """Обновление статуса видео"""
        if not self.video_exists(video_id):
            raise ValueError(f"Видео {video_id} не найдено в реестре")
        
        self.data["videos"][video_id]["status"] = status
        self.save()
    
    def add_processing_record(self, video_id: str, record: ProcessingRecord):
        """Добавление записи об обработке"""
        if not self.video_exists(video_id):
            raise ValueError(f"Видео {video_id} не найдено в реестре")
        
        self.data["videos"][video_id]["processing_history"].append(
            asdict(record)
        )
        
        # Обновляем статус
        if record.error_message:
            self.data["videos"][video_id]["status"] = "failed"
        else:
            self.data["videos"][video_id]["status"] = "processed"
        
        self.save()
    
    def set_file_path(self, video_id: str, file_type: str, path: str):
        """Сохранение пути к файлу"""
        if not self.video_exists(video_id):
            raise ValueError(f"Видео {video_id} не найдено в реестре")
        
        self.data["videos"][video_id]["files"][file_type] = path
        self.save()
    
    def get_video(self, video_id: str) -> Optional[dict]:
        """Получение информации о видео"""
        return self.data["videos"].get(video_id)
    
    def get_pending_videos(self) -> List[str]:
        """Получение списка необработанных видео"""
        return [
            video_id for video_id, data in self.data["videos"].items()
            if data["status"] == "pending"
        ]
    
    def get_failed_videos(self) -> List[str]:
        """Получение списка проблемных видео"""
        return [
            video_id for video_id, data in self.data["videos"].items()
            if data["status"] == "failed"
        ]
    
    def get_statistics(self) -> dict:
        """Детальная статистика реестра"""
        videos = list(self.data["videos"].values())
        
        if not videos:
            return {"total": 0}
        
        total_blocks = sum(
            record.get("blocks_created", 0)
            for video in videos
            for record in video.get("processing_history", [])
        )
        
        total_entities = sum(
            record.get("entities_extracted", 0)
            for video in videos
            for record in video.get("processing_history", [])
        )
        
        total_cost = sum(
            record.get("api_cost_estimate", 0)
            for video in videos
            for record in video.get("processing_history", [])
        )
        
        processed_count = self.data["processed"]
        
        return {
            "total_videos": self.data["total_videos"],
            "processed": processed_count,
            "failed": self.data["failed"],
            "pending": self.data["pending"],
            "total_blocks": total_blocks,
            "total_entities": total_entities,
            "total_api_cost": round(total_cost, 2),
            "avg_blocks_per_video": round(total_blocks / processed_count, 1) if processed_count > 0 else 0
        }

