# Vietnam Stock Advisor RAG Agent

Agent tư vấn và phân tích dữ liệu chứng khoán Việt Nam cho môn học. Project có hai nhánh dữ liệu:

- Structured data vào Postgres để agent tự sinh SQL và query.
- Text data vào Qdrant để agent retrieve theo RAG.

## Cấu trúc

```text
src/
  ingestion/    Lấy dữ liệu từ vnstock và load vào Postgres/Qdrant
  chunking/     Cắt văn bản thành các đoạn nhỏ
  embeddings/   Tạo vector embedding cục bộ
  vectordb/     Tạo collection và upsert các đoạn văn bản vào Qdrant
  retrieval/    Retriever lấy tài liệu từ Qdrant
  prompts/      Prompt hệ thống cho agent SQL + RAG
  llm/          Tạo LangChain agent và LLM client
  api/          Wrapper gọi agent cho UI/API
  utils/        Config, env, Postgres helpers
```

## Chạy tất cả bằng Docker

```powershell
docker compose up -d
```

Lệnh này khởi động Postgres, Qdrant, khởi tạo schema, ingest dữ liệu giá, ingest dữ liệu văn bản RAG, Adminer và Streamlit.

## Chạy từng job

Khởi tạo schema:

```powershell
docker compose run --rm init-postgres
```

Lấy dữ liệu giá cổ phiếu vào Postgres:

```powershell
docker compose run --rm ingest-prices
```

Lấy hồ sơ doanh nghiệp, chia nhỏ văn bản và tạo embedding vào Qdrant:

```powershell
docker compose run --rm ingest-texts
```

Xóa collection cũ rồi tạo embedding lại:

```powershell
docker compose run --rm ingest-texts python -m src.ingestion.text_loader --recreate-collection
```

## Mở ứng dụng

```text
http://localhost:8501
```

Adminer để xem Postgres:

```text
http://localhost:8080
```

Collection Qdrant mặc định:

```text
vn_stock_text_chunks
```
