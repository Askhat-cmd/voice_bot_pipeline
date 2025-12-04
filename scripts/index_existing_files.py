#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилита для индексации существующих SAG v2.0 JSON файлов в векторную базу данных
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from vector_db import VectorDBManager, EmbeddingService, VectorIndexer
from env_utils import load_env
import yaml

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Индексация существующих SAG v2.0 JSON файлов в векторную БД"
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Путь к файлу конфигурации (по умолчанию: config.yaml)"
    )
    parser.add_argument(
        "--input-dir",
        default="data/sag_final",
        help="Директория с SAG v2.0 JSON файлами (по умолчанию: data/sag_final)"
    )
    parser.add_argument(
        "--pattern",
        default="*.for_vector.json",
        help="Шаблон для поиска файлов (по умолчанию: *.for_vector.json)"
    )
    parser.add_argument(
        "--levels",
        nargs="+",
        default=["documents", "blocks", "graph_entities"],
        choices=["documents", "blocks", "graph_entities"],
        help="Уровни для индексации (по умолчанию: все)"
    )
    
    args = parser.parse_args()
    
    # Загрузка переменных окружения
    load_env()
    
    # Загрузка конфигурации
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Файл конфигурации не найден: {config_path}")
        return 1
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    if 'vector_db' not in config:
        logger.error("Секция vector_db не найдена в config.yaml")
        return 1
    
    # Инициализация компонентов
    try:
        db_manager = VectorDBManager(
            db_path=config['vector_db']['db_path'],
            collection_prefix=config['vector_db']['collection_prefix']
        )
        
        # Модель: сначала из env, потом из config
        embedding_model = os.getenv("SENTENCE_TRANSFORMERS_MODEL") or config['vector_db']['embedding'].get('model')
        embedding_service = EmbeddingService(model=embedding_model)
        indexer = VectorIndexer(
            db_manager=db_manager,
            embedding_service=embedding_service,
            batch_size=config['vector_db'].get('batch_size', 100)
        )
    except Exception as e:
        logger.error(f"Ошибка при инициализации компонентов: {e}", exc_info=True)
        return 1
    
    # Поиск файлов для индексации
    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        logger.error(f"Директория не найдена: {input_dir}")
        return 1
    
    json_files = list(input_dir.glob(args.pattern))
    if not json_files:
        logger.warning(f"Не найдено файлов по шаблону {args.pattern} в {input_dir}")
        return 0
    
    logger.info(f"📂 Найдено файлов для индексации: {len(json_files)}")
    
    # Индексация файлов
    results = {
        "total_files": len(json_files),
        "successful": 0,
        "failed": 0,
        "details": []
    }
    
    for i, json_file in enumerate(json_files, 1):
        logger.info(f"📝 [{i}/{len(json_files)}] Индексация: {json_file.name}")
        
        try:
            result = indexer.index_sag_file(json_file, index_levels=args.levels)
            results["details"].append(result)
            
            if result["success"]:
                results["successful"] += 1
                logger.info(
                    f"✅ Успешно: документов={result['indexed']['documents']}, "
                    f"блоков={result['indexed']['blocks']}, "
                    f"сущностей={result['indexed']['graph_entities']}"
                )
            else:
                results["failed"] += 1
                logger.error(f"❌ Ошибка: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            results["failed"] += 1
            logger.error(f"❌ Исключение при индексации {json_file.name}: {e}", exc_info=True)
            results["details"].append({
                "file": str(json_file),
                "success": False,
                "error": str(e)
            })
    
    # Итоговая статистика
    logger.info("\n" + "="*60)
    logger.info("📊 ИТОГОВАЯ СТАТИСТИКА ИНДЕКСАЦИИ")
    logger.info("="*60)
    logger.info(f"Всего файлов: {results['total_files']}")
    logger.info(f"✅ Успешно: {results['successful']}")
    logger.info(f"❌ Ошибок: {results['failed']}")
    
    if results['successful'] > 0:
        total_docs = sum(d.get('indexed', {}).get('documents', 0) for d in results['details'] if d.get('success'))
        total_blocks = sum(d.get('indexed', {}).get('blocks', 0) for d in results['details'] if d.get('success'))
        total_entities = sum(d.get('indexed', {}).get('graph_entities', 0) for d in results['details'] if d.get('success'))
        
        logger.info(f"\n📈 Проиндексировано:")
        logger.info(f"  - Документов: {total_docs}")
        logger.info(f"  - Блоков: {total_blocks}")
        logger.info(f"  - Граф-сущностей: {total_entities}")
    
    # Сохранение результатов
    results_file = input_dir / "indexing_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"\n💾 Результаты сохранены: {results_file}")
    
    return 0 if results['failed'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

