import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.batch import ImageJob

router = APIRouter(prefix="/api/images", tags=["images"])


@router.get("/{image_id}/original")
def serve_original(image_id: str, db: Session = Depends(get_db)):
    job = db.query(ImageJob).filter(ImageJob.id == image_id).first()
    if not job or not os.path.exists(job.original_path):
        raise HTTPException(404, "Image not found")
    return FileResponse(job.original_path)


@router.get("/{image_id}/output/{language}")
def serve_output(image_id: str, language: str, db: Session = Depends(get_db)):
    job = db.query(ImageJob).filter(ImageJob.id == image_id).first()
    if not job:
        raise HTTPException(404, "Image not found")
    
    path = job.output_path_zh_hant if language == "zh-Hant" else job.output_path_en
    if not path or not os.path.exists(path):
        raise HTTPException(404, f"Output for {language} not ready yet")
    
    return FileResponse(path)
