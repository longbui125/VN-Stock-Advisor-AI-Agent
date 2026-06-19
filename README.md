# Vietnam Stock Advisor RAG Agent

Agent phân tích dữ liệu chứng khoán Việt Nam. Project có hai luồng dữ liệu chính:

- Dữ liệu có cấu trúc được lưu vào Postgres để agent tự sinh SQL và truy vấn.
- Dữ liệu văn bản được chunk, embed và lưu vào Qdrant để agent truy xuất theo RAG.

## Cấu Trúc

```text
src/
  ingestion/    Lấy dữ liệu từ vnstock và load vào Postgres/Qdrant
  chunking/     Chia văn bản thành các đoạn nhỏ
  embeddings/   Tạo embedding local
  vectordb/     Tạo collection và upsert vector vào Qdrant
  retrieval/    Truy xuất tài liệu từ Qdrant
  prompts/      System prompt cho SQL + RAG agent
  llm/          Tạo LangChain agent và Ollama client
  utils/        Config, biến môi trường và Postgres helpers
```

## Cài Ollama Local

Lần đầu tiên, cài Ollama trên Windows và tải model:

```powershell
winget install Ollama.Ollama
ollama pull qwen3:8b
ollama pull bge-m3
ollama list
```

Model mặc định hiện tại:

```text
qwen3:8b
```

Nếu máy đủ mạnh, có thể dùng model tốt hơn:

```powershell
ollama pull qwen3:14b
```

Sau đó đổi `.env`:

```env
OLLAMA_MODEL=qwen3:14b
```

## Chạy Hạ Tầng Và Data Pipeline

Docker chỉ chạy Postgres, Qdrant, Adminer và các job ingest. Streamlit chạy riêng trên terminal Windows để theo dõi verbose/agent trace.

```powershell
docker compose up -d
```

Lệnh này khởi động:

```text
postgres
qdrant
init-postgres
ingest-prices
ingest-texts
adminer
```

## Chạy Streamlit Riêng

```powershell
$env:POSTGRES_URI="postgresql://stocks:stocks@localhost:5432/stocks"
$env:QDRANT_URL="http://localhost:6333"
$env:QDRANT_COLLECTION="vn_stock_text_chunks"
$env:OLLAMA_BASE_URL="http://localhost:11434"
$env:OLLAMA_MODEL="qwen3:8b"
$env:OLLAMA_EMBED_MODEL="bge-m3"
$env:AGENT_VERBOSE="true"
$env:AGENT_MAX_ITERATIONS="6"
$env:QDRANT_TOP_K="8"
streamlit run main.py
```

Mở ứng dụng:

```text
http://localhost:8501
```

## Chạy Lại Từng Job

Khởi tạo schema Postgres:

```powershell
docker compose run --rm init-postgres
```

Lấy giá cổ phiếu vào Postgres:

```powershell
docker compose run --rm ingest-prices
```

Lấy company profile, chunk text và embed vào Qdrant:

```powershell
docker compose run --rm ingest-texts
```

Xóa collection Qdrant cũ rồi embed lại:

```powershell
docker compose run --rm ingest-texts python -m src.ingestion.text_loader --recreate-collection
```

## Theo Dõi Dữ Liệu

Adminer để xem Postgres:

```text
http://localhost:8080
```

Qdrant dashboard:

```text
http://localhost:6333/dashboard
```

Collection Qdrant mặc định:

```text
vn_stock_text_chunks
```

## Cấu Hình Chính

File `.env` tối thiểu:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b
OLLAMA_EMBED_MODEL=bge-m3
AGENT_VERBOSE=true
AGENT_MAX_ITERATIONS=6
POSTGRES_URI=postgresql://stocks:stocks@localhost:5432/stocks
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=vn_stock_text_chunks
QDRANT_TOP_K=8
```
