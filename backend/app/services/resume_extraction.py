import pdfplumber
from docx import Document
import pytesseract
from PIL import Image
import io
from typing import Optional


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF using pdfplumber."""
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")
    return text.strip()


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


def extract_resume_text(file_path: str, file_extension: str) -> str:
    """Main function to extract text based on file type."""
    file_extension = file_extension.lower()
    
    if file_extension == ".pdf":
        try:
            return extract_text_from_pdf(file_path)
        except:
            # Fallback to OCR if pdfplumber fails
            return extract_text_with_ocr(file_path)
    elif file_extension in [".docx", ".doc"]:
        return extract_text_from_docx(file_path)
    else:
        # Try OCR for images
        return extract_text_with_ocr(file_path)

