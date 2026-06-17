# Vietnam Stock Advisor RAG Agent

Agent tu van va phan tich du lieu chung khoan Viet Nam cho mon hoc. Project co hai nhanh du lieu:

- Structured data vao Postgres de agent tu sinh SQL va query.
- Text data vao Qdrant de agent retrieve theo RAG.

## Cau truc

```text
src/
  ingestion/    Lay du lieu tu vnstock va load vao Postgres/Qdrant
  chunking/     Cat text thanh chunks
  embeddings/   Tao vector embedding local
  vectordb/     Tao collection va upsert chunks vao Qdrant
  retrieval/    Retriever doc tu Qdrant
  prompts/      System prompt cho SQL + RAG agent
  llm/          Tao LangChain agent va LLM client
  api/          Wrapper goi agent cho UI/API
  utils/        Config, env, Postgres helpers
```

## Chay tat ca bang Docker

```powershell
docker compose up -d
```

Lenh nay khoi dong Postgres, Qdrant, init schema, ingest gia, ingest text RAG, Adminer va Streamlit.

## Chay tung job

Khoi tao schema:

```powershell
docker compose run --rm init-postgres
```

Lay gia co phieu vao Postgres:

```powershell
docker compose run --rm ingest-prices
```

Lay company profile, chunk va embed vao Qdrant:

```powershell
docker compose run --rm ingest-texts
```

Xoa collection cu roi embed lai:

```powershell
docker compose run --rm ingest-texts python -m src.ingestion.text_loader --recreate-collection
```

## Mo ung dung

```text
http://localhost:8501
```

Adminer xem Postgres:

```text
http://localhost:8080
```

Qdrant collection mac dinh:

```text
vn_stock_text_chunks
```
