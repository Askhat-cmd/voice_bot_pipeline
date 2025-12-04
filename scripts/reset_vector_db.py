#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для удаления всех старых коллекций ChromaDB перед миграцией на Sentence-Transformers
"""

import sys
import logging
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from vector_db import VectorDBManager
import yaml

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Удаляет все коллекции ChromaDB для переиндексации с новой моделью"""
    
    # Загрузка конфигурации
    config_path = Path("config.yaml")
    if not config_path.exists():
        logger.error(f"Файл конфигурации не найден: {config_path}")
        return 1
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    if 'vector_db' not in config:
        logger.error("Секция vector_db не найдена в config.yaml")
        return 1
    
    # Инициализация менеджера БД
    db_manager = VectorDBManager(
        db_path=config['vector_db']['db_path'],
        collection_prefix=config['vector_db']['collection_prefix']
    )
    
    # Список всех коллекций
    collections = db_manager.list_collections()
    
    if not collections:
        logger.info("✅ Коллекции не найдены, база данных пуста")
        return 0
    
    logger.warning(f"⚠️  Найдено коллекций: {len(collections)}")
    for col in collections:
        logger.info(f"   - {col}")
    
    # Подтверждение
    logger.warning("\n⚠️  ВНИМАНИЕ: Все коллекции будут удалены!")
    logger.warning("   Это необходимо для переиндексации с новой моделью Sentence-Transformers")
    
    # Удаление всех коллекций через reset
    try:
        db_manager.reset_database()
        logger.info("✅ Все коллекции успешно удалены")
        logger.info("   Теперь можно запустить индексацию заново с новой моделью")
        return 0
    except Exception as e:
        logger.error(f"❌ Ошибка при удалении коллекций: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

