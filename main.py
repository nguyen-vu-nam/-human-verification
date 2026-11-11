import os
import re
import sqlite3
import secrets
import hmac
from urllib.parse import urlparse, urlencode, parse_qsl, urlunparse
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, send_from_directory, url_for, session,
    flash, abort
)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "links.db")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-secret-key-before-deploying")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
)

app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True


@app.after_request
def no_cache(resp):
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp


SLUG_RE = re.compile(r"^[a-zA-Z0-9_-]{2,40}$")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                destination TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL,
                query_string TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def valid_destination(value):
    try:
        parsed = urlparse(value.strip())
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


@app.before_request
def protect_admin_posts():
    if request.method == "POST" and request.path.startswith("/admin"):
        expected = session.get("_csrf_token", "")
        supplied = request.form.get("_csrf_token", "")
        if not expected or not supplied or not hmac.compare_digest(expected, supplied):
            abort(400)


@app.context_processor
def inject_csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_urlsafe(32)
    return {"csrf_token": session["_csrf_token"]}


def append_tracking_params(destination, incoming_query):
    """Append incoming tracking parameters without overwriting destination parameters."""
    if not incoming_query:
        return destination
    parsed = urlparse(destination)
    existing = parse_qsl(parsed.query, keep_blank_values=True)
    existing_keys = {k for k, _ in existing}
    incoming = [
        (k, v) for k, v in parse_qsl(incoming_query, keep_blank_values=True)
        if k not in existing_keys
    ]
    merged = existing + incoming
    return urlunparse(parsed._replace(query=urlencode(merged, doseq=True)))


@app.route("/")
def home():
    return render_template("index.html", link_name="Trang chủ", slug=None)


@app.route("/admin/login")
def admin_login():
    return redirect(url_for("admin_dashboard"))


@app.route("/admin", methods=["GET", "POST"])
def admin_dashboard():
    if request.method == "POST":
        action = request.form.get("action", "create")
        name = request.form.get("name", "").strip()
        slug = request.form.get("slug", "").strip().lstrip("/")
        destination = request.form.get("destination", "").strip()
        enabled = 1 if request.form.get("enabled") == "on" else 0

        if action == "delete":
            link_id = request.form.get("id", type=int)
            with db() as conn:
                conn.execute("DELETE FROM links WHERE id = ?", (link_id,))
            flash("Đã xóa liên kết.", "success")
            return redirect(url_for("admin_dashboard"))

        if action == "toggle":
            link_id = request.form.get("id", type=int)
            with db() as conn:
                conn.execute("UPDATE links SET enabled = CASE enabled WHEN 1 THEN 0 ELSE 1 END WHERE id = ?", (link_id,))
            flash("Đã cập nhật trạng thái.", "success")
            return redirect(url_for("admin_dashboard"))

        if not name or not SLUG_RE.fullmatch(slug):
            flash("Tên link không được để trống; mã đường dẫn chỉ gồm chữ, số, _ hoặc -, dài 2–40 ký tự.", "error")
        elif not valid_destination(destination):
            flash("URL đích phải bắt đầu bằng http:// hoặc https:// và có hostname hợp lệ.", "error")
        else:
            try:
                with db() as conn:
                    if action == "update":
                        link_id = request.form.get("id", type=int)
                        conn.execute(
                            "UPDATE links SET name=?, slug=?, destination=?, enabled=? WHERE id=?",
                            (name, slug, destination, enabled, link_id)
                        )
                        flash("Đã cập nhật liên kết.", "success")
                    else:
                        conn.execute(
                            "INSERT INTO links (name, slug, destination, enabled) VALUES (?, ?, ?, ?)",
                            (name, slug, destination, enabled)
                        )
                        flash("Đã tạo liên kết.", "success")
                return redirect(url_for("admin_dashboard"))
            except sqlite3.IntegrityError:
                flash("Mã đường dẫn này đã tồn tại. Hãy chọn mã khác.", "error")

    with db() as conn:
        links = conn.execute("""
            SELECT l.*, (SELECT COUNT(*) FROM visits v WHERE v.slug=l.slug) AS visits
            FROM links l ORDER BY l.id DESC
        """).fetchall()
    edit_id = request.args.get("edit", type=int)
    edit_link = None
    if edit_id:
        edit_link = next((item for item in links if item["id"] == edit_id), None)
    return render_template("admin.html", mode="dashboard", links=links, edit_link=edit_link)


@app.route("/<slug>")
def landing(slug):
    if slug in ("admin", "static", "favicon.ico"):
        abort(404)
    with db() as conn:
        link = conn.execute(
            "SELECT * FROM links WHERE slug=? AND enabled=1", (slug,)
        ).fetchone()
        if not link:
            abort(404)
        conn.execute(
            "INSERT INTO visits (slug, query_string) VALUES (?, ?)",
            (slug, request.query_string.decode("utf-8", errors="replace"))
        )
    return render_template(
        "index.html",
        link_name=link["name"],
        slug=slug,
        tracking_query=request.query_string.decode("utf-8", errors="replace")
    )


@app.route("/go/<slug>")
def go(slug):
    with db() as conn:
        link = conn.execute(
            "SELECT * FROM links WHERE slug=? AND enabled=1", (slug,)
        ).fetchone()
    if not link:
        abort(404)
    target = append_tracking_params(link["destination"], request.query_string.decode("utf-8", errors="replace"))
    return redirect(target, code=302)


@app.errorhandler(404)
def not_found(_error):
    return render_template("not_found.html"), 404

@app.route("/logo.png")
def serve_template_logo():
    return send_from_directory(
        app.template_folder,
        "logo.png"
    )
init_db()

if __name__ == "__main__":
    # For local testing only. Put behind HTTPS/reverse proxy for public deployment.
    app.run(host="127.0.0.1", port=5000, debug=False)
