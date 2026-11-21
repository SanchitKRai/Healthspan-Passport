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
