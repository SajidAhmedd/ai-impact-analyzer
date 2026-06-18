# AI Change Impact Analyzer

A multi-agent AI system that analyzes business and policy changes to predict technical, operational, and risk impacts. Built with LangGraph for orchestration, Ollama for local LLM inference, and FastAPI for the backend.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-purple.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Overview

Organizations frequently face challenges when implementing business or policy changes, as these can have far-reaching impacts across technical systems, operations, and risk profiles. This AI-powered analyzer uses a **multi-agent architecture** to provide comprehensive impact assessments by:

- Ingesting and understanding organizational documents (policies, procedures, technical docs)
- Using RAG (Retrieval-Augmented Generation) to find relevant context
- Running specialized AI agents in parallel to analyze different impact dimensions
- Synthesizing findings into actionable recommendations

## Architecture

```
+---------------------------------------------------------------------+
|                         User Interface                               |
|                    (Streamlit / API Clients)                         |
+-----------------------------------+---------------------------------+
                                    |
                                    v
+---------------------------------------------------------------------+
|                         FastAPI Backend                              |
|              (Authentication, Request Handling, Logging)             |
+-----------------------------------+---------------------------------+
                                    |
                                    v
+---------------------------------------------------------------------+
|                      LangGraph Workflow                              |
|  +-----------+                                                       |
|  | Retriever | --> Hybrid Search (BM25 + Vector)                    |
|  +-----+-----+                                                       |
|        |                                                             |
|        v                                                             |
|  +----------------------------------------------------------+       |
|  |              Parallel Agent Execution                     |       |
|  |  +----------+  +-----------+  +------------+             |       |
|  |  |Technical |  |Operational|  |    Risk    |             |       |
|  |  |  Agent   |  |   Agent   |  |   Agent    |             |       |
|  |  +----------+  +-----------+  +------------+             |       |
|  +----------------------------+-----------------------------+       |
|                               |                                      |
|                               v                                      |
|                      +-----------------+                             |
|                      |   Synthesizer   |                             |
|                      |      Agent      |                             |
|                      +-----------------+                             |
+---------------------------------------------------------------------+
                                    |
                    +---------------+---------------+
                    v                               v
           +--------------+                +--------------+
           |    Ollama    |                |   ChromaDB   |
           |  (Local LLM) |                | (Vector DB)  |
           +--------------+                +--------------+
```

## Features

### Multi-Agent Analysis
- **Technical Agent**: Analyzes system dependencies, integration points, and technical debt implications
- **Operational Agent**: Evaluates workflow changes, resource requirements, and process impacts
- **Risk Agent**: Identifies compliance risks, security concerns, and mitigation strategies
- **Synthesizer Agent**: Combines insights and generates prioritized recommendations

### RAG Pipeline
- **Hybrid Retrieval**: Combines BM25 keyword search with semantic vector search
- **Document Processing**: Supports PDF, DOCX, TXT, and MD files
- **Smart Chunking**: Context-aware document splitting with overlap

### Production Ready
- **API Authentication**: Secure API key-based authentication
- **Request Logging**: Structured logging with request tracing
- **Health Checks**: Comprehensive health monitoring endpoints
- **Docker Support**: Multi-stage builds with docker-compose orchestration

### Evaluation Framework
- Built-in evaluation suite for measuring analysis quality
- Automated scoring across technical, operational, and risk dimensions

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI, Pydantic |
| Orchestration | LangGraph |
| LLM | Ollama (llama3) |
| Embeddings | nomic-embed-text |
| Vector DB | ChromaDB |
| Frontend | Streamlit |
| Logging | Structlog |
| Containerization | Docker, Docker Compose |

## Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Ollama installed locally (or via Docker)

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-change-impact-analyzer.git
cd ai-change-impact-analyzer

# Copy environment file
cp .env.example .env

# Start all services
docker compose up -d

# Pull required Ollama models (first time only)
docker exec -it impact-analyzer-ollama ollama pull llama3
docker exec -it impact-analyzer-ollama ollama pull nomic-embed-text
```

**Access:**
- API Documentation: http://localhost:8000/docs
- Streamlit UI: http://localhost:8501
- Health Check: http://localhost:8000/health

### Option 2: Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start Ollama (separate terminal)
ollama serve

# Pull required models
ollama pull llama3
ollama pull nomic-embed-text

# Copy and configure environment
cp .env.example .env

# Run FastAPI server
uvicorn app.main:app --reload --port 8000

# Run Streamlit (separate terminal)
streamlit run streamlit_app/app.py
```

## API Usage

### Authentication

All protected endpoints require an API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/documents/stats
```

### Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Full health check (Ollama, ChromaDB) |
| `/health/live` | GET | No | Quick liveness probe |
| `/health/ready` | GET | No | Readiness probe |
| `/docs` | GET | No | Swagger documentation |
| `/documents/upload` | POST | Yes | Upload documents |
| `/documents/stats` | GET | Yes | Get document statistics |
| `/analysis/run` | POST | Yes | Run impact analysis |
| `/traces/` | GET | Yes | Get analysis traces |

### Example: Run Analysis

```bash
curl -X POST "http://localhost:8000/analysis/run"   -H "X-API-Key: your-api-key"   -H "Content-Type: application/json"   -d '{"change_request": "Increase refund approval threshold from 100 to 500"}'
```

### Example Response

```json
{
  "change_request": "Increase refund approval threshold from 100 to 500",
  "technical_analysis": {
    "summary": "Moderate technical impact requiring system updates",
    "affected_systems": ["Refund Processing System", "Customer Support System"]
  },
  "operational_analysis": {
    "summary": "Process changes needed for finance and support teams",
    "affected_workflows": ["Refund Approval", "Manager Review"],
    "disruption_level": "medium"
  },
  "risk_analysis": {
    "summary": "Increased fraud exposure requires monitoring",
    "overall_risk_level": "medium"
  },
  "final_assessment": {
    "recommendation": "proceed_with_caution",
    "overall_impact_level": "medium",
    "executive_summary": "Feasible with proper controls in place."
  },
  "total_time_ms": 45000
}
```

## Project Structure

```
ai-change-impact-analyzer/
├── app/
│   ├── api/
│   │   ├── routes/          # API endpoints
│   │   └── schemas/         # Pydantic models
│   ├── auth/                # API key authentication
│   ├── core/                # LLM, embeddings, vectorstore
│   ├── evaluation/          # Evaluation framework
│   ├── ingestion/           # Document processing
│   ├── observability/       # Logging, tracing, middleware
│   ├── rag/                 # Retrieval logic
│   ├── utils/               # Utilities (JSON parser, etc.)
│   ├── workflow/
│   │   ├── nodes/           # Agent implementations
│   │   ├── graph.py         # LangGraph workflow
│   │   └── state.py         # State management
│   ├── config.py            # Settings management
│   └── main.py              # FastAPI application
├── streamlit_app/           # Streamlit frontend
├── evaluation/              # Evaluation test cases
├── tests/                   # Unit & integration tests
├── prompts/                 # Agent prompt templates
├── docker-compose.yml       # Docker orchestration
├── Dockerfile               # Container build
└── requirements.txt         # Python dependencies
```

## Configuration

Environment variables (`.env`):

```env
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
OLLAMA_EMBED_MODEL=nomic-embed-text

# Model Parameters
LLM_TEMPERATURE=0.1

# ChromaDB
CHROMA_PERSIST_DIR=./data/chroma_db
CHROMA_COLLECTION_NAME=documents

# Retrieval
RETRIEVAL_TOP_K=5

# Authentication
API_KEY=your-secure-api-key-here
AUTH_ENABLED=true

# Application
LOG_LEVEL=INFO
DEBUG=false
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run evaluation suite
python -m app.evaluation.evaluator
```

## Development

```bash
# Format code
ruff format .

# Lint code
ruff check .
```

## Roadmap

- [ ] Support for more document formats (Excel, PowerPoint)
- [ ] Async document processing queue
- [ ] Multi-tenancy support
- [ ] Custom agent configuration via UI
- [ ] Export reports to PDF
- [ ] Integration with ticketing systems (Jira, ServiceNow)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [LangChain](https://github.com/langchain-ai/langchain) & [LangGraph](https://github.com/langchain-ai/langgraph) for the orchestration framework
- [Ollama](https://ollama.ai/) for local LLM inference
- [ChromaDB](https://www.trychroma.com/) for vector storage
- [FastAPI](https://fastapi.tiangolo.com/) for the blazing-fast API framework
