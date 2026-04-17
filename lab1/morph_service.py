import pymorphy3
from typing import List, Dict, Optional, Tuple
from models import Lexeme, WordForm

class MorphologyService:
    
    def __init__(self):
        self.morph = pymorphy3.MorphAnalyzer()
    
    def analyze_word(self, word: str) -> List[Lexeme]:
        parses = self.morph.parse(word)
        lexemes = []
        
        for parse in parses:

            lemma = parse.normal_form
            pos = self._get_pos_name(parse.tag.POS)
            stem = self._extract_stem(parse)
            lexeme = Lexeme(lemma=lemma, pos=pos, stem=stem)
            forms = self._get_all_forms(parse)
            for form, gram_info in forms:
                ending = form[len(stem):] if form.startswith(stem) else ""
                lexeme.add_wordform(ending, gram_info, form)
            
            lexemes.append(lexeme)
        
        return lexemes
    
    def _get_pos_name(self, pos_code: Optional[str]) -> str:
        pos_map = {
            "NOUN": "Существительное",
            "ADJF": "Прилагательное (полное)",
            "ADJS": "Прилагательное (краткое)",
            "COMP": "Компаратив",
            "VERB": "Глагол (личная форма)",
            "INFN": "Глагол (инфинитив)",
            "PRTF": "Причастие (полное)",
            "PRTS": "Причастие (краткое)",
            "GRND": "Деепричастие",
            "NUMR": "Числительное",
            "ADVB": "Наречие",
            "NPRO": "Местоимение",
            "PRED": "Предикатив",
            "PREP": "Предлог",
            "CONJ": "Союз",
            "PRCL": "Частица",
            "INTJ": "Междометие"
        }
        return pos_map.get(pos_code, "Неизвестно")
    
    def _extract_stem(self, parse) -> str:
        word = parse.word
        
        normal_form = parse.normal_form
        
        if parse.tag.POS == "NOUN":
            return self._guess_stem_noun(parse)
        elif parse.tag.POS in ["ADJF", "ADJS"]:
            return self._guess_stem_adjective(parse)
        elif parse.tag.POS in ["VERB", "INFN"]:
            return self._guess_stem_verb(parse)

        if len(normal_form) > 2:
            return normal_form[:-2]
        return normal_form
    
    def _guess_stem_noun(self, parse) -> str:
        nf = parse.normal_form
        # Типичные окончания
        endings = ["а", "я", "о", "е", "ие", "ие", "ть", "сть", "ов", "ев", "ей"]
        for end in sorted(endings, key=len, reverse=True):
            if nf.endswith(end):
                return nf[:-len(end)]
        return nf
    
    def _guess_stem_adjective(self, parse) -> str:
        nf = parse.normal_form
        endings = ["ый", "ий", "ой", "ая", "яя", "ое", "ее", "ые", "ие"]
        for end in sorted(endings, key=len, reverse=True):
            if nf.endswith(end):
                return nf[:-len(end)]
        return nf
    
    def _guess_stem_verb(self, parse) -> str:
        nf = parse.normal_form
        if nf.endswith("ть"):
            return nf[:-2]
        elif nf.endswith("ти"):
            return nf[:-2]
        elif nf.endswith("чь"):
            return nf[:-2]
        return nf
    
    def _get_all_forms(self, parse) -> List[Tuple[str, str]]:
        forms = []
        try:
            lexeme = parse.lexeme
            for form in lexeme:
                gram_info = self._format_grammemes(form.tag)
                forms.append((form.word, gram_info))
        except:
            forms.append((parse.word, str(parse.tag)))
        return forms
    
    def _format_grammemes(self, tag) -> str:
        parts = []
        
        if tag.gender:
            gender_map = {"masc": "м.р.", "femn": "ж.р.", "neut": "ср.р."}
            parts.append(gender_map.get(tag.gender, tag.gender))
        
        if tag.number:
            number_map = {"sing": "ед.ч.", "plur": "мн.ч."}
            parts.append(number_map.get(tag.number, tag.number))
        
        if tag.case:
            case_map = {
                "nomn": "им.п.", "gent": "род.п.", "datv": "дат.п.",
                "accs": "вин.п.", "ablt": "твор.п.", "loct": "пр.п.",
                "voct": "зв.п.", "gen2": "род.п.2", "acc2": "вин.п.2",
                "loc2": "пр.п.2"
            }
            parts.append(case_map.get(tag.case, tag.case))

        if tag.tense:
            tense_map = {"past": "прош.", "pres": "наст.", "futr": "буд."}
            parts.append(tense_map.get(tag.tense, tag.tense))

        if tag.person:
            parts.append(f"{tag.person} л.")

        if tag.mood:
            mood_map = {"indc": "изъяв.", "impr": "повелит."}
            parts.append(mood_map.get(tag.mood, tag.mood))

        if tag.aspect:
            aspect_map = {"perf": "сов.", "impf": "несов."}
            parts.append(aspect_map.get(tag.aspect, tag.aspect))

        if tag.transitivity:
            trans_map = {"tran": "перех.", "intr": "неперех."}
            parts.append(trans_map.get(tag.transitivity, tag.transitivity))
        
        return ", ".join(parts) if parts else str(tag)
    
    def generate_form(self, lexeme: Lexeme, ending: str) -> str:
        return lexeme.stem + ending
    
    def get_available_pos(self) -> List[str]:
        return [
            "Существительное", "Прилагательное (полное)", "Прилагательное (краткое)",
            "Глагол (личная форма)", "Глагол (инфинитив)", "Причастие (полное)",
            "Причастие (краткое)", "Деепричастие", "Числительное", "Наречие",
            "Местоимение", "Предлог", "Союз", "Частица", "Междометие"
        ]