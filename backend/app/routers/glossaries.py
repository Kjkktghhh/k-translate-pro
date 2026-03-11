import uuid
import csv
import io
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.batch import Glossary
from app.schemas.batch import GlossaryCreate, GlossaryResponse, GlossaryEntry

router = APIRouter(prefix="/api/glossaries", tags=["glossaries"])


@router.post("/", response_model=GlossaryResponse)
def create_glossary(data: GlossaryCreate, db: Session = Depends(get_db)):
    g = Glossary(id=str(uuid.uuid4()), name=data.name, description=data.description, entries=[])
    db.add(g)
    db.commit()
    db.refresh(g)
    return g


@router.get("/", response_model=List[GlossaryResponse])
def list_glossaries(db: Session = Depends(get_db)):
    return db.query(Glossary).order_by(Glossary.created_at.desc()).all()


@router.get("/{glossary_id}", response_model=GlossaryResponse)
def get_glossary(glossary_id: str, db: Session = Depends(get_db)):
    g = db.query(Glossary).filter(Glossary.id == glossary_id).first()
    if not g:
        raise HTTPException(404, "Glossary not found")
    return g


@router.get("/{glossary_id}/entries")
def get_entries(glossary_id: str, db: Session = Depends(get_db)):
    g = db.query(Glossary).filter(Glossary.id == glossary_id).first()
    if not g:
        raise HTTPException(404, "Not found")
    return g.entries or []


@router.post("/{glossary_id}/entries")
def add_entry(glossary_id: str, entry: GlossaryEntry, db: Session = Depends(get_db)):
    g = db.query(Glossary).filter(Glossary.id == glossary_id).first()
    if not g:
        raise HTTPException(404, "Not found")
    
    entries = list(g.entries or [])
    entries.append(entry.dict())
    g.entries = entries
    g.entry_count = len(entries)
    db.commit()
    return {"status": "added", "entry_count": g.entry_count}


@router.post("/{glossary_id}/upload-csv")
async def upload_csv(glossary_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a CSV with columns: Korean | zh-Hant | English | Category | DoNotTranslate"""
    g = db.query(Glossary).filter(Glossary.id == glossary_id).first()
    if not g:
        raise HTTPException(404, "Not found")
    
    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    
    entries = list(g.entries or [])
    added = 0
    
    for row in reader:
        # Support various column name conventions
        korean = row.get("Korean") or row.get("korean") or row.get("KO") or ""
        zh_hant = row.get("zh-Hant") or row.get("ZH_HANT") or row.get("Chinese") or ""
        english = row.get("English") or row.get("EN") or row.get("english") or ""
        category = row.get("Category") or row.get("category") or ""
        dnt = row.get("DoNotTranslate") or row.get("do_not_translate") or "N"
        
        if korean:
            entries.append({
                "korean": korean.strip(),
                "zh_hant": zh_hant.strip(),
                "english": english.strip(),
                "category": category.strip(),
                "do_not_translate": dnt.strip().upper() in ("Y", "YES", "TRUE", "1")
            })
            added += 1
    
    g.entries = entries
    g.entry_count = len(entries)
    db.commit()
    
    return {"status": "imported", "added": added, "total": g.entry_count}


@router.delete("/{glossary_id}")
def delete_glossary(glossary_id: str, db: Session = Depends(get_db)):
    g = db.query(Glossary).filter(Glossary.id == glossary_id).first()
    if not g:
        raise HTTPException(404, "Not found")
    db.delete(g)
    db.commit()
    return {"status": "deleted"}
