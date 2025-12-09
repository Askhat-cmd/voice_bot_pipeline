"""
RAG Formatter - подготовка данных для экспорта в RAG систему.

Форматирует Knowledge Graph в структуру для векторной БД:
- Документы с полным текстом
- Метаданные для фильтрации
- Embeddings-ready формат
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import json

from voice_bot_pipeline.text_processor.orchestrator.knowledge_graph import (
    KnowledgeGraph,
    GraphNode,
    NodeType
)


@dataclass
class RAGDocument:
    """Документ для RAG системы"""
    id: str                          # Уникальный ID
    content: str                     # Полный текст для embedding
    metadata: Dict[str, Any]         # Метаданные для фильтрации
    
    # Дополнительные поля
    node_type: str                   # Тип узла
    sarsekenov_terms: List[str]      # Термины Сарсекенова
    tier: Optional[int] = None       # Tier (1-6)
    confidence: float = 1.0          # Уверенность
    
    def to_dict(self) -> Dict:
        """Сериализация в dict"""
        return asdict(self)


class RAGFormatter:
    """
    Форматирование Knowledge Graph для RAG системы.
    
    Преобразует граф в набор документов для векторной БД:
    1. Каждый узел → документ
    2. Связи → метаданные
    3. Форматирование для embedding моделей
    
    ФИЛОСОФИЯ:
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    - Сохранение полного контекста в content
    - Метаданные для точной фильтрации
    - Связи для reasoning chains
    - Готовность для embedding моделей
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    
    def __init__(self, knowledge_graph: KnowledgeGraph):
        """
        Инициализация форматтера.
        
        Args:
            knowledge_graph: Граф знаний для форматирования
        """
        self.graph = knowledge_graph
    
    def format_for_rag(self) -> List[RAGDocument]:
        """
        Форматировать граф для RAG системы.
        
        Returns:
            Список документов для векторной БД
        """
        documents = []
        
        # Обработать все узлы
        for node_id, node in self.graph.nodes.items():
            doc = self._node_to_document(node)
            documents.append(doc)
        
        return documents
    
    def _node_to_document(self, node: GraphNode) -> RAGDocument:
        """
        Преобразовать узел графа в RAG документ.
        
        Args:
            node: Узел графа
            
        Returns:
            RAG документ
        """
        # Формирование content (текст для embedding)
        content_parts = [
            f"Концепт: {node.name}",
            f"Описание: {node.description}"
        ]
        
        # Добавить термины Сарсекенова
        if node.sarsekenov_terms:
            terms_str = ", ".join(node.sarsekenov_terms)
            content_parts.append(f"Ключевые термины: {terms_str}")
        
        # Добавить тип узла
        content_parts.append(f"Тип: {node.node_type.value}")
        
        # Добавить связи
        outgoing_edges = self.graph.get_outgoing_edges(node.id)
        if outgoing_edges:
            relations = []
            for edge in outgoing_edges:
                target_node = self.graph.get_node(edge.to_id)
                if target_node:
                    relations.append(
                        f"{edge.edge_type.value} → {target_node.name}"
                    )
            if relations:
                content_parts.append(f"Связи: {'; '.join(relations)}")
        
        content = "\n".join(content_parts)
        
        # Формирование метаданных
        metadata = {
            "node_id": node.id,
            "node_name": node.name,
            "node_type": node.node_type.value,
            "tier": node.tier,
            "confidence": node.confidence,
            "sarsekenov_terms": node.sarsekenov_terms,
            "source": node.metadata.get("source", "unknown")
        }
        
        # Добавить специфичные метаданные
        if node.node_type == NodeType.EXERCISE:
            metadata.update({
                "duration": node.metadata.get("duration"),
                "frequency": node.metadata.get("frequency"),
                "has_instructions": bool(node.metadata.get("instructions"))
            })
        
        if node.node_type == NodeType.PATTERN:
            metadata.update({
                "pattern_category": node.metadata.get("category"),
                "related_practices": node.metadata.get("related_practices", [])
            })
        
        # Создать документ
        return RAGDocument(
            id=node.id,
            content=content,
            metadata=metadata,
            node_type=node.node_type.value,
            sarsekenov_terms=node.sarsekenov_terms,
            tier=node.tier,
            confidence=node.confidence
        )
    
    def export_to_json(self, filepath: str) -> None:
        """
        Экспортировать документы в JSON файл.
        
        Args:
            filepath: Путь к файлу для сохранения
        """
        documents = self.format_for_rag()
        
        data = {
            "documents": [doc.to_dict() for doc in documents],
            "total_documents": len(documents),
            "graph_statistics": self.graph.get_statistics()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_documents_by_type(
        self,
        node_type: NodeType
    ) -> List[RAGDocument]:
        """
        Получить документы определённого типа.
        
        Args:
            node_type: Тип узлов для извлечения
            
        Returns:
            Список документов заданного типа
        """
        documents = self.format_for_rag()
        return [
            doc for doc in documents
            if doc.node_type == node_type.value
        ]
    
    def get_documents_by_tier(self, tier: int) -> List[RAGDocument]:
        """
        Получить документы определённого tier.
        
        Args:
            tier: Tier (1-6)
            
        Returns:
            Список документов заданного tier
        """
        documents = self.format_for_rag()
        return [
            doc for doc in documents
            if doc.tier == tier
        ]
    
    def format_for_embedding_model(
        self,
        model_name: str = "multilingual-e5-large"
    ) -> List[Dict[str, Any]]:
        """
        Форматировать для конкретной embedding модели.
        
        Args:
            model_name: Название модели
            
        Returns:
            Список документов в формате модели
        """
        documents = self.format_for_rag()
        
        if "e5" in model_name.lower():
            # Формат для E5 моделей: "query: " или "passage: "
            return [
                {
                    "id": doc.id,
                    "text": f"passage: {doc.content}",
                    "metadata": doc.metadata
                }
                for doc in documents
            ]
        
        # Стандартный формат
        return [
            {
                "id": doc.id,
                "text": doc.content,
                "metadata": doc.metadata
            }
            for doc in documents
        ]


# ============================================================================
# HELPER: Utility функции
# ============================================================================

def format_knowledge_graph(
    knowledge_graph: KnowledgeGraph,
    output_format: str = "rag"
) -> Any:
    """
    Быстрое форматирование Knowledge Graph.
    
    Args:
        knowledge_graph: Граф для форматирования
        output_format: Формат ("rag", "json", "embedding")
        
    Returns:
        Форматированные данные
    """
    formatter = RAGFormatter(knowledge_graph)
    
    if output_format == "rag":
        return formatter.format_for_rag()
    elif output_format == "json":
        return [doc.to_dict() for doc in formatter.format_for_rag()]
    elif output_format == "embedding":
        return formatter.format_for_embedding_model()
    else:
        raise ValueError(f"Unknown format: {output_format}")