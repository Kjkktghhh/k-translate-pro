from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.routers import batches, glossaries, images

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="K-Translate Pro API",
    description="Korean image localization platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(batches.router)
app.include_router(glossaries.router)
app.include_router(images.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "K-Translate Pro"}


@app.get("/api/stats")
def get_stats(db=None):
    from app.database import SessionLocal
    from app.models.batch import Batch, ImageJob, BatchStatus
    db = SessionLocal()
    try:
        total_batches = db.query(Batch).count()
        total_images = db.query(ImageJob).count()
        completed = db.query(Batch).filter(Batch.status == BatchStatus.COMPLETE).count()
        return {
            "total_batches": total_batches,
            "total_images": total_images,
            "completed_batches": completed,
        }
    finally:
        db.close()
