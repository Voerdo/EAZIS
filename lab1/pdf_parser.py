import pdfplumber
import PyPDF2
from typing import List
import re

class PDFParser:
    
    @staticmethod
    def extract_text(filepath: str) -> str:
        text = ""
        try:
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\\n"
        except Exception as e:
            print(f"pdfplumber не сработал: {e}, пробуем PyPDF2")
            with open(filepath, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\\n"
        
        return text
    
    @staticmethod
    def extract_words(text: str) -> List[str]:
        words = re.findall(r"[а-яА-ЯёЁ-]+", text.lower())
        words = [w for w in words if len(w) >= 2]
        return words
    
    @staticmethod
    def get_stats(text: str) -> dict:
        words = PDFParser.extract_words(text)
        return {
            "total_chars": len(text),
            "total_words": len(words),
            "unique_words": len(set(words))
        }