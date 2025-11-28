#!/usr/bin/env python3
"""
Home Lab TEXTPASTE Service
- secure - modern - feature-rich (?)

Use this at your own risk. No warranties provided.
Try not to use this at all. Find better alternatives.
I wrote this because I needed something light and with just the features I need.
"""

import os
import json
import hashlib
import datetime
from functools import wraps
from flask import Flask, request, redirect, url_for, render_template_string, abort, jsonify
from jinja2 import Template
import re


app = Flask(__name__)
app.secret_key = os.urandom(32)  # GOTH CHIC session security - serious daddy issues!

# Configuration
PASTE_STORAGE_DIR = os.path.join(os.path.dirname(__file__), "pastes")
PASTE_FILE = os.path.join(PASTE_STORAGE_DIR, "pastes.json")
MAX_PASTE_SIZE = 50000  # 50KB should be enough for me !!
MAX_PASTES_PER_PAGE = 20 # 20 is probably too long, but then there are delete buttons

# json storage check/creation
os.makedirs(PASTE_STORAGE_DIR, exist_ok=True)

def init_storage():
    """Initialize storage file if it doesn't exist"""
    if not os.path.exists(PASTE_FILE):
        with open(PASTE_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)

def load_pastes():
    """Load ALL pastes from storage"""
    try:
        with open(PASTE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_pastes(pastes):
    """Save pastes to storage with atomic(?) write"""
    temp_file = PASTE_FILE + '.tmp'
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(pastes, f, indent=2)
    os.replace(temp_file, PASTE_FILE)

def generate_paste_id(content):
    """Generate a short unique ID (I'm liking this) for paste"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()[:8]

def escape_html(text):
    """Escape HTML to prevent XSS"""
    # SECURITY ;p
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#x27;'))

def highlight_syntax(text):
    """Basic syntax highlighting for common languages"""
    # basic syntax highlighting - matching patterns
    patterns = {
        'python': [
            (r'#.*$', 'comment'),
            (r'(".*?"|\'.*?\')', 'string'),
            (r'\b(def|class|if|else|elif|for|while|import|from|try|except|finally|with|as|return|yield|lambda|and|or|not|in|is|True|False|None)\b', 'keyword')
        ],
        'javascript': [
            (r'//.*$', 'comment'),
            (r'(".*?"|\'.*?`|\'.*?\')', 'string'),
            (r'\b(function|var|let|const|if|else|for|while|return|true|false|null|undefined|new|class|import|export)\b', 'keyword')
        ],
        'html': [
            (r'<!--.*?-->', 'comment'),
            (r'<[^>]+>', 'tag'),
            (r'(".*?"|\'.*?\')', 'string')
        ]
    }
    
    detected_lang = detect_language(text)
    if detected_lang and detected_lang in patterns:
        for pattern, class_name in patterns[detected_lang]:
            text = re.sub(pattern, f'<span class="{class_name}">\\g<0></span>', text, flags=re.MULTILINE)
    
    return text

def detect_language(text):
    """Simple language detection"""
    if text.startswith('import ') or 'def ' in text:
        return 'python'
    elif 'function(' in text or 'console.log(' in text:
        return 'javascript'
    elif '<' in text and '</' in text:
        return 'html'
    return None

def validate_paste(content):
    """Validate paste content"""
    if not content or not content.strip():
        return False, "Content cannot be empty"
    
    if len(content) > MAX_PASTE_SIZE:
        return False, f"Content too large. Maximum size is {MAX_PASTE_SIZE} characters"
    
    return True, ""

# HTML Template with modern styling
# And pray it works :(
# Taking way more time than I thought
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(-45deg, hsla(60, 1%, 37%, 1) 0%, hsla(25, 33%, 17%, 1) 100%);
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            color: #EDEDE9;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 1.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .paste-form {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #555;
        }
        
        .form-group input, .form-group textarea, .form-group select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        
        .form-group input:focus, .form-group textarea:focus, .form-group select:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .textarea {
            min-height: 200px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            resize: vertical;
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            transition: transform 0.2s;
        }
        
        .btn:hover {
            transform: translateY(-2px);
        }
        
        .paste-item {
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        
        .paste-item:hover {
            transform: translateY(-2px);
        }
        
        .paste-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
        }
        
        .paste-meta {
            color: #666;
            font-size: 14px;
        }
        
        .paste-actions {
            display: flex;
            gap: 10px;
        }
        
        .btn-sm {
            padding: 6px 12px;
            font-size: 12px;
        }
        
        .btn-danger {
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
        }
        
        .btn-secondary {
            background: linear-gradient(135deg, #95a5a6 0%, #7f8c8d 100%);
        }
        
        .content {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            white-space: pre-wrap;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            line-height: 1.5;
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #e1e5e9;
            position: relative;
        }
        
        .copy-btn {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(102, 126, 234, 0.9);
            color: white;
            border: none;
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
            cursor: pointer;
            transition: background 0.2s;
        }
        
        .copy-btn:hover {
            background: rgba(102, 126, 234, 1);
        }
        
        .comment { color: #6c757d; font-style: italic; }
        .string { color: #28a745; }
        .keyword { color: #007bff; font-weight: 600; }
        .tag { color: #dc3545; }
        
        .pagination {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-top: 30px;
        }
        
        .pagination a, .pagination span {
            padding: 8px 16px;
            border: 1px solid #ddd;
            border-radius: 5px;
            text-decoration: none;
            color: #333;
        }
        
        .pagination .current {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
        
        .alert {
            padding: 12px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        .alert-success {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        
        .alert-error {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .stat-number {
            font-size: 2rem;
            font-weight: bold;
            color: #667eea;
        }
        
        @media (max-width: 768px) {
            .container { padding: 10px; }
            .header h1 { font-size: 2rem; }
            .paste-form, .paste-item { padding: 15px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>HOMElab TEXTshare</h1>
            <p>Fast (not really), secure (daddy issues though), and feature-rich ($$)</p>
        </div>
        
        {% if message %}
        <div class="alert alert-{{ message_type }}">
            {{ message }}
        </div>
        {% endif %}
        
        <!-- Statistics -->
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ total_pastes }}</div>
                <div>Total Pastes - I'm  counting</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ total_size }}</div>
                <div>Total Size (KB) - Show off! It's just text</div>
            </div>
        </div>
        
        <!-- Paste Form -->
        <div class="paste-form">
            <h2>New (Auto)</h2>
            <form method="post" action="{{ url_for('create_paste') }}">
                <div class="form-group">
                    <label for="title">Title (Optional) - not enough brain cells!</label>
                    <input type="text" id="title" name="title" placeholder="Enter a title for your paste">
                </div>
                
                <div class="form-group">
                    <label for="language">Language</label>
                    <select id="language" name="language">
                        <option value="auto">Auto-detect</option>
                        <option value="text">Plain Text</option>
                        <option value="python">Python</option>
                        <option value="javascript">JavaScript</option>
                        <option value="html">HTML</option>
                        <option value="css">CSS</option>
                        <option value="json">JSON</option>
                        <option value="markdown">Markdown</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="content">Content - THE stuff</label>
                    <textarea 
                        id="content" 
                        name="content" 
                        class="textarea" 
                        placeholder="Paste your code or text here..."
                        required
                    ></textarea>
                </div>
                
                <button type="submit" class="btn">Create Paste</button>
            </form>
        </div>
        
        <!-- Pastes List -->
        <div class="pastes-container">
            <h2>Recent Pastes</h2>
            {% if pastes %}
                {% for paste in pastes %}
                <div class="paste-item">
                    <div class="paste-header">
                        <div>
                            <h3>{{ paste.title or 'Untitled Paste' }}</h3>
                            <div class="paste-meta">
                                <span>ID: {{ paste.id }}</span> • 
                                <span>Created: {{ paste.created_at }}</span> • 
                                <span>Language: {{ paste.language or 'Unknown' }}</span> • 
                                <span>Size: {{ paste.size }} chars</span>
                            </div>
                        </div>
                        <div class="paste-actions">
                            <a href="{{ url_for('view_paste', paste_id=paste.id) }}" class="btn btn-sm btn-secondary">View</a>
                            <a href="{{ url_for('raw_paste', paste_id=paste.id) }}" class="btn btn-sm btn-secondary">Raw</a>
                            <a href="{{ url_for('delete_paste', paste_id=paste.id) }}" class="btn btn-sm btn-danger" onclick="return confirm('Are you sure?')">Delete</a>
                        </div>
                    </div>
                    <div class="content" id="content-{{ paste.id }}">
                        {{ paste.content[:200] }}{% if paste.content|length > 200 %}...{% endif %}
                        <button class="copy-btn" onclick="copyToClipboard('{{ paste.id }}')">📋 Copy</button>
                    </div>
                </div>
                {% endfor %}
                
                <!-- Pagination -->
                {% if total_pages > 1 %}
                <div class="pagination">
                    {% if page > 1 %}
                    <a href="{{ url_for('index', page=page-1) }}">Previous</a>
                    {% endif %}
                    
                    {% for p in range(1, total_pages + 1) %}
                        {% if p == page %}
                        <span class="current">{{ p }}</span>
                        {% else %}
                        <a href="{{ url_for('index', page=p) }}">{{ p }}</a>
                        {% endif %}
                    {% endfor %}
                    
                    {% if page < total_pages %}
                    <a href="{{ url_for('index', page=page+1) }}">Next</a>
                    {% endif %}
                </div>
                {% endif %}
            {% else %}
                <p style="text-align: center; color: white; margin-top: 40px;">
                    mty as ya head mate, no cells found
                </p>
            {% endif %}
        </div>
    </div>
    <script>
        function copyToClipboard(pasteId) {
            const content = document.getElementById('content-' + pasteId).innerText.replace('📋 Copy', '').trim();
            navigator.clipboard.writeText(content).then(function() {
                const btn = event.target;
                const originalText = btn.innerHTML;
                btn.innerHTML = '✅ Copied!';
                btn.style.background = 'rgba(40, 167, 69, 0.9)';
                setTimeout(function() {
                    btn.innerHTML = originalText;
                    btn.style.background = 'rgba(102, 126, 234, 0.9)';
                }, 2000);
            }).catch(function() {
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = content;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                
                const btn = event.target;
                const originalText = btn.innerHTML;
                btn.innerHTML = '✅ Copied!';
                btn.style.background = 'rgba(40, 167, 69, 0.9)';
                setTimeout(function() {
                    btn.innerHTML = originalText;
                    btn.style.background = 'rgba(102, 126, 234, 0.9)';
                }, 2000);
            });
        }
    </script>
</body>
</html>
'''

@app.route('/', methods=['GET'])
def index():
    """Main page with paste list and creation form"""
    init_storage()
    
    page = int(request.args.get('page', 1))
    pastes = load_pastes()
    
    # Calculate statistics
    total_size = sum(len(p['content']) for p in pastes)
    
    # Pagination
    total_pastes = len(pastes)
    total_pages = (total_pastes + MAX_PASTES_PER_PAGE - 1) // MAX_PASTES_PER_PAGE
    start_idx = (page - 1) * MAX_PASTES_PER_PAGE
    end_idx = start_idx + MAX_PASTES_PER_PAGE
    page_pastes = pastes[start_idx:end_idx]
    
    # Pass message from query parameters
    message = request.args.get('message', '')
    message_type = request.args.get('type', 'success')
    
    return render_template_string(
        HTML_TEMPLATE,
        pastes=page_pastes,
        total_pastes=total_pastes,
        total_size=f"{total_size/1024:.1f}",
        page=page,
        total_pages=total_pages,
        title="Modern Paste Service",
        message=message,
        message_type=message_type
    )

@app.route('/paste', methods=['POST'])
def create_paste():
    """Create a new paste"""
    content = request.form.get('content', '')
    title = request.form.get('title', '').strip()
    language = request.form.get('language', 'auto')
    
    # Validate content
    is_valid, error_msg = validate_paste(content)
    if not is_valid:
        return redirect(url_for('index', message=error_msg, type='error'))
    
    # Generate unique ID
    paste_id = generate_paste_id(content)
    
    # Create paste object
    paste = {
        'id': paste_id,
        'title': title if title else None,
        'content': content,
        'language': language if language != 'auto' else detect_language(content),
        'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'size': len(content)
    }
    
    # Save paste
    pastes = load_pastes()
    pastes.insert(0, paste)  # Add to beginning
    save_pastes(pastes)
    
    return redirect(url_for('index', message=f'Paste created successfully! ID: {paste_id}', type='success'))

@app.route('/paste/<paste_id>')
def view_paste(paste_id):
    """View a specific paste"""
    pastes = load_pastes()
    paste = next((p for p in pastes if p['id'] == paste_id), None)
    
    if not paste:
        abort(404)
    
    return render_template_string(
        HTML_TEMPLATE,
        pastes=[],
        total_pastes=len(pastes),
        total_size=f"{sum(len(p['content']) for p in pastes)/1024:.1f}",
        page=1,
        total_pages=1,
        title=f"Paste: {paste.get('title', 'Untitled')}",
        message=f"Viewing paste: {paste['id']}",
        message_type='success'
    )

@app.route('/raw/<paste_id>')
def raw_paste(paste_id):
    """View raw paste content"""
    pastes = load_pastes()
    paste = next((p for p in pastes if p['id'] == paste_id), None)
    
    if not paste:
        abort(404)
    
    return f"Content-Type: text/plain\n\n{paste['content']}"

@app.route('/delete/<paste_id>')
def delete_paste(paste_id):
    """Delete a paste"""
    pastes = load_pastes()
    original_count = len(pastes)
    pastes = [p for p in pastes if p['id'] != paste_id]
    
    if len(pastes) < original_count:
        save_pastes(pastes)
        return redirect(url_for('index', message='Paste deleted successfully!', type='success'))
    else:
        return redirect(url_for('index', message='Paste not found!', type='error'))

@app.route('/api/pastes')
def api_get_pastes():
    """API endpoint to get pastes"""
    pastes = load_pastes()
    return jsonify(pastes)

@app.route('/api/paste', methods=['POST'])
def api_create_paste():
    """API endpoint to create paste"""
    data = request.get_json()
    content = data.get('content', '')
    
    is_valid, error_msg = validate_paste(content)
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    paste_id = generate_paste_id(content)
    paste = {
        'id': paste_id,
        'title': data.get('title'),
        'content': content,
        'language': data.get('language', 'auto'),
        'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'size': len(content)
    }
    
    pastes = load_pastes()
    pastes.insert(0, paste)
    save_pastes(pastes)
    
    return jsonify({'id': paste_id, 'paste': paste})

if __name__ == '__main__':
    print("... launching private texts")
    print("... at http://localhost:5002")
    print("... With love, from Home Lab")
    app.run(host='0.0.0.0', port=5005, debug=True)