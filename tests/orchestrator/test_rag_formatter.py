"""
Тесты для RAGFormatter.

Проверяют:
- Форматирование графа для RAG
- Экспорт документов
- Форматы для embedding моделей
"""

import pytest
import tempfile
import os
import json
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from voice_bot_pipeline.text_processor.orchestrator.knowledge_graph_builder import (
    KnowledgeGraphBuilder
)
from voice_bot_pipeline.text_processor.orchestrator.knowledge_graph import (
    KnowledgeGraph,
    NodeType
)
from voice_bot_pipeline.text_processor.export.rag_formatter import (
    RAGFormatter,
    RAGDocument,
    format_knowledge_graph
)
from voice_bot_pipeline.tests.fixtures.real_sarsekenov_texts import TRIADA_TRANSFORMATION_TEXT


@pytest.fixture
def processor_with_data():
    """Процессор с обработанным текстом"""
    processor = KnowledgeGraphBuilder()
    processor.process_text(
        TRIADA_TRANSFORMATION_TEXT,
        text_id="test_rag"
    )
    return processor


@pytest.fixture
def formatter(processor_with_data):
    """RAG форматтер"""
    graph = processor_with_data.get_knowledge_graph()
    return RAGFormatter(graph)


class TestRAGFormatting:
    """Тесты форматирования для RAG"""
    
    def test_format_for_rag(self, formatter):
        """Тест форматирования графа"""
        documents = formatter.format_for_rag()
        
        assert len(documents) > 0, "No documents generated"
        
        # Проверка структуры документов
        for doc in documents:
            assert isinstance(doc, RAGDocument)
            assert doc.id
            assert doc.content
            assert doc.metadata
            assert doc.node_type
        
        print(f"\n✅ RAG FORMATTING")
        print(f"   Total documents: {len(documents)}")
    
    def test_document_content_structure(self, formatter):
        """Тест структуры content в документах"""
        documents = formatter.format_for_rag()
        
        doc = documents[0]
        
        # Content должен содержать основные части
        assert "Концепт:" in doc.content
        assert "Описание:" in doc.content
        assert "Тип:" in doc.content
        
        print(f"\n   Sample content:\n{doc.content[:200]}...")
    
    def test_metadata_complete(self, formatter):
        """Тест полноты метаданных"""
        documents = formatter.format_for_rag()
        
        for doc in documents:
            metadata = doc.metadata
            
            # Обязательные поля
            assert 'node_id' in metadata
            assert 'node_name' in metadata
            assert 'node_type' in metadata
            assert 'source' in metadata
    
    def test_get_documents_by_type(self, formatter):
        """Тест фильтрации по типу"""
        from voice_bot_pipeline.text_processor.orchestrator.knowledge_graph import NodeType
        
        practice_docs = formatter.get_documents_by_type(NodeType.PRACTICE)
        
        # Должны быть только практики
        for doc in practice_docs:
            assert doc.node_type == "practice"
        
        print(f"\n   Practice documents: {len(practice_docs)}")
    
    def test_get_documents_by_tier(self, formatter):
        """Тест фильтрации по tier"""
        tier3_docs = formatter.get_documents_by_tier(3)
        
        # Должны быть только tier 3
        for doc in tier3_docs:
            assert doc.tier == 3
        
        print(f"\n   Tier 3 documents: {len(tier3_docs)}")


class TestExport:
    """Тесты экспорта"""
    
    def test_export_to_json(self, formatter):
        """Тест экспорта в JSON"""
        # Создать временный файл
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            delete=False
        ) as f:
            filepath = f.name
        
        try:
            # Экспортировать
            formatter.export_to_json(filepath)
            
            # Проверка что файл создан
            assert os.path.exists(filepath)
            
            # Загрузить и проверить структуру
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert 'documents' in data
            assert 'total_documents' in data
            assert 'graph_statistics' in data
            
            print(f"\n✅ EXPORT TO JSON")
            print(f"   Documents: {data['total_documents']}")
            
        finally:
            # Удалить файл
            if os.path.exists(filepath):
                os.remove(filepath)
    
    def test_format_for_embedding_model(self, formatter):
        """Тест форматирования для embedding модели"""
        # Формат для E5 модели
        e5_docs = formatter.format_for_embedding_model("multilingual-e5-large")
        
        assert len(e5_docs) > 0
        
        # Проверка формата
        for doc in e5_docs:
            assert 'id' in doc
            assert 'text' in doc
            assert 'metadata' in doc
            assert doc['text'].startswith("passage: ")
        
        print(f"\n✅ E5 FORMAT")
        print(f"   Documents: {len(e5_docs)}")
        print(f"   Sample: {e5_docs[0]['text'][:100]}...")


class TestUtilityFunctions:
    """Тесты utility функций"""
    
    def test_format_knowledge_graph_rag(self, processor_with_data):
        """Тест utility функции для RAG формата"""
        graph = processor_with_data.get_knowledge_graph()
        
        documents = format_knowledge_graph(graph, output_format="rag")
        
        assert len(documents) > 0
        assert all(isinstance(doc, RAGDocument) for doc in documents)
    
    def test_format_knowledge_graph_json(self, processor_with_data):
        """Тест utility функции для JSON формата"""
        graph = processor_with_data.get_knowledge_graph()
        
        documents = format_knowledge_graph(graph, output_format="json")
        
        assert len(documents) > 0
        assert all(isinstance(doc, dict) for doc in documents)
    
    def test_format_knowledge_graph_embedding(self, processor_with_data):
        """Тест utility функции для embedding формата"""
        graph = processor_with_data.get_knowledge_graph()
        
        documents = format_knowledge_graph(graph, output_format="embedding")
        
        assert len(documents) > 0
        assert all(doc['text'].startswith("passage: ") for doc in documents)