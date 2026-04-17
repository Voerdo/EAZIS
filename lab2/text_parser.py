import os
import re
import subprocess
import chardet
from PyPDF2 import PdfReader
from docx import Document

class TextParser:
    SUPPORTED_FORMATS = {'txt', 'pdf', 'docx', 'doc', 'rtf'}
    
    @staticmethod
    def detect_encoding(file_path):
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(100000)
                if not raw_data:
                    return 'utf-8'
                result = chardet.detect(raw_data)
                encoding = result.get('encoding', 'utf-8')
                return encoding if encoding else 'utf-8'
        except Exception:
            return 'utf-8'

    @classmethod
    def parse(cls, file_path):
        if '.' not in file_path:
            raise ValueError("Файл должен иметь расширение")
        
        ext = file_path.rsplit('.', 1)[1].lower()
        
        if ext not in cls.SUPPORTED_FORMATS:
            raise ValueError(f"Неподдерживаемый формат: '{ext}'. Поддерживаются: {', '.join(cls.SUPPORTED_FORMATS)}")
        
        if ext == 'txt':
            return cls.parse_txt(file_path)
        elif ext == 'pdf':
            return cls.parse_pdf(file_path)
        elif ext == 'docx':
            return cls.parse_docx(file_path)
        elif ext == 'doc':
            return cls.parse_doc_windows(file_path)
        elif ext == 'rtf':
            return cls.parse_rtf(file_path)
    
    @staticmethod
    def parse_txt(file_path):
        encodings = ['utf-8', 'utf-8-sig', 'windows-1251', 'cp1251', 'koi8-r', 'iso-8859-5']
        
        try:
            with open(file_path, 'rb') as f:
                raw = f.read(10000)
                detected = chardet.detect(raw)
                if detected['encoding']:
                    encodings.insert(0, detected['encoding'])
        except:
            pass
        
        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc, errors='ignore') as f:
                    content = f.read()
                    if len(content) > 0 and '' not in content[:1000]:
                        return content
            except:
                continue
        
        with open(file_path, 'rb') as f:
            return f.read().decode('utf-8', errors='ignore')

    @staticmethod
    def parse_pdf(file_path):
        try:
            reader = PdfReader(file_path)
            text = '\n'.join([page.extract_text() or '' for page in reader.pages])
            return text
        except Exception as e:
            raise ValueError(f"Ошибка чтения PDF: {str(e)}")

    @staticmethod
    def parse_docx(file_path):
        try:
            doc = Document(file_path)
            return '\n'.join([p.text for p in doc.paragraphs])
        except Exception as e:
            raise ValueError(f"Ошибка чтения DOCX: {str(e)}")

    @staticmethod
    def parse_doc_windows(file_path):       
        try:
            import win32com.client
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            
            doc = word.Documents.Open(os.path.abspath(file_path))
            text = doc.Content.Text
            doc.Close(False)
            word.Quit()
            
            return text
        except Exception as e:
            pass
        
        try:
            result = subprocess.run(['antiword', file_path], 
                                  capture_output=True, text=True, timeout=10,
                                  encoding='utf-8', errors='ignore')
            if result.returncode == 0 and result.stdout:
                return result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        try:
            result = subprocess.run(['catdoc', file_path], 
                                  capture_output=True, text=True, timeout=10,
                                  encoding='utf-8', errors='ignore')
            if result.returncode == 0 and result.stdout:
                return result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        raise ValueError(
            "Не удалось прочитать .doc файл. Варианты решения:\n"
            "1. Установите: pip install textract\n"
            "2. Или установите pywin32: pip install pywin32 (требуется Microsoft Word)\n"
            "3. Или установите antiword/catdoc через WSL/Cygwin\n"
            "4. Или конвертируйте .doc в .docx вручную"
        )

    @staticmethod
    def parse_rtf(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            text = re.sub(r'\\[a-z]+[-]?\d* ?', '', content)
            text = re.sub(r'[{}]', '', text)
            text = re.sub(r'\\', '', text)
            return text
        except Exception as e:
            raise ValueError(f"Ошибка чтения RTF: {str(e)}")