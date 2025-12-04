#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChromaDB Manager for managing vector database collections
"""

import logging
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class VectorDBManager:
    """Менеджер для управления ChromaDB коллекциями"""
    
    def __init__(self, db_path: str = "data/chromadb", collection_prefix: str = "sag_v2"):
        """
        Инициализация менеджера ChromaDB
        
        Args:
            db_path: Путь к директории с базой данных ChromaDB
            collection_prefix: Префикс для имен коллекций
        """
        self.db_path = Path(db_path)
        self.collection_prefix = collection_prefix
        
        # Создаем директорию если не существует
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Инициализация persistent client
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Кэш коллекций
        self._collections = {}
        
        logger.info(f"✅ VectorDBManager инициализирован: {self.db_path}")
    
    def get_or_create_collection(
        self, 
        collection_name: str, 
        embedding_dimension: int = 1024
    ) -> chromadb.Collection:
        """
        Получает или создает коллекцию
        
        Args:
            collection_name: Имя коллекции
            embedding_dimension: Размерность эмбеддингов
            
        Returns:
            Коллекция ChromaDB
        """
        full_name = f"{self.collection_prefix}_{collection_name}"
        
        if full_name in self._collections:
            return self._collections[full_name]
        
        try:
            # Пытаемся получить существующую коллекцию
            collection = self.client.get_collection(name=full_name)
            logger.info(f"📂 Коллекция найдена: {full_name}")
        except Exception:
            # Создаем новую коллекцию
            collection = self.client.create_collection(
                name=full_name,
                metadata={"description": f"SAG v2.0 {collection_name} collection"}
            )
            logger.info(f"✨ Коллекция создана: {full_name}")
        
        self._collections[full_name] = collection
        return collection
    
    def get_collection(self, collection_name: str) -> Optional[chromadb.Collection]:
        """
        Получает существующую коллекцию
        
        Args:
            collection_name: Имя коллекции
            
        Returns:
            Коллекция ChromaDB или None если не найдена
        """
        full_name = f"{self.collection_prefix}_{collection_name}"
        
        if full_name in self._collections:
            return self._collections[full_name]
        
        try:
            collection = self.client.get_collection(name=full_name)
            self._collections[full_name] = collection
            return collection
        except Exception:
            logger.warning(f"⚠️ Коллекция не найдена: {full_name}")
            return None
    
    def list_collections(self) -> list:
        """Возвращает список всех коллекций"""
        collections = self.client.list_collections()
        return [col.name for col in collections]
    
    def delete_collection(self, collection_name: str) -> bool:
        """
        Удаляет коллекцию
        
        Args:
            collection_name: Имя коллекции
            
        Returns:
            True если успешно удалена
        """
        full_name = f"{self.collection_prefix}_{collection_name}"
        
        try:
            self.client.delete_collection(name=full_name)
            if full_name in self._collections:
                del self._collections[full_name]
            logger.info(f"🗑️ Коллекция удалена: {full_name}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении коллекции {full_name}: {e}")
            return False
    
    def reset_database(self) -> bool:
        """
        Сбрасывает всю базу данных (удаляет все коллекции)
        
        Returns:
            True если успешно
        """
        try:
            self.client.reset()
            self._collections.clear()
            logger.warning("⚠️ База данных полностью сброшена")
            return True
        except Exception as e:
            logger.error(f"Ошибка при сбросе базы данных: {e}")
            return False

