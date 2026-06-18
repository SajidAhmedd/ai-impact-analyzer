# """Quick test to verify LLM, embeddings, and vector store work."""

# import sys
# sys.path.insert(0, ".")

# from app.core.llm import get_llm, check_ollama_connection
# from app.core.embeddings import get_embeddings, check_embeddings_connection
# from app.core.vectorstore import (
#     get_chroma_client,
#     add_documents_to_store,
#     search_documents,
#     get_collection_stats
# )

# print("=" * 50)
# print("Testing Ollama LLM...")
# print("=" * 50)

# if check_ollama_connection():
#     print("✓ LLM working!\n")
# else:
#     print("✗ LLM failed - is Ollama running?")
#     exit(1)

# print("=" * 50)
# print("Testing Embedding Model...")
# print("=" * 50)

# if check_embeddings_connection():
#     print("✓ Embeddings working!\n")
# else:
#     print("✗ Embeddings failed")
#     exit(1)

# print("=" * 50)
# print("Testing ChromaDB Vector Store...")
# print("=" * 50)

# try:
#     # Add test documents
#     test_docs = [
#         "The refund policy allows returns within 30 days.",
#         "Technical support is available 24/7 via email.",
#         "Employee onboarding requires HR approval first."
#     ]
#     test_metadata = [
#         {"source": "policy.txt", "department": "finance"},
#         {"source": "support.txt", "department": "IT"},
#         {"source": "hr_guide.txt", "department": "HR"}
#     ]

#     add_documents_to_store(test_docs, test_metadata)

#     # Get stats
#     stats = get_collection_stats()
#     print(f"Documents in store: {stats['count']}")

#     # Test search
#     results = search_documents("How do I get a refund?", k=2)
#     print(f"\nSearch results for 'How do I get a refund?':")
#     for doc, score in results:
#         print(f"  - Score: {score:.3f} | {doc.page_content[:50]}...")

#     print("\n✓ ChromaDB working!\n")

# except Exception as e:
#     print(f"✗ ChromaDB failed: {e}")
#     exit(1)

# print("=" * 50)
# print("All systems operational!")
# print("=" * 50)

#2

# """Test the complete ingestion pipeline."""

# import sys
# sys.path.insert(0, ".")

# from app.core.vectorstore import get_collection_stats, search_documents
# from app.ingestion.processor import process_document

# print("=" * 50)
# print("Testing Document Ingestion Pipeline")
# print("=" * 50)

# # Process the sample document
# file_path = "data/documents/sample_policy.txt"
# metadata = {
#     "department": "customer_service",
#     "doc_type": "policy",
#     "criticality": "high"
# }

# try:
#     chunks = process_document(file_path, metadata)
#     print(f"✓ Processed document into {chunks} chunks\n")
# except FileNotFoundError:
#     print(f"✗ File not found: {file_path}")
#     print("  Create the sample document first!")
#     exit(1)

# # Check stats
# stats = get_collection_stats()
# print(f"Total documents in store: {stats['count']}\n")

# # Test search
# print("=" * 50)
# print("Testing Search...")
# print("=" * 50)

# queries = [
#     "How do I get a refund?",
#     "What is the return policy?",
#     "How to contact support?"
# ]

# for query in queries:
#     print(f"\nQuery: '{query}'")
#     results = search_documents(query, k=2)
#     for doc, score in results:
#         print(f"  Score: {score:.3f} | {doc.page_content[:60]}...")

# print("\n" + "=" * 50)
# print("✓ Ingestion pipeline working!")
# print("=" * 50)

#3

# """Test the RAG retriever."""

# import sys
# sys.path.insert(0, ".")

# from app.rag.retriever import get_retriever, HybridRetriever

# print("=" * 50)
# print("Testing Hybrid Retriever")
# print("=" * 50)

# # Create retriever
# retriever = get_retriever(k=3)

# # Test queries
# queries = [
#     "How do I get a refund?",
#     "contact support email",
#     "digital products return policy",
# ]

# for query in queries:
#     print(f"\n{'='*50}")
#     print(f"Query: '{query}'")
#     print("=" * 50)

#     docs = retriever.retrieve(query)
#     docs = retriever.add_retrieval_explanation(docs, query)

#     if not docs:
#         print("  No results found")
#         continue

#     for i, doc in enumerate(docs, 1):
#         print(f"\n  Result {i}:")
#         print(f"  Content: {doc.page_content[:80]}...")
#         print(f"  Source: {doc.metadata.get('source', 'unknown')}")
#         explanation = doc.metadata.get('retrieval_explanation', {})
#         print(f"  Matched terms: {explanation.get('matched_terms', [])}")

# print("\n" + "=" * 50)
# print("✓ Hybrid retriever working!")
# print("=" * 50)




#4

"""Test the LangGraph workflow."""

import sys
sys.path.insert(0, ".")

from app.workflow.graph import run_analysis
import json

print("=" * 60)
print("Testing LangGraph Analysis Workflow")
print("=" * 60)

# Test change request
change_request = """
Increase the refund approval threshold from $100 to $500.
This change affects the customer service department's ability
to process refunds without manager approval.
"""

print(f"\nChange Request:\n{change_request.strip()}\n")
print("=" * 60)
print("Running analysis (this may take a moment)...")
print("=" * 60)

# Run the analysis
result = run_analysis(change_request)

# Display results
print("\n📄 RETRIEVED DOCUMENTS:")
print("-" * 40)
for i, doc in enumerate(result.get("retrieved_docs", []), 1):
    print(f"\n  Doc {i}: {doc['metadata'].get('source', 'unknown')}")
    print(f"  Content: {doc['content'][:100]}...")

print("\n\n🔧 TECHNICAL ANALYSIS:")
print("-" * 40)
tech = result.get("technical_analysis", {})
print(json.dumps(tech, indent=2))

print("\n\n📊 EXECUTION TRACE:")
print("-" * 40)
for step in result.get("execution_trace", []):
    print(f"  {step['node']}: {step['latency_ms']:.0f}ms")

print("\n" + "=" * 60)
print("✓ Workflow test complete!")
print("=" * 60)