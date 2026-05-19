# WhatsApp Personal Document Bot (Django + DRF + RAG)

A WhatsApp bot users join by scanning a QR code. They send any PDF, image,
text, or DOCX into the chat, and later ask plain-English questions like
"What is my PAN number?" or "What is my account number?" and the bot answers
from the user's own documents only.

The backend is Django + DRF, storage is SQLite, retrieval is sentence-transformers
embeddings with cosine search, and generation uses Groq with an extractive
fallback.

## Stack

- Django 5 + Django REST Framework
- SQLite (data + JSON-encoded vectors)
- Twilio WhatsApp (Sandbox or production)
- sentence-transformers `all-MiniLM-L6-v2`
- PyMuPDF + python-docx + Tesseract OCR
- Groq for generative answers (optional)

## Project layout

```
bot/
├── config/                   # Django project (settings, urls, wsgi/asgi)
├── core/                     # WhatsAppUser model
├── documents/                # Document & Chunk models, parser, chunker, ingestion, REST
├── rag/                      # Embedder, vector store, RAG engine, /api/query/
├── messaging/                # Twilio webhook, dispatcher (commands), inbound log
├── onboarding/               # QR code landing page
├── templates/onboarding/     # landing.html
├── manage.py
├── requirements.txt
└── .env.example
```

## Prerequisites

- Python 3.11+
- **Tesseract OCR** installed and on `PATH`
  - macOS: `brew install tesseract`
  - Ubuntu/Debian: `sudo apt install tesseract-ocr`
  - Windows: https://github.com/UB-Mannheim/tesseract/wiki (default path: `C:\Program Files\Tesseract-OCR`)
- A Twilio account with WhatsApp Sandbox enabled (or a production WhatsApp sender)
- (Optional) A Groq API key for generative answers

## Setup

```bash
python -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                      # then edit values
python manage.py migrate
python manage.py createsuperuser          # optional, for /admin/
python manage.py runserver 127.0.0.1:8000
```

First request that triggers an embedding will download the model (~90 MB for
MiniLM, plus tokenizer files); be patient on the first call.

## Configure Twilio

1. In Twilio Console, open **Messaging → Try it out → Send a WhatsApp message**.
2. Note your sandbox number (e.g. `whatsapp:+14155238886`) and join code (e.g. `join example-word`).
3. In `.env` set:
   ```
   TWILIO_ACCOUNT_SID=ACxxxxxxxx
   TWILIO_AUTH_TOKEN=xxxxxxxxxxxx
   TWILIO_WHATSAPP_NUMBERS=whatsapp:+14155238886
   TWILIO_SANDBOX_JOIN_CODE=join example-word
   ```
4. Expose your local server with ngrok:
   ```bash
   ngrok http 8000
   ```
   Copy the HTTPS URL into `.env` as `PUBLIC_BASE_URL=https://<id>.ngrok-free.app`.
5. In the Sandbox settings set **WHEN A MESSAGE COMES IN** to:
   ```
   https://<id>.ngrok-free.app/webhook/whatsapp/
   ```
   Method: POST.
6. Restart the server.

## Onboarding

Open `http://127.0.0.1:8000/` (or your public URL). The page shows a QR that
encodes `https://wa.me/<picked_number>?text=<join code or hi>`. Multiple numbers
in `TWILIO_WHATSAPP_NUMBERS` will be rotated daily.

## Bot commands

- Plain text → asked as a question against the user's own documents
- Send a file or photo → indexed for that user
- `/help` — show help
- `/list` — list your documents
- `/delete <id>` — delete one document
- `/reset` — delete everything you uploaded

## REST API (for testing without WhatsApp)

```
GET  /api/documents/?wa_id=whatsapp:+91XXXXXXXXXX
POST /api/documents/        multipart: wa_id, file
DELETE /api/documents/<uuid>/?wa_id=whatsapp:+91XXXXXXXXXX

POST /api/query/
{
  "wa_id": "whatsapp:+91XXXXXXXXXX",
  "question": "What is my PAN number?",
  "top_k": 4
}
```

## Generation backends

- `GENERATION_BACKEND=groq` + `GROQ_API_KEY=...` → LLM answers (recommended)
- `GENERATION_BACKEND=extractive` → returns the top retrieved chunk verbatim, no API key needed

## Handoff: implementing the RAG layer

The HTTP/WhatsApp side works without `sentence-transformers` or `groq`
installed, so the API can be tested today. The RAG implementer only needs
to honor the contract in `rag/services/interface.py`:

- `rag.services.embedder.embed_texts` and `embed_query`
- `rag.services.engine.answer_question`
- `rag.services.vector_store.search_for_user`

Until the embedder is online, ingestion still saves files and chunks but
records `is_embedded=False`. To backfill once the model is wired up:

```bash
pip install sentence-transformers groq      # heavy ML deps
python manage.py embed_pending --batch 64
```

Querying without an embedder returns HTTP 503 with a clear message; the
WhatsApp dispatcher returns a friendly fallback reply instead of crashing.

## Privacy & isolation

Every `Document` and `Chunk` is keyed to the WhatsApp user (`wa_id`). The
vector store filters by `user_id` at query time, so users never see each
other's data.

## Notes

- Twilio limits a single WhatsApp reply to ~1600 chars; replies are trimmed.
- Linear cosine search is fine for personal-scale data. If you outgrow SQLite,
  switch the `vector_store` service to FAISS, Chroma, or `sqlite-vec`.
- Inbound media is downloaded with the Twilio Account SID/Auth Token because
  Twilio media URLs are private.
- For production, set `TWILIO_VALIDATE_SIGNATURE=true` (default) and serve
  over HTTPS; the webhook validates Twilio's `X-Twilio-Signature`.
