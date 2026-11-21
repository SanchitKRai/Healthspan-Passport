import io
import logging
from typing import Dict, Any, Tuple
from PIL import Image
import pdfplumber

logger = logging.getLogger(__name__)

# Initialize RapidOCR lazily
_ocr_engine = None

def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _ocr_engine = RapidOCR()
        except Exception as e:
            logger.warning(f"Failed to initialize RapidOCR: {e}")
            _ocr_engine = False
    return _ocr_engine


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
                # Also check tables if regular text is sparse
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
                    try:
                        pil_img = page.to_image(resolution=200).original
                        ocr_text = extract_text_from_pil_image(pil_img)
                        if ocr_text.strip():
                            page_text = ocr_text
                            metadata["ocr_used"] = True
                    except Exception as ocr_err:
                        logger.debug(f"OCR fallback on PDF page {page_idx} skipped: {ocr_err}")

                extracted_pages.append(f"--- PAGE {page_idx} ---\n{page_text}")

        full_text = "\n\n".join(extracted_pages).strip()
        return full_text, metadata

    except Exception as e:
        logger.error(f"Error parsing PDF: {e}")
        metadata["error"] = str(e)
        return "", metadata


def extract_text_from_pil_image(image: Image.Image) -> str:
    """Extract text from a PIL Image using RapidOCR."""
    engine = get_ocr_engine()
    if not engine:
        return ""

    try:
        import numpy as np
        # Convert PIL Image to numpy RGB array for RapidOCR
        img_np = np.array(image.convert("RGB"))
        ocr_result, _ = engine(img_np)
        if not ocr_result:
            return ""
        
        # Each item in ocr_result is: [box_coordinates, text, confidence]
        lines = []
        for item in ocr_result:
            if len(item) >= 2:
                text_content = item[1]
                lines.append(str(text_content))
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"RapidOCR extraction failed: {e}")
        return ""


def extract_text_from_image(image_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
    """Extract text from image bytes (PNG, JPEG, etc.)."""
    metadata = {
        "format": "image",
        "ocr_used": True,
        "width": 0,
        "height": 0,
        "error": None
    }

    try:
        img = Image.open(io.BytesIO(image_bytes))
        metadata["width"] = img.width
        metadata["height"] = img.height

        text = extract_text_from_pil_image(img)
        return text, metadata

    except Exception as e:
        logger.error(f"Error parsing image: {e}")
        metadata["error"] = str(e)
        return "", metadata


def extract_text_from_file(file_bytes: bytes, filename: str) -> Tuple[str, Dict[str, Any]]:
    """Universal text extraction dispatch based on file extension / signature."""
    lower_name = filename.lower()
    if lower_name.endswith(".txt"):
        return file_bytes.decode("utf-8", errors="ignore"), {"format": "text", "page_count": 1, "ocr_used": False, "error": None}
    elif lower_name.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif lower_name.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif")):
        return extract_text_from_image(file_bytes)
    else:
        # Attempt PDF check first, then image
        if file_bytes.startswith(b"%PDF"):
            return extract_text_from_pdf(file_bytes)
        try:
            return extract_text_from_image(file_bytes)
        except Exception:
            return "", {"format": "unknown", "error": f"Unsupported file type for {filename}"}
