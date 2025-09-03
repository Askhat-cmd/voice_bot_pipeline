#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Subtitles Extractor - Упрощенная версия
Получает субтитры напрямую с YouTube используя youtube-transcript-api
"""

import os
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional
import re
import logging

try:
    from youtube_transcript_api import YouTubeTranscriptApi, CouldNotRetrieveTranscript
except ImportError:
    logging.error("[ERROR] Ошибка: Не установлена библиотека youtube-transcript-api")
    logging.error("Установите: pip install youtube-transcript-api")
    raise

from requests.exceptions import HTTPError

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class YouTubeSubtitlesExtractor:
    """Класс для извлечения субтитров с YouTube"""
    
    def __init__(self, output_dir: str = "data/subtitles"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Извлекает ID видео из URL YouTube"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/live\/)([^&\n?#]+)',
            r'youtube\.com\/watch\?.*v=([^&\n?#]+)',
            r'youtu\.be\/([^&\n?#]+)',
            r'youtube\.com\/live\/([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # Если URL не распознан, возможно это уже ID
        if len(url) == 11 and re.match(r'^[A-Za-z0-9_-]{11}$', url):
            return url
            
        return None
    
    def get_subtitles(self, video_id: str, language: str = 'ru') -> List[Dict]:
        """Получает субтитры для указанного языка"""
        try:
            api = YouTubeTranscriptApi()
            transcript_list = api.list(video_id)
        except (CouldNotRetrieveTranscript, HTTPError) as e:
            logger.error("Ошибка при получении списка субтитров: %s", e)
            raise

        try:
            transcript = transcript_list.find_transcript([language])
            subtitles = transcript.fetch()
            logger.info("[OK] Получены субтитры на языке: %s", language)
            return subtitles
        except (CouldNotRetrieveTranscript, HTTPError) as e:
            logger.error("Ошибка при получении субтитров: %s", e)
            raise
        except Exception:
            logger.info("[WARNING] Субтитры на языке '%s' не найдены", language)
            try:
                transcript = transcript_list[0]
                subtitles = transcript.fetch()
                logger.info("[OK] Получены субтитры на языке: %s", transcript.language_code)
                return subtitles
            except (CouldNotRetrieveTranscript, HTTPError) as e:
                logger.error("[ERROR] Не удалось получить субтитры: %s", e)
                raise
    
    def _seconds_to_srt_time(self, seconds: float) -> str:
        """Конвертирует секунды в формат SRT времени"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    def save_subtitles(self, video_id: str, subtitles: List[Dict]) -> Dict[str, str]:
        """Сохраняет субтитры в различных форматах"""
        base_filename = f"{video_id}"
        
        # Метаданные
        total_duration = 0
        for item in subtitles:
            if hasattr(item, 'duration'):
                total_duration += item.duration
            elif isinstance(item, dict):
                total_duration += item.get('duration', 0)
        
        metadata = {
            "video_id": video_id,
            "subtitle_count": len(subtitles),
            "total_duration": total_duration
        }
        
        saved_files = {}
        
        # Сохраняем JSON
        json_path = self.output_dir / f"{base_filename}.json"
        
        # Конвертируем объекты в словари для JSON
        subtitles_dict = []
        for item in subtitles:
            if hasattr(item, 'text'):
                subtitles_dict.append({
                    'text': item.text,
                    'start': item.start,
                    'duration': item.duration
                })
            elif isinstance(item, dict):
                subtitles_dict.append(item)
            else:
                subtitles_dict.append({'text': str(item), 'start': 0, 'duration': 0})
        
        json_data = {
            "metadata": metadata,
            "subtitles": subtitles_dict
        }
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        saved_files['json'] = str(json_path)
        
        # Сохраняем TXT (только текст)
        txt_path = self.output_dir / f"{base_filename}.txt"
        text_content = ""
        for item in subtitles:
            # Проверяем тип объекта
            if hasattr(item, 'text'):
                text_content += item.text + " "
            elif isinstance(item, dict):
                text_content += item.get('text', '') + " "
            else:
                text_content += str(item) + " "
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(text_content.strip())
        saved_files['txt'] = str(txt_path)
        
        # Сохраняем SRT
        srt_path = self.output_dir / f"{base_filename}.srt"
        srt_lines = []
        
        for i, item in enumerate(subtitles, 1):
            # Получаем данные
            if hasattr(item, 'text'):
                text = item.text
                start = item.start
                duration = item.duration
            elif isinstance(item, dict):
                text = item.get('text', '')
                start = item.get('start', 0)
                duration = item.get('duration', 0)
            else:
                text = str(item)
                start = 0
                duration = 0
            
            end = start + duration
            
            # Форматируем время
            start_time = self._seconds_to_srt_time(start)
            end_time = self._seconds_to_srt_time(end)
            
            # Добавляем в SRT
            srt_lines.append(f"{i}")
            srt_lines.append(f"{start_time} --> {end_time}")
            srt_lines.append(text)
            srt_lines.append("")
        
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(srt_lines))
        saved_files['srt'] = str(srt_path)
        
        return saved_files
    
    def process_url(self, url: str, language: str = 'ru') -> bool:
        """Обрабатывает URL и сохраняет субтитры"""
        logger.info("Обрабатываю URL: %s", url)
        
        video_id = self.extract_video_id(url)
        if not video_id:
            logger.error("[ERROR] Не удалось извлечь ID видео из URL")
            return False
        
        subtitles = self.get_subtitles(video_id, language)
        if not subtitles:
            logger.error("[ERROR] Не удалось получить субтитры")
            return False
        
        saved_files = self.save_subtitles(video_id, subtitles)
        logger.info("[OK] Файлы сохранены: %s", saved_files)
        return True

def main():
    parser = argparse.ArgumentParser(description="Извлечение субтитров с YouTube")
    parser.add_argument("--url", help="URL видео YouTube")
    parser.add_argument("--urls-file", "--file", dest="urls_file", help="Файл со списком URL (по одному на строку)")
    parser.add_argument("--output", default="data/subtitles", help="Папка для сохранения")
    parser.add_argument("--language", default="ru", help="Предпочитаемый язык (по умолчанию: ru)")
    args = parser.parse_args()
    
    extractor = YouTubeSubtitlesExtractor(args.output)
    
    if args.url:
        ok = extractor.process_url(args.url, args.language)
        if ok:
            logger.info("[OK] Обработка завершена успешно")
        else:
            logger.error("[ERROR] Обработка завершена с ошибками")
        return

    urls_path = args.urls_file or str((Path(__file__).resolve().parents[1] / "urls.txt"))
    if os.path.exists(urls_path):
        with open(urls_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
        results = {}
        for url in urls:
            results[url] = extractor.process_url(url, args.language)
        failed = [url for url, ok in results.items() if not ok]
        if failed:
            logger.error("\n[ERROR] Неудачные URL:")
            for url in failed:
                logger.error("   - %s", url)
        return

    logger.error("[ERROR] Укажите --url или --urls-file (или создайте urls.txt в корне проекта)")
    parser.print_help()

if __name__ == "__main__":
    main()
