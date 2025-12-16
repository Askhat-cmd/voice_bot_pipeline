#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для полного парсинга канала YouTube Сарсекенова
Получает список все видео канала с метаданными и сохраняет в Markdown документ
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
from collections import defaultdict

# Добавляем родительскую директорию в путь для импорта модулей
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from env_utils import load_env
from utils.video_registry import VideoRegistry

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    HAS_GOOGLE_API = True
except ImportError:
    HAS_GOOGLE_API = False
    print("[ERROR] google-api-python-client не установлен. Установите: pip install google-api-python-client")
    sys.exit(1)

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("[WARNING] tqdm не установлен. Прогресс-бар будет недоступен.")


class ChannelParser:
    """Парсер канала YouTube для получения всех видео и их метаданных"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Инициализация парсера канала.
        
        Args:
            api_key: YouTube Data API ключ. Если не указан, берется из YOUTUBE_API_KEY env.
        """
        load_env()
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        self.youtube = None
        
        if not self.api_key:
            raise ValueError("YOUTUBE_API_KEY не найден в переменных окружения")
        
        if HAS_GOOGLE_API:
            try:
                self.youtube = build('youtube', 'v3', developerKey=self.api_key)
            except Exception as e:
                raise RuntimeError(f"Не удалось инициализировать YouTube API: {e}")
        else:
            raise RuntimeError("google-api-python-client не установлен")
    
    @staticmethod
    def extract_channel_handle(url: str) -> str:
        """
        Извлечение handle канала из URL.
        
        Args:
            url: URL канала (например, https://www.youtube.com/@Salsar/videos)
        
        Returns:
            Handle канала без @ (например, 'Salsar')
        """
        # Паттерн для handle: @username
        match = re.search(r'@([a-zA-Z0-9_-]+)', url)
        if match:
            return match.group(1)
        
        # Паттерн для channel_id: UC...
        match = re.search(r'channel/([a-zA-Z0-9_-]+)', url)
        if match:
            return match.group(1)
        
        raise ValueError(f"Не удалось извлечь handle или channel_id из: {url}")
    
    def get_channel_id(self, handle: str) -> Dict[str, str]:
        """
        Получение channel_id и uploadPlaylistId по handle канала.
        
        Args:
            handle: Handle канала (например, 'Salsar')
        
        Returns:
            Словарь с channel_id и uploadPlaylistId
        """
        try:
            # Пробуем получить через forHandle (новый способ для @handle)
            request = self.youtube.channels().list(
                part='contentDetails',
                forHandle=handle
            )
            response = request.execute()
            
            if response.get('items'):
                channel_id = response['items'][0]['id']
                upload_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                return {
                    'channel_id': channel_id,
                    'upload_playlist_id': upload_playlist_id
                }
            
            # Если не получилось, пробуем через forUsername (старый способ)
            request = self.youtube.channels().list(
                part='contentDetails',
                forUsername=handle
            )
            response = request.execute()
            
            if response.get('items'):
                channel_id = response['items'][0]['id']
                upload_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                return {
                    'channel_id': channel_id,
                    'upload_playlist_id': upload_playlist_id
                }
            
            # Если handle это уже channel_id
            if handle.startswith('UC'):
                request = self.youtube.channels().list(
                    part='contentDetails',
                    id=handle
                )
                response = request.execute()
                
                if response.get('items'):
                    channel_id = response['items'][0]['id']
                    upload_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                    return {
                        'channel_id': channel_id,
                        'upload_playlist_id': upload_playlist_id
                    }
            
            raise ValueError(f"Канал '{handle}' не найден")
            
        except HttpError as e:
            raise RuntimeError(f"Ошибка YouTube API при получении channel_id: {e}")
    
    def get_all_video_ids(self, upload_playlist_id: str) -> List[str]:
        """
        Получение всех video_id из плейлиста загрузок канала.
        
        Args:
            upload_playlist_id: ID плейлиста загрузок канала
        
        Returns:
            Список всех video_id
        """
        video_ids = []
        next_page_token = None
        
        print(f"[INFO] Получение списка всех видео канала...")
        
        while True:
            try:
                request = self.youtube.playlistItems().list(
                    part='contentDetails',
                    playlistId=upload_playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
                )
                response = request.execute()
                
                items = response.get('items', [])
                for item in items:
                    video_id = item['contentDetails']['videoId']
                    video_ids.append(video_id)
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
                    
            except HttpError as e:
                raise RuntimeError(f"Ошибка YouTube API при получении списка видео: {e}")
        
        print(f"[OK] Найдено видео: {len(video_ids)}")
        return video_ids
    
    def get_videos_metadata(self, video_ids: List[str]) -> List[Dict]:
        """
        Получение метаданных для списка видео (батчинг).
        
        Args:
            video_ids: Список video_id
        
        Returns:
            Список словарей с метаданными видео
        """
        videos_metadata = []
        batch_size = 50  # Максимум 50 видео за запрос
        
        print(f"[INFO] Получение метаданных для {len(video_ids)} видео...")
        
        iterator = range(0, len(video_ids), batch_size)
        if HAS_TQDM:
            iterator = tqdm(iterator, desc="Обработка видео")
        
        for i in iterator:
            batch_ids = video_ids[i:i + batch_size]
            
            try:
                request = self.youtube.videos().list(
                    part='snippet,statistics,contentDetails',
                    id=','.join(batch_ids)
                )
                response = request.execute()
                
                for item in response.get('items', []):
                    snippet = item['snippet']
                    statistics = item.get('statistics', {})
                    content_details = item.get('contentDetails', {})
                    
                    # Парсинг длительности из ISO 8601 (PT1H23M45S)
                    duration_str = content_details.get('duration', 'PT0S')
                    duration_seconds = self._parse_duration(duration_str)
                    
                    videos_metadata.append({
                        'video_id': item['id'],
                        'title': snippet.get('title', 'Без названия'),
                        'published_at': snippet.get('publishedAt', ''),
                        'view_count': int(statistics.get('viewCount', 0)),
                        'duration_seconds': duration_seconds,
                        'url': f"https://www.youtube.com/watch?v={item['id']}"
                    })
                    
            except HttpError as e:
                print(f"[WARNING] Ошибка при получении метаданных для батча {i}: {e}")
                continue
        
        return videos_metadata
    
    def get_channel_playlists(self, channel_id: str) -> Dict[str, str]:
        """
        Получение всех плейлистов канала.
        
        Args:
            channel_id: ID канала
        
        Returns:
            Словарь {playlist_id: playlist_title}
        """
        playlists = {}
        next_page_token = None
        
        print(f"[INFO] Получение списка плейлистов канала...")
        
        while True:
            try:
                request = self.youtube.playlists().list(
                    part='snippet',
                    channelId=channel_id,
                    maxResults=50,
                    pageToken=next_page_token
                )
                response = request.execute()
                
                items = response.get('items', [])
                for item in items:
                    playlist_id = item['id']
                    playlist_title = item['snippet']['title']
                    playlists[playlist_id] = playlist_title
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
                    
            except HttpError as e:
                print(f"[WARNING] Ошибка при получении плейлистов: {e}")
                break
        
        print(f"[OK] Найдено плейлистов: {len(playlists)}")
        return playlists
    
    def get_playlist_videos(self, playlist_id: str) -> Set[str]:
        """
        Получение всех video_id из плейлиста.
        
        Args:
            playlist_id: ID плейлиста
        
        Returns:
            Множество video_id в плейлисте
        """
        video_ids = set()
        next_page_token = None
        
        while True:
            try:
                request = self.youtube.playlistItems().list(
                    part='contentDetails',
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
                )
                response = request.execute()
                
                items = response.get('items', [])
                for item in items:
                    video_id = item['contentDetails']['videoId']
                    video_ids.add(video_id)
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
                    
            except HttpError:
                # Игнорируем ошибки для отдельных плейлистов
                break
        
        return video_ids
    
    def map_videos_to_playlists(self, video_ids: List[str], channel_playlists: Dict[str, str]) -> Dict[str, List[str]]:
        """
        Создание карты соответствия видео -> плейлисты.
        Оптимизированная версия: получаем все видео из каждого плейлиста один раз.
        
        Args:
            video_ids: Список всех video_id канала
            channel_playlists: Словарь всех плейлистов канала {playlist_id: title}
        
        Returns:
            Словарь {video_id: [playlist_titles]}
        """
        video_playlists_map = defaultdict(list)
        
        print(f"[INFO] Определение принадлежности видео к плейлистам...")
        
        # Создаем множество для быстрого поиска
        video_ids_set = set(video_ids)
        
        iterator = channel_playlists.items()
        if HAS_TQDM:
            iterator = tqdm(channel_playlists.items(), desc="Обработка плейлистов")
        
        for playlist_id, playlist_title in iterator:
            playlist_videos = self.get_playlist_videos(playlist_id)
            
            # Находим пересечение: какие видео канала есть в этом плейлисте
            common_videos = video_ids_set & playlist_videos
            
            for video_id in common_videos:
                video_playlists_map[video_id].append(playlist_title)
        
        return video_playlists_map
    
    def format_date(self, iso_date: str) -> str:
        """
        Форматирование даты из ISO формата в DD.MM.YYYY.
        
        Args:
            iso_date: Дата в ISO формате (например, '2024-03-15T18:30:00Z')
        
        Returns:
            Дата в формате DD.MM.YYYY
        """
        try:
            dt = datetime.fromisoformat(iso_date.replace('Z', '+00:00'))
            return dt.strftime('%d.%m.%Y')
        except:
            return iso_date
    
    def format_view_count(self, count: int) -> str:
        """
        Форматирование количества просмотров для читаемости.
        
        Args:
            count: Количество просмотров
        
        Returns:
            Отформатированная строка (например, '1 234 567')
        """
        return f"{count:,}".replace(',', ' ')
    
    @staticmethod
    def _parse_duration(duration_str: str) -> int:
        """
        Парсинг ISO 8601 duration в секунды.
        
        Args:
            duration_str: Длительность в формате ISO 8601 (например, 'PT1H23M45S')
        
        Returns:
            Длительность в секундах
        """
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
        match = re.match(pattern, duration_str)
        
        if not match:
            return 0
        
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        
        return hours * 3600 + minutes * 60 + seconds
    
    def format_duration(self, seconds: int) -> str:
        """
        Форматирование длительности из секунд в читаемый формат.
        
        Args:
            seconds: Длительность в секундах
        
        Returns:
            Отформатированная строка (например, '1:23:45' или '45:30')
        """
        if seconds == 0:
            return '0:00'
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
    
    def save_to_markdown(self, videos_metadata: List[Dict], video_playlists_map: Dict[str, List[str]], 
                        output_path: Path, registry: Optional[VideoRegistry] = None) -> None:
        """
        Сохранение результатов в Markdown файл.
        
        Args:
            videos_metadata: Список метаданных видео
            video_playlists_map: Карта видео -> плейлисты
            output_path: Путь к выходному файлу
            registry: Реестр видео для проверки статуса обработки (опционально)
        """
        # Сортировка по дате публикации (новые сначала)
        videos_metadata.sort(key=lambda x: x['published_at'], reverse=True)
        
        # Загружаем реестр если не передан
        if registry is None:
            registry_path = Path(__file__).resolve().parent.parent / "data" / "video_registry.json"
            if registry_path.exists():
                try:
                    registry = VideoRegistry(str(registry_path))
                except:
                    registry = None
        
        # Формирование содержимого Markdown
        lines = []
        lines.append("# Список видео канала Сарсекенова\n")
        lines.append(f"**Дата парсинга:** {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        lines.append(f"**Всего видео:** {len(videos_metadata)}\n")
        lines.append("| № | Дата публикации | Название | Плейлист | Просмотры | Длительность | Статус | Дата обработки | Ссылка |")
        lines.append("|---|----------------|----------|----------|-----------|--------------|--------|----------------|--------|")
        
        for idx, video in enumerate(videos_metadata, 1):
            video_id = video['video_id']
            date = self.format_date(video['published_at'])
            title = video['title'].replace('|', '\\|')  # Экранирование для таблицы
            playlists = video_playlists_map.get(video_id, [])
            playlist_str = ', '.join(playlists) if playlists else 'Нет плейлиста'
            playlist_str = playlist_str.replace('|', '\\|')  # Экранирование
            views = self.format_view_count(video['view_count'])
            duration = self.format_duration(video.get('duration_seconds', 0))
            url = video['url']
            
            # Проверяем статус обработки
            status_symbol = '[ ]'  # Не обработано
            processed_date = ''
            
            if registry and registry.video_exists(video_id):
                video_data = registry.data["videos"].get(video_id, {})
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
            
            lines.append(f"| {idx} | {date} | {title} | {playlist_str} | {views} | {duration} | {status_symbol} | {processed_date} | [Ссылка]({url}) |")
        
        # Сохранение файла
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"[OK] Результаты сохранены в: {output_path}")
    
    def save_to_json(self, videos_metadata: List[Dict], video_playlists_map: Dict[str, List[str]], 
                    output_path: Path) -> None:
        """
        Сохранение результатов в JSON файл для программного использования.
        
        Args:
            videos_metadata: Список метаданных видео
            video_playlists_map: Карта видео -> плейлисты
            output_path: Путь к выходному файлу
        """
        import json
        
        # Сортировка по дате публикации (новые сначала) - должна совпадать с Markdown
        videos_metadata.sort(key=lambda x: x['published_at'], reverse=True)
        
        # Формирование JSON структуры
        json_data = {
            "metadata": {
                "parsed_at": datetime.now().isoformat(),
                "parsed_at_formatted": datetime.now().strftime('%d.%m.%Y %H:%M'),
                "total_videos": len(videos_metadata),
                "channel_url": "https://www.youtube.com/@Salsar/videos"
            },
            "videos": []
        }
        
        for idx, video in enumerate(videos_metadata, 1):
            video_id = video['video_id']
            playlists = video_playlists_map.get(video_id, [])
            
            video_entry = {
                "number": idx,
                "video_id": video_id,
                "url": video['url'],
                "title": video['title'],
                "published_date": video['published_at'],
                "published_date_formatted": self.format_date(video['published_at']),
                "view_count": video['view_count'],
                "view_count_formatted": self.format_view_count(video['view_count']),
                "duration_seconds": video.get('duration_seconds', 0),
                "duration_formatted": self.format_duration(video.get('duration_seconds', 0)),
                "playlists": playlists if playlists else []
            }
            
            json_data["videos"].append(video_entry)
        
        # Сохранение файла
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        print(f"[OK] JSON результаты сохранены в: {output_path}")


def main():
    """Основная функция скрипта"""
    channel_url = "https://www.youtube.com/@Salsar/videos"
    data_dir = Path(__file__).resolve().parent.parent / "data" / "channel_video_list"
    md_output_path = data_dir / "channel_videos_list.md"
    json_output_path = data_dir / "channel_videos_list.json"
    
    print("=" * 60)
    print("Парсинг канала YouTube Сарсекенова")
    print("=" * 60)
    print(f"Канал: {channel_url}")
    print(f"Markdown файл: {md_output_path}")
    print(f"JSON файл: {json_output_path}")
    print()
    
    try:
        # Инициализация парсера
        parser = ChannelParser()
        
        # Извлечение handle канала
        handle = parser.extract_channel_handle(channel_url)
        print(f"[INFO] Handle канала: @{handle}")
        
        # Получение channel_id и upload_playlist_id
        channel_info = parser.get_channel_id(handle)
        channel_id = channel_info['channel_id']
        upload_playlist_id = channel_info['upload_playlist_id']
        print(f"[INFO] Channel ID: {channel_id}")
        print(f"[INFO] Upload Playlist ID: {upload_playlist_id}\n")
        
        # Получение всех video_id
        video_ids = parser.get_all_video_ids(upload_playlist_id)
        
        if not video_ids:
            print("[WARNING] Видео не найдено")
            return
        
        # Получение метаданных видео
        videos_metadata = parser.get_videos_metadata(video_ids)
        
        # Получение плейлистов канала
        channel_playlists = parser.get_channel_playlists(channel_id)
        
        # Определение принадлежности видео к плейлистам
        video_playlists_map = parser.map_videos_to_playlists(video_ids, channel_playlists)
        
        # Загружаем реестр для проверки статусов
        registry_path = Path(__file__).resolve().parent.parent / "data" / "video_registry.json"
        registry = None
        if registry_path.exists():
            try:
                registry = VideoRegistry(str(registry_path))
            except:
                pass
        
        # Сохранение результатов в оба формата
        parser.save_to_markdown(videos_metadata, video_playlists_map, md_output_path, registry)
        parser.save_to_json(videos_metadata, video_playlists_map, json_output_path)
        
        print("\n" + "=" * 60)
        print("[OK] Парсинг завершен успешно!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] Ошибка при выполнении скрипта: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

