#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для миграции существующих обработанных видео в реестр
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Добавляем родительскую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.video_registry import VideoRegistry, VideoMetadata, ProcessingRecord
from utils.youtube_metadata_fetcher import YouTubeAPIMetadataFetcher


def find_existing_videos(data_dir: Path) -> list:
    """Находит уже обработанные видео в sag_final"""
    sag_dir = data_dir / "sag_final"
    if not sag_dir.exists():
        return []
    
    videos = {}
    for json_file in sag_dir.glob("*.for_vector.json"):
        video_id = json_file.stem.replace(".for_vector", "")
        videos[video_id] = {
            "video_id": video_id,
            "sag_json": str(json_file),
            "sag_md": str(json_file.parent / f"{video_id}.for_review.md"),
            "raw_subtitles": str(data_dir / "raw_subtitles" / f"{video_id}.json")
        }
    
    return list(videos.values())


def migrate_video(registry: VideoRegistry, metadata_fetcher: YouTubeAPIMetadataFetcher, video_info: dict):
    """Мигрирует одно видео в реестр"""
    video_id = video_info["video_id"]
    
    print(f"\n📹 Обработка видео {video_id}...")
    
    # Проверяем, есть ли уже в реестре
    if registry.video_exists(video_id):
        print(f"  ⚠️ Видео {video_id} уже в реестре, пропускаем")
        return False
    
    # Получаем метаданные через API
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        metadata_dict = metadata_fetcher.fetch_metadata(url)
        video_metadata = VideoMetadata(**metadata_dict)
    except Exception as e:
        print(f"  ⚠️ Ошибка получения метаданных: {e}")
        # Используем базовые метаданные
        video_metadata = VideoMetadata(
            video_id=video_id,
            title=f"Video {video_id}",
            channel="Unknown",
            published_date=datetime.now().isoformat(),
            duration_seconds=0,
            url=f"https://www.youtube.com/watch?v={video_id}"
        )
    
    # Добавляем в реестр
    registry.add_video(video_metadata)
    
    # Сохраняем пути к файлам
    if Path(video_info["sag_json"]).exists():
        registry.set_file_path(video_id, "sag_json", video_info["sag_json"])
    if Path(video_info["sag_md"]).exists():
        registry.set_file_path(video_id, "sag_md", video_info["sag_md"])
    if Path(video_info["raw_subtitles"]).exists():
        registry.set_file_path(video_id, "raw_subtitles", video_info["raw_subtitles"])
    
    # Пытаемся получить информацию о блоках из SAG файла
    blocks_count = 0
    entities_count = 0
    try:
        with open(video_info["sag_json"], 'r', encoding='utf-8') as f:
            sag_data = json.load(f)
            blocks_count = len(sag_data.get("blocks", []))
            for block in sag_data.get("blocks", []):
                entities_count += len(block.get("graph_entities", []))
    except:
        pass
    
    # Создаем запись об обработке (помечаем как обработанное)
    processing_record = ProcessingRecord(
        processed_at=datetime.now().isoformat(),
        pipeline_version="v2.1",
        stage_completed="all",
        blocks_created=blocks_count,
        entities_extracted=entities_count,
        processing_time_seconds=0.0,  # Неизвестно
        api_cost_estimate=0.0  # Неизвестно
    )
    registry.add_processing_record(video_id, processing_record)
    
    print(f"  ✅ Видео {video_id} добавлено в реестр")
    return True


def main():
    """Основная функция миграции"""
    data_dir = Path(__file__).parent.parent / "data"
    registry_path = data_dir / "video_registry.json"
    
    print("🔄 Начало миграции существующих видео в реестр...")
    print(f"📁 Директория данных: {data_dir}")
    print(f"📋 Реестр: {registry_path}\n")
    
    # Инициализация
    registry = VideoRegistry(str(registry_path))
    metadata_fetcher = YouTubeAPIMetadataFetcher()
    
    # Находим существующие видео
    existing_videos = find_existing_videos(data_dir)
    
    if not existing_videos:
        print("❌ Не найдено обработанных видео в sag_final/")
        return 1
    
    print(f"📊 Найдено {len(existing_videos)} обработанных видео:")
    for v in existing_videos:
        print(f"  • {v['video_id']}")
    
    # Мигрируем каждое видео
    migrated = 0
    for video_info in existing_videos:
        if migrate_video(registry, metadata_fetcher, video_info):
            migrated += 1
    
    # Показываем статистику
    stats = registry.get_statistics()
    print(f"\n{'='*60}")
    print(f"📊 ИТОГОВАЯ СТАТИСТИКА")
    print(f"{'='*60}")
    print(f"Мигрировано видео: {migrated}")
    print(f"Всего в реестре: {stats['total_videos']}")
    print(f"Обработано: {stats['processed']}")
    print(f"{'='*60}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

