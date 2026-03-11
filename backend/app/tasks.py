"""
Celery tasks: orchestrate the full OCR → translate → reconstruct pipeline.
"""
import asyncio
import logging
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, "/app/processing")

from app.celery_app import celery_app
from app.config import settings

logger = logging.getLogger(__name__)


def get_db_session():
    from app.database import SessionLocal
    return SessionLocal()


@celery_app.task(bind=True, name="process_image")
def process_image_task(self, image_job_id: str):
    """Process a single image through the full pipeline."""
    from app.models.batch import ImageJob, ImageStatus, Batch, BatchStatus
    
    db = get_db_session()
    try:
        job = db.query(ImageJob).filter(ImageJob.id == image_job_id).first()
        if not job:
            logger.error(f"ImageJob {image_job_id} not found")
            return
        
        job.status = ImageStatus.PROCESSING
        db.commit()
        
        # --- Stage 1: OCR ---
        from processing.ocr.engine import extract_text_blocks
        logger.info(f"OCR: {job.filename}")
        ocr_result = extract_text_blocks(job.original_path)
        job.ocr_data = ocr_result
        job.width = ocr_result.get("image_width")
        job.height = ocr_result.get("image_height")
        db.commit()
        
        # --- Stage 2: Translation ---
        from processing.translation.engine import translate_blocks
        
        # Load glossary if set
        glossary_entries = []
        if job.batch and job.batch.glossary:
            glossary_entries = job.batch.glossary.entries or []
        
        # Get batch languages
        batch = db.query(Batch).filter(Batch.id == job.batch_id).first()
        target_languages = batch.target_languages if batch else ["zh-Hant", "en"]
        
        logger.info(f"Translating {len(ocr_result['blocks'])} blocks")
        translated_blocks = asyncio.run(translate_blocks(
            blocks=ocr_result["blocks"],
            target_languages=target_languages,
            glossary=glossary_entries,
            google_api_key=settings.google_translate_api_key,
            deepl_api_key=settings.deepl_api_key,
        ))
        job.translation_data = translated_blocks
        db.commit()
        
        # --- Stage 3: Reconstruction ---
        from processing.reconstruction.engine import reconstruct_image
        logger.info(f"Reconstructing image: {job.filename}")
        
        output_dir = os.path.join(settings.output_dir, job.batch_id)
        output_paths = reconstruct_image(
            original_path=job.original_path,
            blocks_with_translations=translated_blocks,
            output_dir=output_dir,
            target_languages=target_languages,
            job_id=job.id,
        )
        
        job.output_path_zh_hant = output_paths.get("zh-Hant")
        job.output_path_en = output_paths.get("en")
        
        # --- Compute overall confidence ---
        if translated_blocks:
            confs = [b.get("overall_confidence", 0) for b in translated_blocks]
            avg_conf = sum(confs) / len(confs)
        else:
            avg_conf = 0.0
        
        job.confidence_score = round(avg_conf * 100, 1)  # 0-100 scale
        
        if avg_conf >= 0.90:
            job.status = ImageStatus.HIGH_CONFIDENCE
        elif avg_conf >= 0.70:
            job.status = ImageStatus.MEDIUM_CONFIDENCE
        else:
            job.status = ImageStatus.LOW_CONFIDENCE
            
        db.commit()
        
        # Update batch progress
        _update_batch_progress(db, job.batch_id)
        logger.info(f"Completed image {job.filename} with confidence {job.confidence_score}")
        
    except Exception as e:
        logger.exception(f"Failed to process image {image_job_id}: {e}")
        job = db.query(ImageJob).filter(ImageJob.id == image_job_id).first()
        if job:
            from app.models.batch import ImageStatus
            job.status = ImageStatus.FAILED
            job.error_message = str(e)
            db.commit()
            _update_batch_progress(db, job.batch_id)
    finally:
        db.close()


def _update_batch_progress(db, batch_id: str):
    """Recompute and update batch-level stats."""
    from app.models.batch import Batch, BatchStatus, ImageJob, ImageStatus
    
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        return
    
    jobs = db.query(ImageJob).filter(ImageJob.batch_id == batch_id).all()
    total = len(jobs)
    done_statuses = {ImageStatus.HIGH_CONFIDENCE, ImageStatus.MEDIUM_CONFIDENCE, 
                     ImageStatus.LOW_CONFIDENCE, ImageStatus.FAILED, ImageStatus.APPROVED}
    
    processed = sum(1 for j in jobs if j.status in done_statuses)
    failed = sum(1 for j in jobs if j.status == ImageStatus.FAILED)
    
    batch.processed_images = processed
    batch.failed_images = failed
    
    conf_scores = [j.confidence_score for j in jobs if j.confidence_score is not None]
    if conf_scores:
        batch.avg_confidence = round(sum(conf_scores) / len(conf_scores), 1)
    
    if processed == total:
        batch.status = BatchStatus.REVIEW_READY
        batch.completed_at = datetime.utcnow()
    
    db.commit()
