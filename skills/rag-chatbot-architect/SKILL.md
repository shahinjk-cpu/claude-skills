---
name: rag-chatbot-architect
description: >-
  Architects and implements production-grade RAG (Retrieval-Augmented Generation)
  systems, vector databases (Supabase pgvector, Qdrant, Chroma, Pinecone), hybrid
  search pipelines, stateful AI chatbots, and PixelRAG (visual document/screenshot RAG). Use when building document Q&A systems,
  knowledge assistants, conversational bots, embedding pipelines, or troubleshooting
  RAG retrieval accuracy and hallucinations.
---

# RAG, AI Chatbot & PixelRAG Architect

Use this skill when designing, coding, or optimizing Retrieval-Augmented Generation (RAG) pipelines, conversational AI chatbots, and multimodal visual document search systems.

---

## 1. End-to-End RAG Architecture Blueprint

### Phase 1: Document Ingestion & Smart Chunking
- **Never use naive fixed-character splitting** on structured documents.
- **Preferred Chunking Strategies**:
  1. **Markdown / Heading-Aware Splitting**: Preserve section hierarchy (`# H1 > ## H2 > ### H3`) and prepend the breadcrumb path to every chunk so the chunk never loses its parent context.
  2. **Semantic / Recursive Splitting**: Split by paragraphs -> sentences -> words, targeting **300–600 tokens per chunk** with **10–15% overlap**.
  3. **Contextual Retrieval Header**: Prepend `[Document: <title> | Section: <header> | Date: <date>]` to the text before embedding.
  4. **Tables & Code Blocks**: Keep markdown tables and code blocks intact within a single chunk whenever possible.

### Phase 2: Embeddings & Vector Storage
- Store rich metadata alongside every vector: `source_id`, `doc_title`, `section`, `page_number`, `created_at`, `access_role`.
- **Supabase `pgvector` Best Practices**:
  - Use `halfvec` or `vector` with an **HNSW** index (`m = 16, ef_construction = 64`) for fast approximate nearest neighbor search.
  - Combine vector similarity with metadata pre-filtering (`WHERE tenant_id = ...`) and Row Level Security (RLS).

### Phase 3: Hybrid Retrieval & Reranking (High Precision)
- **Query Transformation**:
  - Rewrite conversational follow-up queries (e.g., *"How much does it cost?"* -> *"What is the pricing for Enterprise Plan X?"*) using conversation history before searching.
- **Hybrid Search**:
  - Combine **Dense Vector Search** (semantic meaning) + **BM25 / Full-Text Search** (exact keywords, IDs, product codes, legal articles) using Reciprocal Rank Fusion (RRF).
- **Cross-Encoder Reranking**:
  - Retrieve top 20–30 candidates via Hybrid Search, then rerank to the top 5–8 most relevant chunks before passing to the LLM.

### Phase 4: Grounded Generation & Citations
- Instruct the LLM to answer **strictly** from the retrieved chunks and cite sources inline (e.g., `[1]`, `[DocName, p. 4]`).
- Include a fallback path: if retrieval confidence is below threshold, ask a clarifying question or state clearly that the knowledge base does not contain the answer.

---

## 2. PixelRAG & Visual Multimodal RAG (`StarTrail-org/PixelRAG`)

When working with complex PDF reports, financial statements, slide decks, scientific papers, or websites containing rich graphics, charts, and intricate tables, **text extraction destroys crucial information**. Implement the **PixelRAG** visual paradigm:

```
[PDF / Web Document] ──> Render High-DPI Screenshot Tiles (via Playwright / pdf2image)
                               │
                               ▼
                    [Visual Embedding Model] (ColPali / Qwen-VL Embedding)
                               │
                               ▼
                     [Visual Vector Index] (FAISS / pgvector)
                               │
                    [User Query: "Show me Q3 profit margin"]
                               │
                               ▼
        Retrieve Exact Screenshot Tile (containing graphic/table)
                               │
                               ▼
        Feed Image Tile directly to Multimodal VLM (Gemini 2.5 Flash / GPT-4o)
                               │
                               ▼
        100% Accurate Visual Answer (No OCR errors, zero broken table columns)
```

### When to Use PixelRAG Over Text RAG:
1. **Scientific Dissertations & Papers**: Formulas, architecture diagrams, loss curves, and ANOVA tables.
2. **Financial Filings (10-K, Balance Sheets)**: Multi-column tabular data where standard text extractors merge adjacent rows.
3. **Presentations & Slide Decks**: Slide layouts where visual hierarchy and icon positioning dictate meaning.

---

## 3. Stateful Chatbot Architecture

1. **Three-Tier Memory System**:
   - **Short-Term Window**: Last 6–10 turns verbatim.
   - **Rolling Summary**: Compressed summary of older turns updated asynchronously.
   - **Long-Term User/Entity Memory**: Key facts/preferences stored in DB and retrieved on session start.
2. **Streaming & UX**:
   - Stream tokens via SSE / WebSockets (`gemini-interactions-api` or `gemini-live-api-dev` for voice).
   - Emit structured status events (`Searching knowledge base...`, `Generating chart...`) so the UI feels responsive.
3. **Evaluation (RAG Triad)**:
   - Measure **Context Relevance** (did we fetch the right chunks?), **Groundedness / Faithfulness** (did the LLM stick to the chunks?), and **Answer Relevance** (did it answer the user's question?).
