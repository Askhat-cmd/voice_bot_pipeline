#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI для управления реестром видео
"""

import sys
from pathlib import Path

# Добавляем родительскую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import click
except ImportError:
    print("[ERROR] Не установлена библиотека click")
    print("Установите: pip install click")
    sys.exit(1)

from utils.video_registry import VideoRegistry


@click.group()
def cli():
    """Управление реестром видео"""
    pass


@cli.command()
@click.option('--registry-path', default='data/video_registry.json', help='Путь к файлу реестра')
def stats(registry_path):
    """Показать статистику"""
    registry = VideoRegistry(registry_path)
    stats = registry.get_statistics()
    
    click.echo("\n📊 Статистика реестра видео:")
    click.echo("=" * 50)
    click.echo(f"Всего видео:      {stats['total_videos']}")
    click.echo(f"Обработано:       {stats['processed']}")
    click.echo(f"Ошибок:           {stats['failed']}")
    click.echo(f"В очереди:        {stats['pending']}")
    click.echo(f"Всего блоков:     {stats['total_blocks']}")
    click.echo(f"Всего сущностей:  {stats['total_entities']}")
    click.echo(f"Затраты API:      ${stats['total_api_cost']}")
    if stats['processed'] > 0:
        click.echo(f"Средний блоков/видео: {stats['avg_blocks_per_video']}")
    click.echo("=" * 50)


@cli.command()
@click.argument('video_id')
@click.option('--registry-path', default='data/video_registry.json', help='Путь к файлу реестра')
def info(video_id, registry_path):
    """Информация о конкретном видео"""
    registry = VideoRegistry(registry_path)
    video = registry.get_video(video_id)
    
    if not video:
        click.echo(f"❌ Видео {video_id} не найдено")
        return
    
    click.echo(f"\n📹 Информация о видео {video_id}:")
    click.echo("=" * 60)
    click.echo(f"Название:  {video['title']}")
    click.echo(f"Канал:     {video['channel']}")
    click.echo(f"Дата:      {video['published_date']}")
    click.echo(f"Статус:    {video['status']}")
    click.echo(f"URL:       {video['url']}")
    
    if video.get('processing_history'):
        click.echo(f"\nИстория обработки:")
        for i, record in enumerate(video['processing_history'], 1):
            click.echo(f"  {i}. {record['processed_at']}")
            click.echo(f"     Блоков: {record['blocks_created']}, Сущностей: {record['entities_extracted']}")
            click.echo(f"     Время: {record['processing_time_seconds']:.1f}s, Стоимость: ${record['api_cost_estimate']}")
            if record.get('error_message'):
                click.echo(f"     Ошибка: {record['error_message']}")
    
    if video.get('files'):
        click.echo(f"\nФайлы:")
        for file_type, file_path in video['files'].items():
            click.echo(f"  {file_type}: {file_path}")
    
    click.echo("=" * 60)


@cli.command()
@click.option('--registry-path', default='data/video_registry.json', help='Путь к файлу реестра')
def pending(registry_path):
    """Список необработанных видео"""
    registry = VideoRegistry(registry_path)
    pending_list = registry.get_pending_videos()
    
    click.echo(f"\n📋 Необработанные видео ({len(pending_list)}):")
    for video_id in pending_list:
        video = registry.get_video(video_id)
        click.echo(f"  • {video_id}: {video['title']}")


@cli.command()
@click.option('--registry-path', default='data/video_registry.json', help='Путь к файлу реестра')
def failed(registry_path):
    """Список проблемных видео"""
    registry = VideoRegistry(registry_path)
    failed_list = registry.get_failed_videos()
    
    click.echo(f"\n❌ Проблемные видео ({len(failed_list)}):")
    for video_id in failed_list:
        video = registry.get_video(video_id)
        click.echo(f"  • {video_id}: {video['title']}")
        
        # Показываем последнюю ошибку
        if video.get('processing_history'):
            last_record = video['processing_history'][-1]
            if last_record.get('error_message'):
                click.echo(f"    Ошибка: {last_record['error_message']}")


if __name__ == '__main__':
    cli()

