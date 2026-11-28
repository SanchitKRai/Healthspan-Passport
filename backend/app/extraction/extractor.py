import gc
import io
import logging
import threading
from typing import Dict, Any, Tuple
from PIL import Image, ImageOps
import pdfplumber

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB upload cap
MAX_OCR_IMAGE_DIM = 1600            # Max pixels on the long side before OCR

# Initialize RapidOCR lazily behind a single-worker lock so concurrent requests never
# instantiate or run multiple ONNX Runtime sessions simultaneously in memory.
_ocr_engine = None
_ocr_lock = threading.Lock()


def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _ocr_engine = RapidOCR()
        except Exception as e:
            logger.warning("Failed to initialize RapidOCR (%s)", type(e).__name__)
            _ocr_engine = False
    return _ocr_engine


def _downscale_for_ocr(image: Image.Image, max_dim: int = MAX_OCR_IMAGE_DIM) -> Image.Image:
    """Apply EXIF transpose, normalize to RGB, and cap long side at max_dim pixels."""
    img = ImageOps.exif_transpose(image)
    if img.mode != "RGB":
        converted = img.convert("RGB")
        if converted is not img:
            img = converted
    if max(img.width, img.height) > max_dim:
        resampling = getattr(Image, "Resampling", Image).LANCZOS
        resized = img.copy()
        resized.thumbnail((max_dim, max_dim), resampling)
        return resized
    return img


def extract_text_from_pdf(pdf_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    """Extract text from PDF using pdfplumber, falling back to OCR if pages are scanned images."""
    extracted_pages = []
    metadata = {
        "format": "pdf",
        "page_count": 0,
        "ocr_used": False,
        "error": None
    }

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            metadata["page_count"] = len(pdf.pages)
            for page_idx, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text(layout=True) or ""
                if not page_text.strip():
                    tables = page.extract_tables() or []
                    table_lines = []
                    for table in tables:
                        for row in table:
                            row_clean = [str(c or "").strip() for c in row if c is not None]
                            if any(row_clean):
                                table_lines.append(" | ".join(row_clean))
                    if table_lines:
                        page_text = "\n".join(table_lines)

                # Fallback to OCR if page has almost no text (likely a scanned report image embedded in PDF)
                if len(page_text.strip()) < 30:
                    rendered = None
                    try:
                        rendered = page.to_image(resolution=150)
                        ocr_text = extract_text_from_pil_image(rendered.original)
                        if ocr_text.strip():
                            page_text = ocr_text
                            metadata["ocr_used"] = True
                    except Exception as ocr_err:
                        logger.debug("OCR fallback on PDF page %d skipped (%s)", page_idx, type(ocr_err).__name__)
                    finally:
                        if rendered is not None:
                            del rendered

                extracted_pages.append(f"--- PAGE {page_idx} ---\n{page_text}")

        full_text = "\n\n".join(extracted_pages).strip()
        return full_text, metadata

    except Exception as e:
        logger.error("Error parsing PDF (%s)", type(e).__name__)
        metadata["error"] = str(e)
        return "", metadata


def extract_text_from_pil_image(image: Image.Image) -> str:
    """Downscale image to <=1600px, run RapidOCR under a single-worker lock, and release memory."""
    import numpy as np

    scaled = None
    img_np = None
    ocr_result = None
    try:
        scaled = _downscale_for_ocr(image, MAX_OCR_IMAGE_DIM)
        img_np = np.array(scaled)
        # Drop PIL buffer before ONNX inference
        if scaled is not image:
            scaled.close()
        scaled = None

        with _ocr_lock:
            engine = get_ocr_engine()
            if not engine:
                return ""
            ocr_result, _ = engine(img_np)

        if not ocr_result:
            return ""

        lines = []
        for item in ocr_result:
            if len(item) >= 2:
                lines.append(str(item[1]))
        return "\n".join(lines)
    except Exception as e:
        logger.warning("RapidOCR extraction failed (%s)", type(e).__name__)
        return ""
    finally:
        del img_np, ocr_result
        if scaled is not None and scaled is not image:
            try:
                scaled.close()
            except Exception:
                pass
        gc.collect()


def extract_text_from_image(image_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    """Extract text from image bytes (PNG, JPEG, etc.) with 1600px downscale safety."""
    metadata = {
        "format": "image",
        "ocr_used": True,
        "width": 0,
        "height": 0,
        "processed_width": 0,
        "processed_height": 0,
        "error": None,
    }

    try:
        with Image.open(io.BytesIO(image_bytes)) as raw_img:
            metadata["width"] = raw_img.width
            metadata["height"] = raw_img.height

            scaled = _downscale_for_ocr(raw_img, MAX_OCR_IMAGE_DIM)
            metadata["processed_width"] = scaled.width
            metadata["processed_height"] = scaled.height
            try:
                text = extract_text_from_pil_image(scaled)
            finally:
                if scaled is not raw_img:
                    scaled.close()
                del scaled
        gc.collect()
        return text, metadata

    except Exception as e:
        logger.error("Error parsing image (%s)", type(e).__name__)
        metadata["error"] = str(e)
        return "", metadata


def extract_text_from_file(file_bytes: bytes, filename: str) -> Tuple[str, Dict[str, Any]]:
    """Universal text extraction dispatch based on file extension / signature with 8 MB size cap."""
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        return "", {
            "format": "rejected",
            "error": f"File size exceeds maximum limit of {MAX_UPLOAD_BYTES // (1024 * 1024)} MB",
        }

    lower_name = filename.lower()
    if lower_name.endswith(".txt"):
        return file_bytes.decode("utf-8", errors="ignore"), {"format": "text", "page_count": 1, "ocr_used": False, "error": None}
    elif lower_name.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif lower_name.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif")):
        return extract_text_from_image(file_bytes)
    else:
        if file_bytes.startswith(b"%PDF"):
            return extract_text_from_pdf(file_bytes)
        try:
            return extract_text_from_image(file_bytes)
        except Exception:
            return "", {"format": "unknown", "error": "Unsupported file type"}
