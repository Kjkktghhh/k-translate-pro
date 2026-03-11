"""
Multi-engine OCR system: PaddleOCR (primary) → EasyOCR (fallback) → Tesseract (tertiary)
Returns structured text blocks with bounding polygons and confidence scores.
"""
import os
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from PIL import Image
import cv2

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.70


def preprocess_image(image_path: str) -> np.ndarray:
    """Preprocess image: denoise, enhance contrast, fix skew."""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Cannot read image: {image_path}")
    
    # Convert to RGB for processing
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Gentle contrast enhancement
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    enhanced = cv2.merge([cl, a, b])
    enhanced_rgb = cv2.cvtColor(cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR), cv2.COLOR_BGR2RGB)
    
    return enhanced_rgb


def run_paddle_ocr(image_path: str) -> List[Dict[str, Any]]:
    """Run PaddleOCR and return text blocks."""
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_angle_cls=True, lang='korean', show_log=False)
        result = ocr.ocr(image_path, cls=True)
        
        blocks = []
        if result and result[0]:
            for idx, line in enumerate(result[0]):
                polygon, (text, confidence) = line
                if text.strip():
                    blocks.append({
                        "id": f"paddle_{idx}",
                        "text": text.strip(),
                        "confidence": float(confidence),
                        "polygon": polygon,  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                        "engine": "paddleocr",
                        "bbox": _polygon_to_bbox(polygon)
                    })
        return blocks
    except Exception as e:
        logger.warning(f"PaddleOCR failed: {e}")
        return []


def run_easyocr(image_path: str) -> List[Dict[str, Any]]:
    """Run EasyOCR as fallback."""
    try:
        import easyocr
        reader = easyocr.Reader(['ko', 'en'], gpu=False, verbose=False)
        result = reader.readtext(image_path)
        
        blocks = []
        for idx, (polygon, text, confidence) in enumerate(result):
            if text.strip():
                blocks.append({
                    "id": f"easy_{idx}",
                    "text": text.strip(),
                    "confidence": float(confidence),
                    "polygon": polygon,
                    "engine": "easyocr",
                    "bbox": _polygon_to_bbox(polygon)
                })
        return blocks
    except Exception as e:
        logger.warning(f"EasyOCR failed: {e}")
        return []


def _polygon_to_bbox(polygon) -> Dict[str, int]:
    """Convert polygon points to bounding box."""
    pts = np.array(polygon, dtype=int)
    x, y, w, h = cv2.boundingRect(pts)
    return {"x": int(x), "y": int(y), "w": int(w), "h": int(h)}


def _merge_blocks(paddle_blocks: List, easy_blocks: List) -> List[Dict[str, Any]]:
    """
    Merge results from multiple engines:
    - Use PaddleOCR by default
    - For low-confidence paddle blocks, check if EasyOCR found the same region
      with higher confidence and use that instead
    """
    if not paddle_blocks:
        return easy_blocks
    if not easy_blocks:
        return paddle_blocks
    
    merged = []
    for pb in paddle_blocks:
        if pb["confidence"] >= CONFIDENCE_THRESHOLD:
            merged.append(pb)
            continue
        
        # Find overlapping EasyOCR block
        best_easy = None
        best_iou = 0.3  # minimum overlap threshold
        for eb in easy_blocks:
            iou = _bbox_iou(pb["bbox"], eb["bbox"])
            if iou > best_iou and eb["confidence"] > pb["confidence"]:
                best_iou = iou
                best_easy = eb
        
        if best_easy:
            logger.debug(f"Replacing low-confidence paddle block with easyocr: '{pb['text']}' → '{best_easy['text']}'")
            merged.append({**best_easy, "id": pb["id"]})
        else:
            merged.append(pb)
    
    return merged


def _bbox_iou(a: Dict, b: Dict) -> float:
    """Intersection over Union for two bboxes."""
    ax1, ay1 = a["x"], a["y"]
    ax2, ay2 = a["x"] + a["w"], a["y"] + a["h"]
    bx1, by1 = b["x"], b["y"]
    bx2, by2 = b["x"] + b["w"], b["y"] + b["h"]
    
    inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
    inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
    
    if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
        return 0.0
    
    inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
    a_area = a["w"] * a["h"]
    b_area = b["w"] * b["h"]
    union_area = a_area + b_area - inter_area
    
    return inter_area / union_area if union_area > 0 else 0.0


def extract_text_blocks(image_path: str) -> Dict[str, Any]:
    """
    Main entry: extract all text from image using multi-engine approach.
    Returns structured result with blocks and metadata.
    """
    logger.info(f"Starting OCR on {image_path}")
    
    # Get image dimensions
    img = Image.open(image_path)
    width, height = img.size
    
    # Run primary engine
    paddle_blocks = run_paddle_ocr(image_path)
    logger.info(f"PaddleOCR found {len(paddle_blocks)} blocks")
    
    # Check if any blocks are low-confidence → run fallback
    low_conf = [b for b in paddle_blocks if b["confidence"] < CONFIDENCE_THRESHOLD]
    easy_blocks = []
    if low_conf or not paddle_blocks:
        logger.info(f"{len(low_conf)} low-confidence blocks, running EasyOCR fallback")
        easy_blocks = run_easyocr(image_path)
    
    # Merge
    final_blocks = _merge_blocks(paddle_blocks, easy_blocks)
    
    # Sort blocks by reading order (top-to-bottom, left-to-right)
    final_blocks.sort(key=lambda b: (b["bbox"]["y"] // 50, b["bbox"]["x"]))
    
    # Annotate confidence tiers
    for block in final_blocks:
        c = block["confidence"]
        block["confidence_tier"] = "high" if c >= 0.9 else "medium" if c >= 0.7 else "low"
    
    avg_confidence = (
        sum(b["confidence"] for b in final_blocks) / len(final_blocks)
        if final_blocks else 0.0
    )
    
    return {
        "blocks": final_blocks,
        "total_blocks": len(final_blocks),
        "avg_confidence": round(avg_confidence, 3),
        "image_width": width,
        "image_height": height,
        "engines_used": list(set(b["engine"] for b in final_blocks)),
    }
