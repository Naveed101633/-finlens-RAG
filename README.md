# FinLens RAG

**A production-grade financial document analyst powered by Hybrid Retrieval Augmented Generation. Upload PDF annual reports and ask questions in plain language — every answer is grounded in source documents with exact page citations.**

---

## Architecture Overview

FinLens implements a sophisticated hybrid RAG pipeline that combines semantic understanding with keyword precision to extract accurate, cited answers from financial documents.

### Ingestion Pipeline
```
PDF Upload → Text Extraction → Chunking → Dual Indexing
                                              ├─ Semantic Embeddings (Qdrant)
                                              └─ BM25 Index (In-Memory)
```

**Process:**
1. User uploads PDF financial report via the web UI
2. Document is parsed into pages and split into overlapping chunks
3. Each chunk is embedded using `sentence-transformers/all-MiniLM-L6-v2`
4. Embeddings are indexed in Qdrant vector database
5. Chunks are simultaneously indexed in BM25 keyword search index
6. Metadata (source file, page number, chunk ID) is preserved for citations

### Query Pipeline
```
User Question → Hybrid Search → Reranking → LLM Generation → Cited Answer
                    ↓
            ┌───────┴───────┐
            ↓               ↓
        Semantic         BM25
        Search           Search
            ↓               ↓
            └───────┬───────┘
                    ↓
          Reciprocal Rank Fusion
                    ↓
           Top-K Documents Selected
                    ↓
              Gemini 2.5 Flash
                    ↓
          Grounded Answer + Citations
```

**Process:**
1. User submits a question through the web interface
2. Query is executed against both semantic (Qdrant) and keyword (BM25) indices
3. Results are merged using Reciprocal Rank Fusion (RRF) for optimal ranking
4. Top contexts are passed to Google Gemini 2.5 Flash with strict grounding instructions
5. LLM generates answer constrained to provided context only
6. Top 3 source citations (by relevance score) are returned with page numbers
7. Client receives answer with inline source references

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend** | Python 3.12, FastAPI | REST API, request handling |
| **Vector DB** | Qdrant | Semantic search, embedding storage |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2) | Text → vector encoding |
| **Keyword Search** | BM25 | Exact term matching and ranking |
| **Ranking** | Reciprocal Rank Fusion (RRF) | Hybrid result fusion |
| **LLM** | Google Gemini 2.5 Flash | Answer generation |
| **Frontend** | Next.js 15, TypeScript | Web UI, real-time interaction |
| **Styling** | Tailwind CSS | Responsive design system |
| **Infrastructure** | Docker | Containerized Qdrant service |
| **Package Manager** | UV | Fast Python dependency management |

---

## Project Structure

```
financial-rag/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI application entry point
│   │   ├── config.py               # Environment and settings
│   │   ├── models/
│   │   │   └── schemas.py          # Pydantic request/response schemas
│   │   └── routes/
│   │       ├── ingest.py           # Upload, list, delete endpoints
│   │       └── query.py            # Question answering endpoint
│   ├── ingestion/
│   │   ├── loader.py               # PDF text extraction
│   │   ├── chunker.py              # Document → overlapping chunks
│   │   ├── embedder.py             # Chunk → vector conversion
│   │   └── indexer.py              # Qdrant indexing operations
│   ├── rag/
│   │   ├── pipeline.py             # Unified RAG pipeline orchestrator
│   │   ├── retriever.py            # Hybrid search + RRF fusion
│   │   ├── reranker.py             # Result reranking (placeholder)
│   │   └── generator.py            # Gemini answer generation
│   ├── prompts/
│   │   ├── rag_prompt.py           # Query generation prompts
│   │   └── system_prompt.py        # LLM system instructions
│   ├── evaluation/
│   │   ├── eval_runner.py          # RAGAS evaluation harness
│   │   └── eval_dataset.json       # Ground truth evaluation set
│   ├── requirements.txt            # Python dependencies
│   └── docker-compose.yml          # Qdrant service definition
├── frontend/
│   ├── app/
│   │   ├── page.tsx                # Main dashboard component
│   │   ├── layout.tsx              # Root layout wrapper
│   │   ├── globals.css             # Tailwind configuration
│   │   └── ...                     # Additional page components
│   ├── package.json                # Node.js dependencies
│   ├── next.config.ts              # Next.js configuration
│   └── tsconfig.json               # TypeScript settings
├── data/
│   ├── raw/                        # Original uploaded PDFs
│   ├── processed/                  # Processed chunks (optional)
│   └── eval_sets/                  # Evaluation datasets
├── docker-compose.yml              # Full stack orchestration
├── pyproject.toml                  # Python project metadata
├── .env.example                    # Environment template
└── README.md                       # This file
```

---

## Quick Start

### Prerequisites
- **Python 3.12** or later
- **Docker Desktop** (for Qdrant vector database)
- **Node.js 18+** (for frontend)
- **UV** package manager ([install](https://docs.astral.sh/uv/))
- **Google API Key** (for Gemini, [create at console.cloud.google.com](https://console.cloud.google.com/))

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Naveed101633/financial-RAG.git
   cd financial-rag
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your Google API key:
   ```
   GOOGLE_API_KEY=your_gemini_api_key_here
   ```

3. **Install Python dependencies**
   ```bash
   uv sync
   ```

4. **Start Qdrant vector database**
   ```bash
   docker-compose up -d
   ```
   Verify Qdrant is running: `docker ps` (should show `qdrant` container)

5. **Start backend API server**
   ```bash
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   Backend runs at `http://localhost:8000`
   Interactive API docs at `http://localhost:8000/docs`

6. **Start frontend (new terminal)**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Frontend runs at `http://localhost:3000`

7. **Upload your first document**
   - Open `http://localhost:3000`
   - Expand the upload panel
   - Select a PDF annual report
   - Click "Upload and Index"
   - Once complete, ask questions in the text area

---

## API Endpoints

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| `POST` | `/api/upload` | Upload and index a PDF | `file: binary` | `{filename, pages_loaded, chunks_created, status, message}` |
| `POST` | `/api/query` | Ask a question about indexed documents | `{question, top_k}` | `{answer, citations, query, model_used}` |
| `GET` | `/api/documents` | List all indexed documents | None | `{documents: string[], total: number}` |
| `DELETE` | `/api/documents/{filename}` | Remove document from index | Path param: `filename` | `{filename, status, message}` |
| `GET` | `/api/health` | Service health check | None | `{status, pipeline_info}` |

**Example Query Request:**
```json
{
  "question": "What was the total revenue in 2023?",
  "top_k": 5
}
```

**Example Query Response:**
```json
{
  "answer": "According to the financial statements (Page 12), total revenue in 2023 was $4.2 billion, representing a 12% year-over-year increase.",
  "citations": [
    {
      "page_number": 12,
      "source_file": "annual_report_2023.pdf",
      "chunk_id": "chunk_45",
      "score": 0.89
    }
  ],
  "query": "What was the total revenue in 2023?",
  "model_used": "gemini-2.5-flash"
}
```

---

## How It Works

### Step 1: Document Ingestion
When you upload a PDF, FinLens extracts all text, splits it into overlapping chunks (512 tokens, 100-token overlap), and embeds each chunk using a lightweight transformer model. These embeddings and BM25 indices are stored for fast retrieval.

### Step 2: Hybrid Retrieval
Your question is simultaneously searched against both indices:
- **Semantic Search**: Finds conceptually similar passages using vector similarity
- **Keyword Search**: Identifies exact term matches using BM25 rankings

Results are merged using Reciprocal Rank Fusion, which weights both signals intelligently.

### Step 3: Context Ranking & Generation
The top retrieved passages are passed to Google Gemini 2.5 Flash with strict system instructions to:
- Answer **only** based on provided context
- Cite sources with exact page numbers
- Return "not found" if information is absent

### Step 4: Citation & Response
The model generates a grounded answer and cites its sources. You see the answer with inline page references you can investigate further.

---

## Why Hybrid Search?

**Semantic Search Alone** (vector embeddings):
- ✅ Understands context and synonyms ("profit" vs. "net income")
- ❌ Misses exact financial figures (e.g., "$4.2B" vs. "4200 million")

**Keyword Search Alone** (BM25):
- ✅ Finds exact terms and numbers reliably
- ❌ Semantic drift ("revenue" vs. "sales" may rank differently)

**Hybrid + RRF**:
- ✅ Captures both semantic relevance and exact matches
- ✅ Top financial documents appear in both indices, ranking highest
- ✅ Rare but important context (regulatory footnotes) preserved via keyword match
- ✅ Hallucination prevention: only information present in documents can be retrieved

---

## Evaluation

RAGAS (Retrieval-Augmented Generation Assessment) evaluation suite is configured in `backend/evaluation/`:

- **Eval Dataset**: [eval_runner.py](backend/evaluation/eval_runner.py) with 50+ diverse financial questions
- **Metrics**: Faithfulness, Answer Relevancy, Context Precision, Context Recall
- **Status**: Integration pipeline ready (run `python -m backend.evaluation.eval_runner` after setup)

Ground truth dataset maintained in `backend/evaluation/eval_dataset.json`.

---

## Environment Variables

Create `.env` from `.env.example` with these required variables:

```bash
# Google Gemini API
GOOGLE_API_KEY=your_api_key_here

# Qdrant vector database
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=financial_reports

# Embedding model (fixed: all-MiniLM-L6-v2)
EMBEDDING_DIMENSION=384

# Chunking strategy
CHUNK_SIZE=512
CHUNK_OVERLAP=100

# API configuration
API_PORT=8000
RELOAD=true
```

---

## Performance Considerations

- **Embeddings**: All-MiniLM-L6-v2 (22M parameters) runs locally — no API calls, minimal latency
- **Qdrant**: In-memory vector search with IVF indexing — sub-100ms retrieval
- **BM25**: In-memory inverted index — instant exact-match queries
- **Gemini**: Streaming responses with 5s typical latency for complex financial questions
- **Document Size**: Tested with 50–500 page PDFs; handles efficiently with scroll-based processing

---

## Production Deployment

For production use, consider:

1. **Persistent Qdrant**: Replace Docker with managed Qdrant Cloud or self-hosted with persistent volumes
2. **Authentication**: Add JWT/OAuth to `/auth` endpoints (FastAPI middleware)
3. **Rate Limiting**: Use FastAPI `SlowAPI` to prevent API abuse
4. **Monitoring**: Integrate OpenTelemetry for tracing, Prometheus for metrics
5. **Document Versioning**: Track document update history and chunk lineage
6. **Cost Optimization**: Cache embeddings and use batch processing for bulk uploads
7. **Multi-Tenancy**: Add user/organization isolation at the Qdrant collection level

---

## Troubleshooting

**"No documents are currently indexed"**
- Upload a PDF file first using the UI
- Check that Docker container is running: `docker ps`

**"Error generating answer"**
- Verify `GOOGLE_API_KEY` in `.env` is correct
- Check API quota at [Google Cloud Console](https://console.cloud.google.com/)
- Ensure internet connectivity for Gemini API calls

**Slow document upload**
- Large PDFs (>200 pages) take time to embed (all-MiniLM-L6-v2 processes ~50 chunks/sec)
- Monitor progress in server logs with `--reload` flag active

**Qdrant connection refused**
- Run `docker-compose up -d` to start Qdrant
- Verify port 6333 is not in use: `lsof -i :6333`

---

## License

MIT License — See [LICENSE](LICENSE) for details.

---

## Author

**Naveed Soomro** — AI Engineer  
Building production AI systems with retrieval-augmented generation and hybrid search architectures.

---

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## Acknowledgments

- [Qdrant](https://qdrant.tech/) — Vector database
- [Sentence Transformers](https://www.sbert.net/) — Embedding model
- [FastAPI](https://fastapi.tiangolo.com/) — Web framework
- [Next.js](https://nextjs.org/) — React framework
- [Google Gemini](https://ai.google.dev/) — Language model

---

**Last Updated**: April 2026 | Built for modern financial AI applications
