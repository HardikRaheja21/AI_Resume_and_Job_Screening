import logging
import os
from time import perf_counter
from typing import Optional

from ..utils.config import settings
from ..utils import metrics

logger = logging.getLogger("resume_parser.ocr")

try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image, ImageFilter, ImageOps
    _OCR_AVAILABLE = True
except ImportError as exc:
    _OCR_AVAILABLE = False
    _OCR_IMPORT_ERROR = exc
    metrics.inc_ocr_fallback()


def is_ocr_available() -> bool:
    if not settings.OCR_ENABLE:
        logger.info("ocr_disabled")
        return False
    if not _OCR_AVAILABLE:
        logger.warning("ocr_import_missing", extra={"error": str(_OCR_IMPORT_ERROR)})
        return False
    if settings.OCR_TESSERACT_CMD:
        try:
            pytesseract.pytesseract.tesseract_cmd = settings.OCR_TESSERACT_CMD
        except Exception as exc:
            logger.warning("Failed to set Tesseract command: %s", exc)
            return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception as exc:
        logger.warning("Tesseract availability check failed: %s", exc)
        return False


def preprocess_image(image: "Image.Image") -> "Image.Image":
    image = image.convert("L")
    image = ImageOps.autocontrast(image)
    image = image.filter(ImageFilter.MedianFilter(size=3))
    image = image.point(lambda pixel: 0 if pixel < 140 else 255, "1")
    return image


def _pdf_has_images(file_path: str) -> bool:
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(file_path)
        for page in reader.pages:
            resources = page.get("/Resources") or {}
            xobject = resources.get("/XObject") or resources.get(b"/XObject")
            if not xobject:
                continue
            for obj in xobject.values():
                subtype = obj.get("/Subtype")
                if subtype == "/Image" or str(subtype).lower().endswith("image"):
                    return True
        return False
    except Exception:
        return False


def is_scanned_pdf(file_path: str) -> bool:
    return _pdf_has_images(file_path)


def ocr_pdf(file_path: str) -> str:
    if not is_ocr_available():
        logger.warning("ocr_not_available", extra={"file_name": os.path.basename(file_path)})
        metrics.inc_ocr_fallback()
        raise RuntimeError("OCR is not configured or available")
    start = perf_counter()
    try:
        images = convert_from_path(
            file_path,
            dpi=settings.OCR_DPI,
            first_page=1,
            last_page=settings.OCR_PAGE_LIMIT,
        )
    except Exception as exc:
        logger.warning(
            "pdf_conversion_failed",
            extra={"file_name": os.path.basename(file_path), "error": str(exc)},
        )
        raise

    text_pages = []
    for page_number, image in enumerate(images, start=1):
        try:
            if settings.OCR_IMAGE_PREPROCESS:
                image = preprocess_image(image)
            ocr_text = pytesseract.image_to_string(
                image,
                lang=settings.OCR_LANG,
                config=settings.OCR_TESSERACT_CONFIG or "--psm 3 --oem 1",
            )
            text_pages.append(ocr_text or "")
        except Exception as exc:
            logger.warning("ocr_page_failed", extra={"file_name": os.path.basename(file_path), "page": page_number, "error": str(exc)})
            text_pages.append("")
    duration_ms = round((perf_counter() - start) * 1000, 2)
    logger.info(
        "ocr_completed",
        extra={
            "file_name": os.path.basename(file_path),
            "pages": len(images),
            "duration_ms": duration_ms,
        },
    )
    # record Prometheus metric (seconds)
    try:
        metrics.observe_ocr_duration(duration_ms / 1000.0)
    except Exception:
        pass
    # Do not log OCR text content to avoid leaking sensitive resume data
    return "\n".join(text_pages).strip()
