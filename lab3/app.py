import os
import re
from datetime import datetime

from flask import Flask, render_template, request, jsonify, send_from_directory

import db
import parser

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = "uploads"

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "Файл не выбран"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Файл не выбран"}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".doc", ".docx"]:
        return jsonify({"error": "Поддерживаются только файлы .doc и .docx"}), 400

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    text, method = parser.extract_text_from_doc(filepath)
    if text is None:
        os.remove(filepath)
        return jsonify({"error": f"Не удалось извлечь текст из файла. {method}"}), 500

    text = re.sub(r'\s+', ' ', text)

    doc_id = db.insert_document(
        filename=filename,
        original_name=file.filename,
        text_content=text,
        file_size=os.path.getsize(filepath)
    )

    sentence_count = 0
    if parser.nlp is not None:
        doc = parser.nlp(text)
        sentences = list(doc.sents)
        sentence_count = len(sentences)
        for i, sent in enumerate(sentences):
            sent_text = sent.text.strip()
            if sent_text:
                analysis = parser.analyze_sentence(sent_text)
                if analysis:
                    db.save_analysis_to_db(doc_id, sent_text, i, analysis)

    return jsonify({
        "success": True,
        "doc_id": doc_id,
        "filename": file.filename,
        "method": method,
        "text_preview": text[:500] + "..." if len(text) > 500 else text,
        "sentence_count": sentence_count
    })

@app.route("/documents")
def get_documents():
    return jsonify(db.get_all_documents())

@app.route("/document/<int:doc_id>")
def view_document(doc_id):
    doc = db.get_document(doc_id)
    if not doc:
        return "Документ не найден", 404
    original_name, text_content = doc
    sentences = db.get_sentences(doc_id)
    return render_template("document.html",
                           doc_id=doc_id,
                           doc_name=original_name,
                           text=text_content,
                           sentences=sentences)

@app.route("/api/sentence/<int:sentence_id>/tree")
def get_sentence_tree(sentence_id):
    sent_text, tokens = db.get_sentence_tree_data(sentence_id)
    if not sent_text:
        return jsonify({"error": "Предложение не найдено"}), 404

    words = []
    for t in tokens:
        words.append({
            "text": t[1],
            "tag": t[4] or t[3],
            "data": [
                ["id", t[0]], ["lemma", t[2] or ""],
                ["pos", t[3] or ""], ["dep", t[5] or ""],
                ["dep_ru", t[6] or ""], ["member", t[9] or "-"]
            ]
        })

    arcs = []
    token_index_map = {t[0]: i for i, t in enumerate(tokens)}
    for t in tokens:
        if t[7] and t[7] in token_index_map:  # head_id
            arcs.append({
                "start": token_index_map[t[7]],
                "end": token_index_map[t[0]],
                "label": t[5] or "dep",
                "label_ru": t[6] or "зависимость"
            })

    return jsonify({
        "sentence_text": sent_text,
        "words": words,
        "arcs": arcs
    })

@app.route("/api/sentence/<int:sentence_id>/constituency-tree")
def get_constituency_tree(sentence_id):
    sent_text, tree_string = db.get_constituency_tree(sentence_id)
    if not sent_text:
        return jsonify({"error": "Предложение не найдено"}), 404

    if not tree_string and parser.nlp:
        tree_string = parser.build_simple_constituency_tree(sent_text)

    return jsonify({
        "sentence_text": sent_text,
        "tree": tree_string or "Дерево составляющих недоступно"
    })

@app.route("/api/update_token", methods=["POST"])
def update_token():
    data = request.get_json()
    token_id = data.get("token_id")
    updates = data.get("updates", {})
    if not token_id:
        return jsonify({"error": "token_id обязателен"}), 400
    db.update_token(token_id, updates)
    return jsonify({"success": True})

@app.route("/sentence-tree")
def sentence_tree_view():
    return render_template("sentence_tree.html")

@app.route("/constituency-tree")
def constituency_tree_view():
    return render_template("constituency_tree.html")

@app.route("/help")
def help_page():
    return render_template("help.html")

@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename)

if __name__ == "__main__":
    db.init_db()
    print("Синтаксический анализатор текста")
    print(f"База данных: {db.DB_NAME}")
    print(f"Папка загрузок: {app.config['UPLOAD_FOLDER']}")
    print(f"spaCy модель: {'en_core_web_sm' if parser.nlp else 'НЕ ЗАГРУЖЕНА'}")
    print("Доступные методы чтения DOC:")
    methods_status = parser.get_available_methods()
    for name, available in methods_status.items():
        status = "OK" if available else "--"
        print(f"  [{status}] {name}")
    print("Откройте http://127.0.0.1:5000 в браузере")
    app.run(debug=True, host="0.0.0.0", port=5000)