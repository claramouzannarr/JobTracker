import pdfplumber
from docx import Document
import pytesseract
from PIL import Image
import io
from typing import Optional


def extract_text_from_pdf(file_path: str) -> tuple[str, int]:
    """Extract text from PDF using pdfplumber. Returns (text, page_count)."""
    text = ""
    page_count = 0
    try:
        with pdfplumber.open(file_path) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")
    return text.strip(), page_count


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
    except Exception as e:
        raise Exception(f"Error extracting text from DOCX: {str(e)}")
    return text.strip()


def extract_text_with_ocr(file_path: str) -> str:
    """Extract text from image/PDF using OCR (Tesseract)."""
    try:
        # For PDFs, convert to images first (simplified - in production use pdf2image)
        # For now, assume it's an image file
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
    except Exception as e:
        raise Exception(f"Error extracting text with OCR: {str(e)}")
    return text.strip()


def extract_resume_text(file_path: str, file_extension: str) -> tuple[str, int]:
    """Main function to extract text based on file type. Returns (text, page_count)."""
    file_extension = file_extension.lower()
    
    if file_extension == ".pdf":
        try:
            return extract_text_from_pdf(file_path)
        except:
            # Fallback to OCR if pdfplumber fails
            ocr_text = extract_text_with_ocr(file_path)
            # Estimate page count (rough: ~500 words per page)
            word_count = len(ocr_text.split())
            estimated_pages = max(1, (word_count + 499) // 500)
            return ocr_text, estimated_pages
    elif file_extension in [".docx", ".doc"]:
        docx_text = extract_text_from_docx(file_path)
        # Estimate page count for DOCX
        word_count = len(docx_text.split())
        estimated_pages = max(1, (word_count + 499) // 500)
        return docx_text, estimated_pages
    else:
        # Try OCR for images
        ocr_text = extract_text_with_ocr(file_path)
        estimated_pages = 1  # Assume single page for images
        return ocr_text, estimated_pages

