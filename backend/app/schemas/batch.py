from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
from app.models.batch import BatchStatus, ImageStatus

class BatchCreate(BaseModel):
    name: str
    target_languages: List[str] = ["zh-Hant", "en"]
    glossary_id: Optional[str] = None

class BatchResponse(BaseModel):
    id: str
    name: str
    status: BatchStatus
    total_images: int
    processed_images: int
    failed_images: int
    target_languages: List[str]
    glossary_id: Optional[str]
    avg_confidence: Optional[float]
    processing_time_seconds: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]
    class Config:
        from_attributes = True

class ImageJobResponse(BaseModel):
    id: str
    batch_id: str
    filename: str
    status: ImageStatus
    confidence_score: Optional[float]
    ocr_data: Optional[Any]
    translation_data: Optional[Any]
    manual_corrections: Optional[List[Any]]
    error_message: Optional[str]
    width: Optional[int]
    height: Optional[int]
    created_at: datetime
    class Config:
        from_attributes = True

class ManualCorrection(BaseModel):
    block_id: str
    language: str
    corrected_text: str
    add_to_glossary: bool = False

class GlossaryCreate(BaseModel):
    name: str
    description: Optional[str] = None

class GlossaryEntry(BaseModel):
    korean: str
    zh_hant: str
    english: str
    category: Optional[str] = None
    do_not_translate: bool = False

class GlossaryResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    entry_count: int
    created_at: datetime
    updated_at: Optional[datetime]
    class Config:
        from_attributes = True
