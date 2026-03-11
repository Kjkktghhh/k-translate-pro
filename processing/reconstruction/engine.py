"""
Image reconstruction: inpaint original text regions, re-render translated text.
Uses OpenCV inpainting (fast, no GPU needed for MVP) with Pillow for text rendering.
"""
import logging
import os
import uuid
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

logger = logging.getLogger(__name__)

# Font fallback chain for CJK + Latin
FONT_PATHS = {
    "zh-Hant": [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/app/fonts/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
    ],
    "en": [
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/app/fonts/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ],
    "default": None  # Will use PIL default
}


def _load_font(language: str, size: int) -> ImageFont.FreeTypeFont:
    """Load best available font for the target language."""
    paths = FONT_PATHS.get(language, []) + FONT_PATHS.get("en", [])
    for path in paths:
        if path and os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    # Last resort: PIL default
    return ImageFont.load_default()


def _bbox_to_mask(img_shape: Tuple, bbox: Dict, padding: int = 3) -> np.ndarray:
    """Create binary mask for a text bounding box."""
    h, w = img_shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    x, y, bw, bh = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
    x1 = max(0, x - padding)
    y1 = max(0, y - padding)
    x2 = min(w, x + bw + padding)
    y2 = min(h, y + bh + padding)
    mask[y1:y2, x1:x2] = 255
    return mask


def inpaint_text_regions(image: np.ndarray, blocks: List[Dict]) -> np.ndarray:
    """
    Remove text from all detected regions using OpenCV inpainting.
    Uses TELEA algorithm for quality, with radius tuned per block size.
    """
    combined_mask = np.zeros(image.shape[:2], dtype=np.uint8)
    
    for block in blocks:
        bbox = block.get("bbox", {})
        if not bbox:
            continue
        block_mask = _bbox_to_mask(image.shape, bbox, padding=4)
        combined_mask = cv2.bitwise_or(combined_mask, block_mask)
    
    if not combined_mask.any():
        return image
    
    # Dilate mask slightly to catch anti-aliased edges
    kernel = np.ones((3, 3), np.uint8)
    combined_mask = cv2.dilate(combined_mask, kernel, iterations=1)
    
    # Apply inpainting
    inpainted = cv2.inpaint(image, combined_mask, inpaintRadius=7, flags=cv2.INPAINT_TELEA)
    return inpainted


def _detect_text_color(image: np.ndarray, bbox: Dict) -> Tuple[int, int, int]:
    """Sample the dominant text color from the original image region."""
    x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
    x = max(0, x); y = max(0, y)
    region = image[y:y+h, x:x+w]
    
    if region.size == 0:
        return (0, 0, 0)
    
    # Convert to grayscale, find darkest pixels (likely text)
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY) if len(region.shape) == 3 else region
    threshold = np.percentile(gray, 15)  # bottom 15% = text
    mask = gray < threshold
    
    if mask.any() and len(region.shape) == 3:
        text_pixels = region[mask]
        avg_color = text_pixels.mean(axis=0)
        # Return as RGB
        return (int(avg_color[2]), int(avg_color[1]), int(avg_color[0]))
    
    return (30, 30, 30)  # default near-black


def render_translated_text(
    pil_image: Image.Image,
    blocks: List[Dict],
    language: str
) -> Image.Image:
    """
    Re-render translated text onto the inpainted image.
    Attempts to match original font size and color.
    """
    img = pil_image.copy()
    draw = ImageDraw.Draw(img)
    
    for block in blocks:
        translations = block.get("translations", {})
        if language not in translations:
            continue
        
        translated_text = translations[language]["text"]
        bbox = block.get("bbox", {})
        if not bbox:
            continue
        
        x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
        
        # Estimate original font size from bbox height
        font_size = max(10, int(h * 0.75))
        font = _load_font(language, font_size)
        
        # Detect original text color
        np_img = np.array(pil_image)
        if len(np_img.shape) == 3 and np_img.shape[2] >= 3:
            bgr_img = cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)
            text_color = _detect_text_color(bgr_img, bbox)
        else:
            text_color = (0, 0, 0)
        
        # Fit text in bbox — shrink font if overflow
        for attempt in range(5):
            try:
                bbox_size = draw.textbbox((0, 0), translated_text, font=font)
                text_w = bbox_size[2] - bbox_size[0]
                text_h = bbox_size[3] - bbox_size[1]
            except Exception:
                text_w, text_h = font_size * len(translated_text) // 2, font_size
            
            if text_w <= w * 1.1:  # allow 10% overflow
                break
            font_size = int(font_size * 0.85)
            font = _load_font(language, max(8, font_size))
        
        # Center text in original bbox
        text_x = x + max(0, (w - text_w) // 2)
        text_y = y + max(0, (h - text_h) // 2)
        
        # Draw text
        draw.text((text_x, text_y), translated_text, font=font, fill=text_color)
    
    return img


def reconstruct_image(
    original_path: str,
    blocks_with_translations: List[Dict],
    output_dir: str,
    target_languages: List[str],
    job_id: str
) -> Dict[str, str]:
    """
    Full reconstruction pipeline for one image:
    1. Load original
    2. Inpaint all text regions
    3. For each target language: render translated text → save
    Returns dict of {language: output_path}
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Load image
    pil_orig = Image.open(original_path).convert("RGB")
    np_orig = np.array(pil_orig)
    bgr_orig = cv2.cvtColor(np_orig, cv2.COLOR_RGB2BGR)
    
    # Step 1: Inpaint
    logger.info(f"Inpainting {len(blocks_with_translations)} text regions")
    inpainted_bgr = inpaint_text_regions(bgr_orig, blocks_with_translations)
    inpainted_rgb = cv2.cvtColor(inpainted_bgr, cv2.COLOR_BGR2RGB)
    inpainted_pil = Image.fromarray(inpainted_rgb)
    
    output_paths = {}
    ext = Path(original_path).suffix.lower() or ".jpg"
    base_name = Path(original_path).stem
    
    # Step 2: Render each target language
    for lang in target_languages:
        rendered = render_translated_text(inpainted_pil, blocks_with_translations, lang)
        lang_slug = lang.replace("-", "_").lower()
        out_filename = f"{base_name}_{lang_slug}_{job_id[:8]}{ext}"
        out_path = os.path.join(output_dir, out_filename)
        
        # Save preserving format
        if ext in [".jpg", ".jpeg"]:
            rendered.save(out_path, "JPEG", quality=95)
        elif ext == ".png":
            rendered.save(out_path, "PNG")
        else:
            rendered.save(out_path)
        
        output_paths[lang] = out_path
        logger.info(f"Saved {lang} output: {out_path}")
    
    return output_paths
