# AI Change Impact Analyzer: A Beginner's Tutorial

This tutorial walks you through the whole code base of the AI Change Impact Analyzer, file by file and function by function. By the end you should be able to explain what every part does, why it was written that way, and where you would change it.

You need mid-level Python: functions, classes, imports and `try/except`. You do **not** need to know web frameworks, databases or AI libraries. Each one is explained when it first appears.

## Contents

1. [How to use this tutorial](#1-how-to-use-this-tutorial)
2. [The big picture](#2-the-big-picture)
3. [Folder map](#3-folder-map)
4. [Python concepts you need](#4-python-concepts-you-need)
5. [The libraries](#5-the-libraries)
6. [Every file and every function](#6-every-file-and-every-function)
7. [One request traced from start to finish](#7-one-request-traced-from-start-to-finish)
8. [Things to notice](#8-things-to-notice)
9. [Exercises](#9-exercises)
10. [Glossary](#10-glossary)

---

## 1. How to use this tutorial

This tutorial is meant to be read **next to the code**, not on its own.

1. Open the repo folder in VS Code (`File → Open Folder…`).
2. Open `TUTORIAL.md`, then press **Ctrl+K V** (Cmd+K V on a Mac). This opens the Markdown preview in a panel to the side, so the tutorial sits on the right and the code on the left.
3. Every link that looks like [app/config.py:20-86](app/config.py#L20-L86) is clickable. Clicking it in the preview opens that file and jumps to those lines. Read the explanation, then glance left at the real code.
4. Links in section headings (like the contents list above) jump inside this file.

Why read this way? Code is only understood by reading it. The tutorial tells you *what to look for* and *why it is there*; the code shows you *exactly how*. The snippets below are short extracts. The link always takes you to the full version.

A tip: read sections 2 to 5 first, in order. Section 6 is long and follows the order in which files import each other, so a file is only explained after everything it depends on. You can stop after any file and come back later.

---

## 2. The big picture

### What the project does

Imagine a company wants to change a rule, for example: *"Increase the refund approval threshold from $100 to $500."* Before doing it, someone should ask:

- **Technical**: which software systems need to change?
- **Operational**: which teams and daily processes are affected? Does anyone need training?
- **Risk**: what could go wrong (fraud, compliance, security)?

This project asks those three questions to an AI model (an LLM, a "large language model") for you. Each question is handled by a separate **agent** (a function with its own instructions to the LLM). A fourth agent, the **synthesizer**, reads the three answers and writes a final recommendation such as "proceed with caution".

To make the answers specific to *your* company, the agents are given relevant extracts from your own documents (policies, procedures). Finding those extracts is called **retrieval**, and giving them to the LLM is called **RAG** (retrieval-augmented generation). Without RAG, the LLM would only use general knowledge; with RAG, it can say "your refund policy says refunds are processed within 5-7 business days".

### How the pieces fit together

```
                 You (in a browser)
                        |
                        v
     +--------------------------------------+
     |  Streamlit UI  (streamlit_app/app.py) |   a simple web page
     +--------------------------------------+
                        |  HTTP POST /analysis/run  + X-API-Key header
                        v
     +--------------------------------------+
     |  FastAPI backend  (app/main.py)       |   the "server"
     |   - request logging middleware        |
     |   - API key check  (app/auth)         |
     |   - routes         (app/api/routes)   |
     +--------------------------------------+
                        |  run_analysis(change_request)
                        v
     +--------------------------------------------------------+
     |  LangGraph workflow  (app/workflow/graph.py)            |
     |                                                         |
     |  retrieve -> technical -> operational -> risk -> synthesize
     |     |            \____________|___________/          |  |
     |     |                    each calls the LLM          |  |
     +-----|---------------------------|-----------------------+
           v                           v
   +----------------+         +---------------------+
   | Hybrid search  |         | LLM provider         |
   | (app/rag)      |         | (app/core/llm.py)    |
   |  BM25 + vector |         |  Groq / Gemini /     |
   +----------------+         |  Ollama              |
           |                  +---------------------+
           v
   +----------------+       +------------------------+
   | ChromaDB       | <---- | Embeddings              |
   | (vector store, |       | (app/core/embeddings.py)|
   |  data/chroma_db)|      |  FastEmbed / Ollama     |
   +----------------+       +------------------------+
           ^
           |  documents are loaded, chunked and stored here
   +----------------------------------+
   | Ingestion (app/ingestion)         |
   |  upload or startup seeding        |
   +----------------------------------+
```

Two important facts about this diagram:

- The four agents run **one after another**, not in parallel. The README says "parallel", but the code in [app/workflow/graph.py:143-149](app/workflow/graph.py#L143-L149) chains them in a line. More on this in [section 8](#8-things-to-notice).
- The UI and the backend are **two separate programs** that talk over HTTP. You could delete the UI and still use the backend with `curl` or the automatic docs page at `/docs`.

### Two ways it runs

| Setting | LLM | Embeddings | Where |
|---|---|---|---|
| **Local** (default in `.env.example`) | Ollama running on your PC (`llama3`) | Ollama (`nomic-embed-text`) | your machine or `docker compose` |
| **Hosted demo** (defaults in the Dockerfile) | Groq, falling back to Gemini | FastEmbed, inside the Python process | one Docker container on Hugging Face Spaces |

The switch between them is just configuration, read in [app/config.py](app/config.py). No code changes are needed. That is a deliberate design choice you'll see again and again.

---

## 3. Folder map

Every folder and file in the repo, one line each.

```
ai-impact-analyzer/
├── .dockerignore              files Docker should not copy into the image
├── .env.example               template for your secret/config file .env (copy it to .env)
├── .gitattributes             forces Unix line endings for .sh files (so start.sh runs in Linux)
├── .github/workflows/
│   ├── ci.yml                 GitHub Actions: lint, run tests, build the Docker image on every push
│   └── deploy-hf.yml          GitHub Actions: push to Hugging Face Spaces, ping the demo twice a day
├── .gitignore                 files git should not track (.env, logs, the database, caches)
├── Dockerfile                 recipe for the single container used by the hosted demo
├── LICENSE                    MIT licence
├── README.md                  project overview; its top block is also the Hugging Face Space config
├── app/                       the backend (FastAPI) package
│   ├── __init__.py            empty; marks app/ as a package so "import app.x" works
│   ├── main.py                creates the FastAPI app, adds middleware and routes, startup seeding
│   ├── config.py              all settings in one class, read from environment variables / .env
│   ├── api/
│   │   ├── __init__.py        empty package marker
│   │   ├── routes/
│   │   │   ├── __init__.py    empty package marker
│   │   │   ├── analysis.py    POST /analysis/run: runs the whole workflow
│   │   │   ├── documents.py   upload a document, get stats, clear the store
│   │   │   ├── health.py      /health, /health/ready, /health/live
│   │   │   └── traces.py      /traces endpoints (see section 8: always empty)
│   │   └── schemas/
│   │       └── __init__.py    empty; the folder is reserved but unused
│   ├── auth/
│   │   ├── __init__.py        re-exports the auth functions
│   │   └── api_key.py         checks the X-API-Key header
│   ├── core/
│   │   ├── __init__.py        empty package marker
│   │   ├── embeddings.py      builds the embedding model (FastEmbed or Ollama)
│   │   ├── llm.py             builds the chat model (Groq, Gemini or Ollama) with optional fallback
│   │   └── vectorstore.py     opens the ChromaDB vector database
│   ├── evaluation/
│   │   ├── __init__.py        re-exports the evaluator classes
│   │   └── evaluator.py       scores the agents' answers against expected results
│   ├── ingestion/
│   │   ├── __init__.py        empty package marker
│   │   ├── chunker.py         splits long documents into overlapping chunks
│   │   ├── loader.py          reads .txt, .md, .pdf and .docx files
│   │   └── processor.py       load -> chunk -> store, for one file or a whole folder
│   ├── observability/
│   │   ├── __init__.py        empty package marker
│   │   ├── logger.py          structured (JSON) logging set-up
│   │   ├── middleware.py      logs every HTTP request with an ID and a duration
│   │   └── tracer.py          an execution-trace store (built but never filled, see section 8)
│   ├── prompts/
│   │   └── __init__.py        loads the prompt .txt files from the top-level prompts/ folder
│   ├── rag/
│   │   ├── __init__.py        empty package marker
│   │   └── retriever.py       hybrid search: vector search + BM25 keyword search
│   ├── utils/
│   │   ├── __init__.py        one-line docstring
│   │   └── json_parser.py     turns messy LLM text into a Python dict
│   └── workflow/
│       ├── __init__.py        empty package marker
│       ├── graph.py           wires the agents together with LangGraph
│       ├── state.py           the shared "state" dictionary every agent reads and writes
│       └── nodes/
│           ├── __init__.py    empty package marker
│           ├── retriever.py   agent 0: fetch relevant document chunks
│           ├── technical.py   agent 1: technical impact
│           ├── operational.py agent 2: operational impact
│           ├── risk.py        agent 3: risks
│           └── synthesizer.py agent 4: final recommendation + confidence score
├── data/documents/
│   └── sample_policy.txt      a tiny refund policy, loaded at startup in the demo
├── docker-compose.yml         runs API + UI + Ollama as three containers locally
├── evaluation/
│   ├── evaluator.py           an older duplicate of app/evaluation/evaluator.py (unused)
│   ├── run_evaluation.py      command-line script that runs the evaluator and prints scores
│   └── test_cases/
│       └── sample_cases.json  4 example changes with what a good answer should contain
├── prompts/
│   ├── operational.txt        instructions sent to the LLM by the operational agent
│   ├── risk.txt               instructions for the risk agent
│   ├── synthesizer.txt        instructions for the synthesizer
│   └── technical.txt          instructions for the technical agent
├── pyproject.toml             project metadata and ruff settings (its dependency list is out of date)
├── requirements.txt           the real dependency list used by Docker and CI
├── start.sh                   starts API and UI together inside the hosted container
├── streamlit_app/
│   ├── __init__.py            empty package marker
│   ├── app.py                 the web UI
│   └── components/
│       └── __init__.py        empty; reserved but unused
├── test_setup.py              old manual smoke-test script (mostly commented out)
└── tests/
    ├── __init__.py            docstring only
    ├── test_config.py         3 tests for the default settings
    ├── test_state.py          1 test for the state dictionary
    ├── test_api/__init__.py   empty; no API tests yet
    └── test_workflow/__init__.py  empty; no workflow tests yet
```

---

## 4. Python concepts you need

These are the Python features this code uses that go beyond "functions, classes, imports, try/except". Each has a one-line recap and a pointer to where you'll see it.

**Type hints.** `def load_prompt(name: str) -> str:` says "name should be a string, and this returns a string". Python does not enforce them at runtime; they help readers, editors and libraries like Pydantic. Seen everywhere, e.g. [app/prompts/__init__.py:18](app/prompts/__init__.py#L18).

**`Optional[X]`** means "X or `None`". From the `typing` module. [app/observability/tracer.py:21](app/observability/tracer.py#L21).

**Decorators.** A line starting with `@` above a function wraps that function in another one. `@lru_cache` (below) and `@router.get("/live")` are both decorators. The second one *registers* the function as the handler for a web address. [app/api/routes/health.py:54-57](app/api/routes/health.py#L54-L57).

**`functools.lru_cache`.** Remembers a function's return value. The first call runs the function; later calls with the same arguments return the saved result instantly. This project uses it to create expensive objects (settings, the LLM client, the embedding model) *once* and share them. [app/config.py:89-104](app/config.py#L89-L104).

```python
@lru_cache
def get_settings() -> Settings:
    return Settings()          # runs only on the very first call
```

**Dataclasses.** `@dataclass` writes the boring `__init__` for you from a list of typed fields. [app/observability/tracer.py:15-27](app/observability/tracer.py#L15-L27). `field(default_factory=list)` gives each object its own new empty list (a plain `= []` default would be shared by all objects, a classic bug).

**`TypedDict`.** A dictionary type that lists which keys exist and what type each value has. It is still an ordinary `dict` at runtime. `total=False` means every key is optional. [app/workflow/state.py:18](app/workflow/state.py#L18).

**Dictionary unpacking `{**d, "k": v}`.** Builds a *new* dict: a copy of `d` with key `k` added or replaced. Every agent returns its result this way, e.g. [app/workflow/nodes/technical.py:131-135](app/workflow/nodes/technical.py#L131-L135).

**List comprehensions and conditional expressions.** `[x for x in items if cond]` and `a if cond else b`. Used to build the context text in each agent, [app/workflow/nodes/technical.py:71-74](app/workflow/nodes/technical.py#L71-L74).

**Imports inside a function.** `from langchain_groq import ChatGroq` is placed *inside* the `if provider == "groq":` block ([app/core/llm.py:37-38](app/core/llm.py#L37-L38)). Why? So you only need that library installed if you actually use that provider, and start-up is faster.

**Module-level code runs on import.** Code that is not inside a function runs the moment a file is imported. For example [app/prompts/__init__.py:60-63](app/prompts/__init__.py#L60-L63) reads four files from disk as soon as anything imports `app.prompts`. Keep this in mind when you see a crash "at import time".

**Global variables as singletons.** [app/observability/tracer.py:165-173](app/observability/tracer.py#L165-L173) keeps one shared `ExecutionTracer` in a module variable and uses `global _tracer` to replace it the first time. Same idea as `lru_cache`, written by hand.

**`async def` and `await`.** An `async` function can pause while waiting (for a file upload or network reply) and let the server handle other requests meanwhile. FastAPI can call both normal and `async` functions. You'll see `await file.read()` in [app/api/routes/documents.py:52](app/api/routes/documents.py#L52) and `await call_next(request)` in [app/observability/middleware.py:43](app/observability/middleware.py#L43). You don't need to write async code to follow this tutorial; just read `await` as "wait for this result".

**Context managers (`with`).** An object with `__enter__` and `__exit__` methods can be used in a `with` block; `__exit__` always runs at the end, even on errors. [app/observability/logger.py:78-96](app/observability/logger.py#L78-L96) defines one.

**Operator overloading.** A class can decide what `a | b` means. LangChain makes `prompt | llm` mean "feed the prompt's output into the LLM", building a small pipeline called a *chain*. [app/workflow/nodes/technical.py:81](app/workflow/nodes/technical.py#L81).

**Regular expressions (`re`).** A mini-language for finding text patterns. `re.sub(r',\s*}', '}', s)` means "replace a comma followed by any spaces and a `}` with just `}`". Used heavily in [app/utils/json_parser.py](app/utils/json_parser.py).

**`pathlib.Path`.** An object for file paths. `Path("logs") / "app.log"` joins paths with `/`; `.exists()`, `.read_text()`, `.mkdir()` do what they say. [app/ingestion/loader.py:35-40](app/ingestion/loader.py#L35-L40).

**Nested classes for configuration.** Pydantic lets you put `class Config:` inside a model to set options, like an example for the docs page. [app/api/routes/analysis.py:25-30](app/api/routes/analysis.py#L25-L30).

---

## 5. The libraries

These are all the packages in [requirements.txt](requirements.txt), grouped as in that file, plus three that are used in the code but arrive indirectly.

### Web framework

**FastAPI** (`fastapi`). A library for building web APIs. You write normal Python functions and decorate them with the URL they answer; FastAPI turns the incoming JSON into Python objects, validates it, and turns your return value back into JSON. It also generates an interactive docs page at `/docs` for free.
*Why here:* the backend needs to receive "analyse this change" requests from the UI and return results.

```python
from fastapi import FastAPI
app = FastAPI()

@app.get("/hello")
def hello(name: str):
    return {"message": f"Hi {name}"}   # GET /hello?name=Sam  ->  {"message": "Hi Sam"}
```
*Where:* [app/main.py:21-27](app/main.py#L21-L27), every file in [app/api/routes](app/api/routes/analysis.py), [app/auth/api_key.py](app/auth/api_key.py).

**Uvicorn** (`uvicorn`). The program that actually listens on a network port and passes requests to FastAPI. FastAPI is the "what to do", Uvicorn is the "server running it".
*Where:* started from the command line: `uvicorn app.main:app` in [start.sh:6](start.sh#L6) and [docker-compose.yml:8](docker-compose.yml#L8). `app.main:app` means "the variable `app` in the module `app/main.py`".

**python-multipart** (`python-multipart`). FastAPI needs it to read form fields and file uploads. You never import it; FastAPI does.
*Where:* needed by `File(...)` and `Form(...)` in [app/api/routes/documents.py:33-38](app/api/routes/documents.py#L33-L38).

### LLM and AI

**LangChain** (`langchain`, `langchain-community`, plus `langchain-core` which comes with them). A toolkit that gives a common interface to many LLMs, embedding models, vector stores and document tools. Its key idea: every component is a *Runnable* with `.invoke(input)`, and runnables can be joined with `|`.
*Why here:* the same agent code works with Groq, Gemini or Ollama because they all look the same through LangChain.

```python
from langchain_core.prompts import ChatPromptTemplate
prompt = ChatPromptTemplate.from_template("Translate to French: {text}")
chain = prompt | llm                       # llm is any LangChain chat model
print(chain.invoke({"text": "Good morning"}).content)
```
*Where:* `ChatPromptTemplate` in every agent ([app/workflow/nodes/technical.py:77](app/workflow/nodes/technical.py#L77)); `Document` objects in [app/ingestion/loader.py:19](app/ingestion/loader.py#L19); `BM25Retriever` from `langchain_community` in [app/rag/retriever.py:12](app/rag/retriever.py#L12); `FastEmbedEmbeddings` in [app/core/embeddings.py:45](app/core/embeddings.py#L45); `.with_fallbacks()` in [app/core/llm.py:116](app/core/llm.py#L116).

**langchain-ollama** (`langchain-ollama`). LangChain's connector to **Ollama**, a free program that runs open models (like Llama 3) on your own computer.
*Where:* `ChatOllama` in [app/core/llm.py:67-80](app/core/llm.py#L67-L80), `OllamaEmbeddings` in [app/core/embeddings.py:51-64](app/core/embeddings.py#L51-L64).

**langchain-groq** (`langchain-groq`). Connector to **Groq**, a hosted service that runs open models very fast, with a free tier. Needs `GROQ_API_KEY`.
*Where:* [app/core/llm.py:37-50](app/core/llm.py#L37-L50).

**langchain-google-genai** (`langchain-google-genai`). Connector to Google **Gemini**. Needs `GEMINI_API_KEY`.
*Where:* [app/core/llm.py:52-65](app/core/llm.py#L52-L65).

**LangGraph** (`langgraph`). Builds a workflow as a *graph*: boxes (nodes, here our agents) and arrows (edges, the order). A shared *state* dictionary flows along the arrows. It is overkill for a straight line, but makes it easy to add branches or parallel steps later.

```python
from langgraph.graph import StateGraph, END
g = StateGraph(dict)
g.add_node("a", lambda s: {**s, "x": 1})
g.set_entry_point("a")
g.add_edge("a", END)
print(g.compile().invoke({}))   # {'x': 1}
```
*Where:* only in [app/workflow/graph.py:110](app/workflow/graph.py#L110) and [app/workflow/graph.py:123-156](app/workflow/graph.py#L123-L156).

### Vector database and retrieval

**ChromaDB** (`chromadb`) and its LangChain connector **langchain-chroma** (`langchain-chroma`). A *vector database*: it stores pieces of text together with their *embeddings* (lists of numbers that capture meaning, see FastEmbed below) and can find the stored pieces whose numbers are closest to a query's numbers. That is "semantic search": "money back" can find a chunk that says "refund". Chroma saves to a folder on disk (`data/chroma_db`).
*Where:* [app/core/vectorstore.py:59-63](app/core/vectorstore.py#L59-L63).

```python
from langchain_chroma import Chroma
store = Chroma(collection_name="demo", embedding_function=embeddings, persist_directory="./db")
store.add_texts(["Refunds take 5-7 days."])
print(store.similarity_search("how long for money back?", k=1))
```

**rank-bm25** (`rank-bm25`). Implements **BM25**, a classic keyword-search scoring formula (the kind search engines used before AI). It rewards documents that contain the query's exact words, especially rare ones. You never import it directly; LangChain's `BM25Retriever` uses it inside.
*Why here:* semantic search can miss exact terms like "JWT" or "$500". Combining both is called *hybrid* search.
*Where:* [app/rag/retriever.py:71-74](app/rag/retriever.py#L71-L74).

**FastEmbed** (`fastembed`). A small library that turns text into embeddings on the CPU, inside the Python process, no separate server needed. The model used here (`BAAI/bge-small-en-v1.5`) gives 384 numbers per text.
*Why here:* the hosted demo can't run Ollama, so it embeds locally with FastEmbed.
*Where:* [app/core/embeddings.py:44-49](app/core/embeddings.py#L44-L49) and the model download at build time in [Dockerfile:50](Dockerfile#L50).

### Document processing

**pypdf** (`pypdf`). Reads PDF files and extracts their text page by page.
*Where:* [app/ingestion/loader.py:66-77](app/ingestion/loader.py#L66-L77).

```python
from pypdf import PdfReader
for page in PdfReader("policy.pdf").pages:
    print(page.extract_text())
```

**python-docx** (`python-docx`, imported as `docx`). Reads Word `.docx` files.
*Where:* [app/ingestion/loader.py:105-115](app/ingestion/loader.py#L105-L115).

### Data validation

**Pydantic** (`pydantic`). You describe the shape of data as a class with typed fields; Pydantic checks real data against it and converts it. FastAPI uses Pydantic models for request and response bodies.

```python
from pydantic import BaseModel, Field
class AnalysisRequest(BaseModel):
    change_request: str = Field(..., min_length=10)
AnalysisRequest(change_request="short")   # raises ValidationError: too short
```
*Where:* request/response models in [app/api/routes/analysis.py:22-49](app/api/routes/analysis.py#L22-L49), [app/api/routes/health.py:15-20](app/api/routes/health.py#L15-L20), and unused models in [app/workflow/nodes/technical.py:29-43](app/workflow/nodes/technical.py#L29-L43).

**pydantic-settings** (`pydantic-settings`). Like Pydantic, but fills the fields from environment variables and a `.env` file.
*Where:* [app/config.py:17-86](app/config.py#L17-L86).

### Observability

**structlog** (`structlog`). Structured logging: instead of `print("Loaded 5 chunks")` you write `logger.info("Loaded", chunks=5)`, and the output is a JSON line with separate fields. Machines (and you, with `grep`) can then filter logs by field.
*Where:* configured in [app/observability/logger.py:46-62](app/observability/logger.py#L46-L62); used in almost every file as `logger = structlog.get_logger()`.

### Frontend

**Streamlit** (`streamlit`). Builds a web page from a plain Python script. Each `st.button`, `st.text_area`, `st.json` call adds a widget. Every time the user clicks something, **the whole script runs again from the top**; values you want to keep between runs go in `st.session_state`.

```python
import streamlit as st
name = st.text_input("Your name")
if st.button("Greet"):
    st.success(f"Hello {name}")
```
*Where:* [streamlit_app/app.py](streamlit_app/app.py).

**requests** (not listed in `requirements.txt`; it is installed as a dependency of `langchain-community`). The standard library for making HTTP calls from Python.
*Where:* the UI calls the API with it in [streamlit_app/app.py:81-86](streamlit_app/app.py#L81-L86).

**langchain-text-splitters** (not listed; installed with `langchain`). Splits long text into chunks.
*Where:* [app/ingestion/chunker.py:12](app/ingestion/chunker.py#L12).

### Development tools

**pytest** (`pytest`). Finds functions named `test_*` in files named `test_*.py` and runs them; a failed `assert` is a failed test.
*Where:* [tests/test_config.py](tests/test_config.py), [tests/test_state.py](tests/test_state.py), CI in [.github/workflows/ci.yml:56-59](.github/workflows/ci.yml#L56-L59).

**pytest-asyncio** (`pytest-asyncio`). Lets pytest run `async def` tests. No test uses it yet.

**httpx** (`httpx`). An HTTP client; FastAPI's `TestClient` needs it to call your API in tests without starting a server. Installed but not used yet (see [exercise 9](#9-exercises)).

**ruff** (`ruff`). A very fast linter (finds unused imports, style problems). Configured in [pyproject.toml:53-55](pyproject.toml#L53-L55), run in [.github/workflows/ci.yml:28-31](.github/workflows/ci.yml#L28-L31).

---

## 6. Every file and every function

Files are explained in **dependency order**: a file appears only after every project file it imports. So when you reach the agents, you already know the LLM, retriever and JSON parser they use.

### 6.1 Settings: app/config.py

Everything configurable lives in one class. That way no other file reads environment variables directly.

**`class Settings(BaseSettings)`** [app/config.py:20-86](app/config.py#L20-L86). Each class attribute is a setting with a type and a default:

```python
LLM_PROVIDER: str = "ollama"
LLM_FALLBACK_PROVIDER: str = ""
EMBEDDINGS_PROVIDER: str = "ollama"
...
API_KEY: str = "dev-api-key-change-in-production"
AUTH_ENABLED: bool = True
```

When you create `Settings()`, pydantic-settings looks for each name first in the real environment variables, then in the `.env` file, then falls back to the default. It also converts types: the text `"false"` in `.env` becomes the boolean `False`. The provider switches are at [app/config.py:34-40](app/config.py#L34-L40). The block at [app/config.py:82-86](app/config.py#L82-L86) tells it which file to read, and `extra="ignore"` means unknown variables in `.env` (like `API_URL`, which only the UI uses) don't cause an error.

**`get_settings()`** [app/config.py:89-104](app/config.py#L89-L104). Returns `Settings()`, cached with `@lru_cache`, so the `.env` file is read once per process. Every other file calls `get_settings()` instead of creating its own `Settings`.

*Why a function and not a global variable?* Tests can create a fresh `Settings()` with different values (as [tests/test_config.py:9](tests/test_config.py#L9) does), and FastAPI can use such functions as dependencies.

### 6.2 Logging set-up: app/observability/logger.py

Imports: `app.config`.

**`setup_logging()`** [app/observability/logger.py:20-62](app/observability/logger.py#L20-L62). Called once when the API starts. It:

1. Creates a `logs/` folder and a log file named by date, e.g. `logs/app_20261028.log` ([lines 29-33](app/observability/logger.py#L29-L33)).
2. Configures Python's built-in `logging` to write to both the screen and that file, at the level from `LOG_LEVEL` ([lines 36-43](app/observability/logger.py#L36-L43)). `getattr(logging, "INFO")` turns the text `"INFO"` into the constant `logging.INFO`.
3. Configures structlog with a list of *processors* ([lines 46-62](app/observability/logger.py#L46-L62)). Each processor adds or transforms something: the logger name, the level, an ISO timestamp, exception text. The last one decides the output format:

```python
structlog.processors.JSONRenderer() if not settings.DEBUG else structlog.dev.ConsoleRenderer(),
```

So in production you get one JSON object per line; with `DEBUG=true` you get coloured, human-friendly lines.

**`get_logger(name)`** [app/observability/logger.py:65-75](app/observability/logger.py#L65-L75). A thin wrapper around `structlog.get_logger`. Only `main.py` and `middleware.py` use it; other files call `structlog.get_logger()` directly. Both give the same kind of logger.

**`class LogContext`** [app/observability/logger.py:78-96](app/observability/logger.py#L78-L96). A context manager meant to attach extra fields (like `request_id`) to every log line inside a `with` block. It is never used, and would not work as configured: see [section 8](#8-things-to-notice).

### 6.3 Request logging: app/observability/middleware.py

Imports: `app.observability.logger`.

*Middleware* is code that wraps **every** request: it runs before your route function and after it, like a security guard who notes when each visitor comes in and leaves.

**`class RequestLoggingMiddleware(BaseHTTPMiddleware)`** [app/observability/middleware.py:15-73](app/observability/middleware.py#L15-L73). Its only method:

**`dispatch(request, call_next)`** [app/observability/middleware.py:25-73](app/observability/middleware.py#L25-L73).

```python
request_id = str(uuid.uuid4())[:8]          # short random ID, e.g. "3f9a1c2b"
start_time = time.time()
...
response = await call_next(request)         # run the actual route
duration_ms = (time.time() - start_time) * 1000
...
response.headers["X-Request-ID"] = request_id
```

`call_next` is "the rest of the app". Everything before it happens on the way in, everything after on the way out. The ID is sent back in a response header, so if a user reports a problem you can find their exact request in the logs. If the route raises an exception, it is logged with its duration and re-raised ([lines 63-73](app/observability/middleware.py#L63-L73)).

### 6.4 Execution traces: app/observability/tracer.py

Imports: no project files.

A *trace* is a record of what happened during one analysis: which steps ran, how long each took, whether each succeeded. This file defines the data structures and an in-memory store for them.

**`TraceStep`** [app/observability/tracer.py:15-27](app/observability/tracer.py#L15-L27). A dataclass for one step: node name, timestamp, latency, model, and optional summaries.

**`ExecutionTrace`** [app/observability/tracer.py:30-56](app/observability/tracer.py#L30-L56). A dataclass for one whole run, holding a list of steps. Its methods:
- **`add_step`** [lines 43-45](app/observability/tracer.py#L43-L45): appends a step and adds its latency to the total.
- **`complete`** [lines 47-50](app/observability/tracer.py#L47-L50): stamps the end time and success flag.
- **`to_dict` / `to_json`** [lines 52-56](app/observability/tracer.py#L52-L56): `asdict` converts the dataclass (and its nested steps) to plain dicts; `default=str` tells `json.dumps` to turn anything it can't handle into a string.

**`ExecutionTracer`** [app/observability/tracer.py:59-161](app/observability/tracer.py#L59-L161). Keeps traces in a dict keyed by `trace_id`.
- **`__init__`** [lines 62-65](app/observability/tracer.py#L62-L65): creates `logs/traces/` for saving.
- **`start_trace`** [lines 67-79](app/observability/tracer.py#L67-L79): the ID is the current UTC time down to microseconds, e.g. `20261028_101500_123456`.
- **`trace_step`** [lines 81-112](app/observability/tracer.py#L81-L112): records one step (summaries are cut to 100 characters).
- **`complete_trace`** [lines 114-130](app/observability/tracer.py#L114-L130), **`save_trace`** [lines 132-140](app/observability/tracer.py#L132-L140), **`get_trace`** [lines 142-143](app/observability/tracer.py#L142-L143), **`list_traces`** [lines 145-161](app/observability/tracer.py#L145-L161): finish, save to a JSON file, fetch one, and list the newest few.

**`get_tracer()`** [app/observability/tracer.py:168-173](app/observability/tracer.py#L168-L173). Returns the one shared tracer, creating it on first use.

> Important: nothing in the workflow ever calls `start_trace` or `trace_step`. The agents keep their own simpler trace list in the state instead. So the `/traces` endpoints always return an empty list. This is a good example of "infrastructure built, never wired in". See [section 8](#8-things-to-notice) and [exercise 8](#9-exercises).

### 6.5 Authentication: app/auth/api_key.py and app/auth/\_\_init\_\_.py

Imports: `app.config`.

The protected endpoints require a secret key in an HTTP header called `X-API-Key`. Think of it as a password the client sends with every request.

**The header scheme** [app/auth/api_key.py:27-31](app/auth/api_key.py#L27-L31):

```python
APIKeyHeader = APIKeyHeader(
    name=get_settings().API_KEY_HEADER,
    auto_error=False,
    ...
)
```

`fastapi.security.APIKeyHeader` is a class that knows how to read a named header. Here an *instance* is created and stored in a variable with **the same name as the class**, which hides the class from then on. It works, but it is confusing; see [section 8](#8-things-to-notice). `auto_error=False` means "if the header is missing, give me `None` instead of failing", so the code can return its own clearer error. Note that `get_settings()` is called at import time here, so the header name is fixed when the module loads.

**`verify_api_key(api_key)`** [app/auth/api_key.py:34-50](app/auth/api_key.py#L34-L50). Compares the given key with `settings.API_KEY`:

```python
return secrets.compare_digest(api_key, expected_key)
```

*Why not `==`?* A normal string comparison stops at the first different character, so a wrong key that starts correctly takes a tiny bit longer to reject. An attacker measuring response times could guess the key one character at a time (a *timing attack*). `compare_digest` always takes the same time.

**`get_api_key(api_key_header)`** [app/auth/api_key.py:53-99](app/auth/api_key.py#L53-L99). This is a FastAPI **dependency**: a function FastAPI runs *before* the route, whose result (or exception) decides whether the route runs at all. `Security(APIKeyHeader)` tells FastAPI to fill the parameter from the header. Three outcomes:

- `AUTH_ENABLED` is false → allow, return `"auth-disabled"` ([lines 77-79](app/auth/api_key.py#L77-L79)).
- no header → **401 Unauthorized** ([lines 82-88](app/auth/api_key.py#L82-L88)).
- wrong key → **403 Forbidden** ([lines 91-96](app/auth/api_key.py#L91-L96)).

401 means "you didn't say who you are"; 403 means "I know what you sent, and it's not allowed".

**`generate_api_key(length)`** [app/auth/api_key.py:102-116](app/auth/api_key.py#L102-L116). Makes a random key with `secrets.token_hex`. Not called by the app; it's a helper you could run once to create a good `API_KEY`.

**[app/auth/\_\_init\_\_.py:1-5](app/auth/__init__.py#L1-L5)** re-exports these names, so routes can write `from app.auth import get_api_key` instead of the longer path.

### 6.6 Embeddings: app/core/embeddings.py

Imports: `app.config`.

An **embedding** turns text into a list of numbers (a *vector*) so that texts with similar meaning get similar numbers. "Refund" and "money back" end up close together; "refund" and "firewall" end up far apart. This is what makes semantic search possible.

**`get_embeddings()`** [app/core/embeddings.py:24-68](app/core/embeddings.py#L24-L68). Cached with `@lru_cache` because loading a model is slow. It reads `EMBEDDINGS_PROVIDER` and returns one of two LangChain embedding objects:

```python
if provider == "fastembed":
    from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
    return FastEmbedEmbeddings(model_name=settings.FASTEMBED_MODEL)

if provider == "ollama":
    from langchain_ollama import OllamaEmbeddings
    return OllamaEmbeddings(model=settings.OLLAMA_EMBED_MODEL, base_url=settings.OLLAMA_BASE_URL)
```

Both have the same methods (`embed_query`, `embed_documents`), so the rest of the code doesn't care which one it gets. That is the point of the shared `Embeddings` base class in the return type. Any other value raises a `ValueError` ([lines 66-68](app/core/embeddings.py#L66-L68)).

**`check_embeddings_connection()`** [app/core/embeddings.py:71-89](app/core/embeddings.py#L71-L89). Embeds the word "test" and returns `True` if that worked. Used by the `/health` endpoint.

### 6.7 The LLM: app/core/llm.py

Imports: `app.config`.

**`_build_llm(provider)`** [app/core/llm.py:32-82](app/core/llm.py#L32-L82). The leading underscore means "private to this file". It builds one LangChain chat model for one provider:

- **groq** [lines 37-50](app/core/llm.py#L37-L50): refuses to start without `GROQ_API_KEY`, sets `max_retries=1` and a 30-second timeout.
- **gemini** [lines 52-65](app/core/llm.py#L52-L65): same idea with `GEMINI_API_KEY`.
- **ollama** [lines 67-80](app/core/llm.py#L67-L80): no key; just the local server address.

All use `temperature=settings.LLM_TEMPERATURE` (0.1). *Temperature* controls randomness: 0 gives the most likely words every time, 1 is more creative. For analysis you want consistent, repeatable answers, so it is kept low.

**`get_llm()`** [app/core/llm.py:85-116](app/core/llm.py#L85-L116). Cached. Builds the primary model, then adds a fallback if one is configured and different from the primary:

```python
primary = _build_llm(settings.LLM_PROVIDER)
...
fallback = _build_llm(fallback_provider)
...
return primary.with_fallbacks([fallback])
```

`with_fallbacks` returns a wrapper that tries `primary` first; if it raises an exception (for example Groq says "rate limit exceeded"), it automatically retries the same input on `fallback`. *Why?* Free tiers have strict limits, and a live demo should not fail just because one provider is busy. If the fallback can't be built (no key), it logs a warning and uses the primary alone ([lines 110-114](app/core/llm.py#L110-L114)).

**`check_llm_connection()`** [app/core/llm.py:119-136](app/core/llm.py#L119-L136). Asks the model to "Say 'ok'". Used by `/health`. Note that this is a **real, paid-for-or-rate-limited LLM call every time `/health` is hit**; see [section 8](#8-things-to-notice).

### 6.8 The vector store: app/core/vectorstore.py

Imports: `app.config`, `app.core.embeddings`.

**`get_chroma_client()`** [app/core/vectorstore.py:29-63](app/core/vectorstore.py#L29-L63). Makes sure the storage folder exists, then opens the Chroma collection:

```python
return Chroma(
    collection_name=settings.CHROMA_COLLECTION_NAME,
    embedding_function=get_embeddings(),
    persist_directory=str(persist_dir),
)
```

Passing the embedding function means Chroma will embed texts automatically when you add or search. This function is **not** cached (the docstring explains why), so every call opens the store again. It is called several times per analysis.

**`get_retriever(k)`** [app/core/vectorstore.py:66-91](app/core/vectorstore.py#L66-L91). Returns a plain vector-only retriever. Not used by the app; the workflow uses the hybrid retriever in `app/rag/retriever.py`, which has a function with the **same name**. Easy to mix up.

**`add_documents_to_store`** [app/core/vectorstore.py:94-121](app/core/vectorstore.py#L94-L121) and **`search_documents`** [app/core/vectorstore.py:124-154](app/core/vectorstore.py#L124-L154). Helpers to add raw strings and to search with scores. Only used by the commented-out code in `test_setup.py`.

**`get_collection_stats()`** [app/core/vectorstore.py:157-170](app/core/vectorstore.py#L157-L170). Returns the collection's name and how many chunks it holds. It reaches into `vectorstore._collection`, the underlying ChromaDB object. The underscore means LangChain considers it private, so this could break in a future LangChain version. Used by `/health`, `/documents/stats` and startup seeding.

### 6.9 Ingestion: loader, chunker, processor

*Ingestion* is how documents get into the vector store. It's a small pipeline: **load** the file into text, **chunk** the text, **store** the chunks.

#### app/ingestion/loader.py

Imports: no project files. Every loader returns a list of LangChain `Document` objects. A `Document` is just `page_content` (the text) plus `metadata` (a dict of extra facts like the file name).

- **`load_text_file`** [app/ingestion/loader.py:25-53](app/ingestion/loader.py#L25-L53): reads a `.txt`/`.md` file into one Document. Metadata: `source` (file name), `file_path`, `file_type`.
- **`load_pdf_file`** [app/ingestion/loader.py:56-92](app/ingestion/loader.py#L56-L92): one Document **per page**, skipping empty pages, with a `page` number in the metadata. Why per page? So a search result can say which page it came from.
- **`load_docx_file`** [app/ingestion/loader.py:95-128](app/ingestion/loader.py#L95-L128): joins all non-empty paragraphs into one Document. Tables in Word files are not read.
- **`load_document`** [app/ingestion/loader.py:131-160](app/ingestion/loader.py#L131-L160): picks a loader by file extension using a dictionary of functions:

```python
loaders = {
    ".txt": load_text_file,
    ".md": load_text_file,
    ".pdf": load_pdf_file,
    ".docx": load_docx_file,
}
...
return loaders[suffix](file_path)
```

This "dictionary of functions" pattern replaces a long `if/elif` chain and makes adding a format a one-line change.

#### app/ingestion/chunker.py

Imports: no project files.

*Why chunk?* An LLM can only read a limited amount of text, and a search that returns a whole 50-page PDF is useless. Small pieces let retrieval return just the relevant paragraph.

- **`create_text_splitter`** [app/ingestion/chunker.py:19-31](app/ingestion/chunker.py#L19-L31): makes a `RecursiveCharacterTextSplitter` with 1,000-character chunks and a 200-character overlap. It tries to split at paragraph breaks first (`"\n\n"`), then lines, then sentences (`". "`), then words. The **overlap** repeats the end of one chunk at the start of the next, so a sentence that sits on a boundary is not lost.
- **`chunk_documents`** [app/ingestion/chunker.py:34-56](app/ingestion/chunker.py#L34-L56): splits all documents and numbers each chunk with `chunk_index` in its metadata ([lines 47-48](app/ingestion/chunker.py#L47-L48)). The chunks keep their parent's metadata (source, page, …).

#### app/ingestion/processor.py

Imports: `app.ingestion.loader`, `app.ingestion.chunker`, `app.core.vectorstore`.

**`process_document(file_path, metadata, ...)`** [app/ingestion/processor.py:19-59](app/ingestion/processor.py#L19-L59). The four steps are labelled in comments: load, add your custom metadata plus a `processed_at` timestamp, chunk, then:

```python
vectorstore = get_chroma_client()
texts = [chunk.page_content for chunk in chunks]
metadatas = [chunk.metadata for chunk in chunks]
vectorstore.add_texts(texts=texts, metadatas=metadatas)
```

`add_texts` embeds each text and saves it. It returns the number of chunks. Note: uploading the same file twice stores its chunks twice; nothing checks for duplicates.

**`process_directory(directory_path, metadata, extensions)`** [app/ingestion/processor.py:62-91](app/ingestion/processor.py#L62-L91). Runs `process_document` on every matching file in a folder. One bad file is logged and skipped rather than stopping the loop ([lines 79-83](app/ingestion/processor.py#L79-L83)). Used by startup seeding.

### 6.10 Hybrid retrieval: app/rag/retriever.py

Imports: `app.config`, `app.core.vectorstore`.

This is the "R" in RAG. Given the change request, it returns the most relevant chunks.

**`class HybridRetriever`** [app/rag/retriever.py:21-179](app/rag/retriever.py#L21-L179).

- **`__init__`** [lines 30-43](app/rag/retriever.py#L30-L43): stores `k` (how many results) and two weights, `vector_weight=0.6` and `bm25_weight=0.4`. Those weights are **never used** anywhere; the merge below ignores them.
- **`_initialize`** [lines 45-77](app/rag/retriever.py#L45-L77): BM25 needs all the texts in memory to compute word statistics, so this reads **every chunk** out of Chroma and builds a `BM25Retriever` from them. The `_initialized` flag makes it run only once per retriever object.

```python
results = collection.get(include=["documents", "metadatas"])
...
self._bm25_retriever = BM25Retriever.from_documents(self._documents, k=self.k)
```

- **`_merge_results`** [lines 79-112](app/rag/retriever.py#L79-L112): combines the two result lists by **taking turns**: 1st vector result, 1st BM25 result, 2nd vector, 2nd BM25, and so on, skipping any text already seen. Each kept document gets `retrieval_method` = `"vector"` or `"bm25"` in its metadata. Simple and fair, but it's not a weighted score.
- **`retrieve`** [lines 114-147](app/rag/retriever.py#L114-L147): the main method. Initialise, run a vector search and a BM25 search, merge, and keep the first `k`.
- **`retrieve_with_scores`** [lines 149-157](app/rag/retriever.py#L149-L157): vector search with similarity scores. Unused.
- **`add_retrieval_explanation`** [lines 159-179](app/rag/retriever.py#L159-L179): for each result, lists which query words (longer than 2 letters) appear in the text, plus the method. This makes results easier to debug: you can see *why* a chunk was picked.

**`get_retriever(k)`** [app/rag/retriever.py:182-185](app/rag/retriever.py#L182-L185). Creates a **new** `HybridRetriever`. Because the workflow calls this on every analysis, the BM25 index is rebuilt from all chunks on every request. Fine for one small policy file, slow for thousands of chunks.

### 6.11 Prompts: app/prompts/\_\_init\_\_.py and the prompts/ folder

Imports: no project files.

A *prompt* is the instruction text sent to the LLM. Keeping prompts in `.txt` files means you can improve the wording without touching Python.

**`PROMPTS_DIR`** [app/prompts/\_\_init\_\_.py:14](app/prompts/__init__.py#L14) is `app/prompts/` → up two levels → `prompts/`, i.e. the top-level [prompts](prompts/technical.txt) folder. `Path(__file__)` is "the path of this very file", which makes the location independent of where you start Python from.

**`load_prompt(name, fallback)`** [app/prompts/\_\_init\_\_.py:17-50](app/prompts/__init__.py#L17-L50). Reads `prompts/<name>.txt`, cached for up to 32 different names. If the file is missing it returns `fallback`, or raises `FileNotFoundError` if there is none.

**`reload_prompts()`** [app/prompts/\_\_init\_\_.py:53-56](app/prompts/__init__.py#L53-L56). Clears the cache so edited files are read again. Never called.

**Module-level exports** [app/prompts/\_\_init\_\_.py:60-63](app/prompts/__init__.py#L60-L63) load all four prompts at import time. The agents don't use these names; each agent calls `load_prompt` again itself (which hits the cache).

**The prompt files.** Open [prompts/technical.txt](prompts/technical.txt). Each prompt has the same structure: a role ("You are a Technical Impact Analyst"), the change request, the retrieved documentation, a numbered list of questions, and the **exact JSON shape** to answer in:

```text
## Change Request
{change_request}

## Relevant Documentation
{context}
...
{{
    "affected_systems": ["system1", "system2"],
```

`{change_request}` and `{context}` are placeholders that LangChain fills in. The **double** braces `{{ }}` are *escaped* braces: they come out as single `{ }` in the final text. Without doubling, LangChain would think `{ "affected_systems": ...}` is a placeholder too. The synthesizer prompt [prompts/synthesizer.txt:3-13](prompts/synthesizer.txt#L3-L13) has different placeholders: the three earlier analyses instead of the documentation.

*Why ask for JSON?* So the program can read fields like `overall_risk_level` directly instead of guessing from free text.

### 6.12 Parsing the LLM's JSON: app/utils/json_parser.py

Imports: no project files.

LLMs are told "respond ONLY with valid JSON", but they often don't quite manage it: they wrap it in Markdown fences, add a sentence before it, leave a trailing comma, or forget a comma. `json.loads` fails on all of those. This file tries progressively more aggressive repairs.

**`parse_json_safely(text, default)`** [app/utils/json_parser.py:113-172](app/utils/json_parser.py#L113-L172) is the entry point. It tries five strategies in order and returns the first one that works:

1. Plain `json.loads(text)` ([lines 132-135](app/utils/json_parser.py#L132-L135)).
2. Cut out the first `{...}` block and parse that ([lines 138-142](app/utils/json_parser.py#L138-L142)).
3. Repair common mistakes, then parse ([lines 145-149](app/utils/json_parser.py#L145-L149)).
4. Treat it as a Python dict literal with `ast.literal_eval`, after swapping `true/false/null` for `True/False/None` ([lines 152-160](app/utils/json_parser.py#L152-L160)). This catches single-quoted keys.
5. Pull out whatever `"key": value` pairs a regex can find ([lines 163-169](app/utils/json_parser.py#L163-L169)).

If all fail, it returns the `default` dict plus `parse_error: True` and the first 500 characters of the raw text ([line 172](app/utils/json_parser.py#L172)). The `parse_error` flag matters later: the synthesizer lowers its confidence score when it sees it.

**`extract_json_from_text`** [app/utils/json_parser.py:21-53](app/utils/json_parser.py#L21-L53). Removes ```` ```json ```` fences, then walks the text counting braces: `{` adds one, `}` subtracts one, and when the count returns to zero the outermost object is complete.

**`fix_json_string`** [app/utils/json_parser.py:56-110](app/utils/json_parser.py#L56-L110). A list of regex repairs: removes `//` and `/* */` comments, trailing commas, adds missing commas between lines, converts `'key':` to `"key":`, and tries to join strings that were broken across lines. These are heuristics: they help in common cases and can occasionally damage valid text (for example, the comment-removal regex would also cut a URL like `https://...` inside a string). That is why it is strategy 3, not strategy 1.

**`extract_key_values`** [app/utils/json_parser.py:175-206](app/utils/json_parser.py#L175-L206). The last resort: separate regexes for string, boolean, number and simple-list values. Nested objects are lost.

### 6.13 The shared state: app/workflow/state.py

Imports: no project files.

**`class AnalysisState(TypedDict, total=False)`** [app/workflow/state.py:18-48](app/workflow/state.py#L18-L48). This is the "clipboard" passed from agent to agent. It lists every key any agent may read or write, grouped by stage: input, retrieval, analysis outputs, final output, metadata, timestamps.

```python
change_request: str
retrieved_docs: List[dict]
technical_analysis: Optional[dict]
...
final_assessment: Optional[dict]
execution_trace: List[dict]
```

*Why a TypedDict and not a class?* LangGraph passes state around as a plain dict, and a TypedDict *is* a plain dict at runtime; it only adds type information for readers and tools. `recommendations`, `confidence_score` and `errors` are declared too. `errors` is initialised to an empty list but no agent ever appends to it.

### 6.14 The agents (nodes)

All five agents follow the same pattern, so read the technical one carefully and the rest will be quick. A LangGraph *node* is just a function that takes the state dict and returns a new state dict.

#### app/workflow/nodes/retriever.py

Imports: `app.workflow.state`, `app.rag.retriever`.

**`retrieve_documents(state)`** [app/workflow/nodes/retriever.py:18-73](app/workflow/nodes/retriever.py#L18-L73).

```python
retriever = get_retriever(k=5)
docs = retriever.retrieve(change_request)
docs = retriever.add_retrieval_explanation(docs, change_request)

retrieved_docs = [
    {"content": doc.page_content, "metadata": doc.metadata}
    for doc in docs
]
```

It converts LangChain `Document` objects into plain dicts ([lines 42-48](app/workflow/nodes/retriever.py#L42-L48)). *Why?* Plain dicts can be turned into JSON and sent back to the UI; `Document` objects can't directly. It times itself and appends a step to `execution_trace` ([lines 54-60](app/workflow/nodes/retriever.py#L54-L60)), then returns the state with three keys updated. Note the hard-coded `k=5`, which ignores the `RETRIEVAL_TOP_K` setting.

#### app/workflow/nodes/technical.py

Imports: `app.workflow.state`, `app.core.llm`, `app.prompts`, `app.utils.json_parser`.

**`TechnicalImpact`** and **`TechnicalAnalysisOutput`** [app/workflow/nodes/technical.py:29-43](app/workflow/nodes/technical.py#L29-L43). Pydantic models describing the expected answer. They are **not used**: the code parses with `parse_json_safely` instead, and `JsonOutputParser` is imported on [line 16](app/workflow/nodes/technical.py#L16) but never used either. They are leftovers from an earlier approach and serve as documentation only.

**`TECHNICAL_PROMPT = load_prompt("technical")`** [line 48](app/workflow/nodes/technical.py#L48). Read once when the module is imported.

**`analyze_technical_impact(state)`** [app/workflow/nodes/technical.py:51-135](app/workflow/nodes/technical.py#L51-L135). Step by step:

1. **Build the context** from the retrieved chunks, each prefixed by its source file and separated by `---` ([lines 71-74](app/workflow/nodes/technical.py#L71-L74)). If nothing was retrieved, the context says so, so the LLM knows it is working without company documents.
2. **Build the chain** ([lines 77-81](app/workflow/nodes/technical.py#L77-L81)):

```python
prompt = ChatPromptTemplate.from_template(TECHNICAL_PROMPT)
llm = get_llm()
chain = prompt | llm
```

3. **Call the LLM** ([lines 85-88](app/workflow/nodes/technical.py#L85-L88)). `chain.invoke({...})` fills `{change_request}` and `{context}`, sends the text, and waits for the reply. This is the slow part: seconds, not milliseconds.
4. **Parse** ([lines 91-100](app/workflow/nodes/technical.py#L91-L100)). Chat models return a message object with `.content`; the `hasattr` check is a safety net in case a plain string comes back. A `default_result` with sensible empty values is passed to the parser.
5. **Handle failure** ([lines 102-111](app/workflow/nodes/technical.py#L102-L111)). If the LLM call itself throws (network down, bad key), the agent does **not** crash the whole workflow. It returns a result with `"error": True` and the message in the summary. This "fail soft" design means one broken agent still lets you see the other three.
6. **Record the step** ([lines 117-123](app/workflow/nodes/technical.py#L117-L123)) and return the state with `technical_analysis` set.

Note `"model": "llama3"` on [line 122](app/workflow/nodes/technical.py#L122) is hard-coded, even when Groq or Gemini is used.

#### app/workflow/nodes/operational.py

Imports: same as technical.

**`analyze_operational_impact(state)`** [app/workflow/nodes/operational.py:27-106](app/workflow/nodes/operational.py#L27-L106). Identical structure to the technical agent, with the operational prompt ([line 24](app/workflow/nodes/operational.py#L24)) and its own default fields: `affected_workflows`, `teams_impacted`, `training_required`, `disruption_level`, … ([lines 58-67](app/workflow/nodes/operational.py#L58-L67)).

#### app/workflow/nodes/risk.py

Imports: same as technical.

**`assess_risks(state)`** [app/workflow/nodes/risk.py:27-102](app/workflow/nodes/risk.py#L27-L102). Same structure again; defaults include `risks`, `overall_risk_level`, `compliance_concerns`, `rollback_complexity` ([lines 58-65](app/workflow/nodes/risk.py#L58-L65)).

The three files are about 90% the same code. That repetition is a refactoring opportunity: one helper function `run_agent(state, prompt_name, defaults, result_key)` could replace most of it ([exercise 6](#9-exercises)).

#### app/workflow/nodes/synthesizer.py

Imports: same as technical.

**`calculate_confidence(state)`** [app/workflow/nodes/synthesizer.py:28-63](app/workflow/nodes/synthesizer.py#L28-L63). A simple rule-based score that doesn't use the LLM. Start at 1.0 and subtract penalties: 0.3 for no documents, 0.1 for fewer than 3, 0.2 for each analysis that errored or failed to parse, 0.1 if the technical agent found no systems. The result is clamped between 0.1 and 1.0:

```python
return max(0.1, min(1.0, score))
```

*Why have this at all?* An LLM's own "confidence: 0.85" is just more generated text. A score computed from facts (did we have context? did parsing work?) is a useful sanity check.

**`synthesize_results(state)`** [app/workflow/nodes/synthesizer.py:66-163](app/workflow/nodes/synthesizer.py#L66-L163). Different input from the other agents: instead of documents it sends the **three previous analyses**, converted to pretty JSON text ([lines 80-82](app/workflow/nodes/synthesizer.py#L80-L82)), into the synthesizer prompt. Then:

- It parses the answer the same way (with a default recommendation of `"reconsider"`).
- It adds `calculated_confidence` from the function above ([lines 130-131](app/workflow/nodes/synthesizer.py#L130-L131)).
- It builds a flat `recommendations` list from the action objects ([lines 146-148](app/workflow/nodes/synthesizer.py#L146-L148)).
- It sets the state's `confidence_score` to the **LLM's** number if present, otherwise the calculated one ([line 161](app/workflow/nodes/synthesizer.py#L161)).

Watch [line 148](app/workflow/nodes/synthesizer.py#L148): `action.get("action", "")` assumes every action is a dict. If the LLM returns a list of plain strings, this raises `AttributeError`, and because it is *outside* the `try` block, the whole analysis fails with a 500 error. See [section 8](#8-things-to-notice).

### 6.15 Wiring the agents: app/workflow/graph.py

Imports: `app.workflow.state` and all five nodes.

Lines [1-97](app/workflow/graph.py#L1-L97) are an **older version of this file, commented out**, followed by a stray note on [line 100](app/workflow/graph.py#L100). The live code starts at [line 102](app/workflow/graph.py#L102). Comparing the two is instructive: the old version only had `retrieve → technical`; the new one adds three more agents.

**`create_analysis_workflow()`** [app/workflow/graph.py:123-156](app/workflow/graph.py#L123-L156).

```python
workflow = StateGraph(AnalysisState)
workflow.add_node("retrieve", retrieve_documents)
workflow.add_node("technical", analyze_technical_impact)
...
workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "technical")
workflow.add_edge("technical", "operational")
workflow.add_edge("operational", "risk")
workflow.add_edge("risk", "synthesize")
workflow.add_edge("synthesize", END)
graph = workflow.compile()
```

`add_node` gives each function a name; `add_edge(a, b)` means "after a, run b"; `END` is LangGraph's special finish marker; `compile()` checks the graph and returns something you can `.invoke()`. The docstring at the top of this live section ([lines 102-107](app/workflow/graph.py#L102-L107)) still says "parallel", but the edges form a straight line, as the function's own docstring admits ([lines 127-131](app/workflow/graph.py#L127-L131)).

**`run_analysis(change_request)`** [app/workflow/graph.py:159-182](app/workflow/graph.py#L159-L182). The single public entry point to the AI part:

```python
initial_state: AnalysisState = {
    "change_request": change_request,
    "retrieved_docs": [],
    "execution_trace": [],
    "errors": [],
    "started_at": datetime.utcnow().isoformat(),
}
workflow = create_analysis_workflow()
result = workflow.invoke(initial_state)
result["completed_at"] = datetime.utcnow().isoformat()
```

It rebuilds the graph on every call (cheap, but could be cached) and adds start/end timestamps.

### 6.16 The API routes

Each file creates an `APIRouter`: a group of related endpoints with a shared URL prefix. `main.py` later plugs them all into the app.

#### app/api/routes/health.py

Imports: `app.core.llm`, `app.core.embeddings`, `app.core.vectorstore`. No authentication: monitoring tools need to call these freely.

- **`HealthStatus`** [app/api/routes/health.py:15-20](app/api/routes/health.py#L15-L20): the response shape.
- **`health_check`** `GET /health` [app/api/routes/health.py:23-45](app/api/routes/health.py#L23-L45): tests the LLM, embeddings and vector store for real and reports `"healthy"` or `"degraded"`. The bare `except:` on [line 33](app/api/routes/health.py#L33) catches *everything*, even Ctrl+C; `except Exception:` would be safer.
- **`readiness_check`** `GET /health/ready` [lines 48-51](app/api/routes/health.py#L48-L51) and **`liveness_check`** `GET /health/live` [lines 54-57](app/api/routes/health.py#L54-L57): instant answers that only prove the server is running. Docker and the UI use `/health/live` because it is cheap.

#### app/api/routes/documents.py

Imports: `app.ingestion.processor`, `app.core.vectorstore`, `app.auth`.

The router passes `dependencies=[Depends(get_api_key)]` ([lines 13-17](app/api/routes/documents.py#L13-L17)), so **every** endpoint in this file requires the API key without repeating it on each function.

- **`upload_document`** `POST /documents/upload` [app/api/routes/documents.py:32-70](app/api/routes/documents.py#L32-L70): checks the file extension, saves the upload to `data/documents/<filename>` ([lines 49-53](app/api/routes/documents.py#L49-L53)), runs `process_document` with department/doc_type/criticality metadata from the form, and returns how many chunks were created. The filename is used exactly as the client sent it; see [section 8](#8-things-to-notice).
- **`get_stats`** `GET /documents/stats` [lines 73-83](app/api/routes/documents.py#L73-L83): chunk count.
- **`clear_documents`** `DELETE /documents/clear` [lines 86-99](app/api/routes/documents.py#L86-L99): deletes every chunk by ID. The files in `data/documents/` stay on disk.

#### app/api/routes/analysis.py

Imports: `app.workflow.graph`, `app.auth`. Also protected by the API key for every route.

- **`AnalysisRequest`** [app/api/routes/analysis.py:22-30](app/api/routes/analysis.py#L22-L30): the request body must have `change_request` of at least 10 characters. FastAPI rejects shorter ones with a **422** error before your code runs.
- **`ExecutionStep`** [lines 33-36](app/api/routes/analysis.py#L33-L36) and **`AnalysisResponse`** [lines 39-49](app/api/routes/analysis.py#L39-L49): the response shape. Using `response_model=AnalysisResponse` means FastAPI validates and documents the output too. Extra keys in each trace step (like `model`) are dropped because `ExecutionStep` doesn't declare them.
- **`analyze_change`** `POST /analysis/run` [lines 52-89](app/api/routes/analysis.py#L52-L89): calls `run_analysis`, computes the total time from the two timestamps, converts the trace, and builds the response. Any exception becomes a **500** error with the message.

Note that `analyze_change` is `async def` but calls `run_analysis`, which is slow and **not** async. While it runs (often a minute), this blocks the server's event loop, so other requests to the same server wait. Defining it with plain `def` would let FastAPI run it in a background thread instead.

#### app/api/routes/traces.py

Imports: `app.observability.tracer`, `app.auth`.

- **`list_traces`** `GET /traces` [app/api/routes/traces.py:18-24](app/api/routes/traces.py#L18-L24) and **`get_trace`** `GET /traces/{trace_id}` [lines 27-38](app/api/routes/traces.py#L27-L38). `{trace_id}` in the path becomes the function parameter. As explained in 6.4, nothing fills the tracer, so these return an empty list and 404 respectively.

### 6.17 The application: app/main.py

Imports: all four routers, `app.config`, `app.observability.logger`, `app.observability.middleware`.

This is the file Uvicorn loads. Reading it top to bottom is reading the start-up sequence:

1. **Logging first** [app/main.py:17-18](app/main.py#L17-L18), so everything after can log.
2. **Create the app** [lines 21-27](app/main.py#L21-L27) with a title and docs URLs.
3. **Middleware** [lines 30-39](app/main.py#L30-L39): the request logger and CORS. *CORS* (cross-origin resource sharing) is a browser rule: JavaScript on website A may only call API B if B says so. `allow_origins=["*"]` allows any website. (The Streamlit UI calls the API from Python, not from browser JavaScript, so it doesn't actually need CORS.) In Starlette the middleware added **last** runs **first**, so CORS wraps the request logger.
4. **Routers** [lines 42-45](app/main.py#L42-L45).
5. **`root`** `GET /` [lines 48-56](app/main.py#L48-L56): a small info message.
6. **`startup_event`** [lines 59-73](app/main.py#L59-L73): runs once when the server starts. Logs the settings, warns if auth is off, and seeds documents if `SEED_SAMPLE_DOCUMENTS` is true.
7. **`seed_sample_documents`** [lines 76-92](app/main.py#L76-L92): if the store is empty, load everything in `data/documents`. *Why "if empty"?* On Hugging Face the disk is wiped on every restart, so the demo would otherwise have no company documents to search; locally, checking first avoids loading the same file twice. The imports are inside the function so they only happen when seeding is on.
8. **`shutdown_event`** [lines 95-98](app/main.py#L95-L98): logs on shutdown.

`@app.on_event` still works but is deprecated in newer FastAPI versions in favour of a "lifespan" function.

### 6.18 Evaluation: app/evaluation and evaluation/

How do you know whether a prompt change made the agents better or worse? You need a fixed set of questions with known good answers. That is what evaluation does.

#### evaluation/test_cases/sample_cases.json

Four cases ([evaluation/test_cases/sample_cases.json](evaluation/test_cases/sample_cases.json)): refund threshold, JWT migration, remote work, data retention. Each has a `change_request` and an `expected` block per agent, for example: the risk answer should mention `"fraud"`, find at least 1 risk, and rate it `"medium"` or `"high"`.

#### app/evaluation/evaluator.py

Imports: `app.workflow.graph`.

- **`EvaluationResult`** [app/evaluation/evaluator.py:20-33](app/evaluation/evaluator.py#L20-L33) and **`EvaluationReport`** [lines 36-50](app/evaluation/evaluator.py#L36-L50): dataclasses for one case and the whole run.
- **`Evaluator.__init__`** / **`_load_test_cases`** [lines 63-74](app/evaluation/evaluator.py#L63-L74): reads the JSON file. The path is relative to wherever you run Python from, so run it from the repo root.
- **`_check_mentions`** [lines 76-80](app/evaluation/evaluator.py#L76-L80): counts how many expected keywords appear (case-insensitive).
- **`_evaluate_technical`** [lines 82-116](app/evaluation/evaluator.py#L82-L116), **`_evaluate_operational`** [lines 118-153](app/evaluation/evaluator.py#L118-L153), **`_evaluate_risk`** [lines 155-190](app/evaluation/evaluator.py#L155-L190), **`_evaluate_synthesis`** [lines 192-216](app/evaluation/evaluator.py#L192-L216): each produces a few sub-scores between 0 and 1 (keywords found, minimum counts, a matching yes/no or level) and averages them. Note that partial credit differs: a wrong `training_required` scores 0.5, a wrong `migration_required` scores 0.
- **`evaluate_case`** [lines 218-291](app/evaluation/evaluator.py#L218-L291): runs the **real** workflow (real LLM calls), scores the four parts, averages them, and passes the case if the average is at least 0.6.
- **`run_evaluation`** [lines 293-330](app/evaluation/evaluator.py#L293-L330) and **`save_report`** [lines 332-341](app/evaluation/evaluator.py#L332-L341): loop over cases and optionally write a JSON report.

This is keyword matching, not true understanding. An answer can mention "fraud" and still be bad. But it is cheap, repeatable, and catches big regressions.

[app/evaluation/\_\_init\_\_.py:1-5](app/evaluation/__init__.py#L1-L5) re-exports the three classes.

#### evaluation/run_evaluation.py

**`main()`** [evaluation/run_evaluation.py:16-65](evaluation/run_evaluation.py#L16-L65). A command-line script using `argparse`: `--case case_001` runs one case, `--save` writes the report. `sys.path.insert(0, ".")` on [line 11](evaluation/run_evaluation.py#L11) lets it `import app...` when run as `python evaluation/run_evaluation.py` from the repo root.

#### evaluation/evaluator.py

A copy of `app/evaluation/evaluator.py` (identical except for the final newline). Nothing imports it. Safe to delete.

### 6.19 The web UI: streamlit_app/app.py

Imports: no project files (it talks to the API over HTTP, so the UI and API can run on different machines).

Remember: Streamlit re-runs this whole script on every click.

- **Settings** [streamlit_app/app.py:14-15](streamlit_app/app.py#L14-L15): `API_URL` and `API_KEY` come from environment variables with local defaults. The UI does **not** read `.env`; see [section 8](#8-things-to-notice).
- **`get_headers()`** [lines 17-18](streamlit_app/app.py#L17-L18): the auth header dict.
- **Sidebar** [lines 25-37](streamlit_app/app.py#L25-L37): pings `/health/live` with a 2-second timeout and shows "API Connected" or "API Not Available". The heading says "Document Management", but there is no upload widget.
- **Example buttons** [lines 45-57](streamlit_app/app.py#L45-L57): clicking one stores its text in `st.session_state.selected_example`. On the re-run, [line 62](streamlit_app/app.py#L62) reads it back as the text area's default. That's the standard Streamlit trick for "a button fills in a field".
- **Analyze button** [line 70](streamlit_app/app.py#L70): disabled while the text box is empty.
- **The API call** [lines 81-86](streamlit_app/app.py#L81-L86): `requests.post` with the JSON body, the header and a 300-second timeout. `st.stop()` ends the script early on errors.
- **Results** [lines 101-161](streamlit_app/app.py#L101-L161): three `st.metric` boxes (recommendation, impact, effort), the executive summary, then four tabs. The risk tab handles both dict and string risks ([lines 152-156](streamlit_app/app.py#L152-L156)), which is more defensive than the synthesizer agent.
- **Download** [lines 169-174](streamlit_app/app.py#L169-L174): the full result as a JSON file.

### 6.20 Tests: tests/ and test_setup.py

- **[tests/test_config.py:7-28](tests/test_config.py#L7-L28)**: three tests that check default settings. They create `Settings()`, which **also reads your `.env`**; if you set `OLLAMA_MODEL=mistral` there, `test_settings_defaults` fails even though the code is fine.
- **[tests/test_state.py:6-18](tests/test_state.py#L6-L18)**: builds a state dict and checks keys. Because a TypedDict is a plain dict, this test can't really fail; it mainly proves the import works.
- **`tests/test_api/`** and **`tests/test_workflow/`** contain only empty `__init__.py` files.
- **[test_setup.py](test_setup.py)**: a manual script, not a pytest test. Lines [1-176](test_setup.py#L1-L176) are four old scripts commented out (one still calls a function `check_ollama_connection` that no longer exists). Only the last one, [lines 180-226](test_setup.py#L180-L226), is active: it runs a full analysis and prints the result. Because the file name starts with `test_`, running plain `pytest` from the repo root makes pytest import it, which **runs a real analysis at import time**. CI avoids this by running `pytest tests/`.

### 6.21 Running and deploying: Dockerfile, start.sh, docker-compose.yml, workflows

- **[Dockerfile](Dockerfile)**: starts from `python:3.11-slim`, installs `curl` (for health checks), creates user `appuser` with UID 1000 because Hugging Face Spaces requires it ([line 15](Dockerfile#L15)), installs requirements, copies the code, sets the hosted defaults Groq + Gemini fallback + FastEmbed + seeding ([lines 44-47](Dockerfile#L44-L47)), and **downloads the FastEmbed model at build time** ([line 50](Dockerfile#L50)) so the first request isn't slow. `ENV PYTHONPATH=/app` is what lets `import app...` work anywhere in the container.
- **[start.sh](start.sh)**: one container, two programs. It starts Uvicorn in the background ([line 6](start.sh#L6)), waits up to 60 seconds for `/health/live` ([lines 10-15](start.sh#L10-L15)), starts Streamlit on port 7860 ([lines 17-23](start.sh#L17-L23)), then loops; if either program dies, it exits with an error so the platform restarts the container ([lines 27-30](start.sh#L27-L30)).
- **[docker-compose.yml](docker-compose.yml)**: the local, three-container version: `api`, `streamlit` and `ollama`. Services find each other by name (`http://ollama:11434`, `http://api:8000`) on a private network. The UI waits until the API's health check passes ([lines 48-50](docker-compose.yml#L48-L50)). That health check calls the full `/health` ([line 24](docker-compose.yml#L24)), which asks the LLM a question every 30 seconds.
- **[.github/workflows/ci.yml](.github/workflows/ci.yml)**: on every push or pull request: lint with ruff and mypy, run pytest with coverage, build the Docker image. Lint, type check and tests all have `continue-on-error: true` ([lines 31](.github/workflows/ci.yml#L31), [36](.github/workflows/ci.yml#L36), [59](.github/workflows/ci.yml#L59)), so CI shows green even when tests fail.
- **[.github/workflows/deploy-hf.yml](.github/workflows/deploy-hf.yml)**: on push to `main`, force-pushes the repo to the Hugging Face Space ([line 29](.github/workflows/deploy-hf.yml#L29)), which then rebuilds from the Dockerfile. A schedule every 12 hours ([line 9](.github/workflows/deploy-hf.yml#L9)) pings the demo so the free Space doesn't go to sleep.
- **[README.md:1-10](README.md#L1-L10)**: the block between `---` lines is read by Hugging Face to configure the Space (Docker SDK, port 7860).

---

## 7. One request traced from start to finish

Let's follow one click all the way through. You type **"Increase refund approval threshold from $100 to $500"** in the UI and press **Analyze Impact**. Assume the hosted settings (Groq, FastEmbed, sample policy seeded).

**1. The UI sends the request.** Streamlit re-runs the script; `analyze_button` is now `True`, so it posts to the API:
[streamlit_app/app.py:81-86](streamlit_app/app.py#L81-L86)
```python
requests.post(f"{API_URL}/analysis/run", json={"change_request": change_request},
              headers=get_headers(), timeout=300)
```
The body is `{"change_request": "Increase refund approval threshold from $100 to $500"}` and the header is `X-API-Key: <key>`.

**2. Uvicorn receives it** and hands it to the FastAPI `app` from [app/main.py:21](app/main.py#L21).

**3. Middleware runs.** CORS (added last, so outermost) lets it through. Then `RequestLoggingMiddleware.dispatch` gives it an ID, starts a timer, logs "Request started", and calls `call_next`:
[app/observability/middleware.py:27-43](app/observability/middleware.py#L27-L43).

**4. Routing.** FastAPI matches `POST /analysis/run` to `analyze_change` via the router prefix `/analysis` and the decorator `@router.post("/run")`:
[app/api/routes/analysis.py:15-19](app/api/routes/analysis.py#L15-L19), [app/api/routes/analysis.py:52](app/api/routes/analysis.py#L52).

**5. Authentication.** Before the route, FastAPI runs the router's dependency `get_api_key`. It reads the header and compares it with `settings.API_KEY` using `compare_digest`. It matches, so the request continues:
[app/auth/api_key.py:53-99](app/auth/api_key.py#L53-L99).

**6. Validation.** FastAPI builds an `AnalysisRequest` from the JSON. The text is over 10 characters, so it's valid:
[app/api/routes/analysis.py:22-23](app/api/routes/analysis.py#L22-L23).

**7. The workflow starts.** `analyze_change` calls `run_analysis`, which builds the initial state, compiles the graph and invokes it:
[app/api/routes/analysis.py:61](app/api/routes/analysis.py#L61) → [app/workflow/graph.py:159-174](app/workflow/graph.py#L159-L174).

**8. Node "retrieve".** `retrieve_documents` creates a `HybridRetriever(k=5)` and calls `retrieve`:
[app/workflow/nodes/retriever.py:37-39](app/workflow/nodes/retriever.py#L37-L39).
- `_initialize` opens Chroma via `get_chroma_client` (which calls the cached `get_embeddings`, a FastEmbed model), reads all stored chunks (the one small sample policy is a single chunk under 1,000 characters), and builds BM25 over them: [app/rag/retriever.py:45-77](app/rag/retriever.py#L45-L77).
- The vector search embeds the query and finds the nearest chunks; BM25 scores by shared words ("refund" appears several times): [app/rag/retriever.py:125-131](app/rag/retriever.py#L125-L131).
- `_merge_results` interleaves them; the policy chunk is found by both, but kept once: [app/rag/retriever.py:79-112](app/rag/retriever.py#L79-L112).
- Back in the node, chunks become dicts; state now has `retrieved_docs` and one trace step.

**9. Node "technical".** `analyze_technical_impact` turns the retrieved chunk into the `context` text, fills [prompts/technical.txt](prompts/technical.txt), and calls the LLM:
[app/workflow/nodes/technical.py:71-88](app/workflow/nodes/technical.py#L71-L88).
- `get_llm()` returns the cached Groq model wrapped with a Gemini fallback: [app/core/llm.py:103-116](app/core/llm.py#L103-L116). If Groq answers "429 Too Many Requests", the same prompt goes to Gemini automatically.
- The reply text, e.g. ```` ```json {"affected_systems": ["Refund Processing System", ...], ...} ``` ````, fails strategy 1 of `parse_json_safely` because of the fences, and succeeds at strategy 2 after `extract_json_from_text` removes them: [app/utils/json_parser.py:131-142](app/utils/json_parser.py#L131-L142).
- State gains `technical_analysis`.

**10. Nodes "operational" and "risk".** The same pattern twice more, each with its own prompt. State gains `operational_analysis` and `risk_analysis`:
[app/workflow/nodes/operational.py:45-68](app/workflow/nodes/operational.py#L45-L68), [app/workflow/nodes/risk.py:45-66](app/workflow/nodes/risk.py#L45-L66).

**11. Node "synthesize".** The three analyses are dumped as JSON into the synthesizer prompt and sent to the LLM. The parsed answer gets a `calculated_confidence` (1.0 minus 0.1 for having fewer than 3 documents = 0.9, assuming every answer parsed and the technical agent named at least one system):
[app/workflow/nodes/synthesizer.py:80-131](app/workflow/nodes/synthesizer.py#L80-L131).
State gains `final_assessment`, `recommendations` and `confidence_score`. The edge `synthesize → END` finishes the graph.

**12. Back in the route.** `run_analysis` stamps `completed_at`. `analyze_change` computes `total_time_ms`, turns each trace step into an `ExecutionStep`, and returns an `AnalysisResponse`. FastAPI turns it into JSON:
[app/api/routes/analysis.py:63-87](app/api/routes/analysis.py#L63-L87).

**13. Back through middleware.** `dispatch` logs "Request completed" with status 200 and the duration, and adds `X-Request-ID` to the response:
[app/observability/middleware.py:46-61](app/observability/middleware.py#L46-L61).

**14. The UI shows it.** `response.json()` becomes `result`; the script stores it in session state and draws the metrics, the summary and the tabs:
[streamlit_app/app.py:87-161](streamlit_app/app.py#L87-L161).

Total: five network-bound steps (one embedding, four LLM calls) one after the other, which is why the UI warns "This may take 1-2 minutes."

---

## 8. Things to notice

Real issues found while reading the code. Each one is a small lesson.

### Bugs and behaviour that differs from the docs

1. **The agents run in sequence, not in parallel.** The README ([README.md:30](README.md#L30)), its diagram, and the docstring at [app/workflow/graph.py:102-107](app/workflow/graph.py#L102-L107) say parallel. The edges at [app/workflow/graph.py:144-149](app/workflow/graph.py#L144-L149) form a line. Making it parallel is not just adding edges: each node returns `{**state, ...}` (the whole state), and parallel branches writing the same keys (`execution_trace`) at the same time would conflict. See [exercise 7](#9-exercises).

2. **`/traces` always returns nothing.** The tracer in [app/observability/tracer.py](app/observability/tracer.py) is never called by the workflow, so [app/api/routes/traces.py:18-38](app/api/routes/traces.py#L18-L38) list zero traces and 404 for any ID.

3. **The synthesizer can crash the whole request.** [app/workflow/nodes/synthesizer.py:146-148](app/workflow/nodes/synthesizer.py#L146-L148) calls `action.get(...)` on each prioritized action. If the LLM returns `["Update the refund system", ...]` (strings), that raises `AttributeError` outside the `try`, and the user gets a 500 error after waiting a minute.

4. **Local UI and API use different API keys by default.** The API reads `API_KEY=change-me` from `.env` ([.env.example:29](.env.example#L29)). The UI does not read `.env`; started with plain `streamlit run`, it uses its built-in default `dev-api-key-change-in-production` ([streamlit_app/app.py:15](streamlit_app/app.py#L15)). Result: "Analysis failed: Invalid API key" (403). Fix it by exporting `API_KEY` in the terminal before starting Streamlit. Under `docker compose` both read the same `.env`, so it works there.

5. **The trace always says `"model": "llama3"`** ([app/workflow/nodes/technical.py:122](app/workflow/nodes/technical.py#L122), [app/workflow/nodes/operational.py:93](app/workflow/nodes/operational.py#L93), [app/workflow/nodes/risk.py:89](app/workflow/nodes/risk.py#L89), [app/workflow/nodes/synthesizer.py:142](app/workflow/nodes/synthesizer.py#L142)), even when Groq or Gemini answered.

6. **Upload filenames are trusted.** [app/api/routes/documents.py:49](app/api/routes/documents.py#L49) builds the save path from `file.filename` directly. A client sending a name like `../../app/main.py` could try to write outside `data/documents/`. The API key limits who can do this, but `Path(file.filename).name` would strip any folders.

7. **The README's evaluation command does nothing.** [README.md:303](README.md#L303) says `python -m app.evaluation.evaluator`, but that module has no `if __name__ == "__main__":` block. Use `python evaluation/run_evaluation.py` instead.

8. **`LogContext` would not add anything to logs.** It uses `structlog.contextvars.bind_contextvars` ([app/observability/logger.py:92](app/observability/logger.py#L92)), but the processor list in `setup_logging` doesn't include `structlog.contextvars.merge_contextvars`, which is what copies those values into each log line. It's also never used.

### Design quirks

9. **`/health` makes a real LLM call** ([app/api/routes/health.py:26](app/api/routes/health.py#L26) → [app/core/llm.py:131](app/core/llm.py#L131)), and `docker-compose.yml` calls it every 30 seconds ([docker-compose.yml:24-25](docker-compose.yml#L24-L25)). That uses up a free-tier quota and can mark the container unhealthy just because the LLM is slow.

10. **The slow analysis blocks the server.** `analyze_change` is `async def` but does slow blocking work ([app/api/routes/analysis.py:53-61](app/api/routes/analysis.py#L53-L61)). While one analysis runs, even `/health/live` waits.

11. **BM25 is rebuilt on every analysis** because a new `HybridRetriever` is created each time ([app/workflow/nodes/retriever.py:37](app/workflow/nodes/retriever.py#L37), [app/rag/retriever.py:182-185](app/rag/retriever.py#L182-L185)), and it loads every chunk into memory.

12. **A class name is shadowed.** [app/auth/api_key.py:27](app/auth/api_key.py#L27) assigns an instance to the name `APIKeyHeader`, hiding the imported class. `app/auth/__init__.py` then exports this instance under the class's name. Calling it `api_key_header` would be clearer.

13. **Mutable default argument.** `extensions: List[str] = [".txt", ...]` in [app/ingestion/processor.py:65](app/ingestion/processor.py#L65). It's harmless here because the list is never changed, but it's a well-known trap: the same list object is shared by all calls.

14. **Two functions named `get_retriever`** in different modules: vector-only in [app/core/vectorstore.py:66](app/core/vectorstore.py#L66), hybrid in [app/rag/retriever.py:182](app/rag/retriever.py#L182). Only the second is used.

15. **The LLM's confidence wins over the computed one** ([app/workflow/nodes/synthesizer.py:161](app/workflow/nodes/synthesizer.py#L161)), even though the computed one is based on facts. Both are returned, so you can compare them.

16. **`datetime.utcnow()`** is used throughout. It is deprecated since Python 3.12; `datetime.now(timezone.utc)` is the modern form.

### Unused code

- `vector_weight` and `bm25_weight` ([app/rag/retriever.py:32-39](app/rag/retriever.py#L32-L39)), `retrieve_with_scores` ([app/rag/retriever.py:149-157](app/rag/retriever.py#L149-L157)).
- `TechnicalImpact`, `TechnicalAnalysisOutput` and the `JsonOutputParser` import in [app/workflow/nodes/technical.py](app/workflow/nodes/technical.py#L16-L43).
- `add_documents_to_store`, `search_documents` and `get_retriever` in [app/core/vectorstore.py](app/core/vectorstore.py#L66-L154).
- `reload_prompts` and the four module-level prompt constants in [app/prompts/\_\_init\_\_.py](app/prompts/__init__.py#L53-L63).
- `generate_api_key` ([app/auth/api_key.py:102-116](app/auth/api_key.py#L102-L116)), `LogContext`, the whole tracer.
- The commented-out old workflow ([app/workflow/graph.py:1-97](app/workflow/graph.py#L1-L97)) and old scripts ([test_setup.py:1-176](test_setup.py#L1-L176)).
- The duplicate [evaluation/evaluator.py](evaluation/evaluator.py), empty `app/api/schemas/` and `streamlit_app/components/` packages, and `data/uploads` created in [Dockerfile:30](Dockerfile#L30).

### Setup gotchas

- **Switching embedding providers breaks an existing database.** Ollama's `nomic-embed-text` makes 768-number vectors, FastEmbed's model makes 384 ([app/core/embeddings.py:9-12](app/core/embeddings.py#L9-L12)). Chroma refuses to mix them. Delete `data/chroma_db/` after switching.
- **Ollama models must be pulled first** (`ollama pull llama3` and `ollama pull nomic-embed-text`), or every LLM call fails and each agent returns its error default.
- **`pyproject.toml` is out of date.** It lists `unstructured` and lacks Groq, Gemini, FastEmbed and langchain-chroma ([pyproject.toml:9-39](pyproject.toml#L9-L39)). Install from `requirements.txt`.
- **CI can't go red for tests or lint** because of `continue-on-error: true` ([.github/workflows/ci.yml:59](.github/workflows/ci.yml#L59)).
- **Run commands from the repo root.** Several paths are relative to the current folder: `logs/`, `data/documents`, `evaluation/test_cases/...`.
- **Plain `pytest` runs `test_setup.py`**, which needs a working LLM. Use `pytest tests/`.
- **The README's endpoint table** lists `/traces/`; the route is `/traces` (FastAPI redirects the slash version by default).

---

## 9. Exercises

From easy to advanced. Each one says which file to change. Run `pytest tests/` after each.

1. **Add an example button.** Add "Move customer support from email to live chat" to the examples list. *File:* [streamlit_app/app.py:45-51](streamlit_app/app.py#L45-L51).

2. **Use the setting instead of a hard-coded number.** Make the retriever node use `RETRIEVAL_TOP_K` from the settings instead of `k=5`. *File:* [app/workflow/nodes/retriever.py:37](app/workflow/nodes/retriever.py#L37). Hint: `get_retriever()` with no argument already does this.

3. **Record the real model name.** Replace `"llama3"` in the four trace entries with the configured provider and model. *Files:* the four nodes in [app/workflow/nodes](app/workflow/nodes/technical.py#L117-L123). Hint: `get_settings().LLM_PROVIDER`.

4. **Fix the API key mismatch.** Make the UI load `.env` too, so local runs use the same key as the API. *File:* [streamlit_app/app.py:14-15](streamlit_app/app.py#L14-L15). Hint: `pydantic-settings` is installed, or add `python-dotenv`.

5. **Make the synthesizer safe.** Handle actions that are strings as well as dicts, and move the loop inside a `try`. *File:* [app/workflow/nodes/synthesizer.py:146-148](app/workflow/nodes/synthesizer.py#L146-L148). Write a test that calls `synthesize_results` with a fake LLM (see exercise 9 for mocking).

6. **Remove the repetition.** Write one helper `run_llm_agent(state, prompt_name, defaults, result_key, node_name)` and make the technical, operational and risk nodes use it. *Files:* [technical.py](app/workflow/nodes/technical.py#L51-L135), [operational.py](app/workflow/nodes/operational.py#L27-L106), [risk.py](app/workflow/nodes/risk.py#L27-L102). Your module should be under 60 lines.

7. **Make the agents really parallel.** Change the graph so `retrieve` fans out to all three analysts and they all lead into `synthesize`. *File:* [app/workflow/graph.py:144-149](app/workflow/graph.py#L144-L149). You will also need to change each analyst to return **only** the keys it changed (not `{**state, ...}`), and give `execution_trace` a reducer in [app/workflow/state.py](app/workflow/state.py#L43) using `Annotated[List[dict], operator.add]` so LangGraph merges the parallel traces. Measure the time before and after.

8. **Wire in the tracer.** Start a trace in `run_analysis`, record each node's step, complete and save it at the end, and return the `trace_id` in the response so `/traces/{id}` works. *Files:* [app/workflow/graph.py:159-182](app/workflow/graph.py#L159-L182), [app/api/routes/analysis.py:39-49](app/api/routes/analysis.py#L39-L49).

9. **Write real API tests.** In `tests/test_api/`, use `fastapi.testclient.TestClient` to check that `/analysis/run` returns 401 without a key and 403 with a wrong key. Then mock the LLM (replace `app.core.llm.get_llm` with a function returning a fake object whose `invoke` returns canned JSON) and check a full 200 response. *Folder:* [tests/test_api](tests/test_api/__init__.py). Also remove `continue-on-error` from the test step in [.github/workflows/ci.yml:59](.github/workflows/ci.yml#L59).

10. **Use the weights for a real hybrid score.** Replace interleaving with *reciprocal rank fusion*: give each document `weight / (60 + rank)` from each list it appears in, add them up, and sort. Use `vector_weight` and `bm25_weight`. *File:* [app/rag/retriever.py:79-112](app/rag/retriever.py#L79-L112). Use the evaluation script to compare before and after.

---

## 10. Glossary

**Agent.** Here, a function that sends a specific instruction to an LLM and returns a structured answer. This project has four (technical, operational, risk, synthesizer) plus a retrieval step.

**API (Application Programming Interface).** A set of URLs a program can call to get things done. The backend is an HTTP API.

**API key.** A secret string sent with each request to prove the caller is allowed.

**BM25.** A classic keyword-search ranking formula. Good at exact words and names.

**Chain (LangChain).** Components joined with `|` so the output of one feeds the next.

**Chunk.** A small piece of a document (here up to 1,000 characters) stored and searched separately.

**CORS.** A browser security rule about which websites may call an API from JavaScript.

**Dependency (FastAPI).** A function FastAPI runs before a route, used here for API-key checks.

**Docker / container / image.** An *image* is a packaged app with everything it needs; a *container* is a running copy of it. `docker compose` runs several containers together.

**Embedding / vector.** A list of numbers representing the meaning of a text. Similar meanings give nearby vectors.

**Endpoint / route.** One URL plus HTTP method that the API answers, e.g. `POST /analysis/run`.

**Fallback.** A second option used automatically when the first one fails.

**Graph, node, edge (LangGraph).** A workflow drawn as boxes (nodes, functions) and arrows (edges, the order).

**HTTP status codes.** 200 OK, 401 not authenticated, 403 forbidden, 404 not found, 422 invalid input, 500 server error.

**Hybrid search.** Combining semantic (vector) search with keyword (BM25) search.

**Ingestion.** Loading documents, splitting them and storing them for search.

**JSON.** A text format for data: `{"key": "value", "list": [1, 2]}`. Python dicts and lists map onto it.

**LLM (Large Language Model).** An AI model that generates text, like Llama 3, Gemini or the models served by Groq.

**Middleware.** Code that wraps every request and response, e.g. for logging.

**Observability.** Being able to see what a running system is doing: logs, traces, health checks.

**Prompt.** The instruction text given to an LLM.

**RAG (Retrieval-Augmented Generation).** Finding relevant text first, then giving it to the LLM along with the question so the answer is grounded in real documents.

**Rate limit.** A cap on how many requests a service allows in a time window. Free tiers have strict ones.

**Retriever.** An object that takes a query and returns relevant documents.

**Semantic search.** Search by meaning (via embeddings) rather than exact words.

**State (LangGraph).** The dictionary passed from node to node, holding everything computed so far.

**Structured logging.** Logs as key/value data (here JSON) rather than plain sentences.

**Temperature.** An LLM setting for randomness; low means consistent, high means creative.

**Trace.** A record of the steps of one run and how long each took.

**Uvicorn.** The server program that runs a FastAPI app.

**Vector store / vector database.** A database that stores embeddings and finds the nearest ones to a query. Here, ChromaDB.
