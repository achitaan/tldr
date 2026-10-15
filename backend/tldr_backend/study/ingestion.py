"""Bounded local extraction; originals retained, extracted content never executed."""
import hashlib
import io
from pathlib import Path
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from .models import Page
from .retrieval import index_page

MAX_BYTES = 20 * 1024 * 1024
MAX_PAGES = 100
Image.MAX_IMAGE_PIXELS = 30_000_000

def tesseract_command():
    import shutil
    import os
    explicit=os.getenv('TESSERACT_CMD')
    if explicit: return shutil.which(explicit)
    found=shutil.which('tesseract')
    standard=Path(r'C:\Program Files\Tesseract-OCR\tesseract.exe')
    return found or (str(standard) if standard.is_file() else None)

def ocr_available():
    return bool(tesseract_command())

def ocr(image):
    if not ocr_available():
        return ''
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = tesseract_command()
    text = pytesseract.image_to_string(image, timeout=45)
    if not text.strip():
        # Diagrams often contain isolated labels rather than a paragraph block.
        text = pytesseract.image_to_string(image, config='--psm 11', timeout=45)
    return text[:100000]

def make_page(source, number, text, image=None):
    page = Page(source=source, number=number, text=text[:100000], original_text=text[:100000])
    if image:
        image = ImageOps.exif_transpose(image).convert('RGB')
        image.thumbnail((2400, 2400))
        output = io.BytesIO()
        image.save(output, format='PNG')
        page.width, page.height = image.size
        page.image.save(f'{source.id}-{number}.png', ContentFile(output.getvalue()), save=False)
    page.save()
    index_page(page)
    return page

def clear_pages(source):
    # Retry removes only this source’s partial pages and their images.
    from django.db import connection
    from .retrieval import ensure_fts
    ensure_fts()
    for old in source.pages.all():
        with connection.cursor() as cursor:
            cursor.execute('DELETE FROM study_page_fts WHERE rowid=%s',[old.id])
        old.image.delete(save=False)
    source.pages.all().delete()


def ingest(source, cancelled=lambda: False):
    if source.kind == 'web':
        from .web_ingestion import ingest_web
        return ingest_web(source, cancelled)
    if not source.original:
        raise ValueError('Source original is missing.')
    path = Path(source.original.path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError('File exceeds 20 MB.')
    source.digest = hashlib.sha256(path.read_bytes()).hexdigest()
    clear_pages(source)
    if source.kind == 'pdf':
        import pypdfium2 as pdfium
        document = pdfium.PdfDocument(str(path))
        try:
            if len(document) > MAX_PAGES:
                raise ValueError('PDF exceeds 100 pages; split it before importing.')
            for i in range(len(document)):
                if cancelled():
                    raise InterruptedError('Cancelled.')
                pdfpage = document[i]
                try:
                    textpage = pdfpage.get_textpage()
                    try:
                        text = textpage.get_text_range()
                    finally:
                        textpage.close()
                    width, height = pdfpage.get_size()
                    scale = min(2, 2400 / max(width, height))
                    bitmap = pdfpage.render(scale=scale)
                    try:
                        image = bitmap.to_pil().copy()
                    finally:
                        bitmap.close()
                    if not text.strip():
                        text = ocr(image)
                    make_page(source, i + 1, text, image)
                finally:
                    pdfpage.close()
        finally:
            document.close()
    elif source.kind == 'image':
        with Image.open(path) as image:
            image = ImageOps.exif_transpose(image).convert('RGB')
            image.thumbnail((2400, 2400))
            make_page(source, 1, ocr(image), image)
    elif source.kind == 'text':
        text = path.read_text(encoding='utf-8-sig')
        if len(text) > 500000:
            raise ValueError('Text exceeds 500,000 characters.')
        chunks = [text[i:i+12000] for i in range(0, len(text), 12000)] or ['']
        for i, chunk in enumerate(chunks):
            if cancelled():
                raise InterruptedError('Cancelled.')
            make_page(source, i + 1, chunk)
    else:
        raise ValueError('Unsupported file type.')
    source.status, source.error = 'ready', ''
    source.save(update_fields=['status', 'error', 'digest'])
