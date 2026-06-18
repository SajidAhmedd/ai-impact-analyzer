"""
Text chunking strategies for document processing.

WHY CHUNK:
- LLMs have token limits
- Smaller chunks = more precise retrieval
- Overlapping chunks preserve context at boundaries
"""

from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import structlog

logger = structlog.get_logger()


def create_text_splitter(
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> RecursiveCharacterTextSplitter:
    """
    Create a text splitter with specified settings.
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def chunk_documents(
    documents: List[Document],
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> List[Document]:
    """
    Split documents into smaller chunks.
    """
    splitter = create_text_splitter(chunk_size, chunk_overlap)

    chunks = splitter.split_documents(documents)

    # Add chunk index to metadata
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = i

    logger.info(
        "Documents chunked",
        input_docs=len(documents),
        output_chunks=len(chunks),
    )

    return chunks