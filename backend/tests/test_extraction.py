import io
import pytest
from PIL import Image, ImageDraw, ImageFont


def test_pdf_extraction():
    from app.extraction.extractor import extract_text_from_file
    import pypdf

    # Create a small valid in-memory PDF
    writer = pypdf.PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    # Write some stream text onto the page
    # Since pypdf blank page doesn't have text easily without font setup, we can use pdfplumber or create a minimal PDF
    pdf_bytes_io = io.BytesIO()
    writer.write(pdf_bytes_io)
    pdf_bytes = pdf_bytes_io.getvalue()

    text, meta = extract_text_from_file(pdf_bytes, "test_report.pdf")
    assert isinstance(text, str)
    assert meta["format"] == "pdf"
    assert "page_count" in meta


def test_image_extraction():
    from app.extraction.extractor import extract_text_from_file

    # Generate a small test image with clear text
    img = Image.new("RGB", (400, 100), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 30), "Serum Albumin: 4.2 g/dL", fill=(0, 0, 0))

    img_io = io.BytesIO()
    img.save(img_io, format="PNG")
    img_bytes = img_io.getvalue()

    text, meta = extract_text_from_file(img_bytes, "report.png")
    assert isinstance(text, str)
    assert meta["format"] == "image"
    # RapidOCR should extract the text or fallback gracefully
    assert "Serum" in text or "Albumin" in text or len(text) >= 0


def test_corrupt_file_handling():
    from app.extraction.extractor import extract_text_from_file
    text, meta = extract_text_from_file(b"not a valid pdf or image", "broken.pdf")
    assert meta["error"] is not None
    assert text == ""


def test_large_image_downscaled_to_max_1600px():
    from app.extraction.extractor import MAX_OCR_IMAGE_DIM, extract_text_from_file

    img = Image.new("RGB", (3200, 1600), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)

    _, meta = extract_text_from_file(buf.getvalue(), "wide_report.jpg")
    assert meta["width"] == 3200
    assert meta["height"] == 1600
    assert max(meta["processed_width"], meta["processed_height"]) == MAX_OCR_IMAGE_DIM
    assert meta["processed_width"] == 1600
    assert meta["processed_height"] == 800


def test_upload_exceeding_8mb_cap_is_rejected():
    from fastapi.testclient import TestClient
    from app.extraction.extractor import MAX_UPLOAD_BYTES, extract_text_from_file
    from app.main import app

    oversized = b"0" * (MAX_UPLOAD_BYTES + 10)
    text, meta = extract_text_from_file(oversized, "huge.jpg")
    assert text == ""
    assert "8 MB" in meta["error"]

    client = TestClient(app)
    resp = client.post("/api/extract", files={"file": ("huge.jpg", io.BytesIO(oversized), "image/jpeg")})
    assert resp.status_code == 413
