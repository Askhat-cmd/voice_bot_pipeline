#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vector Search for semantic search across ChromaDB collections
"""

import logging
from typing import List, Dict, Any, Optional

from .chromadb_manager import VectorDBManager
from .embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class VectorSearch:
    """Сервис для семантического поиска в векторной базе данных"""
    
    def __init__(
        self,
        db_manager: VectorDBManager,
        embedding_service: EmbeddingService
    ):
        """
        Инициализация сервиса поиска
        
        Args:
            db_manager: Менеджер ChromaDB
            embedding_service: Сервис для создания эмбеддингов
        """
        self.db_manager = db_manager
        self.embedding_service = embedding_service
        
        logger.info("✅ VectorSearch инициализирован")
    
    def search_documents(
        self, 
        query: str, 
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Поиск по документам
        
        Args:
            query: Поисковый запрос
            top_k: Количество результатов
            filters: Фильтры по метаданным (например, {"video_id": "xxx"})
        
        Returns:
            Список результатов поиска
        """
        try:
            collection = self.db_manager.get_collection("documents")
            if not collection:
                logger.warning("Коллекция 'documents' не найдена")
                return []
            
            # Создание эмбеддинга для запроса
            query_embedding = self.embedding_service.create_embedding(query)
            
            # Подготовка where-условий для фильтрации
            where = None
            if filters:
                where = filters
            
            # Поиск
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where
            )
            
            # Форматирование результатов
            formatted_results = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    result = {
                        "id": results['ids'][0][i],
                        "document": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i] if 'distances' in results else None
                    }
                    formatted_results.append(result)
            
            logger.info(f"🔍 Найдено документов: {len(formatted_results)}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Ошибка при поиске документов: {e}", exc_info=True)
            return []
    
    def search_blocks(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Поиск по блокам
        
        Args:
            query: Поисковый запрос
            top_k: Количество результатов
            filters: Фильтры по метаданным (например, {"block_type": "question", "video_id": "xxx"})
        
        Returns:
            Список результатов поиска
        """
        try:
            collection = self.db_manager.get_collection("blocks")
            if not collection:
                logger.warning("Коллекция 'blocks' не найдена")
                return []
            
            # Создание эмбеддинга для запроса
            query_embedding = self.embedding_service.create_embedding(query)
            
            # Подготовка where-условий для фильтрации
            where = None
            if filters:
                where = filters
            
            # Поиск
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where
            )
            
            # Форматирование результатов
            formatted_results = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    result = {
                        "id": results['ids'][0][i],
                        "document": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i] if 'distances' in results else None
                    }
                    formatted_results.append(result)
            
            logger.info(f"🔍 Найдено блоков: {len(formatted_results)}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Ошибка при поиске блоков: {e}", exc_info=True)
            return []
    
    def search_graph_entities(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Поиск по граф-сущностям
        
        Args:
            query: Поисковый запрос
            top_k: Количество результатов
            filters: Фильтры по метаданным (например, {"domain": "sarsekenov_neurostalking"})
        
        Returns:
            Список результатов поиска
        """
        try:
            collection = self.db_manager.get_collection("graph_entities")
            if not collection:
                logger.warning("Коллекция 'graph_entities' не найдена")
                return []
            
            # Создание эмбеддинга для запроса
            query_embedding = self.embedding_service.create_embedding(query)
            
            # Подготовка where-условий для фильтрации
            where = None
            if filters:
                where = filters
            
            # Поиск
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where
            )
            
            # Форматирование результатов
            formatted_results = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    result = {
                        "id": results['ids'][0][i],
                        "document": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i] if 'distances' in results else None
                    }
                    formatted_results.append(result)
            
            logger.info(f"🔍 Найдено граф-сущностей: {len(formatted_results)}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Ошибка при поиске граф-сущностей: {e}", exc_info=True)
            return []
    
    def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        document_weight: float = 0.3,
        block_weight: float = 0.5,
        entity_weight: float = 0.2,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Гибридный поиск по всем коллекциям с весами
        
        Args:
            query: Поисковый запрос
            top_k: Общее количество результатов
            document_weight: Вес результатов документов
            block_weight: Вес результатов блоков
            entity_weight: Вес результатов граф-сущностей
            filters: Фильтры по метаданным
        
        Returns:
            Объединенный список результатов с нормализованными расстояниями
        """
        try:
            # Поиск по всем коллекциям
            documents = self.search_documents(query, top_k=top_k, filters=filters)
            blocks = self.search_blocks(query, top_k=top_k, filters=filters)
            entities = self.search_graph_entities(query, top_k=top_k, filters=filters)
            
            # Нормализация расстояний и применение весов
            all_results = []
            
            # Обработка документов
            for doc in documents:
                normalized_distance = doc.get('distance', 1.0) * document_weight
                doc['normalized_distance'] = normalized_distance
                doc['source'] = 'document'
                all_results.append(doc)
            
            # Обработка блоков
            for block in blocks:
                normalized_distance = block.get('distance', 1.0) * block_weight
                block['normalized_distance'] = normalized_distance
                block['source'] = 'block'
                all_results.append(block)
            
            # Обработка граф-сущностей
            for entity in entities:
                normalized_distance = entity.get('distance', 1.0) * entity_weight
                entity['normalized_distance'] = normalized_distance
                entity['source'] = 'graph_entity'
                all_results.append(entity)
            
            # Сортировка по нормализованному расстоянию
            all_results.sort(key=lambda x: x.get('normalized_distance', 1.0))
            
            # Возвращаем top_k результатов
            result = all_results[:top_k]
            
            logger.info(f"🔍 Гибридный поиск: найдено {len(result)} результатов")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при гибридном поиске: {e}", exc_info=True)
            return []

