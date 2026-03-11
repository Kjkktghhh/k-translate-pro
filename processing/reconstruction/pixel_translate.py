"""
pixel_translate.py
──────────────────
Pixel-accurate Korean→Traditional Chinese image reconstruction.

Steps:
1. Scan image for white text pixels to find exact bounding boxes
2. Gaussian-blur erase each text region (background inpainting)
3. Re-render translated text at the measured font size, centered in the exact box

Usage:
    python pixel_translate.py --input image.png --output out.jpg

Or import and call translate_image() directly.
"""

import argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path

FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
FONT_REG  = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
WHITE = (255, 255, 255)


def scan_text_blocks(arr, threshold=228, min_pixels=8):
    """
    Scan image array row-by-row to find contiguous bands of bright pixels.
    Returns list of (y_start, y_end, x_start, x_end) tight bounding boxes.
    """
    H, W = arr.shape[:2]
    blocks = []
    in_block = False
    block_y_start = 0
    block_x_min, block_x_max = W, 0

    for y in range(H):
        row = arr[y]
        bright = np.where(row.mean(axis=1) > threshold)[0]
        has = len(bright) >= min_pixels

        if has and not in_block:
            in_block = True
            block_y_start = y
            block_x_min = int(bright[0])
            block_x_max = int(bright[-1])
        elif has and in_block:
            block_x_min = min(block_x_min, int(bright[0]))
            block_x_max = max(block_x_max, int(bright[-1]))
        elif not has and in_block:
            in_block = False
            blocks.append((block_y_start, y - 1, block_x_min, block_x_max))
            block_x_min, block_x_max = W, 0

    if in_block:
        blocks.append((block_y_start, H - 1, block_x_min, block_x_max))

    return blocks


def inpaint_region(img_pil, x1, y1, x2, y2, radius=28):
    """Erase a region by Gaussian-blurring the surrounding area and pasting in."""
    W, H = img_pil.size
    pad = 40
    cx1, cy1 = max(0, x1 - pad), max(0, y1 - pad)
    cx2, cy2 = min(W, x2 + pad), min(H, y2 + pad)
    patch = img_pil.crop((cx1, cy1, cx2, cy2))
    blurred = patch.filter(ImageFilter.GaussianBlur(radius=radius))
    inner = blurred.crop((x1 - cx1, y1 - cy1, x2 - cx1, y2 - cy1))
    img_pil.paste(inner, (x1, y1))
    return img_pil


def render_text(draw, text, x1, y1, x2, y2, font_path, target_size, color, font_index=2):
    """
    Render text centered in (x1,y1,x2,y2).
    Starts at target_size and shrinks until text fits width.
    """
    bw, bh = x2 - x1, y2 - y1
    size = target_size
    font = None
    tw = th = 0

    while size >= 6:
        try:
            font = ImageFont.truetype(font_path, size, index=font_index)
        except Exception:
            font = ImageFont.truetype(font_path, size)
        bb = draw.textbbox((0, 0), text, font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        if tw <= bw:
            break
        size -= 1

    tx = x1 + (bw - tw) // 2
    ty = y1 + (bh - th) // 2
    draw.text((tx, ty), text, font=font, fill=color)
    return size


# ── Translation map: define regions + translations explicitly.
#    For production, replace with dynamic OCR + translation API calls.
#
# Format: list of dicts with keys:
#   y1, y2, x1, x2   — exact pixel bounding box
#   text              — translated text
#   font              — "bold" | "regular"
#   target_size       — starting font size (shrinks to fit)
#   color             — RGB tuple
DEFAULT_TRANSLATIONS = [
    # "수분 충전 & 잠금" → 補水鎖水 & 全效修護
    dict(y1=860, y2=909, x1=191, x2=549,
         text="補水鎖水 & 全效修護",
         font="bold", target_size=44, color=WHITE),

    # "손상장벽케어를 한번에!" → 肌膚屏障修護，一次到位！
    dict(y1=932, y2=981, x1=123, x2=626,
         text="肌膚屏障修護，一次到位！",
         font="bold", target_size=44, color=WHITE),

    # "#신제품런칭  #전문관리후 사용 가능" → #新品上市  #專業護理後可使用
    dict(y1=1026, y2=1052, x1=148, x2=601,
         text="#新品上市  #專業護理後可使用",
         font="regular", target_size=24, color=WHITE),
]


def translate_image(
    input_path: str,
    output_path: str,
    translations: list = None,
    inpaint_radius: int = 28,
    jpeg_quality: int = 96,
):
    """
    Main entry point.

    Args:
        input_path:     Path to source image (PNG/JPG).
        output_path:    Where to save the result.
        translations:   List of region dicts (see DEFAULT_TRANSLATIONS).
                        If None, uses DEFAULT_TRANSLATIONS.
        inpaint_radius: Gaussian blur radius for background reconstruction.
        jpeg_quality:   Output JPEG quality (1–95).
    """
    if translations is None:
        translations = DEFAULT_TRANSLATIONS

    img = Image.open(input_path).convert("RGB")

    for region in translations:
        x1, y1, x2, y2 = region["x1"], region["y1"], region["x2"], region["y2"]

        # 1. Erase original text
        img = inpaint_region(img, x1, y1, x2, y2, radius=inpaint_radius)

        # 2. Render translation
        draw = ImageDraw.Draw(img)
        font_path = FONT_BOLD if region.get("font") == "bold" else FONT_REG
        final_size = render_text(
            draw,
            region["text"],
            x1, y1, x2, y2,
            font_path=font_path,
            target_size=region.get("target_size", 30),
            color=region.get("color", WHITE),
        )
        print(f"  [{region['text'][:20]}] → size={final_size}px at ({x1},{y1},{x2},{y2})")

    ext = Path(output_path).suffix.lower()
    if ext in (".jpg", ".jpeg"):
        img.save(output_path, "JPEG", quality=jpeg_quality)
    else:
        img.save(output_path)

    print(f"\nSaved: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pixel-accurate Korean→ZH-Hant image translation")
    parser.add_argument("--input",   required=True, help="Source image path")
    parser.add_argument("--output",  required=True, help="Output image path")
    parser.add_argument("--radius",  type=int, default=28, help="Inpaint blur radius")
    parser.add_argument("--quality", type=int, default=96, help="JPEG output quality")
    args = parser.parse_args()

    translate_image(args.input, args.output,
                    inpaint_radius=args.radius,
                    jpeg_quality=args.quality)
