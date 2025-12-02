#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для поиска URL-ов с канала Саламата Сарсекенова
Помогает найти 50+ видео для пакетной обработки
"""

import requests
import json
import re
from typing import List, Dict
from urllib.parse import urlparse, parse_qs

def search_youtube_channel(channel_name: str = "Саламат Сарсекенов", max_results: int = 50) -> List[str]:
    """
    Поиск видео с канала по названию
    Внимание: Это упрощенный поиск, для реального использования нужен YouTube API
    """
    print(f"🔍 Поиск видео с канала: {channel_name}")
    print(f"📊 Максимум результатов: {max_results}")
    
    # Здесь должен быть реальный поиск через YouTube API
    # Пока возвращаем примеры URL-ов
    sample_urls = [
        "https://www.youtube.com/watch?v=4WjHEbOl88w",
        "https://www.youtube.com/watch?v=cGCdRqADR64", 
        "https://www.youtube.com/watch?v=hDtLWJApJDQ",
        "https://www.youtube.com/watch?v=j2YElLQ58FU",
        "https://www.youtube.com/watch?v=M1IjNj05YJU",
        # Добавьте сюда реальные URL-ы с канала Сарсекенова
    ]
    
    print(f"⚠️  Внимание: Это примеры URL-ов. Добавьте реальные URL-ы с канала Сарсекенова")
    print(f"📝 Найдено примеров: {len(sample_urls)}")
    
    return sample_urls

def validate_youtube_url(url: str) -> bool:
    """Проверка корректности YouTube URL"""
    youtube_patterns = [
        r'https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'https?://youtu\.be/([a-zA-Z0-9_-]{11})',
        r'https?://(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in youtube_patterns:
        if re.match(pattern, url):
            return True
    return False

def extract_video_id(url: str) -> str:
    """Извлечение video_id из YouTube URL"""
    patterns = [
        r'[?&]v=([a-zA-Z0-9_-]{11})',
        r'youtu\.be/([a-zA-Z0-9_-]{11})',
        r'embed/([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def create_urls_file(urls: List[str], filename: str = "test_urls_batch.txt") -> None:
    """Создание файла с URL-ами"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("# Тестовые URL-ы для пакетной обработки (50 видео)\n")
        f.write("# Канал Саламата Сарсекенова - нейросталкинг/неосталкинг\n\n")
        
        for i, url in enumerate(urls, 1):
            f.write(f"# Видео {i}\n")
            f.write(f"{url}\n\n")
    
    print(f"✅ Файл создан: {filename}")
    print(f"📊 Количество URL-ов: {len(urls)}")

def main():
    print("🎯 ПОИСК URL-ОВ С КАНАЛА САРСЕКЕНОВА")
    print("=" * 50)
    
    # Поиск URL-ов
    urls = search_youtube_channel()
    
    # Валидация URL-ов
    valid_urls = []
    invalid_urls = []
    
    for url in urls:
        if validate_youtube_url(url):
            valid_urls.append(url)
        else:
            invalid_urls.append(url)
    
    print(f"\n📊 Результаты валидации:")
    print(f"   ✅ Корректных URL-ов: {len(valid_urls)}")
    print(f"   ❌ Некорректных URL-ов: {len(invalid_urls)}")
    
    if invalid_urls:
        print(f"\n❌ Некорректные URL-ы:")
        for url in invalid_urls:
            print(f"   • {url}")
    
    # Создание файла
    if valid_urls:
        create_urls_file(valid_urls)
        
        print(f"\n🎯 СЛЕДУЮЩИЕ ШАГИ:")
        print(f"   1. Отредактируйте test_urls_batch.txt")
        print(f"   2. Добавьте реальные URL-ы с канала Сарсекенова")
        print(f"   3. Запустите: .\\scripts\\run_batch_processing.ps1")
    else:
        print(f"\n❌ Не найдено корректных URL-ов")

if __name__ == "__main__":
    main()



