#!/usr/bin/env python3
import os
import json
import hashlib
import datetime
from flask import Flask, request, redirect, url_for, render_template_string, abort, jsonify, Response

app = Flask(__name__)
app.secret_key = os.urandom(32)

# Configuration
PASTE_STORAGE_DIR = os.path.join(os.path.dirname(__file__), "pastes")
PASTE_FILE = os.path.join(PASTE_STORAGE_DIR, "pastes.json")
MAX_PASTE_SIZE = 50000
MAX_PASTES_PER_PAGE = 20
PORT = 5002

os.makedirs(PASTE_STORAGE_DIR, exist_ok=True)


def init_storage():
    if not os.path.exists(PASTE_FILE):
        with open(PASTE_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def load_pastes():
    try:
        with open(PASTE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_pastes(pastes):
    temp_file = PASTE_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(pastes, f, indent=2)
    os.replace(temp_file, PASTE_FILE)


def generate_paste_id(content: str) -> str:
    return hashlib.md5(content.encode("utf-8")).hexdigest()[:8]


def detect_language(text: str):
    if text.startswith("import ") or "def " in text:
        return "python"
    if "function(" in text or "console.log(" in text:
        return "javascript"
    if "<" in text and "</" in text:
        return "html"
    return None


def validate_paste(content: str):
    if not content or not content.strip():
        return False, "Content cannot be empty"
    if len(content) > MAX_PASTE_SIZE:
        return False, f"Content too large. Maximum size is {MAX_PASTE_SIZE} characters"
    return True, ""


INDEX_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{{ title }}</title>
  <style>
    * { margin:0; padding:0; box-sizing:border-box; }
    body {
      font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
      color:#333;
      background: linear-gradient(-45deg, hsla(60, 1%, 37%, 1) 0%, hsla(25, 33%, 17%, 1) 100%);
      min-height:100vh;
    }
    .container { max-width:1200px; margin:0 auto; padding:20px; }
    .header { text-align:center; color:#EDEDE9; margin-bottom:30px; }
    .header h1 { font-size:1.5rem; margin-bottom:8px; }

    .alert { padding:12px 16px; border-radius:8px; margin-bottom:16px; }
    .alert-success { background:#d4edda; border:1px solid #c3e6cb; color:#155724; }
    .alert-error { background:#f8d7da; border:1px solid #f5c6cb; color:#721c24; }

    .paste-form {
      background:#fff; border-radius:15px; padding:20px;
      box-shadow:0 10px 30px rgba(0,0,0,0.2);
      margin-bottom:24px;
    }
    .form-group { margin-bottom:14px; }
    label { display:block; margin-bottom:6px; font-weight:600; color:#555; }
    input, textarea, select {
      width:100%; padding:12px; border:2px solid #e1e5e9; border-radius:8px; font-size:14px;
    }
    textarea { min-height:200px; font-family: 'Monaco','Menlo','Ubuntu Mono',monospace; resize:vertical; }

    .btn {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color:#fff; border:none; border-radius:8px; cursor:pointer;
      padding:10px 18px; font-weight:700; text-decoration:none; display:inline-block;
    }
    .btn-sm { padding:6px 12px; font-size:12px; font-weight:700; }
    .btn-secondary { background: linear-gradient(135deg, #95a5a6 0%, #7f8c8d 100%); }
    .btn-danger { background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%); }

    .paste-item {
      background:#fff; border-radius:15px; padding:18px; margin-bottom:16px;
      box-shadow:0 5px 15px rgba(0,0,0,0.12);
    }
    .paste-header { display:flex; justify-content:space-between; gap:10px; align-items:flex-start; }
    .meta { color:#666; font-size:13px; margin-top:6px; }
    .actions { display:flex; gap:8px; flex-wrap:wrap; }

    .content {
      position: relative;              /* IMPORTANT: anchor absolute copy button */
      margin-top:12px;
      background:#f8f9fa; border:1px solid #e1e5e9; border-radius:8px;
      padding:14px;
      padding-top:44px;                /* give space so button doesn't cover line 1 */
      font-family:'Monaco','Menlo','Ubuntu Mono',monospace;
      white-space:pre-wrap;
      max-height:240px; overflow:auto;
    }

    .copy-btn {
      position:absolute; top:10px; right:10px;
      background: rgba(102, 126, 234, 0.9);
      color:white; border:none; border-radius:6px;
      padding:6px 10px; font-weight:800; cursor:pointer;
    }

    .pagination { display:flex; justify-content:center; gap:10px; margin-top:22px; flex-wrap:wrap; }
    .pagination a, .pagination span {
      padding:8px 14px; border:1px solid #ddd; border-radius:6px; text-decoration:none;
      color:#333; background:#fff;
    }
    .pagination .current { background:#667eea; color:#fff; border-color:#667eea; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>HOMElab TEXTshare</h1>
      <p>Fast (not really), secure (daddy issues though)</p>
    </div>

    {% if message %}
      <div class="alert alert-{{ message_type }}">{{ message }}</div>
    {% endif %}

    <div class="paste-form">
      <h2>New Paste</h2>
      <form method="post" action="{{ url_for('create_paste') }}">
        <div class="form-group">
          <label for="title">Title (optional)</label>
          <input id="title" name="title" type="text" placeholder="Enter a title">
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
          <label for="content">Content</label>
          <textarea id="content" name="content" required placeholder="Paste your code or text here..."></textarea>
        </div>

        <button class="btn" type="submit">Create Paste</button>
      </form>
    </div>

    <h2 style="color:#EDEDE9; margin-bottom:12px;">Recent Pastes</h2>

    {% if pastes %}
      {% for paste in pastes %}
        <div class="paste-item">
          <div class="paste-header">
            <div>
              <h3>{{ paste.title or 'Untitled Paste' }}</h3>
              <div class="meta">
                ID: {{ paste.id }} • {{ paste.created_at }} • {{ paste.language or 'Unknown' }} • {{ paste.size }} chars
              </div>
            </div>

            <div class="actions">
              <a class="btn btn-sm btn-secondary" href="{{ url_for('view_paste', paste_id=paste.id) }}">View</a>
              <a class="btn btn-sm btn-secondary" href="{{ url_for('raw_paste', paste_id=paste.id) }}">Raw</a>
              <a class="btn btn-sm btn-danger" href="{{ url_for('delete_paste', paste_id=paste.id) }}"
                 onclick="return confirm('Delete this paste?')">Delete</a>
            </div>
          </div>

          <div class="content" id="content-{{ paste.id }}">
            {{ paste.content[:200] }}{% if paste.content|length > 200 %}...{% endif %}
            <button class="copy-btn" onclick="copyToClipboard('{{ paste.id }}', this)">📋 Copy</button>
          </div>
        </div>
      {% endfor %}

      {% if total_pages > 1 %}
        <div class="pagination">
          {% if page > 1 %}
            <a href="{{ url_for('index', page=page-1) }}">Previous</a>
          {% endif %}

          {% for pg in range(1, total_pages+1) %}
            {% if pg == page %}
              <span class="current">{{ pg }}</span>
            {% else %}
              <a href="{{ url_for('index', page=pg) }}">{{ pg }}</a>
            {% endif %}
          {% endfor %}

          {% if page < total_pages %}
            <a href="{{ url_for('index', page=page+1) }}">Next</a>
          {% endif %}
        </div>
      {% endif %}
    {% else %}
      <p style="color:#EDEDE9;">No pastes yet.</p>
    {% endif %}
  </div>

  <script>
    function copyToClipboard(pasteId, btn) {
      const node = document.getElementById('content-' + pasteId);
      if (!node) return;

      const clone = node.cloneNode(true);
      const b = clone.querySelector('button.copy-btn');
      if (b) b.remove();

      const text = (clone.innerText || clone.textContent || '').trim();

      const show = () => {
        const old = btn.innerHTML;
        btn.innerHTML = '✅ Copied!';
        setTimeout(() => btn.innerHTML = old, 1600);
      };

      // HTTPS/localhost works reliably; LAN HTTP often blocks it -> fallback below
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(show).catch(() => fallbackCopy(text, show));
      } else {
        fallbackCopy(text, show);
      }
    }

    function fallbackCopy(text, okCb) {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      document.body.appendChild(ta);
      ta.select();
      try {
        const ok = document.execCommand('copy');
        if (ok) okCb();
        else alert('Copy failed (browser blocked it).');
      } catch (e) {
        alert('Copy failed (browser blocked it).');
      } finally {
        document.body.removeChild(ta);
      }
    }
  </script>
</body>
</html>
"""


# ✅ VIEW PAGE: only paste + home/raw/delete/copy
VIEW_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{{ title }}</title>
  <style>
    * { margin:0; padding:0; box-sizing:border-box; }
    body {
      font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
      background: linear-gradient(-45deg, hsla(60, 1%, 37%, 1) 0%, hsla(25, 33%, 17%, 1) 100%);
      min-height:100vh; padding:20px;
    }
    .wrap { max-width:1100px; margin:0 auto; }

    .topbar {
      display:flex; justify-content:space-between; align-items:center; gap:10px;
      margin-bottom:12px; flex-wrap:wrap;
    }
    .title { color:#EDEDE9; font-weight:800; font-size:16px; }

    .btn {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color:#fff; border:none; border-radius:8px; cursor:pointer;
      padding:8px 14px; font-weight:800; text-decoration:none; display:inline-block;
    }
    .btn-secondary { background: linear-gradient(135deg, #95a5a6 0%, #7f8c8d 100%); }
    .btn-danger { background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%); }

    .content {
      background:#fff; border-radius:14px; padding:18px;
      padding-top:44px;
      box-shadow:0 10px 30px rgba(0,0,0,0.25);
      position:relative;
      font-family:'Monaco','Menlo','Ubuntu Mono',monospace;
      white-space:pre-wrap;
      overflow:auto;
      max-height:80vh;
    }

    .copy-btn {
      position:absolute; top:10px; right:10px;
      background: rgba(102, 126, 234, 0.9);
      color:white; border:none; border-radius:6px;
      padding:6px 10px; font-weight:800; cursor:pointer;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <div class="title">Viewing paste: {{ paste_id }}</div>
      <div style="display:flex; gap:10px; flex-wrap:wrap;">
        <a class="btn btn-secondary" href="{{ url_for('index') }}">Home</a>
        <a class="btn btn-secondary" href="{{ url_for('raw_paste', paste_id=paste_id) }}">Raw</a>
        <a class="btn btn-danger" href="{{ url_for('delete_paste', paste_id=paste_id) }}"
           onclick="return confirm('Delete this paste?')">Delete</a>
      </div>
    </div>

    <div class="content" id="paste-content">
{{ paste_content }}
      <button class="copy-btn" onclick="copyPaste(this)">📋 Copy</button>
    </div>
  </div>

  <script>
    function copyPaste(btn) {
      const node = document.getElementById('paste-content');
      if (!node) return;

      const clone = node.cloneNode(true);
      const b = clone.querySelector('button.copy-btn');
      if (b) b.remove();

      const text = (clone.innerText || clone.textContent || '').trim();

      const show = () => {
        const old = btn.innerHTML;
        btn.innerHTML = '✅ Copied!';
        setTimeout(() => btn.innerHTML = old, 1600);
      };

      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(show).catch(() => fallback(text, show));
      } else {
        fallback(text, show);
      }
    }

    function fallback(text, okCb) {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      document.body.appendChild(ta);
      ta.select();
      try {
        const ok = document.execCommand('copy');
        if (ok) okCb();
        else alert('Copy failed (browser blocked it).');
      } catch (e) {
        alert('Copy failed (browser blocked it).');
      } finally {
        document.body.removeChild(ta);
      }
    }
  </script>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    init_storage()

    page = int(request.args.get("page", 1))
    pastes = load_pastes()

    total_pastes = len(pastes)
    total_pages = (total_pastes + MAX_PASTES_PER_PAGE - 1) // MAX_PASTES_PER_PAGE

    start_idx = (page - 1) * MAX_PASTES_PER_PAGE
    end_idx = start_idx + MAX_PASTES_PER_PAGE
    page_pastes = pastes[start_idx:end_idx]

    message = request.args.get("message", "")
    message_type = request.args.get("type", "success")

    return render_template_string(
        INDEX_TEMPLATE,
        title="Modern Paste Service",
        pastes=page_pastes,
        page=page,
        total_pages=total_pages,
        message=message,
        message_type=message_type,
    )


@app.route("/paste", methods=["POST"])
def create_paste():
    content = request.form.get("content", "")
    title = request.form.get("title", "").strip()
    language = request.form.get("language", "auto")

    is_valid, error_msg = validate_paste(content)
    if not is_valid:
        return redirect(url_for("index", message=error_msg, type="error"))

    paste_id = generate_paste_id(content)

    paste = {
        "id": paste_id,
        "title": title if title else None,
        "content": content,
        "language": language if language != "auto" else detect_language(content),
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "size": len(content),
    }

    pastes = load_pastes()
    pastes.insert(0, paste)
    save_pastes(pastes)

    return redirect(url_for("index", message=f"Paste created successfully! ID: {paste_id}", type="success"))


@app.route("/paste/<paste_id>", methods=["GET"])
def view_paste(paste_id):
    pastes = load_pastes()
    paste = next((paste for paste in pastes if paste.get("id") == paste_id), None)
    if not paste:
        abort(404)

    paste_content = paste.get("content", "")

    return render_template_string(
        VIEW_TEMPLATE,
        title=f"Paste {paste_id}",
        paste_id=paste_id,
        paste_content=paste_content,
    )


@app.route("/raw/<paste_id>", methods=["GET"])
def raw_paste(paste_id):
    pastes = load_pastes()
    paste = next((paste for paste in pastes if paste.get("id") == paste_id), None)
    if not paste:
        abort(404)
    return Response(paste.get("content", ""), mimetype="text/plain; charset=utf-8")


@app.route("/delete/<paste_id>", methods=["GET"])
def delete_paste(paste_id):
    pastes = load_pastes()
    original_count = len(pastes)
    pastes = [paste for paste in pastes if paste.get("id") != paste_id]

    if len(pastes) < original_count:
        save_pastes(pastes)
        return redirect(url_for("index", message="Paste deleted successfully!", type="success"))
    return redirect(url_for("index", message="Paste not found!", type="error"))


@app.route("/api/pastes", methods=["GET"])
def api_get_pastes():
    return jsonify(load_pastes())


@app.route("/api/paste", methods=["POST"])
def api_create_paste():
    data = request.get_json(force=True, silent=True) or {}
    content = data.get("content", "")

    is_valid, error_msg = validate_paste(content)
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    paste_id = generate_paste_id(content)
    paste = {
        "id": paste_id,
        "title": data.get("title"),
        "content": content,
        "language": data.get("language", "auto"),
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "size": len(content),
    }

    pastes = load_pastes()
    pastes.insert(0, paste)
    save_pastes(pastes)

    return jsonify({"id": paste_id, "paste": paste})


if __name__ == "__main__":
    print("... launching private texts")
    print(f"... at http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=True)
