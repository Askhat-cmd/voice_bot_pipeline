#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест скорости векторизации после оптимизации
"""

import time
import logging
from pathlib import Path
import sys
import json

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from vector_db import VectorDBManager, EmbeddingService, VectorIndexer
import yaml

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


def test_vectorization_speed():
    """Тестирует скорость векторизации одного документа"""
    
    # Загрузка конфигурации
    config_path = Path("config.yaml")
    if not config_path.exists():
        logger.error(f"❌ Файл конфигурации не найден: {config_path}")
        return
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    logger.info("=" * 80)
    logger.info("🧪 ТЕСТ СКОРОСТИ ВЕКТОРИЗАЦИИ")
    logger.info("=" * 80)
    
    # Вывод текущей конфигурации
    rate_config = config['vector_db']['rate_limiting']
    logger.info(f"\n📋 Текущая конфигурация:")
    logger.info(f"   chunk_size: {rate_config['chunk_size']}")
    logger.info(f"   delay_between_requests: {rate_config['delay_between_requests']}s")
    logger.info(f"   max_workers: {rate_config['max_workers']}")
    
    # Инициализация компонентов
    db_manager = VectorDBManager(
        db_path=config['vector_db']['db_path'],
        collection_prefix=config['vector_db']['collection_prefix']
    )
    
    # Настройки rate limiting из config
    rate_limiting = config['vector_db'].get('rate_limiting', {})
    text_processing = config['vector_db'].get('text_processing', {})
    embedding_service = EmbeddingService(
        model=config['vector_db']['embedding']['model'],
        chunk_size=rate_limiting.get('chunk_size', 2048),
        delay_between_requests=rate_limiting.get('delay_between_requests', 0.5),
        max_retries=rate_limiting.get('max_retries', 5),
        retry_delay=rate_limiting.get('retry_delay', 2.0),
        max_retry_delay=rate_limiting.get('max_retry_delay', 60.0),
        max_tokens_per_text=text_processing.get('max_tokens_per_text', 8000),
        chunk_overlap=text_processing.get('chunk_overlap', 100),
        max_workers=rate_limiting.get('max_workers', 3)
    )
    
    indexer = VectorIndexer(
        db_manager=db_manager,
        embedding_service=embedding_service,
        batch_size=config['vector_db'].get('batch_size', 100)
    )
    
    # Поиск тестового файла
    sag_final_dir = Path("data/sag_final")
    test_files = list(sag_final_dir.glob("*.for_vector.json"))
    
    if not test_files:
        logger.error("❌ Нет файлов для тестирования в data/sag_final/")
        return
    
    test_file = test_files[0]
    logger.info(f"\n📄 Тестовый файл: {test_file.name}")
    
    # Загрузка данных для статистики
    with open(test_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    blocks_count = len(data.get('blocks', []))
    graph_entities_count = len(data.get('graph_entities', []))
    documents_count = 1 if data.get('document_title') or data.get('document_summary') else 0
    
    logger.info(f"   📊 Документов: {documents_count}")
    logger.info(f"   📊 Блоков: {blocks_count}")
    logger.info(f"   📊 Граф-сущностей: {graph_entities_count}")
    logger.info(f"   📊 Всего элементов: {documents_count + blocks_count + graph_entities_count}")
    
    # Очистка коллекций перед тестом
    logger.info(f"\n🧹 Очистка тестовых коллекций...")
    for level in ['documents', 'blocks', 'graph_entities']:
        try:
            db_manager.delete_collection(level)
            logger.debug(f"   Удалена коллекция: {level}")
        except Exception as e:
            logger.debug(f"   Коллекция {level} не существует или ошибка удаления: {e}")
    
    # Запуск теста
    logger.info(f"\n⏱️  НАЧАЛО ИНДЕКСАЦИИ...")
    logger.info("=" * 80)
    
    start_time = time.time()
    
    result = indexer.index_sag_file(
        test_file,
        index_levels=['documents', 'blocks', 'graph_entities']
    )
    
    elapsed = time.time() - start_time
    
    logger.info("=" * 80)
    logger.info(f"⏱️  ИНДЕКСАЦИЯ ЗАВЕРШЕНА")
    logger.info("=" * 80)
    
    # Результаты
    logger.info(f"\n📊 РЕЗУЛЬТАТЫ:")
    logger.info(f"   ⏱️  Общее время: {elapsed:.2f} секунд")
    
    total_items = sum([
        result.get('indexed', {}).get('documents', 0),
        result.get('indexed', {}).get('blocks', 0),
        result.get('indexed', {}).get('graph_entities', 0)
    ])
    
    if total_items > 0 and elapsed > 0:
        speed = total_items / elapsed
        logger.info(f"   ⚡ Скорость: {speed:.1f} элементов/сек")
    else:
        logger.warning(f"   ⚠️  Не удалось рассчитать скорость (элементов: {total_items}, время: {elapsed:.2f}s)")
    
    if result['success']:
        logger.info(f"   ✅ Статус: УСПЕШНО")
        logger.info(f"   📄 Документов: {result.get('indexed', {}).get('documents', 0)}")
        logger.info(f"   📦 Блоков: {result.get('indexed', {}).get('blocks', 0)}")
        logger.info(f"   🕸️  Граф-сущностей: {result.get('indexed', {}).get('graph_entities', 0)}")
    else:
        logger.error(f"   ❌ Статус: ОШИБКА")
        logger.error(f"   ❌ Детали: {result.get('error', 'Unknown')}")
    
    # Оценка производительности
    logger.info(f"\n🎯 ОЦЕНКА ПРОИЗВОДИТЕЛЬНОСТИ:")
    if elapsed < 2:
        logger.info(f"   🚀 ОТЛИЧНО! Индексация очень быстрая (< 2 сек)")
    elif elapsed < 10:
        logger.info(f"   ✅ ХОРОШО! Индексация быстрая (< 10 сек)")
    elif elapsed < 30:
        logger.info(f"   ⚠️  СРЕДНЕ! Можно улучшить (< 30 сек)")
    else:
        logger.info(f"   ❌ МЕДЛЕННО! Требуется оптимизация (> 30 сек)")
    
    logger.info(f"\n💡 РЕКОМЕНДАЦИИ:")
    if elapsed > 10:
        logger.info(f"   1. Проверьте использование батч-обработки в vector_indexer.py")
        logger.info(f"   2. Уменьшите delay_between_requests до 0.5s в config.yaml")
        logger.info(f"   3. Увеличьте max_workers до 3 в config.yaml")
    else:
        logger.info(f"   ✅ Система работает оптимально!")


if __name__ == "__main__":
    test_vectorization_speed()

