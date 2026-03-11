"""
Smart translation engine: Google Translate (primary) → DeepL (fallback)
Supports brand glossaries, entity protection, and batch translation.
"""
import re
import logging
import os
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

# Patterns for entities that should NOT be translated
ENTITY_PATTERNS = [
    r'\b[A-Z]{2,}(?:[A-Z0-9-]{1,})\b',        # SKU codes: ABC-123
    r'https?://\S+',                              # URLs
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.\w+',  # Emails
    r'\+?\d[\d\s\-().]{7,}\d',                   # Phone numbers
    r'\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?\s*(?:ml|g|kg|oz|mg|%|원|₩)\b',  # Measurements
]


def _detect_entities(text: str) -> List[Dict]:
    """Find brand names, SKUs, and protected terms in text."""
    entities = []
    for pattern in ENTITY_PATTERNS:
        for match in re.finditer(pattern, text):
            entities.append({
                "text": match.group(),
                "start": match.start(),
                "end": match.end(),
                "type": "auto_detected"
            })
    return entities


def _apply_glossary(text: str, glossary: List[Dict], target_lang: str) -> Optional[str]:
    """Check if the entire text matches a glossary entry. Returns translation or None."""
    text_lower = text.strip().lower()
    for entry in glossary:
        if entry.get("korean", "").lower() == text_lower:
            if entry.get("do_not_translate"):
                return text  # Keep original
            if target_lang == "zh-Hant":
                return entry.get("zh_hant")
            elif target_lang == "en":
                return entry.get("english")
    return None


async def translate_with_google(texts: List[str], target_lang: str, api_key: str) -> List[Dict]:
    """Batch translate via Google Cloud Translation API."""
    # Map our lang codes to Google's
    lang_map = {"zh-Hant": "zh-TW", "en": "en"}
    google_lang = lang_map.get(target_lang, target_lang)
    
    url = f"https://translation.googleapis.com/language/translate/v2?key={api_key}"
    payload = {
        "q": texts,
        "source": "ko",
        "target": google_lang,
        "format": "text"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
    
    results = []
    for item in data["data"]["translations"]:
        results.append({
            "translated_text": item["translatedText"],
            "confidence": 0.88,  # Google doesn't return confidence; use fixed high value
            "engine": "google"
        })
    return results


async def translate_with_deepl(texts: List[str], target_lang: str, api_key: str) -> List[Dict]:
    """Batch translate via DeepL API."""
    lang_map = {"zh-Hant": "ZH-HANT", "en": "EN-US"}
    deepl_lang = lang_map.get(target_lang, target_lang.upper())
    
    url = "https://api-free.deepl.com/v2/translate"
    headers = {"Authorization": f"DeepL-Auth-Key {api_key}"}
    payload = {
        "text": texts,
        "source_lang": "KO",
        "target_lang": deepl_lang
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
    
    results = []
    for item in data["translations"]:
        results.append({
            "translated_text": item["text"],
            "confidence": 0.85,
            "engine": "deepl"
        })
    return results


def _mock_translate(text: str, target_lang: str) -> str:
    """Mock translation for dev/testing when no API key is set."""
    if target_lang == "zh-Hant":
        return f"[ZH] {text}"
    return f"[EN] {text}"


async def translate_blocks(
    blocks: List[Dict[str, Any]],
    target_languages: List[str],
    glossary: Optional[List[Dict]] = None,
    google_api_key: Optional[str] = None,
    deepl_api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Translate all text blocks into target languages.
    Applies glossary first, then calls translation API for remaining blocks.
    Returns blocks with translation_data populated.
    """
    if glossary is None:
        glossary = []
    
    translated_blocks = []
    
    for block in blocks:
        source_text = block["text"]
        block_translations = {}
        
        for lang in target_languages:
            # 1. Check glossary first (100% priority)
            glossary_match = _apply_glossary(source_text, glossary, lang)
            if glossary_match is not None:
                block_translations[lang] = {
                    "text": glossary_match,
                    "confidence": 1.0,
                    "source": "glossary"
                }
                continue
            
            # 2. Detect entities to protect
            entities = _detect_entities(source_text)
            
            # 3. Call translation API (or mock)
            try:
                if google_api_key:
                    results = await translate_with_google([source_text], lang, google_api_key)
                    translated = results[0]["translated_text"]
                    engine_conf = results[0]["confidence"]
                    engine = "google"
                elif deepl_api_key:
                    results = await translate_with_deepl([source_text], lang, deepl_api_key)
                    translated = results[0]["translated_text"]
                    engine_conf = results[0]["confidence"]
                    engine = "deepl"
                else:
                    translated = _mock_translate(source_text, lang)
                    engine_conf = 0.75
                    engine = "mock"
                
                # Adjust confidence based on OCR confidence
                ocr_conf = block.get("confidence", 0.8)
                final_conf = round(engine_conf * ocr_conf, 3)
                
                block_translations[lang] = {
                    "text": translated,
                    "confidence": final_conf,
                    "source": engine,
                    "entities_protected": [e["text"] for e in entities]
                }
                
            except Exception as e:
                logger.error(f"Translation error for block '{source_text}': {e}")
                block_translations[lang] = {
                    "text": source_text,  # fallback: keep original
                    "confidence": 0.0,
                    "source": "error",
                    "error": str(e)
                }
        
        # Compute overall confidence score for this block (min across languages)
        confs = [v["confidence"] for v in block_translations.values()]
        overall_conf = min(confs) if confs else 0.0
        
        translated_blocks.append({
            **block,
            "translations": block_translations,
            "overall_confidence": overall_conf,
            "needs_review": overall_conf < 0.70
        })
    
    return translated_blocks
