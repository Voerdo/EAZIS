import json
from datetime import datetime
from typing import List, Dict, Optional

class WordForm:
    def __init__(self, ending: str, gram_info: str, form: str = ""):
        self.ending = ending  # окончание
        self.gram_info = gram_info  # свойства
        self.form = form  # полная форма слова
    
    def to_dict(self):
        return {
            "ending": self.ending,
            "gram_info": self.gram_info,
            "form": self.form
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            ending=data.get("ending", ""),
            gram_info=data.get("gram_info", ""),
            form=data.get("form", "")
        )

class Lexeme:
    def __init__(self, lemma: str, pos: str, stem: str = "", wordforms: List[WordForm] = None, id: int = None):
        self.id = id or int(datetime.now().timestamp() * 1000)
        self.lemma = lemma  # начальная форма
        self.pos = pos      # часть речи
        self.stem = stem    # основа слова
        self.wordforms = wordforms or []  # список словоформ
    
    def add_wordform(self, ending: str, gram_info: str, form: str = ""):
        wf = WordForm(ending, gram_info, form)
        self.wordforms.append(wf)
    
    def remove_wordform(self, index: int):
        if 0 <= index < len(self.wordforms):
            del self.wordforms[index]
    
    def generate_form(self, ending: str) -> str:
        return self.stem + ending
    
    def to_dict(self):
        return {
            "id": self.id,
            "lemma": self.lemma,
            "pos": self.pos,
            "stem": self.stem,
            "wordforms": [wf.to_dict() for wf in self.wordforms]
        }
    
    @classmethod
    def from_dict(cls, data):
        lexeme = cls(
            id=data.get("id"),
            lemma=data["lemma"],
            pos=data["pos"],
            stem=data.get("stem", "")
        )
        lexeme.wordforms = [WordForm.from_dict(wf) for wf in data.get("wordforms", [])]
        return lexeme
    
    def __repr__(self):
        return f"Lexeme({self.lemma}, {self.pos}, форм: {len(self.wordforms)})"

class Dictionary:
    def __init__(self, name: str = "Новый словарь"):
        self.name = name
        self.lexemes: Dict[int, Lexeme] = {}
        self.source_file = None
    
    def add_lexeme(self, lexeme: Lexeme):
        self.lexemes[lexeme.id] = lexeme
    
    def get_lexeme(self, id: int) -> Optional[Lexeme]:
        return self.lexemes.get(id)
    
    def remove_lexeme(self, id: int):
        if id in self.lexemes:
            del self.lexemes[id]
    
    def get_all_lexemes(self, sort_by: str = "alphabet") -> List[Lexeme]:
        lexemes = list(self.lexemes.values())
        if sort_by == "alphabet":
            lexemes.sort(key=lambda x: x.lemma.lower())
        return lexemes
    
    def search(self, query: str, pos_filter: str = None) -> List[Lexeme]:
        results = []
        query = query.lower()
        for lexeme in self.lexemes.values():
            if query in lexeme.lemma.lower():
                if not pos_filter or lexeme.pos == pos_filter:
                    results.append(lexeme)
        return sorted(results, key=lambda x: x.lemma.lower())
    
    def filter_by_pos(self, pos: str) -> List[Lexeme]:
        return sorted(
            [l for l in self.lexemes.values() if l.pos == pos],
            key=lambda x: x.lemma.lower()
        )
    
    def get_stats(self) -> dict:
        pos_counts = {}
        total_forms = 0
        for lex in self.lexemes.values():
            pos_counts[lex.pos] = pos_counts.get(lex.pos, 0) + 1
            total_forms += len(lex.wordforms)
        
        return {
            "total_lexemes": len(self.lexemes),
            "total_forms": total_forms,
            "pos_distribution": pos_counts
        }
    
    def save_to_file(self, filepath: str):
        data = {
            "name": self.name,
            "source_file": self.source_file,
            "lexemes": [lex.to_dict() for lex in self.lexemes.values()]
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        dictionary = cls(name=data.get("name", "Словарь"))
        dictionary.source_file = data.get("source_file")
        
        for lex_data in data.get("lexemes", []):
            lexeme = Lexeme.from_dict(lex_data)
            dictionary.lexemes[lexeme.id] = lexeme
        
        return dictionary
    
    def export_to_txt(self, filepath: str):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"Словарь: {self.name}\\n")
            f.write("=" * 50 + "\\n\\n")
            
            for lexeme in self.get_all_lexemes():
                f.write(f"{lexeme.lemma} ({lexeme.pos})\\n")
                f.write(f"  Основа: {lexeme.stem}\\n")
                if lexeme.wordforms:
                    f.write("  Словоформы:\\n")
                    for wf in lexeme.wordforms:
                        f.write(f"    {wf.form or lexeme.stem + wf.ending} - {wf.gram_info}\\n")
                f.write("\\n")