"""
Document processing pipeline - ties everything together.
"""

from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime

from langchain_core.documents import Document
import structlog

from app.ingestion.loader import load_document
from app.ingestion.chunker import chunk_documents
from app.core.vectorstore import get_chroma_client

logger = structlog.get_logger()


def process_document(
    file_path: str,
    metadata: Optional[Dict] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> int:
    """
    Process a single document: load, chunk, and store.
    """
    logger.info("Processing document", file=file_path)

    # Step 1: Load document
    documents = load_document(file_path)

    # Step 2: Add custom metadata
    if metadata:
        for doc in documents:
            doc.metadata.update(metadata)

    # Add processing timestamp
    for doc in documents:
        doc.metadata["processed_at"] = datetime.utcnow().isoformat()

    # Step 3: Chunk documents
    chunks = chunk_documents(documents, chunk_size, chunk_overlap)

    # Step 4: Store in vector database
    vectorstore = get_chroma_client()

    texts = [chunk.page_content for chunk in chunks]
    metadatas = [chunk.metadata for chunk in chunks]

    vectorstore.add_texts(texts=texts, metadatas=metadatas)

    logger.info(
        "Document processed and stored",
        file=file_path,
        chunks_stored=len(chunks)
    )

    return len(chunks)


def process_directory(
    directory_path: str,
    metadata: Optional[Dict] = None,
    extensions: List[str] = [".txt", ".md", ".pdf", ".docx"]
) -> int:
    """
    Process all documents in a directory.
    """
    path = Path(directory_path)

    if not path.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory_path}")

    total_chunks = 0

    for ext in extensions:
        for file_path in path.glob(f"*{ext}"):
            try:
                chunks = process_document(str(file_path), metadata)
                total_chunks += chunks
            except Exception as e:
                logger.error("Failed to process file", file=str(file_path), error=str(e))

    logger.info(
        "Directory processing complete",
        directory=directory_path,
        total_chunks=total_chunks
    )

    return total_chunks