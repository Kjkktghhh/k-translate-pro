# K-Translate Pro

**Korean image localization platform** — OCR → Translation → Image Reconstruction

Automates extraction of Korean text from product images, translates to Traditional Chinese and English, and reconstructs visually identical images with translated text.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | [FastAPI](https://fastapi.tiangolo.com/) (Python) — REST API served by Uvicorn |
| **ORM / Database** | SQLAlchemy 2.0 + PostgreSQL 15 |
| **Task Queue** | Celery 5.4 + Redis 7 |
| **Frontend** | React 18 + Vite + Tailwind CSS |
| **OCR** | PaddleOCR v2.7 (primary), EasyOCR (fallback) |
| **Translation** | Google Translate API / DeepL API (mock mode available) |
| **Image Processing** | OpenCV (inpainting) + Pillow (text rendering) |
| **Deployment** | Docker Compose |

---

## Quick Start (Local Dev)

### Prerequisites
- Docker Desktop installed and running
- 8 GB RAM recommended (OCR models are memory-hungry)

### 1. Clone and configure

```bash
git clone <repo>
cd k-translate-pro
cp .env.example .env
```

Edit `.env` to add API keys (optional — the system runs with mock translations without them):

```env
GOOGLE_TRANSLATE_API_KEY=your_key_here   # or leave blank for mock mode
DEEPL_API_KEY=your_key_here              # optional fallback
```

### 2. Start everything

```bash
docker compose up --build
```

This starts:
- **Frontend** → http://localhost:3000
- **Backend API** → http://localhost:8000
- **API Docs** → http://localhost:8000/docs
- **Worker** (Celery background processor)
- **Redis** (job queue)
- **PostgreSQL** (metadata storage)

First run takes 5–10 minutes (PaddleOCR model download ~1 GB).

---

## Architecture

```
┌─────────────────┐    ┌──────────────────────────────────────────┐
│  React Frontend │───▶│              FastAPI Backend              │
│  (port 3000)    │    │  (port 8000)                              │
└─────────────────┘    └───────────┬──────────────────────────────┘
                                   │ enqueue tasks
                                   ▼
                        ┌──────────────────────┐
                        │   Celery Worker       │
                        │                       │
                        │  1. PaddleOCR         │
                        │     ↓ fallback        │
                        │  2. EasyOCR           │
                        │     ↓                 │
                        │  3. Google/DeepL      │
                        │     (or mock)         │
                        │     ↓                 │
                        │  4. OpenCV Inpaint    │
                        │     ↓                 │
                        │  5. Pillow Re-render  │
                        └──────────────────────┘
```

## Pipeline Stages

| Stage | Engine | Notes |
|-------|--------|-------|
| OCR | PaddleOCR v2.7 | Korean language model, returns bounding polygons |
| OCR Fallback | EasyOCR | Triggered when confidence < 70% |
| Translation | Google Translate | With glossary enforcement |
| Translation Fallback | DeepL | If Google fails or unavailable |
| Mock Mode | Built-in | When no API keys — prepends [ZH]/[EN] for testing |
| Inpainting | OpenCV TELEA | Removes original text, reconstructs background |
| Rendering | Pillow | Re-renders translated text matching original font size/color |

## API Endpoints

```
POST   /api/batches/                    Create batch + upload images
GET    /api/batches/                    List all batches
GET    /api/batches/{id}                Get batch status
GET    /api/batches/{id}/images         Get images (with filter)
PATCH  /api/batches/{id}/images/{id}/correct  Apply manual correction
GET    /api/batches/{id}/export         Download ZIP

POST   /api/glossaries/                 Create glossary
GET    /api/glossaries/                 List glossaries
POST   /api/glossaries/{id}/entries    Add term
POST   /api/glossaries/{id}/upload-csv Import CSV

GET    /api/images/{id}/original        Serve original image
GET    /api/images/{id}/output/{lang}   Serve translated image
```

## Glossary CSV Format

```csv
Korean,zh-Hant,English,Category,DoNotTranslate
세럼,精華液,Serum,skincare,N
히알루론산,玻尿酸,Hyaluronic Acid,ingredient,N
SPF50+,SPF50+,SPF50+,label,Y
```

## Folder Structure

```
k-translate-pro/
├── docker-compose.yml
├── .env                     ← your API keys go here
├── frontend/                ← React + Vite + Tailwind
│   └── src/
│       ├── pages/           ← Dashboard, NewBatch, BatchDetail, Glossaries
│       └── lib/api.js       ← API client
├── backend/                 ← FastAPI
│   └── app/
│       ├── main.py
│       ├── tasks.py         ← Celery pipeline orchestration
│       ├── routers/         ← batches, glossaries, images
│       ├── models/          ← SQLAlchemy models
│       └── schemas/         ← Pydantic schemas
└── processing/              ← Core ML pipeline
    ├── ocr/engine.py        ← Multi-engine OCR
    ├── translation/engine.py← Google/DeepL/mock
    └── reconstruction/engine.py ← Inpaint + re-render
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_TRANSLATE_API_KEY` | — | Google Cloud Translation API key |
| `DEEPL_API_KEY` | — | DeepL API key (fallback) |
| `MAX_BATCH_SIZE` | 500 | Max images per batch |
| `MAX_FILE_SIZE_MB` | 25 | Max size per image |
| `IMAGE_RETENTION_DAYS` | 90 | Auto-delete after N days |

## Upgrading to Stable Diffusion Inpainting

The MVP uses OpenCV TELEA inpainting (fast, no GPU needed). For production quality with complex backgrounds, replace `inpaint_text_regions()` in `processing/reconstruction/engine.py` with a Stable Diffusion inpainting call. The function signature stays the same.

## Adding Languages

1. Add language code to `FONT_PATHS` in `reconstruction/engine.py`
2. Add to the `LANGUAGES` array in `frontend/src/pages/NewBatch.jsx`
3. Add language mapping in `translation/engine.py` (`lang_map` dicts)

---

## Quick Single-Image Translation (No Docker)

For translating individual images right now without the full stack:

```bash
pip install pillow numpy
python processing/reconstruction/pixel_translate.py \
  --input your_image.png \
  --output translated.jpg
```

Edit the `DEFAULT_TRANSLATIONS` list in `pixel_translate.py` to define your text regions:

```python
DEFAULT_TRANSLATIONS = [
    dict(
        y1=860, y2=909,   # exact pixel bounding box (measure with the scan utils)
        x1=191, x2=549,
        text="補水鎖水 & 全效修護",   # your translated text
        font="bold",               # "bold" or "regular"
        target_size=44,            # font size in px (shrinks to fit if needed)
        color=(255, 255, 255),     # text color RGB
    ),
    ...
]
```

To measure bounding boxes from a new image, run the built-in scanner:

```python
from processing.reconstruction.pixel_translate import scan_text_blocks
from PIL import Image
import numpy as np

arr = np.array(Image.open("your_image.png").convert("RGB"))
blocks = scan_text_blocks(arr)
for b in blocks:
    y1, y2, x1, x2 = b
    print(f"y={y1}–{y2} (h={y2-y1}px)  x={x1}–{x2} (w={x2-x1}px)")
```
