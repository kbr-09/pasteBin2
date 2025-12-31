#!/usr/bin/env python3
import os
import json
import hashlib
import datetime

from flask import (
    Flask,
    request,
    redirect,
    url_for,
    render_template,
    abort,
    jsonify,
    Response,
    send_from_directory,
)

app = Flask(__name__, static_folder="static", template_folder="templates")
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


# Serve JS from /scripts/app.js (your preferred structure)
@app.route("/scripts/<path:filename>")
def scripts(filename):
    return send_from_directory("scripts", filename)


@app.route("/", methods=["GET"])
def index():
    init_storage()

    page = int(request.args.get("page", 1))
    pastes = load_pastes()

    total_pastes = len(pastes)
    total_pages = (total_pastes + MAX_PASTES_PER_PAGE - 1) // MAX_PASTES_PER_PAGE

    # clamp page (prevents empty weirdness if you pass ?page=999)
    if total_pages == 0:
        total_pages = 1
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages

    start_idx = (page - 1) * MAX_PASTES_PER_PAGE
    end_idx = start_idx + MAX_PASTES_PER_PAGE
    page_pastes = pastes[start_idx:end_idx]

    message = request.args.get("message", "")
    message_type = request.args.get("type", "success")

    return render_template(
        "index.html",
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

    return redirect(
        url_for("index", message=f"Paste created successfully! ID: {paste_id}", type="success")
    )


@app.route("/paste/<paste_id>", methods=["GET"])
def view_paste(paste_id):
    pastes = load_pastes()
    paste = next((p for p in pastes if p.get("id") == paste_id), None)
    if not paste:
        abort(404)

    return render_template(
        "view.html",
        title=f"Paste {paste_id}",
        paste_id=paste_id,
        paste_content=paste.get("content", ""),
    )


@app.route("/raw/<paste_id>", methods=["GET"])
def raw_paste(paste_id):
    pastes = load_pastes()
    paste = next((p for p in pastes if p.get("id") == paste_id), None)
    if not paste:
        abort(404)
    return Response(paste.get("content", ""), mimetype="text/plain; charset=utf-8")


@app.route("/delete/<paste_id>", methods=["GET"])
def delete_paste(paste_id):
    pastes = load_pastes()
    original_count = len(pastes)
    pastes = [p for p in pastes if p.get("id") != paste_id]

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
    print(f"... at http://192.168.1.106:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=True)
