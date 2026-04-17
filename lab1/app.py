from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
import os
import json
from dictionary_manager import DictionaryManager
from models import Dictionary

app = Flask(__name__)
app.secret_key = "dictionary_system_secret_key"
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {"pdf"}

dict_manager = DictionaryManager()

if not os.path.exists(app.config["UPLOAD_FOLDER"]):
    os.makedirs(app.config["UPLOAD_FOLDER"])

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    stats = dict_manager.get_stats() if dict_manager.current_dictionary else None
    recent_dictionaries = dict_manager.list_dictionaries()[-5:]  # последние 5
    return render_template("index.html", stats=stats, dictionaries=recent_dictionaries)

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        flash("Файл не выбран", "error")
        return redirect(request.url)
    
    file = request.files["file"]
    if file.filename == "":
        flash("Файл не выбран", "error")
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)
        
        try:
            result = dict_manager.process_pdf(filepath)
            flash(f"Обработано успешно: {result['lexemes_added']} лексем из {result['unique_words']} уникальных слов", "success")
        except Exception as e:
            flash(f"Ошибка обработки: {str(e)}", "error")
        
        return redirect(url_for("view_dictionary"))
    
    flash("Неподдерживаемый формат файла", "error")
    return redirect(url_for("index"))

@app.route("/dictionary")
def view_dictionary():
    if not dict_manager.current_dictionary:
        flash("Сначала создайте или загрузите словарь", "info")
        return redirect(url_for("index"))
    
    sort_by = request.args.get("sort", "alphabet")
    pos_filter = request.args.get("pos", None)
    search_query = request.args.get("q", "")
    
    if search_query:
        lexemes = dict_manager.search(search_query, pos_filter)
    elif pos_filter:
        lexemes = dict_manager.current_dictionary.filter_by_pos(pos_filter)
    else:
        lexemes = dict_manager.current_dictionary.get_all_lexemes(sort_by)
    
    pos_list = dict_manager.morph_service.get_available_pos()
    stats = dict_manager.current_dictionary.get_stats()
    
    return render_template("dictionary.html", 
                         lexemes=lexemes, 
                         stats=stats, 
                         pos_list=pos_list,
                         current_pos=pos_filter,
                         search_query=search_query)

@app.route("/lexeme/<int:lexeme_id>")
def view_lexeme(lexeme_id):
    lexeme = dict_manager.current_dictionary.get_lexeme(lexeme_id) if dict_manager.current_dictionary else None
    if not lexeme:
        flash("Лексема не найдена", "error")
        return redirect(url_for("view_dictionary"))
    
    return render_template("lexeme.html", lexeme=lexeme)

@app.route("/lexeme/<int:lexeme_id>/edit", methods=["GET", "POST"])
def edit_lexeme(lexeme_id):
    if not dict_manager.current_dictionary:
        return redirect(url_for("index"))
    
    lexeme = dict_manager.current_dictionary.get_lexeme(lexeme_id)
    if not lexeme:
        flash("Лексема не найдена", "error")
        return redirect(url_for("view_dictionary"))
    
    if request.method == "POST":
        lexeme.lemma = request.form.get("lemma", lexeme.lemma)
        lexeme.pos = request.form.get("pos", lexeme.pos)
        lexeme.stem = request.form.get("stem", lexeme.stem)
        flash("Лексема обновлена", "success")
        return redirect(url_for("view_lexeme", lexeme_id=lexeme_id))
    
    pos_list = dict_manager.morph_service.get_available_pos()
    return render_template("edit_lexeme.html", lexeme=lexeme, pos_list=pos_list)

@app.route("/lexeme/<int:lexeme_id>/add_form", methods=["POST"])
def add_wordform(lexeme_id):
    ending = request.form.get("ending", "")
    gram_info = request.form.get("gram_info", "")
    
    dict_manager.add_wordform(lexeme_id, ending, gram_info)
    flash("Словоформа добавлена", "success")
    return redirect(url_for("view_lexeme", lexeme_id=lexeme_id))

@app.route("/lexeme/<int:lexeme_id>/generate", methods=["POST"])
def generate_form(lexeme_id):
    ending = request.form.get("ending", "")
    result = dict_manager.generate_wordform(lexeme_id, ending)
    
    if result:
        return jsonify({"success": True, "form": result})
    return jsonify({"success": False, "error": "Не удалось сгенерировать форму"})

@app.route("/lexeme/add", methods=["GET", "POST"])
def add_lexeme():
    if not dict_manager.current_dictionary:
        flash("Сначала создайте словарь", "error")
        return redirect(url_for("index"))
    
    if request.method == "POST":
        lemma = request.form.get("lemma", "")
        pos = request.form.get("pos", "")
        stem = request.form.get("stem", "")
        
        if lemma and pos:
            lexeme = dict_manager.add_lexeme_manual(lemma, pos, stem)
            flash(f"Лексема '{lemma}' добавлена", "success")
            return redirect(url_for("view_lexeme", lexeme_id=lexeme.id))
        else:
            flash("Заполните обязательные поля", "error")
    
    pos_list = dict_manager.morph_service.get_available_pos()
    return render_template("add_lexeme.html", pos_list=pos_list)

@app.route("/lexeme/<int:lexeme_id>/delete", methods=["POST"])
def delete_lexeme(lexeme_id):
    if dict_manager.current_dictionary:
        dict_manager.current_dictionary.remove_lexeme(lexeme_id)
        flash("Лексема удалена", "success")
    return redirect(url_for("view_dictionary"))

@app.route("/dictionary/save", methods=["POST"])
def save_dictionary():
    if not dict_manager.current_dictionary:
        flash("Нет словаря для сохранения", "error")
        return redirect(url_for("index"))
    
    filename = request.form.get("filename", "")
    if not filename.endswith(".json"):
        filename += ".json"
    
    try:
        filepath = dict_manager.save_dictionary(filename)
        flash(f"Словарь сохранен: {filepath}", "success")
    except Exception as e:
        flash(f"Ошибка сохранения: {str(e)}", "error")
    
    return redirect(url_for("view_dictionary"))

@app.route("/dictionary/load", methods=["POST"])
def load_dictionary():
    filename = request.form.get("filename", "")
    filepath = os.path.join("dictionaries", filename)
    
    if os.path.exists(filepath):
        try:
            dict_manager.load_dictionary(filepath)
            flash(f"Словарь '{filename}' загружен", "success")
        except Exception as e:
            flash(f"Ошибка загрузки: {str(e)}", "error")
    else:
        flash("Файл не найден", "error")
    
    return redirect(url_for("view_dictionary"))

@app.route("/dictionary/new", methods=["POST"])
def new_dictionary():
    name = request.form.get("name", "Новый словарь")
    dict_manager.create_dictionary(name)
    flash(f"Создан новый словарь: {name}", "success")
    return redirect(url_for("view_dictionary"))

@app.route("/dictionary/export")
def export_dictionary():
    if not dict_manager.current_dictionary:
        flash("Нет словаря для экспорта", "error")
        return redirect(url_for("index"))
    
    filename = f"{dict_manager.current_dictionary.name.replace(' ', '_')}.txt"
    filepath = os.path.join("dictionaries", filename)
    dict_manager.current_dictionary.export_to_txt(filepath)
    
    return send_file(filepath, as_attachment=True, download_name=filename)

@app.route("/help")
def help_page():
    return render_template("help.html")

@app.route("/api/stats")
def api_stats():
    return jsonify(dict_manager.get_stats())

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)