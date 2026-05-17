# Personal Document RAG System (Simple SQLite Version)

This project provides the complete backend pipeline for:
- Document parsing (PDF, image OCR, TXT, MD, DOCX)
- Chunking and embedding generation
- Local vector storage and retrieval using SQLite
- RAG query API that returns answers with source chunks

The WhatsApp integration layer is intentionally excluded.

## Architecture

1. Upload documents to the API
2. Parse content using PDF extraction, OCR, and document readers
3. Chunk text into retrieval units
4. Create embeddings using Sentence Transformers
5. Store vectors in local SQLite database
6. Query by natural language
7. Retrieve top chunks and generate answer (Groq or extractive fallback)

## Tech Stack

- FastAPI
- SQLite (local file database)
- Sentence Transformers (all-MiniLM-L6-v2)
- Groq API (optional)
- PyMuPDF, pytesseract, python-docx

## Prerequisites

- Python 3.11+
- **Tesseract OCR installed on machine (REQUIRED for image/PDF parsing)**

### Install Tesseract on Windows (IMPORTANT)

**This is mandatory.** Without it, image and scanned PDF ingestion will fail with HTTP 500.

1. Download installer from:
   https://github.com/UB-Mannheim/tesseract/wiki
   
   Latest stable: **v5.4.0 or later**

2. Run installer and install to default path:
   `C:\Program Files\Tesseract-OCR`

3. After install, open a NEW CMD/PowerShell terminal.

4. Verify installation:

```cmd
tesseract --version
```

If command not found, add to PATH:

```cmd
set PATH=C:\Program Files\Tesseract-OCR;%PATH%
tesseract --version
```

5. If still not found, check your actual install path and replace in the command above.

## Setup

1. Activate your virtual environment (existing in this project):

```powershell
.\major_project\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Ensure environment file exists:

```powershell
Copy-Item .env.example .env
```

4. Run API:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

   Note: Use `127.0.0.1` instead of `0.0.0.0` to avoid reload issues on Windows.

5. Open browser:

- Swagger API: http://127.0.0.1:8000/docs

## One-Command Run (Windows)

From project root, run either:

```powershell
.\run_app.ps1
```

or in cmd:

```cmd
run_app.cmd
```

Notes:
- The script auto-installs dependencies.
- The script auto-creates `.env` from `.env.example` if needed.
- To skip dependency install in PowerShell:

```powershell
.\run_app.ps1 -SkipInstall
```

## API Endpoints

- GET /health
- POST /ingest/files
  - Multipart upload with one or more files
  - Supported: .pdf, .txt, .md, .docx, .png, .jpg, .jpeg, .tif, .tiff
- POST /query
  - Body:

```json
{
  "question": "What is my PAN number?",
  "top_k": 4
}
```

## Generation Modes

### 1) Extractive mode (free, no API key)

Set in .env:

```env
GENERATION_BACKEND=extractive
```

### 2) Groq mode (API key required)

Set in .env:

```env
GENERATION_BACKEND=groq
GROQ_API_KEY=your_key_here
GROQ_MODEL=openai/gpt-oss-120b
```

Restart server after env changes.

## Troubleshooting

### "Ingestion failed: tesseract is not installed or it's not in your PATH"

1. Verify Tesseract is installed:
   ```cmd
   tesseract --version
   ```

2. If not found, add to PATH manually:
   ```cmd
   set PATH=C:\Program Files\Tesseract-OCR;%PATH%
   ```

3. Restart your API server after fixing PATH.

### Server reload loop / "localhost refused to connect"

1. Stop server (Ctrl+C)
2. Run without reload flag:
   ```cmd
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
3. This avoids watching the venv folder, which causes excessive reloads.

### Query returns weak/empty answers

1. Upload a clearer document first (UTF-8 text, not scanned images).
2. Ask questions using exact wording from the document.
3. Check that ingest response shows chunks_indexed > 0.

## Notes

- First run downloads the embedding model (~1.5 GB) and may take time.
- Vectors are stored in local SQLite file set by SQLITE_DB_PATH in .env.
- Extractive fallback returns highest-ranked chunk when Groq is not configured.
- Default host is 127.0.0.1 (localhost) to avoid Windows file watcher issues.
"# WhatsApp-Based-Personal-Document-Retrieval-System-Using-RAG" 
