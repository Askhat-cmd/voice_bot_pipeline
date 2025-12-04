#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Получение метаданных видео с YouTube через YouTube Data API v3
"""

import os
import re
from typing import Dict, Optional
from datetime import datetime

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    HAS_GOOGLE_API = True
except ImportError:
    HAS_GOOGLE_API = False

from youtube_transcript_api import YouTubeTranscriptApi


class YouTubeAPIMetadataFetcher:
    """
    Получение полных метаданных через YouTube Data API v3.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Инициализация с API ключом.
        
        Args:
            api_key: YouTube Data API ключ. Если не указан, берется из YOUTUBE_API_KEY env.
        """
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        self.youtube = None
        
        if self.api_key and HAS_GOOGLE_API:
            try:
                self.youtube = build('youtube', 'v3', developerKey=self.api_key)
            except Exception as e:
                print(f"[WARNING] Не удалось инициализировать YouTube API: {e}")
                self.youtube = None
    
    @staticmethod
    def extract_video_id(url: str) -> str:
        """Извлечение video_id из URL"""
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'^([0-9A-Za-z_-]{11})$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        raise ValueError(f"Не удалось извлечь video_id из: {url}")
    
    def fetch_metadata(self, video_url: str) -> Dict[str, any]:
        """
        Получение полных метаданных видео через YouTube Data API.
        
        Args:
            video_url: URL видео или video_id
        
        Returns:
            Словарь с метаданными
        """
        video_id = self.extract_video_id(video_url)
        
        # Пытаемся получить метаданные через API
        if self.youtube:
            try:
                return self._fetch_via_api(video_id)
            except HttpError as e:
                print(f"[WARNING] Ошибка YouTube API для {video_id}: {e}")
                # Fallback на базовый метод
                return self._fetch_basic_metadata(video_id)
            except Exception as e:
                print(f"[WARNING] Неожиданная ошибка при получении метаданных {video_id}: {e}")
                return self._fetch_basic_metadata(video_id)
        else:
            # Если API недоступен, используем базовый метод
            return self._fetch_basic_metadata(video_id)
    
    def _fetch_via_api(self, video_id: str) -> Dict[str, any]:
        """Получение метаданных через YouTube Data API v3"""
        request = self.youtube.videos().list(
            part='snippet,contentDetails',
            id=video_id
        )
        response = request.execute()
        
        if not response.get('items'):
            raise ValueError(f"Видео {video_id} не найдено")
        
        item = response['items'][0]
        snippet = item['snippet']
        content = item['contentDetails']
        
        # Парсинг duration из ISO 8601 (PT1H23M45S)
        duration = self._parse_duration(content.get('duration', 'PT0S'))
        
        return {
            "video_id": video_id,
            "title": snippet.get('title', f"Video {video_id}"),
            "channel": snippet.get('channelTitle', 'Unknown'),
            "published_date": snippet.get('publishedAt', datetime.now().isoformat()),
            "duration_seconds": duration,
            "description": snippet.get('description', ''),
            "tags": snippet.get('tags', []),
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "has_subtitles": self._check_subtitles(video_id),
            "subtitle_type": self._get_subtitle_type(video_id),
            "language": snippet.get('defaultAudioLanguage') or snippet.get('defaultLanguage', 'ru')
        }
    
    def _fetch_basic_metadata(self, video_id: str) -> Dict[str, any]:
        """Базовое получение метаданных без API (только проверка субтитров)"""
        has_subtitles, subtitle_type = self._check_subtitles_with_type(video_id)
        
        return {
            "video_id": video_id,
            "title": f"Video {video_id}",  # ВРЕМЕННО
            "channel": "Unknown",  # ВРЕМЕННО
            "published_date": datetime.now().isoformat(),  # ВРЕМЕННО
            "duration_seconds": 0,  # ВРЕМЕННО
            "description": "",
            "tags": [],
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "has_subtitles": has_subtitles,
            "subtitle_type": subtitle_type,
            "language": "ru"
        }
    
    def _check_subtitles(self, video_id: str) -> bool:
        """Проверка наличия субтитров"""
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            return True
        except:
            return False
    
    def _get_subtitle_type(self, video_id: str) -> str:
        """Определение типа субтитров"""
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            try:
                transcript = transcript_list.find_transcript(['ru'])
                return "manual" if not transcript.is_generated else "auto-generated"
            except:
                return "unknown"
        except:
            return "none"
    
    def _check_subtitles_with_type(self, video_id: str) -> tuple:
        """Проверка субтитров с определением типа"""
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            try:
                transcript = transcript_list.find_transcript(['ru'])
                return True, ("manual" if not transcript.is_generated else "auto-generated")
            except:
                return True, "unknown"
        except:
            return False, "none"
    
    @staticmethod
    def _parse_duration(duration_str: str) -> int:
        """Парсинг ISO 8601 duration в секунды"""
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
        match = re.match(pattern, duration_str)
        
        if not match:
            return 0
        
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        
        return hours * 3600 + minutes * 60 + seconds

