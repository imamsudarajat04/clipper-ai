# Clipper AI 🎬✂️

**Auto highlight detection dari video YouTube** menggunakan AI (Whisper + Groq LLM) dan signal analysis (PyDub + OpenCV).

---

## ✨ Fitur

| Fase | Fitur |
|------|-------|
| **Phase 1** ✅ | Download video, ekstrak audio, job queue real-time |
| **Phase 2** 🔜 | Transkripsi Whisper, analisis Groq LLM, signal detection |
| **Phase 3** 🔜 | Export clips, merged reel, share link |

---

## 🧱 Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 14, Tailwind CSS, TypeScript |
| Backend | FastAPI (Python 3.11+) |
| Queue | Celery + Redis |
| Download | yt-dlp |
| Audio | ffmpeg |
| AI | Whisper (local) + Groq API (LLaMA 3) |
| Signal | PyDub + OpenCV |

---

## 📋 Prerequisites

Pastikan semua tool berikut sudah terinstall:

- **Python** ≥ 3.11 → [python.org](https://python.org)
- **Node.js** ≥ 18 → [nodejs.org](https://nodejs.org)
- **Docker & Docker Compose** → [docker.com](https://docker.com)
- **ffmpeg** (untuk setup manual)
  ```bash
  # macOS
  brew install ffmpeg
  
  # Ubuntu/Debian
  sudo apt install ffmpeg
  
  # Windows (via Chocolatey)
  choco install ffmpeg
  ```
- **Git**

---

## 🚀 Quick Start (Docker — Direkomendasikan)

Cara paling mudah: satu command langsung semua jalan.

```bash
# 1. Clone repo
git clone <repo-url>
cd clipper-ai

# 2. Setup environment
cp .env.example .env
# Edit .env jika perlu (GROQ_API_KEY untuk Phase 2)

# 3. Jalankan semua service
docker compose up --build

# 4. Jalankan frontend (terminal baru)
cd frontend
npm install
npm run dev
```

Buka browser di **http://localhost:3000** 🎉

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Flower (monitoring) | http://localhost:5555 *(profile: monitoring)* |

---

## 🛠 Manual Setup (Tanpa Docker)

### 1. Redis

```bash
# macOS
brew install redis
brew services start redis

# Ubuntu
sudo apt install redis-server
sudo systemctl start redis

# Windows — gunakan WSL atau Docker:
docker run -d -p 6379:6379 redis:7-alpine
```

### 2. Backend

```bash
cd backend

# Buat virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp ../.env.example ../.env
# Edit .env, set OUTPUT_DIR=../data dan REDIS_URL=redis://localhost:6379/0

# Jalankan API server
uvicorn app.main:app --reload --port 8000

# Terminal baru — jalankan Celery worker
source .venv/bin/activate
celery -A app.core.celery_app worker --loglevel=info -Q pipeline -c 2
```

### 3. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Jalankan dev server
npm run dev
```

---

## ⚙️ Environment Variables

Semua variabel ada di `.env.example`. Salin ke `.env` lalu sesuaikan:

| Variable | Default | Keterangan |
|----------|---------|-----------|
| `DEBUG` | `false` | Mode debug FastAPI |
| `REDIS_URL` | `redis://localhost:6379/0` | URL koneksi Redis |
| `OUTPUT_DIR` | `../data` | Direktori output video/audio/clips |
| `GROQ_API_KEY` | *(kosong)* | API key Groq — [dapatkan di sini](https://console.groq.com) |
| `WHISPER_MODEL` | `base` | Model Whisper: `tiny`/`base`/`small`/`medium` |
| `MAX_VIDEO_DURATION_SECONDS` | `3600` | Batas durasi video (detik) |
| `DEFAULT_MIN_CLIP_DURATION` | `10` | Durasi minimum clip (detik) |
| `DEFAULT_MAX_CLIPS` | `10` | Jumlah maksimum clip |
| `DEFAULT_SCORE_THRESHOLD` | `0.5` | Minimum confidence score |

---

## 📖 Cara Pakai

### Via UI (http://localhost:3000)

1. **Paste URL YouTube** di input box kiri
2. **Pilih mode deteksi:**
   - 🤖 **AI** — transkripsi Whisper → analisis Groq LLM
   - 📊 **Signal** — deteksi audio peak + scene change
   - ⚡ **Hybrid** — kombinasi AI + Signal (default)
3. *(Opsional)* Buka **Advanced Settings** untuk atur durasi, jumlah clip, threshold
4. Klik **Detect Highlights** → lihat progress real-time di panel bawah
5. Setelah selesai, hasil clips muncul di panel kanan (3 per halaman)
6. **Export:** download JSON, timestamps .txt, atau copy share link

### Via API (curl)

```bash
# Submit video
curl -X POST http://localhost:8000/api/process \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "settings": {
      "mode": "hybrid",
      "min_clip_duration": 10,
      "max_clips": 5,
      "score_threshold": 0.6,
      "auto_trim_silence": true,
      "output_format": "mp4"
    }
  }'
# Response: { "job_id": "abc-123", "status": "pending", ... }

# Poll status
curl http://localhost:8000/api/job/abc-123

# Stream progress (SSE)
curl -N http://localhost:8000/api/job/abc-123/stream

# Get clips (setelah status = done)
curl http://localhost:8000/api/clips/abc-123
```

---

## 🏗 Struktur Folder

```
clipper-ai/
├── frontend/                   # Next.js 14
│   └── src/
│       ├── app/                # App Router pages
│       ├── components/         # UI components
│       ├── hooks/              # useJobSSE
│       └── lib/                # API client + types
├── backend/                    # FastAPI
│   └── app/
│       ├── api/routes/         # process, jobs, clips
│       ├── core/               # config, celery
│       ├── models/             # Pydantic models
│       ├── pipeline/           # downloader, audio, (Phase 2: whisper, groq, signal)
│       └── tasks/              # Celery task
├── data/                       # Output files (gitignored)
│   ├── videos/
│   ├── audio/
│   └── clips/
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🔧 Troubleshooting

### `yt-dlp` error: `Video unavailable`
- Video mungkin di-private atau geo-blocked
- Coba update yt-dlp: `pip install -U yt-dlp`

### `ffmpeg: command not found`
- Install ffmpeg (lihat Prerequisites di atas)
- Jika pakai Docker, ffmpeg sudah termasuk di image

### `Redis connection refused`
- Pastikan Redis running: `redis-cli ping` → harus balas `PONG`
- Cek `REDIS_URL` di `.env`

### `Job stuck di PENDING`
- Celery worker belum berjalan
- Cek apakah worker bisa konek ke Redis: lihat log worker

### Worker tidak terima task
- Pastikan queue-nya sama: worker pakai `-Q pipeline`, task dikirim ke queue `pipeline`

### Frontend tidak bisa konek ke backend
- Cek `NEXT_PUBLIC_API_URL` di `frontend/.env.local`
- Pastikan backend running di port 8000

---

## 🗺 Roadmap

- [x] **Phase 1** — Project setup, yt-dlp download, ffmpeg audio extract, job queue
- [ ] **Phase 2** — Whisper transcription, Groq LLM analysis, PyDub + OpenCV signal detection
- [ ] **Phase 3** — ffmpeg clip cutting, merged reel export, thumbnail generation, history page

---

## 📄 License

MIT
