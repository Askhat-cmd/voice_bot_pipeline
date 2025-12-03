#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vector Indexer for indexing SAG v2.0 data into ChromaDB
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from .chromadb_manager import VectorDBManager
from .embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class VectorIndexer:
    """Индексатор для добавления SAG v2.0 данных в векторную базу"""
    
    def __init__(
        self, 
        db_manager: VectorDBManager,
        embedding_service: EmbeddingService,
        batch_size: int = 100
    ):
        """
        Инициализация индексатора
        
        Args:
            db_manager: Менеджер ChromaDB
            embedding_service: Сервис для создания эмбеддингов
            batch_size: Размер батча для обработки
        """
        self.db_manager = db_manager
        self.embedding_service = embedding_service
        self.batch_size = batch_size
        
        logger.info("✅ VectorIndexer инициализирован")
    
    def index_document(self, sag_data: Dict[str, Any]) -> bool:
        """
        Индексирует документ целиком (document_summary + document_title)
        
        Args:
            sag_data: Данные SAG v2.0
            
        Returns:
            True если успешно
        """
        try:
            collection = self.db_manager.get_or_create_collection("documents")
            
            # Подготовка текста для векторизации
            document_title = sag_data.get("document_title", "")
            document_summary = sag_data.get("document_summary", "")
            text_to_embed = f"{document_title}\n{document_summary}".strip()
            
            if not text_to_embed:
                logger.warning("Пустой документ, пропускаем индексацию")
                return False
            
            # Создание эмбеддинга
            embedding = self.embedding_service.create_embedding(text_to_embed)
            
            # Подготовка метаданных
            metadata = sag_data.get("document_metadata", {})
            doc_metadata = {
                "video_id": metadata.get("video_id", ""),
                "document_title": document_title,
                "source_url": metadata.get("source_url", ""),
                "language": metadata.get("language", "ru"),
                "domain": metadata.get("domain", ""),
                "collection_target": metadata.get("collection_target", ""),
                "main_topics": ", ".join(metadata.get("main_topics", [])),
                "difficulty_level": metadata.get("difficulty_level", ""),
                "total_blocks": str(metadata.get("total_blocks", 0)),
                "schema_version": metadata.get("schema_version", "2.0"),
            }
            
            # ID документа
            doc_id = f"doc_{metadata.get('video_id', 'unknown')}"
            
            # Добавление в коллекцию
            collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text_to_embed],
                metadatas=[doc_metadata]
            )
            
            logger.info(f"✅ Документ проиндексирован: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при индексации документа: {e}", exc_info=True)
            return False
    
    def index_blocks(self, sag_data: Dict[str, Any]) -> int:
        """
        Индексирует все блоки документа
        
        Args:
            sag_data: Данные SAG v2.0
            
        Returns:
            Количество проиндексированных блоков
        """
        try:
            collection = self.db_manager.get_or_create_collection("blocks")
            blocks = sag_data.get("blocks", [])
            
            if not blocks:
                logger.warning("Нет блоков для индексации")
                return 0
            
            video_id = sag_data.get("document_metadata", {}).get("video_id", "unknown")
            document_title = sag_data.get("document_title", "")
            
            # Подготовка данных для батч-обработки
            texts_to_embed = []
            block_ids = []
            metadatas_list = []
            
            for block in blocks:
                # Подготовка текста для векторизации
                block_title = block.get("title", "")
                block_summary = block.get("summary", "")
                block_content = block.get("content", "")
                keywords = ", ".join(block.get("keywords", []))
                
                text_to_embed = f"{block_title}\n{block_summary}\n{keywords}\n{block_content}".strip()
                
                if not text_to_embed:
                    continue
                
                texts_to_embed.append(text_to_embed)
                block_id = block.get("block_id", f"{video_id}_unknown")
                block_ids.append(block_id)
                
                # Подготовка метаданных
                metadata = {
                    "block_id": block_id,
                    "video_id": video_id,
                    "document_title": document_title,
                    "start": block.get("start", ""),
                    "end": block.get("end", ""),
                    "block_type": block.get("block_type", ""),
                    "emotional_tone": block.get("emotional_tone", ""),
                    "conceptual_depth": block.get("conceptual_depth", ""),
                    "complexity_score": str(block.get("complexity_score", 0.0)),
                    "collection_target": sag_data.get("document_metadata", {}).get("collection_target", ""),
                    "youtube_link": block.get("youtube_link", ""),
                    "graph_entities": ", ".join(block.get("graph_entities", [])[:10]),  # Первые 10 для метаданных
                }
                metadatas_list.append(metadata)
            
            if not texts_to_embed:
                logger.warning("Нет валидных блоков для индексации")
                return 0
            
            # Батч-создание эмбеддингов
            embeddings = self.embedding_service.create_embeddings_batch(texts_to_embed)
            
            # Добавление в коллекцию батчами
            indexed_count = 0
            for i in range(0, len(block_ids), self.batch_size):
                batch_ids = block_ids[i:i + self.batch_size]
                batch_embeddings = embeddings[i:i + self.batch_size]
                batch_documents = texts_to_embed[i:i + self.batch_size]
                batch_metadatas = metadatas_list[i:i + self.batch_size]
                
                collection.add(
                    ids=batch_ids,
                    embeddings=batch_embeddings,
                    documents=batch_documents,
                    metadatas=batch_metadatas
                )
                indexed_count += len(batch_ids)
            
            logger.info(f"✅ Проиндексировано блоков: {indexed_count}/{len(blocks)}")
            return indexed_count
            
        except Exception as e:
            logger.error(f"Ошибка при индексации блоков: {e}", exc_info=True)
            return 0
    
    def index_graph_entities(self, sag_data: Dict[str, Any]) -> int:
        """
        Индексирует граф-сущности с контекстом
        
        Args:
            sag_data: Данные SAG v2.0
            
        Returns:
            Количество проиндексированных сущностей
        """
        try:
            collection = self.db_manager.get_or_create_collection("graph_entities")
            blocks = sag_data.get("blocks", [])
            
            if not blocks:
                logger.warning("Нет блоков для извлечения граф-сущностей")
                return 0
            
            video_id = sag_data.get("document_metadata", {}).get("video_id", "unknown")
            document_title = sag_data.get("document_title", "")
            
            # Собираем все уникальные граф-сущности с контекстом
            entity_contexts: Dict[str, List[str]] = {}
            
            for block in blocks:
                graph_entities = block.get("graph_entities", [])
                block_title = block.get("title", "")
                block_summary = block.get("summary", "")
                block_id = block.get("block_id", "")
                
                for entity in graph_entities:
                    if entity not in entity_contexts:
                        entity_contexts[entity] = []
                    # Добавляем контекст блока
                    context = f"Блок: {block_title}\n{block_summary}"
                    entity_contexts[entity].append(context)
            
            if not entity_contexts:
                logger.warning("Нет граф-сущностей для индексации")
                return 0
            
            # Подготовка данных для индексации
            texts_to_embed = []
            entity_ids = []
            metadatas_list = []
            
            for entity, contexts in entity_contexts.items():
                # Объединяем контексты
                context_text = "\n\n".join(contexts[:5])  # Максимум 5 контекстов
                text_to_embed = f"Граф-сущность: {entity}\n\nКонтекст:\n{context_text}".strip()
                
                texts_to_embed.append(text_to_embed)
                entity_id = f"entity_{video_id}_{entity}"
                entity_ids.append(entity_id)
                
                # Метаданные
                metadata = {
                    "entity_name": entity,
                    "video_id": video_id,
                    "document_title": document_title,
                    "frequency": str(len(contexts)),
                    "domain": sag_data.get("document_metadata", {}).get("domain", ""),
                }
                metadatas_list.append(metadata)
            
            # Батч-создание эмбеддингов
            embeddings = self.embedding_service.create_embeddings_batch(texts_to_embed)
            
            # Добавление в коллекцию
            indexed_count = 0
            for i in range(0, len(entity_ids), self.batch_size):
                batch_ids = entity_ids[i:i + self.batch_size]
                batch_embeddings = embeddings[i:i + self.batch_size]
                batch_documents = texts_to_embed[i:i + self.batch_size]
                batch_metadatas = metadatas_list[i:i + self.batch_size]
                
                collection.add(
                    ids=batch_ids,
                    embeddings=batch_embeddings,
                    documents=batch_documents,
                    metadatas=batch_metadatas
                )
                indexed_count += len(batch_ids)
            
            logger.info(f"✅ Проиндексировано граф-сущностей: {indexed_count}")
            return indexed_count
            
        except Exception as e:
            logger.error(f"Ошибка при индексации граф-сущностей: {e}", exc_info=True)
            return 0
    
    def index_sag_file(self, json_path: Path, index_levels: List[str] = None) -> Dict[str, Any]:
        """
        Полная индексация SAG v2.0 JSON файла
        
        Args:
            json_path: Путь к JSON файлу
            index_levels: Список уровней для индексации (documents, blocks, graph_entities)
                         Если None, индексирует все уровни
        
        Returns:
            Словарь с результатами индексации
        """
        if index_levels is None:
            index_levels = ["documents", "blocks", "graph_entities"]
        
        results = {
            "file": str(json_path),
            "success": False,
            "indexed": {
                "documents": 0,
                "blocks": 0,
                "graph_entities": 0
            }
        }
        
        try:
            # Загрузка JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                sag_data = json.load(f)
            
            logger.info(f"📂 Индексация файла: {json_path.name}")
            
            # Индексация на разных уровнях
            if "documents" in index_levels:
                if self.index_document(sag_data):
                    results["indexed"]["documents"] = 1
            
            if "blocks" in index_levels:
                blocks_count = self.index_blocks(sag_data)
                results["indexed"]["blocks"] = blocks_count
            
            if "graph_entities" in index_levels:
                entities_count = self.index_graph_entities(sag_data)
                results["indexed"]["graph_entities"] = entities_count
            
            results["success"] = True
            logger.info(f"✅ Файл проиндексирован: {json_path.name}")
            
        except Exception as e:
            logger.error(f"Ошибка при индексации файла {json_path}: {e}", exc_info=True)
            results["error"] = str(e)
        
        return results

