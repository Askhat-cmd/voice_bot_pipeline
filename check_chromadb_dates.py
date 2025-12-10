#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка наличия published_date в метаданных ChromaDB
"""

import sys
import codecs

# Force UTF-8 for stdout to handle emojis on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from vector_db import VectorDBManager

def check_collection(collection_name, db_manager):
    """Проверяет наличие published_date в коллекции"""
    print(f"\n{'='*60}")
    print(f"📦 Проверка коллекции: {collection_name}")
    print(f"{'='*60}")
    
    collection = db_manager.get_collection(collection_name)
    
    if not collection:
        print(f"❌ Коллекция не найдена: sag_v2_{collection_name}")
        return False
    
    # Получаем первые 3 элемента
    results = collection.get(limit=3)
    total = collection.count()
    
    print(f"✅ Всего элементов: {total}")
    
    if not results['ids']:
        print(f"⚠️  Коллекция пустая")
        return True
    
    # Проверяем каждый элемент
    has_dates = True
    for i, doc_id in enumerate(results['ids']):
        metadata = results['metadatas'][i] if results['metadatas'] else {}
        published_date = metadata.get('published_date', '')
        
        print(f"\n📄 Элемент {i+1}: {doc_id}")
        print(f"   Video ID: {metadata.get('video_id', 'N/A')}")
        print(f"   Title: {metadata.get('document_title', metadata.get('entity_name', 'N/A'))[:50]}...")
        
        if published_date:
            print(f"   ✅ Published Date: {published_date}")
        else:
            print(f"   ❌ Published Date: ОТСУТСТВУЕТ")
            has_dates = False
    
    return has_dates

def main():
    print("🔍 Проверка наличия published_date в метаданных ChromaDB\n")
    
    # Инициализация
    db_manager = VectorDBManager("data/chromadb", "sag_v2")
    
    # Проверяем все коллекции
    collections = ["documents", "blocks", "graph_entities"]
    results = {}
    
    for collection_name in collections:
        results[collection_name] = check_collection(collection_name, db_manager)
    
    # Итоговый результат
    print(f"\n{'='*60}")
    print("📊 ИТОГОВЫЙ РЕЗУЛЬТАТ")
    print(f"{'='*60}")
    
    all_ok = all(results.values())
    
    for collection_name, has_dates in results.items():
        status = "✅ PASSED" if has_dates else "❌ FAILED"
        print(f"{status} - sag_v2_{collection_name}")
    
    print(f"{'='*60}")
    
    if all_ok:
        print("✅ Все коллекции содержат published_date в метаданных!")
    else:
        print("❌ Некоторые коллекции не содержат published_date")
        print("   Решение: Переиндексируйте данные после изменений в vector_indexer.py")

if __name__ == "__main__":
    main()