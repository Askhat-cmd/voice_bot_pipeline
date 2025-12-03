#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилита для тестирования семантического поиска в векторной базе данных
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from vector_db import VectorDBManager, EmbeddingService, VectorSearch
import yaml

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)


def print_search_results(results: list, result_type: str):
    """Красивый вывод результатов поиска"""
    if not results:
        print(f"\n❌ {result_type}: результатов не найдено")
        return
    
    print(f"\n✅ {result_type}: найдено {len(results)} результатов")
    print("-" * 80)
    
    for i, result in enumerate(results, 1):
        print(f"\n[{i}] ID: {result['id']}")
        print(f"    Расстояние: {result.get('distance', 'N/A'):.4f}")
        
        metadata = result.get('metadata', {})
        if metadata:
            print(f"    Метаданные:")
            for key, value in list(metadata.items())[:5]:  # Первые 5 полей
                print(f"      - {key}: {value}")
        
        # Показываем первые 200 символов документа
        document = result.get('document', '')
        if document:
            preview = document[:200] + "..." if len(document) > 200 else document
            print(f"    Текст: {preview}")


def main():
    parser = argparse.ArgumentParser(
        description="Тестирование семантического поиска в векторной БД"
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Путь к файлу конфигурации (по умолчанию: config.yaml)"
    )
    parser.add_argument(
        "--query",
        required=True,
        help="Поисковый запрос"
    )
    parser.add_argument(
        "--type",
        choices=["documents", "blocks", "graph_entities", "hybrid", "test_embeddings"],
        default="hybrid",
        help="Тип поиска или тест (по умолчанию: hybrid). 'test_embeddings' - тест создания эмбеддингов"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Количество результатов (по умолчанию: 5)"
    )
    parser.add_argument(
        "--filter",
        help="Фильтр по метаданным в формате JSON (например: '{\"video_id\": \"xxx\"}')"
    )
    
    args = parser.parse_args()
    
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
        # Настройки rate limiting из config (используем оптимизированные значения)
        rate_limiting = config['vector_db'].get('rate_limiting', {})
        text_processing = config['vector_db'].get('text_processing', {})
        embedding_service = EmbeddingService(
            model=config['vector_db']['embedding']['model'],
            chunk_size=rate_limiting.get('chunk_size', 2048),
            delay_between_requests=rate_limiting.get('delay_between_requests', 15.0),
            max_retries=rate_limiting.get('max_retries', 5),
            retry_delay=rate_limiting.get('retry_delay', 2.0),
            max_retry_delay=rate_limiting.get('max_retry_delay', 60.0),
            max_tokens_per_text=text_processing.get('max_tokens_per_text', 8000),
            chunk_overlap=text_processing.get('chunk_overlap', 100),
            max_workers=rate_limiting.get('max_workers', 1)
        )
        search = VectorSearch(
            db_manager=db_manager,
            embedding_service=embedding_service
        )
    except Exception as e:
        logger.error(f"Ошибка при инициализации компонентов: {e}", exc_info=True)
        return 1
    
    # Парсинг фильтров
    filters = None
    if args.filter:
        try:
            filters = json.loads(args.filter)
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка при парсинге фильтров: {e}")
            return 1
    
    # Тест создания эмбеддингов
    if args.type == "test_embeddings":
        print(f"\n🧪 Тест создания эмбеддингов")
        print(f"📝 Текст: '{args.query}'")
        print("=" * 80)
        
        try:
            # Создаем эмбеддинг для одного текста
            print("\n⏳ Создание эмбеддинга...")
            embedding = embedding_service.create_embedding(args.query)
            
            print(f"✅ Эмбеддинг успешно создан!")
            print(f"📊 Размерность: {len(embedding)}")
            print(f"📈 Первые 10 значений: {embedding[:10]}")
            print(f"📉 Минимум: {min(embedding):.6f}, Максимум: {max(embedding):.6f}")
            print(f"📊 Среднее: {sum(embedding)/len(embedding):.6f}")
            
            # Тест батч-обработки
            test_texts = [
                args.query,
                "Это второй тестовый текст для проверки батч-обработки",
                "Третий текст для тестирования параллельной обработки эмбеддингов"
            ]
            print(f"\n⏳ Тест батч-обработки ({len(test_texts)} текстов)...")
            batch_embeddings = embedding_service.create_embeddings_batch(test_texts)
            
            print(f"✅ Батч-обработка завершена!")
            print(f"📊 Создано эмбеддингов: {len(batch_embeddings)}")
            for i, emb in enumerate(batch_embeddings, 1):
                print(f"  [{i}] Размерность: {len(emb)}, Среднее: {sum(emb)/len(emb):.6f}")
            
            # Сохранение результатов
            output_file = Path("embedding_test_results.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "query": args.query,
                    "single_embedding": {
                        "dimension": len(embedding),
                        "first_10_values": embedding[:10],
                        "stats": {
                            "min": min(embedding),
                            "max": max(embedding),
                            "mean": sum(embedding)/len(embedding)
                        }
                    },
                    "batch_embeddings": {
                        "count": len(batch_embeddings),
                        "dimensions": [len(emb) for emb in batch_embeddings]
                    }
                }, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Результаты сохранены: {output_file}")
            
            print("\n" + "=" * 80)
            print("✅ Тест эмбеддингов завершен успешно")
            return 0
            
        except Exception as e:
            logger.error(f"Ошибка при тестировании эмбеддингов: {e}", exc_info=True)
            return 1
    
    # Выполнение поиска
    print(f"\n🔍 Поиск: '{args.query}'")
    print(f"📊 Тип: {args.type}")
    print(f"📈 Top-K: {args.top_k}")
    if filters:
        print(f"🔧 Фильтры: {filters}")
    print("=" * 80)
    
    try:
        if args.type == "documents":
            results = search.search_documents(args.query, top_k=args.top_k, filters=filters)
            print_search_results(results, "Документы")
            
        elif args.type == "blocks":
            results = search.search_blocks(args.query, top_k=args.top_k, filters=filters)
            print_search_results(results, "Блоки")
            
        elif args.type == "graph_entities":
            results = search.search_graph_entities(args.query, top_k=args.top_k, filters=filters)
            print_search_results(results, "Граф-сущности")
            
        elif args.type == "hybrid":
            results = search.hybrid_search(args.query, top_k=args.top_k, filters=filters)
            print("\n✅ Гибридный поиск: найдено результатов из всех коллекций")
            print("-" * 80)
            
            # Группировка по источникам
            by_source = {}
            for result in results:
                source = result.get('source', 'unknown')
                if source not in by_source:
                    by_source[source] = []
                by_source[source].append(result)
            
            for source, source_results in by_source.items():
                print(f"\n📦 {source.upper()}: {len(source_results)} результатов")
                for i, result in enumerate(source_results[:3], 1):  # Показываем первые 3
                    print(f"  [{i}] {result['id']} (расстояние: {result.get('normalized_distance', 'N/A'):.4f})")
            
            # Сохранение полных результатов в JSON
            output_file = Path("search_results.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "query": args.query,
                    "type": args.type,
                    "top_k": args.top_k,
                    "filters": filters,
                    "results": results
                }, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Полные результаты сохранены: {output_file}")
        
        print("\n" + "=" * 80)
        print("✅ Поиск завершен успешно")
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении поиска: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

