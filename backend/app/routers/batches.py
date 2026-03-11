import os
import shutil
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.batch import Batch, BatchStatus, ImageJob, ImageStatus
from app.schemas.batch import BatchCreate, BatchResponse, ImageJobResponse, ManualCorrection
from app.config import settings

router = APIRouter(prefix="/api/batches", tags=["batches"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp", ".gif"}


@router.post("/", response_model=BatchResponse)
async def create_batch(
    name: str = Form(...),
    target_languages: str = Form('["zh-Hant","en"]'),
    glossary_id: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Create a new batch job and upload images."""
    import json
    langs = json.loads(target_languages)
    
    # Validate files
    valid_files = []
    for f in files:
        ext = os.path.splitext(f.filename or "")[1].lower()
        if ext in ALLOWED_EXTENSIONS:
            valid_files.append(f)
    
    if not valid_files:
        raise HTTPException(400, "No valid image files provided")
    if len(valid_files) > settings.max_batch_size:
        raise HTTPException(400, f"Max batch size is {settings.max_batch_size} images")
    
    # Create batch record
    batch = Batch(
        id=str(uuid.uuid4()),
        name=name,
        target_languages=langs,
        glossary_id=glossary_id,
        total_images=len(valid_files),
        status=BatchStatus.QUEUED,
    )
    db.add(batch)
    db.flush()
    
    # Save files and create image job records
    upload_dir = os.path.join(settings.upload_dir, batch.id)
    os.makedirs(upload_dir, exist_ok=True)
    
    for f in valid_files:
        file_id = str(uuid.uuid4())
        ext = os.path.splitext(f.filename or "image")[1].lower()
        saved_path = os.path.join(upload_dir, f"{file_id}{ext}")
        
        content = await f.read()
        with open(saved_path, "wb") as out:
            out.write(content)
        
        job = ImageJob(
            id=file_id,
            batch_id=batch.id,
            filename=f.filename,
            original_path=saved_path,
            status=ImageStatus.PENDING,
        )
        db.add(job)
    
    db.commit()
    db.refresh(batch)
    
    # Enqueue processing tasks
    from app.tasks import process_image_task
    jobs = db.query(ImageJob).filter(ImageJob.batch_id == batch.id).all()
    batch.status = BatchStatus.OCR
    db.commit()
    
    for job in jobs:
        process_image_task.delay(job.id)
    
    return batch


@router.get("/", response_model=List[BatchResponse])
def list_batches(db: Session = Depends(get_db)):
    return db.query(Batch).order_by(Batch.created_at.desc()).limit(50).all()


@router.get("/{batch_id}", response_model=BatchResponse)
def get_batch(batch_id: str, db: Session = Depends(get_db)):
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Batch not found")
    return batch


@router.get("/{batch_id}/images", response_model=List[ImageJobResponse])
def get_batch_images(
    batch_id: str,
    filter: Optional[str] = None,  # all|high|medium|low|flagged
    db: Session = Depends(get_db)
):
    query = db.query(ImageJob).filter(ImageJob.batch_id == batch_id)
    
    if filter == "high":
        query = query.filter(ImageJob.status == ImageStatus.HIGH_CONFIDENCE)
    elif filter == "medium":
        query = query.filter(ImageJob.status == ImageStatus.MEDIUM_CONFIDENCE)
    elif filter == "low":
        query = query.filter(ImageJob.status == ImageStatus.LOW_CONFIDENCE)
    elif filter == "flagged":
        query = query.filter(ImageJob.status == ImageStatus.FLAGGED)
    
    return query.all()


@router.patch("/{batch_id}/images/{image_id}/correct")
def apply_correction(
    batch_id: str,
    image_id: str,
    correction: ManualCorrection,
    db: Session = Depends(get_db)
):
    """Apply a manual translation correction to an image block."""
    job = db.query(ImageJob).filter(
        ImageJob.id == image_id,
        ImageJob.batch_id == batch_id
    ).first()
    if not job:
        raise HTTPException(404, "Image job not found")
    
    # Update translation data
    if job.translation_data:
        for block in job.translation_data:
            if block.get("id") == correction.block_id:
                if "translations" not in block:
                    block["translations"] = {}
                block["translations"][correction.language] = {
                    "text": correction.corrected_text,
                    "confidence": 1.0,
                    "source": "manual"
                }
        
        corrections = job.manual_corrections or []
        corrections.append(correction.dict())
        job.manual_corrections = corrections
        db.commit()
        
        # Re-trigger reconstruction for this image
        from app.tasks import process_image_task
        process_image_task.delay(job.id)
    
    return {"status": "correction applied"}


@router.post("/{batch_id}/images/{image_id}/approve")
def approve_image(batch_id: str, image_id: str, db: Session = Depends(get_db)):
    job = db.query(ImageJob).filter(
        ImageJob.id == image_id, ImageJob.batch_id == batch_id
    ).first()
    if not job:
        raise HTTPException(404, "Not found")
    job.status = ImageStatus.APPROVED
    db.commit()
    return {"status": "approved"}


@router.get("/{batch_id}/export")
def export_batch(batch_id: str, db: Session = Depends(get_db)):
    """Create a ZIP of all translated images + metadata JSON."""
    import zipfile
    import json
    import tempfile
    from fastapi.responses import FileResponse
    
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Batch not found")
    
    jobs = db.query(ImageJob).filter(ImageJob.batch_id == batch_id).all()
    
    tmp = tempfile.mktemp(suffix=".zip")
    metadata = []
    
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
        for job in jobs:
            if job.output_path_zh_hant and os.path.exists(job.output_path_zh_hant):
                zf.write(job.output_path_zh_hant, f"zh-Hant/{job.filename}")
            if job.output_path_en and os.path.exists(job.output_path_en):
                zf.write(job.output_path_en, f"en/{job.filename}")
            
            metadata.append({
                "filename": job.filename,
                "status": job.status,
                "confidence_score": job.confidence_score,
                "ocr_blocks": len(job.ocr_data.get("blocks", [])) if job.ocr_data else 0,
                "translations": job.translation_data,
                "manual_corrections": job.manual_corrections,
            })
        
        zf.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2))
    
    return FileResponse(tmp, filename=f"batch_{batch_id[:8]}_translated.zip", media_type="application/zip")
