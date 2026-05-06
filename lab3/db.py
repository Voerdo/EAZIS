import sqlite3
from datetime import datetime  
DB_NAME = "syntax_analyzer.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_name TEXT NOT NULL,
            upload_date TEXT NOT NULL,
            text_content TEXT,
            file_size INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sentences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id INTEGER NOT NULL,
            sentence_text TEXT NOT NULL,
            sentence_order INTEGER NOT NULL,
            FOREIGN KEY (doc_id) REFERENCES documents(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sentence_id INTEGER NOT NULL,
            token_text TEXT NOT NULL,
            lemma TEXT, pos TEXT, pos_ru TEXT,
            dep_code TEXT, dep_name TEXT,
            head_id INTEGER, token_order INTEGER NOT NULL,
            member TEXT,
            FOREIGN KEY (sentence_id) REFERENCES sentences(id),
            FOREIGN KEY (head_id) REFERENCES tokens(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS constituency_trees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sentence_id INTEGER NOT NULL,
            tree_string TEXT,
            FOREIGN KEY (sentence_id) REFERENCES sentences(id)
        )
    """)
    conn.commit()
    conn.close()

def insert_document(filename, original_name, text_content, file_size):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO documents (filename, original_name, upload_date, text_content, file_size)
        VALUES (?, ?, ?, ?, ?)
    """, (filename, original_name, datetime.now().isoformat(), text_content, file_size))
    doc_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return doc_id

def save_analysis_to_db(doc_id, sentence_text, sentence_order, analysis_result):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sentences (doc_id, sentence_text, sentence_order)
        VALUES (?, ?, ?)
    """, (doc_id, sentence_text, sentence_order))
    sentence_id = cursor.lastrowid

    token_id_map = {}
    for token in analysis_result["tokens"]:
        cursor.execute("""
            INSERT INTO tokens (sentence_id, token_text, lemma, pos, pos_ru, dep_code, dep_name, head_id, token_order, member)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sentence_id, token["text"], token["lemma"], token["pos"],
            token["pos_ru"], token["dep"], token["dep_ru"],
            None, token["id"], None
        ))
        token_id_map[token["id"]] = cursor.lastrowid

    for token in analysis_result["tokens"]:
        if token["head_id"] is not None and token["head_id"] in token_id_map:
            cursor.execute("""
                UPDATE tokens SET head_id = ? WHERE sentence_id = ? AND token_order = ?
            """, (token_id_map[token["head_id"]], sentence_id, token["id"]))

    if analysis_result.get("constituency_tree"):
        cursor.execute("""
            INSERT INTO constituency_trees (sentence_id, tree_string)
            VALUES (?, ?)
        """, (sentence_id, analysis_result["constituency_tree"]))

    conn.commit()
    conn.close()
    return sentence_id

def get_all_documents():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.id, d.original_name, d.upload_date, d.file_size, COUNT(s.id) as sentence_count
        FROM documents d
        LEFT JOIN sentences s ON d.id = s.doc_id
        GROUP BY d.id
        ORDER BY d.upload_date DESC
    """)
    docs = cursor.fetchall()
    conn.close()
    return [
        {
            "id": d[0],
            "name": d[1],
            "date": d[2],
            "size": d[3],
            "sentences": d[4]
        } for d in docs
    ]

def get_document(doc_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT original_name, text_content FROM documents WHERE id = ?", (doc_id,))
    doc = cursor.fetchone()
    conn.close()
    return doc  # (name, text) или None

def get_sentences(doc_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, sentence_text, sentence_order FROM sentences
        WHERE doc_id = ? ORDER BY sentence_order
    """, (doc_id,))
    sentences = cursor.fetchall()
    conn.close()
    return sentences  # список кортежей

def get_sentence_tree_data(sentence_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT sentence_text FROM sentences WHERE id = ?", (sentence_id,))
    sent = cursor.fetchone()
    if not sent:
        conn.close()
        return None, None
    cursor.execute("""
        SELECT id, token_text, lemma, pos, pos_ru, dep_code, dep_name, head_id, token_order, member
        FROM tokens WHERE sentence_id = ? ORDER BY token_order
    """, (sentence_id,))
    tokens = cursor.fetchall()
    conn.close()
    return sent[0], tokens  # sentence_text, список токенов

def get_constituency_tree(sentence_id):
    """Возвращает текст предложения и строку дерева (или None)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT sentence_text FROM sentences WHERE id = ?", (sentence_id,))
    sent = cursor.fetchone()
    if not sent:
        conn.close()
        return None, None
    cursor.execute("SELECT tree_string FROM constituency_trees WHERE sentence_id = ?", (sentence_id,))
    tree = cursor.fetchone()
    conn.close()
    return sent[0], (tree[0] if tree else None)

def update_token(token_id, updates):
    allowed_fields = ["token_text", "lemma", "pos_ru", "member", "dep_code", "head_id"]
    set_clause = []
    values = []
    for field, value in updates.items():
        if field in allowed_fields:
            set_clause.append(f"{field} = ?")
            values.append(value)
    if not set_clause:
        return
    values.append(token_id)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE tokens SET {', '.join(set_clause)} WHERE id = ?", values)
    conn.commit()
    conn.close()