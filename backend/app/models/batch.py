from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid
from app.database import Base

def gen_uuid():
    return str(uuid.uuid4())

class BatchStatus(str, enum.Enum):
    QUEUED = "queued"
    PREPROCESSING = "preprocessing"
    OCR = "ocr"
    TRANSLATING = "translating"
    RECONSTRUCTING = "reconstructing"
    REVIEW_READY = "review_ready"
    EXPORTING = "exporting"
    COMPLETE = "complete"
    FAILED = "failed"

class ImageStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    HIGH_CONFIDENCE = "high_confidence"
    MEDIUM_CONFIDENCE = "medium_confidence"
    LOW_CONFIDENCE = "low_confidence"
    FLAGGED = "flagged"
    APPROVED = "approved"
    FAILED = "failed"

class Batch(Base):
    __tablename__ = "batches"
    
    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    status = Column(Enum(BatchStatus), default=BatchStatus.QUEUED)
    total_images = Column(Integer, default=0)
    processed_images = Column(Integer, default=0)
    failed_images = Column(Integer, default=0)
    target_languages = Column(JSON, default=["zh-Hant", "en"])
    glossary_id = Column(String, ForeignKey("glossaries.id"), nullable=True)
    avg_confidence = Column(Float, nullable=True)
    processing_time_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    images = relationship("ImageJob", back_populates="batch", cascade="all, delete-orphan")
    glossary = relationship("Glossary", back_populates="batches")

class ImageJob(Base):
    __tablename__ = "image_jobs"
    
    id = Column(String, primary_key=True, default=gen_uuid)
    batch_id = Column(String, ForeignKey("batches.id"), nullable=False)
    filename = Column(String, nullable=False)
    original_path = Column(String, nullable=False)
    output_path_zh_hant = Column(String, nullable=True)
    output_path_en = Column(String, nullable=True)
    status = Column(Enum(ImageStatus), default=ImageStatus.PENDING)
    confidence_score = Column(Float, nullable=True)
    ocr_data = Column(JSON, nullable=True)       # text blocks + bounding boxes
    translation_data = Column(JSON, nullable=True) # translations per block
    manual_corrections = Column(JSON, default=[])
    error_message = Column(Text, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    batch = relationship("Batch", back_populates="images")

class Glossary(Base):
    __tablename__ = "glossaries"
    
    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    entry_count = Column(Integer, default=0)
    entries = Column(JSON, default=[])  # [{korean, zh_hant, english, category, do_not_translate}]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    batches = relationship("Batch", back_populates="glossary")
