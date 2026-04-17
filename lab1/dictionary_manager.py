from typing import List, Optional
from models import Dictionary, Lexeme
from morph_service import MorphologyService
from pdf_parser import PDFParser
import os

class DictionaryManager:
    
    def __init__(self, storage_dir: str = "dictionaries"):
        self.storage_dir = storage_dir
        self.current_dictionary: Optional[Dictionary] = None
        self.morph_service = MorphologyService()
        self.pdf_parser = PDFParser()
        
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)
    
    def create_dictionary(self, name: str) -> Dictionary:
        self.current_dictionary = Dictionary(name)
        return self.current_dictionary
    
    def load_dictionary(self, filepath: str) -> Dictionary:
        self.current_dictionary = Dictionary.load_from_file(filepath)
        return self.current_dictionary
    
    def save_dictionary(self, filename: str = None):
        if not self.current_dictionary:
            raise ValueError("Нет активного словаря")
        
        if not filename:
            filename = f"{self.current_dictionary.name.replace(' ', '_')}.json"
        
        filepath = os.path.join(self.storage_dir, filename)
        self.current_dictionary.save_to_file(filepath)
        return filepath
    
    def process_pdf(self, pdf_path: str, auto_analyze: bool = True) -> dict:
        if not self.current_dictionary:
            self.create_dictionary("Словарь из PDF")
        
        # Извлекаем текст
        text = self.pdf_parser.extract_text(pdf_path)
        stats = self.pdf_parser.get_stats(text)
        words = self.pdf_parser.extract_words(text)
        unique_words = list(set(words))
        
        if auto_analyze:
            processed = set()
            for word in unique_words:
                if word in processed:
                    continue
                try:
                    lexemes = self.morph_service.analyze_word(word)
                    if lexemes:
                        lexeme = lexemes[0]
                        exists = False
                        for existing in self.current_dictionary.lexemes.values():
                            if existing.lemma == lexeme.lemma and existing.pos == lexeme.pos:
                                exists = True
                                break
                        if not exists:
                            self.current_dictionary.add_lexeme(lexeme)
                        processed.add(word)
                except Exception as e:
                    print(f"Ошибка анализа слова '{word}': {e}")
        
        self.current_dictionary.source_file = os.path.basename(pdf_path)
        
        return {
            "stats": stats,
            "unique_words": len(unique_words),
            "lexemes_added": len(processed)
        }
    
    def add_lexeme_manual(self, lemma: str, pos: str, stem: str) -> Lexeme:
        if not self.current_dictionary:
            self.create_dictionary("Новый словарь")
        
        lexeme = Lexeme(lemma=lemma, pos=pos, stem=stem)
        self.current_dictionary.add_lexeme(lexeme)
        return lexeme
    
    def update_lexeme(self, lexeme_id: int, **kwargs) -> Optional[Lexeme]:
        if not self.current_dictionary:
            return None
        
        lexeme = self.current_dictionary.get_lexeme(lexeme_id)
        if lexeme:
            for key, value in kwargs.items():
                if hasattr(lexeme, key):
                    setattr(lexeme, key, value)
        return lexeme
    
    def add_wordform(self, lexeme_id: int, ending: str, gram_info: str):
        if not self.current_dictionary:
            return None
        
        lexeme = self.current_dictionary.get_lexeme(lexeme_id)
        if lexeme:
            form = lexeme.stem + ending
            lexeme.add_wordform(ending, gram_info, form)
        return lexeme
    
    def generate_wordform(self, lexeme_id: int, ending: str) -> Optional[str]:
        if not self.current_dictionary:
            return None
        
        lexeme = self.current_dictionary.get_lexeme(lexeme_id)
        if lexeme:
            return self.morph_service.generate_form(lexeme, ending)
        return None
    
    def search(self, query: str, pos_filter: str = None) -> List[Lexeme]:
        if not self.current_dictionary:
            return []
        if pos_filter == "":
            pos_filter = None
        return self.current_dictionary.search(query, pos_filter)
    
    def get_stats(self) -> dict:
        if not self.current_dictionary:
            return {"error": "Нет активного словаря"}
        return self.current_dictionary.get_stats()
    
    def list_dictionaries(self) -> List[str]:
        files = []
        for f in os.listdir(self.storage_dir):
            if f.endswith(".json"):
                files.append(f)
        return sorted(files)