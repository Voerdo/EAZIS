import sqlite3
import json
import re
from datetime import datetime
from collections import Counter
import pandas as pd
import pymorphy3

class CorpusManager:
    def __init__(self, db_path='corpus.db'):
        self.db_path = db_path
        self.morph = pymorphy3.MorphAnalyzer()
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def _get_pos_name(self, pos_code):
        """Перевод кода части речи на русский"""
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
            "INTJ": "Междометие",
            "UNK": "Неизвестно"
        }
        return pos_map.get(pos_code, pos_code)
    
    def _format_grammemes(self, gram_tags_str):
        parts = []
        
        if 'masc' in gram_tags_str:
            parts.append("м.р.")
        elif 'femn' in gram_tags_str:
            parts.append("ж.р.")
        elif 'neut' in gram_tags_str:
            parts.append("ср.р.")
        
        if 'sing' in gram_tags_str:
            parts.append("ед.ч.")
        elif 'plur' in gram_tags_str:
            parts.append("мн.ч.")
        
        case_map = {
            'nomn': 'им.п.',
            'gent': 'род.п.',
            'datv': 'дат.п.',
            'accs': 'вин.п.',
            'ablt': 'твор.п.',
            'loct': 'пр.п.',
            'voct': 'зв.п.',
            'gen2': 'род.п.2',
            'acc2': 'вин.п.2',
            'loc2': 'пр.п.2'
        }
        for code, name in case_map.items():
            if code in gram_tags_str:
                parts.append(name)
                break
        
        if 'past' in gram_tags_str:
            parts.append("прош.вр.")
        elif 'pres' in gram_tags_str:
            parts.append("наст.вр.")
        elif 'futr' in gram_tags_str:
            parts.append("буд.вр.")
        
        if '1per' in gram_tags_str:
            parts.append("1 л.")
        elif '2per' in gram_tags_str:
            parts.append("2 л.")
        elif '3per' in gram_tags_str:
            parts.append("3 л.")
        
        if 'indc' in gram_tags_str:
            parts.append("изъяв.")
        elif 'impr' in gram_tags_str:
            parts.append("повелит.")
        
        if 'perf' in gram_tags_str:
            parts.append("сов.вид")
        elif 'impf' in gram_tags_str:
            parts.append("несов.вид")
        
        if 'tran' in gram_tags_str:
            parts.append("перех.")
        elif 'intr' in gram_tags_str:
            parts.append("неперех.")
        
        return ", ".join(parts) if parts else gram_tags_str
    
    def get_pos_choices(self):
        return [
            ('', 'Все части речи'),
            ('NOUN', 'Существительное'),
            ('ADJF', 'Прилагательное (полное)'),
            ('ADJS', 'Прилагательное (краткое)'),
            ('VERB', 'Глагол'),
            ('INFN', 'Инфинитив'),
            ('PRTF', 'Причастие'),
            ('PRTS', 'Причастие (краткое)'),
            ('GRND', 'Деепричастие'),
            ('NUMR', 'Числительное'),
            ('ADVB', 'Наречие'),
            ('NPRO', 'Местоимение'),
            ('PREP', 'Предлог'),
            ('CONJ', 'Союз'),
            ('PRCL', 'Частица'),
            ('INTJ', 'Междометие')
        ]
    
    
    def init_db(self):
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT,
                subject_area TEXT DEFAULT 'Досуг',
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                word_count INTEGER DEFAULT 0
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id INTEGER,
                token TEXT,
                lemma TEXT,
                pos TEXT,
                gram_tags TEXT,
                position INTEGER,
                sentence_id INTEGER,
                FOREIGN KEY (doc_id) REFERENCES documents(id)
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS sentences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id INTEGER,
                text TEXT,
                position INTEGER,
                FOREIGN KEY (doc_id) REFERENCES documents(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_document(self, title, content, source=None):
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO documents (title, content, source, word_count)
            VALUES (?, ?, ?, ?)
        ''', (title, content, source, len(content.split())))
        
        doc_id = c.lastrowid
        
        sentences = re.split(r'(?<=[.!?])\s+', content)
        
        for sent_pos, sent in enumerate(sentences):
            if not sent.strip():
                continue
            
            c.execute('''
                INSERT INTO sentences (doc_id, text, position)
                VALUES (?, ?, ?)
            ''', (doc_id, sent.strip(), sent_pos))
            
            sent_id = c.lastrowid
            words = re.findall(r'\b[а-яА-ЯёЁ]+\b', sent)
            
            for word_pos, word in enumerate(words):
                parsed = self.morph.parse(word)[0]
                c.execute('''
                    INSERT INTO tokens (doc_id, token, lemma, pos, gram_tags, position, sentence_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    doc_id,
                    word.lower(),
                    parsed.normal_form,
                    parsed.tag.POS or 'UNK',
                    str(parsed.tag),
                    word_pos,
                    sent_id
                ))
        
        conn.commit()
        conn.close()
        return doc_id
    
    def update_document(self, doc_id, title=None, content=None):
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('SELECT * FROM documents WHERE id = ?', (doc_id,))
        current = c.fetchone()
        
        if not current:
            conn.close()
            return False
        
        new_title = title if title is not None else current[1]
        
        if content is not None:
            c.execute('DELETE FROM tokens WHERE doc_id = ?', (doc_id,))
            c.execute('DELETE FROM sentences WHERE doc_id = ?', (doc_id,))
            c.execute('''
                UPDATE documents SET title = ?, content = ?, word_count = ?
                WHERE id = ?
            ''', (new_title, content, len(content.split()), doc_id))
            
            sentences = re.split(r'(?<=[.!?])\s+', content)
            for sent_pos, sent in enumerate(sentences):
                if not sent.strip():
                    continue
                c.execute('INSERT INTO sentences (doc_id, text, position) VALUES (?, ?, ?)',
                         (doc_id, sent.strip(), sent_pos))
                sent_id = c.lastrowid
                words = re.findall(r'\b[а-яА-ЯёЁ]+\b', sent)
                for word_pos, word in enumerate(words):
                    parsed = self.morph.parse(word)[0]
                    c.execute('''
                        INSERT INTO tokens (doc_id, token, lemma, pos, gram_tags, position, sentence_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (doc_id, word.lower(), parsed.normal_form,
                          parsed.tag.POS or 'UNK', str(parsed.tag), word_pos, sent_id))
        else:
            c.execute('UPDATE documents SET title = ? WHERE id = ?', (new_title, doc_id))
        
        conn.commit()
        conn.close()
        return True
    
    def get_documents(self):
        conn = self.get_connection()
        df = pd.read_sql_query('''
            SELECT id, title, source, upload_date, word_count 
            FROM documents 
            ORDER BY upload_date DESC
        ''', conn)
        conn.close()
        return df.to_dict('records')
    
    def get_document(self, doc_id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM documents WHERE id = ?', (doc_id,))
        doc = c.fetchone()
        if doc:
            columns = [desc[0] for desc in c.description]
            doc = dict(zip(columns, doc))
        conn.close()
        return doc
    
    def get_document_tokens(self, doc_id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('''
            SELECT token, lemma, pos, gram_tags 
            FROM tokens 
            WHERE doc_id = ? 
            ORDER BY position
        ''', (doc_id,))
        tokens = c.fetchall()
        conn.close()
        
        result = []
        for token, lemma, pos, gram_tags in tokens:
            result.append({
                'token': token,
                'lemma': lemma,
                'pos': pos,
                'pos_rus': self._get_pos_name(pos),
                'gram_tags': gram_tags,
                'gram_rus': self._format_grammemes(gram_tags) 
            })
        return result
    
    
    def get_concordance(self, word, window=5, pos_filter=None, gram_filter=None):
        conn = self.get_connection()
        c = conn.cursor()
        
        sql = '''
            SELECT t.id, t.sentence_id, t.token, t.lemma, d.title, d.id as doc_id
            FROM tokens t
            JOIN sentences s ON t.sentence_id = s.id
            JOIN documents d ON t.doc_id = d.id
            WHERE (t.token = ? OR t.lemma = ?)
        '''
        params = [word.lower(), word.lower()]
        
        if pos_filter:
            sql += ' AND t.pos = ?'
            params.append(pos_filter)
        
        if gram_filter:
            sql += ' AND t.gram_tags LIKE ?'
            params.append(f'%{gram_filter}%')
        
        c.execute(sql, params)
        matches = c.fetchall()
        results = []
        
        for match in matches:
            sent_id = match[1]
            doc_id = match[5]
            
            c.execute('SELECT token, lemma FROM tokens WHERE sentence_id = ? ORDER BY position', (sent_id,))
            tokens = c.fetchall()
            
            for i, t in enumerate(tokens):
                if t[0] == word.lower() or t[1] == word.lower():
                    left = ' '.join([tok[0] for tok in tokens[max(0, i-window):i]])
                    right = ' '.join([tok[0] for tok in tokens[i+1:min(len(tokens), i+window+1)]])
                    center = tokens[i][0]
                    results.append({
                        'left': left, 'center': center, 'right': right,
                        'document': match[4], 'doc_id': doc_id
                    })
        
        conn.close()
        return results
    
    def get_statistics(self):
        conn = self.get_connection()
        c = conn.cursor()
        
        stats = {}
        c.execute('SELECT COUNT(*) FROM documents')
        stats['doc_count'] = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM tokens')
        stats['token_count'] = c.fetchone()[0]
        c.execute('SELECT COUNT(DISTINCT lemma) FROM tokens')
        stats['unique_lemmas'] = c.fetchone()[0]
        
        c.execute('SELECT lemma, pos, COUNT(*) as freq FROM tokens GROUP BY lemma, pos ORDER BY freq DESC LIMIT 50')
        top_lemmas = c.fetchall()
        stats['top_lemmas'] = [(lemma, self._get_pos_name(pos), freq) for lemma, pos, freq in top_lemmas]
        
        c.execute('SELECT pos, COUNT(*) as freq FROM tokens GROUP BY pos ORDER BY freq DESC')
        pos_dist = c.fetchall()
        stats['pos_distribution'] = [(self._get_pos_name(pos), freq) for pos, freq in pos_dist]
        
        conn.close()
        return stats
    
    def get_frequency_dict(self, pos_filter=None, gram_filter=None):
        conn = self.get_connection()
        sql = 'SELECT token, lemma, pos, gram_tags, COUNT(*) as freq FROM tokens WHERE 1=1'
        params = []
        if pos_filter:
            sql += ' AND pos = ?'
            params.append(pos_filter)
        if gram_filter:
            sql += ' AND gram_tags LIKE ?'
            params.append(f'%{gram_filter}%')
        sql += ' GROUP BY lemma, pos ORDER BY freq DESC'
        df = pd.read_sql_query(sql, conn, params=params)
        conn.close()
        
        result = df.to_dict('records')
        for item in result:
            item['pos_rus'] = self._get_pos_name(item['pos'])
            item['gram_rus'] = self._format_grammemes(item['gram_tags'])
        return result
    
    def search(self, query, search_type='token', pos_filter=None, gram_filter=None):
        conn = self.get_connection()
        c = conn.cursor()
        
        sql = '''
            SELECT t.*, s.text as sentence_text, d.title 
            FROM tokens t
            JOIN sentences s ON t.sentence_id = s.id
            JOIN documents d ON t.doc_id = d.id
            WHERE 1=1
        '''
        params = []
        
        if search_type == 'token':
            sql += ' AND t.token = ?'
            params.append(query.lower())
        elif search_type == 'lemma':
            sql += ' AND t.lemma = ?'
            params.append(query.lower())
        elif search_type == 'pos':
            sql += ' AND t.pos = ?'
            params.append(query)
        
        if pos_filter:
            sql += ' AND t.pos = ?'
            params.append(pos_filter)
        
        if gram_filter:
            sql += ' AND t.gram_tags LIKE ?'
            params.append(f'%{gram_filter}%')
        
        c.execute(sql, params)
        results = c.fetchall()
        columns = [desc[0] for desc in c.description]
        conn.close()
        
        enriched_results = []
        for row in results:
            row_dict = dict(zip(columns, row))
            row_dict['pos_rus'] = self._get_pos_name(row_dict.get('pos'))
            row_dict['gram_rus'] = self._format_grammemes(row_dict.get('gram_tags', ''))
            enriched_results.append(row_dict)
        
        return enriched_results
    
    def delete_document(self, doc_id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('DELETE FROM tokens WHERE doc_id = ?', (doc_id,))
        c.execute('DELETE FROM sentences WHERE doc_id = ?', (doc_id,))
        c.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
        conn.commit()
        conn.close()
    
    def get_gram_categories(self):
        return {
            'pos': self.get_pos_choices(),
            'gender': [('masc', 'м.р.'), ('femn', 'ж.р.'), ('neut', 'ср.р.')],
            'number': [('sing', 'ед.ч.'), ('plur', 'мн.ч.')],
            'case': [('nomn', 'им.п.'), ('gent', 'род.п.'), ('datv', 'дат.п.'), 
                    ('accs', 'вин.п.'), ('ablt', 'твор.п.'), ('loct', 'пр.п.')],
            'tense': [('past', 'прош.'), ('pres', 'наст.'), ('futr', 'буд.')],
            'aspect': [('perf', 'сов.'), ('impf', 'несов.')]
        }