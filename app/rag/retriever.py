"""
Hybrid retriever combining vector search and BM25 keyword search.

WHY HYBRID:
- Vector search: Good for semantic similarity
- BM25 search: Good for exact keyword matches
- Combined: Better results for business/policy documents
"""

from typing import List, Tuple
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
import structlog

from app.config import get_settings
from app.core.vectorstore import get_chroma_client

logger = structlog.get_logger()


class HybridRetriever:
    """
    Combines vector similarity search with BM25 keyword search.

    Usage:
        retriever = HybridRetriever()
        docs = retriever.retrieve("What is the refund policy?")
    """

    def __init__(
        self,
        vector_weight: float = 0.6,
        bm25_weight: float = 0.4,
        k: int = None
    ):
        settings = get_settings()
        self.k = k or settings.RETRIEVAL_TOP_K
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight

        self._bm25_retriever = None
        self._documents = []
        self._initialized = False

    def _initialize(self):
        """Load documents from vectorstore for BM25."""
        if self._initialized:
            return

        vectorstore = get_chroma_client()
        collection = vectorstore._collection
        results = collection.get(include=["documents", "metadatas"])

        if not results["documents"]:
            logger.warning("No documents in vectorstore")
            self._documents = []
            self._initialized = True
            return

        # Convert to LangChain Documents
        self._documents = [
            Document(
                page_content=doc,
                metadata=meta or {}
            )
            for doc, meta in zip(results["documents"], results["metadatas"])
        ]

        # Create BM25 retriever
        if self._documents:
            self._bm25_retriever = BM25Retriever.from_documents(
                self._documents,
                k=self.k
            )

        self._initialized = True
        logger.info(f"Initialized with {len(self._documents)} documents")

    def _merge_results(
        self,
        vector_docs: List[Document],
        bm25_docs: List[Document]
    ) -> List[Document]:
        """
        Merge results from both retrievers, removing duplicates.

        Simple approach: interleave results, skip duplicates.
        """
        seen_content = set()
        merged = []

        # Interleave: take from vector, then bm25, alternating
        max_len = max(len(vector_docs), len(bm25_docs))

        for i in range(max_len):
            # Add vector result
            if i < len(vector_docs):
                content = vector_docs[i].page_content
                if content not in seen_content:
                    seen_content.add(content)
                    vector_docs[i].metadata["retrieval_method"] = "vector"
                    merged.append(vector_docs[i])

            # Add BM25 result
            if i < len(bm25_docs):
                content = bm25_docs[i].page_content
                if content not in seen_content:
                    seen_content.add(content)
                    bm25_docs[i].metadata["retrieval_method"] = "bm25"
                    merged.append(bm25_docs[i])

        return merged

    def retrieve(self, query: str, k: int = None) -> List[Document]:
        """
        Retrieve relevant documents using hybrid search.
        """
        k = k or self.k
        self._initialize()

        if not self._documents:
            return []

        # Get vector results
        vectorstore = get_chroma_client()
        vector_docs = vectorstore.similarity_search(query, k=k)

        # Get BM25 results
        bm25_docs = []
        if self._bm25_retriever:
            bm25_docs = self._bm25_retriever.invoke(query)

        # Merge results
        merged = self._merge_results(vector_docs, bm25_docs)

        # Limit to k
        results = merged[:k]

        logger.info(
            "Hybrid retrieval complete",
            query=query[:50],
            vector_count=len(vector_docs),
            bm25_count=len(bm25_docs),
            merged_count=len(results)
        )

        return results

    def retrieve_with_scores(
        self,
        query: str,
        k: int = None
    ) -> List[Tuple[Document, float]]:
        """Retrieve documents with relevance scores (vector only)."""
        k = k or self.k
        vectorstore = get_chroma_client()
        return vectorstore.similarity_search_with_score(query, k=k)

    def add_retrieval_explanation(
        self,
        docs: List[Document],
        query: str
    ) -> List[Document]:
        """Add explanation metadata to retrieved documents."""
        query_terms = set(query.lower().split())

        for doc in docs:
            content_lower = doc.page_content.lower()
            matched_terms = [
                term for term in query_terms
                if term in content_lower and len(term) > 2
            ]

            doc.metadata["retrieval_explanation"] = {
                "matched_terms": matched_terms,
                "method": doc.metadata.get("retrieval_method", "unknown"),
            }

        return docs


def get_retriever(k: int = None) -> HybridRetriever:
    """Get a configured hybrid retriever."""
    settings = get_settings()
    return HybridRetriever(k=k or settings.RETRIEVAL_TOP_K)