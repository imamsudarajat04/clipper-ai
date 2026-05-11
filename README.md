# Clipper AI 🎬✂️

**Deteksi highlight otomatis dari video YouTube** — download, transkripsi lokal (Whisper), analisis AI (Groq), sinyal audio/scene (PyDub + OpenCV), **hybrid scoring**, lalu **export clip MP4** lewat Celery + SSE progress di UI.

---

## Fitur

| Fase | Status | Isi |
|------|--------|-----|
| **Phase 1** | Selesai | Download yt-dlp, ekstrak audio (ffmpeg), job queue (Celery + Redis), status & SSE |
| **Phase 2** | Selesai | Whisper, Groq (JSON highlight), signal detection, hybrid engine, export clip per window |
| **Phase 3** | Rencana | Reel gabungan, thumbnail batch, history persisten / share link matang |

---

## Tech stack

| Layer | Teknologi |
|-------|-----------|
| Frontend | Next.js 14, Tailwind, TypeScript |
| Backend | FastAPI (Python 3.11+) |
| Queue | Celery + Redis |
| Download | yt-dlp |
| Media | ffmpeg |
| AI | openai-whisper (lokal) + Groq Chat Completions |
| Sinyal | PyDub + OpenCV |

---

## Prerequisites

- **Python** ≥ 3.11 — [python.org](https://python.org)
- **Node.js** ≥ 18 — [nodejs.org](https://nodejs.org)
- **Docker & Docker Compose** — [docker.com](https://docker.com)
- **ffmpeg** (wajib untuk setup manual lokal)
  ```bash
  # macOS
  brew install ffmpeg

  # Ubuntu/Debian
  sudo apt install ffmpeg
  ```
- **Git**

Untuk mode **AI** atau **Hybrid**, siapkan **Groq API key** ([console.groq.com](https://console.groq.com)).

---

## Quick start (Docker — disarankan)

```bash
git clone <repo-url>
cd clipper-ai

cp .env.example .env
# Isi GROQ_API_KEY. Opsional: GROQ_MODEL, GROQ_TRANSCRIPT_MAX_CHARS, YTDLP_COOKIES_FILE (lihat bawah).

docker compose up --build -d
```

Frontend (terminal terpisah):

```bash
cd frontend
npm install
npm run dev
```

Buka **http://localhost:3000**. API: **http://localhost:8000** — dokumentasi interaktif: **http://localhost:8000/docs**.

| Service | URL / catatan |
|---------|----------------|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| Flower (monitor Celery) | http://localhost:5555 — jalankan dengan `docker compose --profile monitoring up -d` |

**Setelah mengubah `.env`** (misalnya cookies atau model Groq), recreate container agar variabel terbaca:

```bash
docker compose up -d --force-recreate api worker
```

Image API memakai `uvicorn` **tanpa** `--reload` (hindari race dengan bind-mount). Setelah edit kode backend: `docker compose restart api`.

Redis di Compose dipetakan ke host **port 6380** → `6380:6379`. Service di dalam jaringan Docker memakai hostname `redis` dan port **6379**.

---

## Setup manual (tanpa Docker)

### Redis

```bash
# macOS: brew install redis && brew services start redis
# Ubuntu: sudo apt install redis-server && sudo systemctl start redis
# Atau: docker run -d -p 6379:6379 redis:7-alpine
```

Di `.env` untuk lokal: `REDIS_URL=redis://localhost:6379/0`, `OUTPUT_DIR=../data` (relatif dari folder `backend/` saat menjalankan uvicorn).

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env
uvicorn app.main:app --reload --port 8000
```

Terminal lain — worker:

```bash
cd backend && source .venv/bin/activate
celery -A app.core.celery_app worker --loglevel=info -Q pipeline -c 2
```

### Frontend

```bash
cd frontend
npm install
# Opsional: echo 'NEXT_PUBLIC_API_URL=http://localhost:8000' > .env.local
npm run dev
```

---

## Environment variables

Ringkasan (lengkap ada di `.env.example`):

| Variable | Keterangan |
|----------|------------|
| `DEBUG` | Mode debug FastAPI |
| `ALLOWED_ORIGINS` | CORS (JSON array string di `.env`) |
| `REDIS_URL` | Redis untuk Celery |
| `OUTPUT_DIR` | Video, audio, clip (`/data` di Docker) |
| `YTDLP_COOKIES_FILE` | Path **Netscape cookies.txt** jika YouTube meminta login / anti-bot ([wiki yt-dlp](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies)). Di Docker sering: `/data/youtube_cookies.txt` dengan file di `./data/` host |
| `GROQ_API_KEY` | Wajib untuk mode AI / hybrid |
| `GROQ_MODEL` | Default disarankan: `llama-3.3-70b-versatile` (TPM lebih longgar). `llama-3.1-8b-instant` punya TPM ~6K — mudah kena limit |
| `GROQ_TRANSCRIPT_MAX_CHARS` | Batas panjang transcript bertimestamp ke Groq (hindari error TPM) |
| `WHISPER_MODEL` | `tiny` / `base` / `small` / … |
| `MAX_VIDEO_DURATION_SECONDS` | Batas durasi proses (detik) |
| `DEFAULT_*` | Min durasi clip, max clips, threshold score pipeline |

---

## Cara pakai

### UI (http://localhost:3000)

1. Tempel URL YouTube.
2. Pilih mode: **AI** (Whisper + Groq), **Signal** (audio + scene), **Hybrid** (gabungan).
3. Opsional: **Advanced** — durasi, jumlah clip, threshold.
4. **Detect Highlights** — progress lewat SSE.
5. Setelah **selesai**, daftar clip (paginasi) dan panel export (JSON / timestamps sesuai implementasi UI).

### API

```bash
curl -X POST http://localhost:8000/api/process \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "settings": {
      "mode": "hybrid",
      "min_clip_duration": 10,
      "max_clips": 5,
      "score_threshold": 0.6
    }
  }'

curl -N http://localhost:8000/api/job/<job_id>/stream
curl http://localhost:8000/api/clips/<job_id>
```

- **409** pada `/api/clips/...` — job belum `done` (masih diproses).
- **422** — job `failed` (lihat pesan / log worker).

---

## Struktur repo

```
clipper-ai/
├── frontend/
│   └── src/
│       ├── app/
│       ├── components/
│       └── lib/                 # api client, types
├── backend/app/
│   ├── api/routes/              # process, job, clips
│   ├── core/                    # config, celery
│   ├── models/
│   ├── pipeline/
│   │   ├── downloader.py
│   │   ├── detect_types.py
│   │   ├── transcribe_whisper.py
│   │   ├── groq_highlights.py
│   │   ├── signal_detect.py
│   │   ├── hybrid_engine.py
│   │   └── clip_export.py
│   └── tasks/pipeline_task.py
├── data/                        # output (gitignored)
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Troubleshooting

| Masalah | Tindakan |
|---------|----------|
| YouTube: *Sign in to confirm you're not a bot* | Set `YTDLP_COOKIES_FILE` ke cookies Netscape yang valid, file bisa dibaca di container, lalu `docker compose up -d --force-recreate worker` |
| Groq **413** / *tokens per minute* / TPM | Kurangi `GROQ_TRANSCRIPT_MAX_CHARS` atau pakai model TPM lebih tinggi (`GROQ_MODEL`); tier Dev di Groq bila perlu |
| `Redis connection refused` | Pastikan Redis jalan; di Docker cek service `redis` dan `REDIS_URL` |
| Job stuck **PENDING** | Pastikan worker Celery jalan dengan queue `-Q pipeline` |
| Frontend tidak konek API | Set `NEXT_PUBLIC_API_URL` di `frontend/.env.local` ke URL API |
| `ffmpeg: command not found` | Install ffmpeg di host (di image Docker sudah ada) |

---

## Roadmap

- [x] Phase 1 — Setup, download, audio extract, job queue + SSE
- [x] Phase 2 — Whisper, Groq, signal, hybrid, clip export
- [ ] Phase 3 — Reel merged, thumbnails, history / share link

---

## License

MIT
