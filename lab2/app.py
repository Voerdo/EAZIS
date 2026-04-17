from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
import os
import io
import json
from werkzeug.utils import secure_filename
from corpus_manager import CorpusManager
from text_parser import TextParser

app = Flask(__name__)
app.secret_key = 'corpus_secret_key_2024'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'doc', 'rtf'}
cm = CorpusManager()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    docs = cm.get_documents()
    stats = cm.get_statistics() if docs else None
    return render_template('index.html', documents=docs, stats=stats)

@app.route('/help')
def help_page():
    return render_template('help.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Файл не выбран', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        title = request.form.get('title', '')
        
        if file.filename == '':
            flash('Файл не выбран', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                content = TextParser.parse(filepath)
                doc_id = cm.add_document(
                    title=title or filename,
                    content=content,
                    source=filename
                )
                
                flash(f'Документ успешно добавлен (ID: {doc_id})', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                flash(f'Ошибка обработки файла: {str(e)}', 'error')
                if os.path.exists(filepath):
                    os.remove(filepath)
        else:
            flash('Неподдерживаемый формат файла. Поддерживаются: TXT, PDF, DOC, DOCX, RTF', 'error')
    
    return render_template('upload.html')

@app.route('/document/<int:doc_id>')
def view_document(doc_id):
    doc = cm.get_document(doc_id)
    if not doc:
        flash('Документ не найден', 'error')
        return redirect(url_for('index'))
    
    tokens = cm.get_document_tokens(doc_id)
    return render_template('document.html', doc=doc, tokens=tokens)

@app.route('/document/<int:doc_id>/edit', methods=['GET', 'POST'])
def edit_document(doc_id):
    doc = cm.get_document(doc_id)
    if not doc:
        flash('Документ не найден', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        new_title = request.form.get('title', '').strip()
        new_content = request.form.get('content', '').strip()
        
        if not new_title or not new_content:
            flash('Название и содержание не могут быть пустыми', 'error')
        else:
            cm.update_document(doc_id, title=new_title, content=new_content)
            flash('Документ успешно обновлен', 'success')
            return redirect(url_for('view_document', doc_id=doc_id))
    
    return render_template('edit_document.html', doc=doc)

@app.route('/search', methods=['GET', 'POST'])
def search():
    results = None
    query = ''
    search_type = 'token'
    pos_filter = None
    gram_filter = None
    
    if request.method == 'POST':
        query = request.form.get('query', '')
        search_type = request.form.get('search_type', 'token')
        pos_filter = request.form.get('pos_filter', None) or None
        gram_filter = request.form.get('gram_filter', None) or None
        
        if query:
            results = cm.search(query, search_type, pos_filter, gram_filter)
    
    gram_categories = cm.get_gram_categories()
    return render_template('search.html', results=results, query=query, 
                         search_type=search_type, gram_categories=gram_categories,
                         pos_filter=pos_filter, gram_filter=gram_filter)

@app.route('/concordance', methods=['GET', 'POST'])
def concordance():
    results = None
    word = ''
    window = 5
    pos_filter = None
    gram_filter = None
    
    if request.method == 'POST':
        word = request.form.get('word', '')
        window = int(request.form.get('window', 5))
        pos_filter = request.form.get('pos_filter', None) or None
        gram_filter = request.form.get('gram_filter', None) or None
        
        if word:
            results = cm.get_concordance(word, window, pos_filter, gram_filter)
    
    gram_categories = cm.get_gram_categories()
    return render_template('concordance.html', results=results, word=word, 
                         window=window, gram_categories=gram_categories,
                         pos_filter=pos_filter, gram_filter=gram_filter)

@app.route('/statistics')
def statistics():
    stats = cm.get_statistics()
    freq_dict = cm.get_frequency_dict()
    return render_template('statistics.html', stats=stats, freq_dict=freq_dict)

@app.route('/api/frequency')
def api_frequency():
    pos_filter = request.args.get('pos', None)
    gram_filter = request.args.get('gram', None)
    data = cm.get_frequency_dict(pos_filter=pos_filter, gram_filter=gram_filter)
    return jsonify(data)


@app.route('/export/frequency/json')
def export_frequency_json():
    pos_filter = request.args.get('pos', None)
    gram_filter = request.args.get('gram', None)
    data = cm.get_frequency_dict(pos_filter=pos_filter, gram_filter=gram_filter)
    
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    buffer = io.BytesIO(json_str.encode('utf-8'))
    
    return send_file(
        buffer,
        mimetype='application/json',
        as_attachment=True,
        download_name='frequency_dict.json'
    )

@app.route('/delete/<int:doc_id>', methods=['POST'])
def delete_document(doc_id):
    cm.delete_document(doc_id)
    flash('Документ удален', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True, port=5000)