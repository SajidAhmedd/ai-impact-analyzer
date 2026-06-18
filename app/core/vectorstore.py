"""
ChromaDB vector store for document storage and retrieval.

WHAT THIS DOES:
- Stores document chunks as vectors (embeddings)
- Enables semantic search (find docs similar to a query)
- Persists to disk so data survives restarts

HOW IT WORKS:
1. Documents are split into chunks
2. Each chunk is converted to a vector (embedding)
3. Vectors are stored in ChromaDB with metadata
4. When querying, your query becomes a vector
5. ChromaDB finds the most similar stored vectors
"""

from functools import lru_cache
from pathlib import Path

from langchain_chroma import Chroma
import structlog

from app.config import get_settings
from app.core.embeddings import get_embeddings

logger = structlog.get_logger()


def get_chroma_client() -> Chroma:
    """
    Returns a ChromaDB vector store instance.

    NOT cached because we might want fresh instances
    for different collections or after adding documents.

    Usage:
        from app.core.vectorstore import get_chroma_client

        vectorstore = get_chroma_client()

        # Add documents
        vectorstore.add_texts(["Hello world", "Goodbye world"])

        # Search
        results = vectorstore.similarity_search("greeting", k=1)
    """
    settings = get_settings()

    # Ensure the persist directory exists
    persist_dir = Path(settings.CHROMA_PERSIST_DIR)
    persist_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Initializing ChromaDB",
        persist_directory=str(persist_dir),
        collection_name=settings.CHROMA_COLLECTION_NAME
    )

    return Chroma(
        collection_name=settings.CHROMA_COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=str(persist_dir),
    )


def get_retriever(k: int = None):
    """
    Returns a retriever for semantic search.

    A retriever is a simplified interface for searching:
    - Input: query string
    - Output: list of relevant documents

    Args:
        k: Number of documents to retrieve (default from settings)

    Usage:
        retriever = get_retriever(k=3)
        docs = retriever.invoke("What is the refund policy?")
        for doc in docs:
            print(doc.page_content)
    """
    settings = get_settings()
    k = k or settings.RETRIEVAL_TOP_K

    vectorstore = get_chroma_client()

    return vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k}
    )


def add_documents_to_store(documents: list, metadatas: list = None) -> int:
    """
    Add documents to the vector store.

    Args:
        documents: List of text strings to add
        metadatas: Optional list of metadata dicts (one per document)

    Returns:
        Number of documents added

    Usage:
        docs = ["Policy document text...", "Another document..."]
        metadata = [{"source": "policy.pdf"}, {"source": "guide.pdf"}]
        count = add_documents_to_store(docs, metadata)
    """
    vectorstore = get_chroma_client()

    logger.info("Adding documents to vector store", count=len(documents))

    if metadatas:
        vectorstore.add_texts(texts=documents, metadatas=metadatas)
    else:
        vectorstore.add_texts(texts=documents)

    logger.info("Documents added successfully", count=len(documents))

    return len(documents)


def search_documents(query: str, k: int = None) -> list:
    """
    Search for documents similar to a query.

    Args:
        query: The search query
        k: Number of results to return

    Returns:
        List of (document, score) tuples

    Usage:
        results = search_documents("refund policy", k=3)
        for doc, score in results:
            print(f"Score: {score:.2f}")
            print(f"Content: {doc.page_content[:100]}...")
    """
    settings = get_settings()
    k = k or settings.RETRIEVAL_TOP_K

    vectorstore = get_chroma_client()

    results = vectorstore.similarity_search_with_score(query, k=k)

    logger.info(
        "Search completed",
        query=query[:50],
        results_count=len(results)
    )

    return results


def get_collection_stats() -> dict:
    """
    Get statistics about the vector store.

    Returns:
        Dict with collection stats (document count, etc.)
    """
    vectorstore = get_chroma_client()
    collection = vectorstore._collection

    return {
        "name": collection.name,
        "count": collection.count(),
    }