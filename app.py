import os
import sqlite3
import hmac
import uuid
from datetime import datetime, timedelta
from functools import wraps
from io import BytesIO
from xml.sax.saxutils import escape

from flask import (
    Flask, request, redirect, url_for, render_template_string,
    send_from_directory, send_file, abort, session, flash
)
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "")
if not app.config["SECRET_KEY"]:
    # Set SECRET_KEY in Render environment variables for stable sessions.
    app.config["SECRET_KEY"] = uuid.uuid4().hex + uuid.uuid4().hex

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "programs.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_PHOTOS = 10
MAX_PHOTO_SIZE = 5 * 1024 * 1024

# Set ADMIN_USERNAME and ADMIN_PASSWORD in Render -> Environment.
# Do not put your real password directly in this file or in GitHub.
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

TEXT = {
    "en": {
        "title": "CyberPolice Assist", "subtitle": "Cyber Awareness Program Management",
        "login": "Administrator Login", "username": "Username", "password": "Password",
        "sign_in": "Sign In", "logout": "Log Out", "login_error": "Invalid username or password.",
        "welcome": "Welcome to CyberPolice Assist",
        "intro": "Private program records, photographs and reports.",
        "add_program": "Add Program", "all_programs": "All Programs",
        "total_programs": "Total Programs", "total_attendees": "Total Attendees",
        "date": "Date", "station": "Police Station", "place": "Place",
        "name": "Program Name", "attendees": "Number of Attendees",
        "details": "Program Details", "photos": "Program Photographs", "actions": "Actions",
        "search": "Search by date, station, place or program name", "search_button": "Search",
        "submit": "Save Program", "save_changes": "Save Changes", "cancel": "Cancel",
        "view": "View", "edit": "Edit", "delete": "Delete", "back": "Back to Programs",
        "no_programs": "No programs found. Add your first program to get started.",
        "required": "Please fill in all required fields correctly.",
        "saved": "Program saved successfully.", "updated": "Program updated successfully.",
        "not_found": "Program not found.", "invalid_photo": "Upload JPG, PNG or WEBP images under 5 MB each.",
        "too_many": "You can upload up to 10 photographs for one program in total.",
        "photo_help": "Optional. Select up to 10 JPG, PNG or WEBP images, maximum 5 MB each.",
        "details_placeholder": "Enter program details, topics covered, officers' names, outcomes, etc.",
        "station_placeholder": "Enter police station name", "place_placeholder": "Enter program location",
        "name_placeholder": "Enter program name", "no_photo": "No photographs uploaded",
        "program_details": "Program Information", "clear_search": "Clear Search",
        "download_pdf": "Download PDF Report", "confirm_delete": "Delete this program and its photographs? This cannot be undone.",
        "deleted": "Program deleted.", "existing_photos": "Existing photographs",
        "add_more_photos": "Add more photographs", "footer": "Private Admin Area • Cyber Awareness",
        "not_configured": "Admin password is not configured. Set ADMIN_PASSWORD in Render environment variables.",
        "created": "Created", "report": "CYBER AWARENESS PROGRAM REPORT",
        "report_generated": "Generated", "photo_page": "PROGRAM PHOTOGRAPHS",
        "page_info": "Page 1 contains program information. Photographs start on the next page.",
    },
    "mr": {
        "title": "सायबरपोलीस सहाय्य", "subtitle": "सायबर जनजागृती कार्यक्रम व्यवस्थापन",
        "login": "प्रशासक लॉगिन", "username": "वापरकर्तानाव", "password": "पासवर्ड",
        "sign_in": "लॉगिन करा", "logout": "लॉगआउट", "login_error": "वापरकर्तानाव किंवा पासवर्ड चुकीचा आहे.",
        "welcome": "सायबरपोलीस सहाय्य मध्ये आपले स्वागत आहे",
        "intro": "खासगी कार्यक्रम नोंदी, छायाचित्रे आणि अहवाल.",
        "add_program": "कार्यक्रम जोडा", "all_programs": "सर्व कार्यक्रम",
        "total_programs": "एकूण कार्यक्रम", "total_attendees": "एकूण सहभागी",
        "date": "दिनांक", "station": "पोलीस स्टेशन", "place": "ठिकाण",
        "name": "कार्यक्रमाचे नाव", "attendees": "सहभागी संख्या",
        "details": "कार्यक्रमाची माहिती", "photos": "कार्यक्रमाची छायाचित्रे", "actions": "कृती",
        "search": "दिनांक, स्टेशन, ठिकाण किंवा नाव शोधा", "search_button": "शोधा",
        "submit": "कार्यक्रम जतन करा", "save_changes": "बदल जतन करा", "cancel": "रद्द करा",
        "view": "पहा", "edit": "संपादित करा", "delete": "हटवा", "back": "कार्यक्रमांकडे परत जा",
        "no_programs": "कार्यक्रम आढळला नाही. पहिला कार्यक्रम जोडा.",
        "required": "कृपया सर्व आवश्यक माहिती योग्यरीत्या भरा.",
        "saved": "कार्यक्रम यशस्वीपणे जतन झाला.", "updated": "कार्यक्रम अद्ययावत झाला.",
        "not_found": "कार्यक्रम आढळला नाही.", "invalid_photo": "प्रत्येक 5 MB पेक्षा कमी JPG, PNG किंवा WEBP छायाचित्रे अपलोड करा.",
        "too_many": "एका कार्यक्रमासाठी एकूण जास्तीत जास्त 10 छायाचित्रे अपलोड करू शकता.",
        "photo_help": "पर्यायी. कमाल 10 छायाचित्रे, प्रत्येक 5 MB पर्यंत.",
        "details_placeholder": "कार्यक्रमाची माहिती, विषय, अधिकाऱ्यांची नावे, निष्कर्ष इत्यादी लिहा.",
        "station_placeholder": "पोलीस स्टेशनचे नाव लिहा", "place_placeholder": "कार्यक्रमाचे ठिकाण लिहा",
        "name_placeholder": "कार्यक्रमाचे नाव लिहा", "no_photo": "छायाचित्रे अपलोड केलेली नाहीत",
        "program_details": "कार्यक्रमाची माहिती", "clear_search": "शोध काढा",
        "download_pdf": "PDF अहवाल डाउनलोड करा", "confirm_delete": "हा कार्यक्रम आणि छायाचित्रे हटवायची? ही कृती पूर्ववत करता येणार नाही.",
        "deleted": "कार्यक्रम हटवला.", "existing_photos": "सध्याची छायाचित्रे",
        "add_more_photos": "अधिक छायाचित्रे जोडा", "footer": "खासगी प्रशासक विभाग • सायबर जनजागृती",
        "not_configured": "प्रशासक पासवर्ड सेट केलेला नाही. Render मध्ये ADMIN_PASSWORD सेट करा.",
        "created": "तयार केले", "report": "सायबर जनजागृती कार्यक्रम अहवाल",
        "report_generated": "अहवाल तयार केला", "photo_page": "कार्यक्रमाची छायाचित्रे",
        "page_info": "पहिल्या पानावर कार्यक्रमाची माहिती आहे. पुढील पानावर छायाचित्रे सुरू होतील.",
    }
}

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS programs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            station TEXT NOT NULL,
            place TEXT NOT NULL,
            name TEXT NOT NULL,
            attendees INTEGER NOT NULL DEFAULT 0,
            details TEXT DEFAULT '',
            photo TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS program_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            program_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            FOREIGN KEY(program_id) REFERENCES programs(id) ON DELETE CASCADE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT DEFAULT ''
        )
    """)
    # Preserve old one-photo records by migrating their photo into the gallery table.
    old_rows = conn.execute(
        "SELECT id, photo FROM programs WHERE COALESCE(photo, '') != ''"
    ).fetchall()
    for row in old_rows:
        found = conn.execute(
            "SELECT 1 FROM program_photos WHERE program_id=? AND filename=?",
            (row["id"], row["photo"])
        ).fetchone()
        if not found:
            conn.execute(
                "INSERT INTO program_photos(program_id,filename) VALUES (?,?)",
                (row["id"], row["photo"])
            )
    conn.commit()
    conn.close()

init_db()

def logged_in():
    return session.get("admin_logged_in") is True

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not logged_in():
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapped

def get_language():
    lang = request.values.get("lang", request.args.get("lang", "en"))
    return lang if lang in TEXT else "en"

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def render_page(page, lang="en", **kwargs):
    values = {
        "page": page, "lang": lang, "t": TEXT[lang],
        "message": kwargs.pop("message", ""),
        "error": kwargs.pop("error", False),
    }
    values.update(kwargs)
    return render_template_string(PAGE, **values)

PAGE = r"""
<!DOCTYPE html><html lang="{{ 'mr' if lang == 'mr' else 'en' }}"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ t.title }}</title>
<style>
:root{--bg:#101512;--panel:#19221c;--panel2:#202b23;--green:#69d68b;--text:#edf3ee;--muted:#a9b7ac;--border:#34443a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:Arial,Helvetica,sans-serif;line-height:1.6}
a{color:var(--green);text-decoration:none}a:hover{text-decoration:underline}
.header{background:#171e19;border-bottom:1px solid var(--border);padding:16px 22px}.header-inner{max-width:1100px;margin:auto;display:flex;align-items:center;justify-content:space-between;gap:15px;flex-wrap:wrap}
.brand{font-size:23px;font-weight:bold;color:var(--green)}.brand-subtitle{color:var(--muted);font-size:12px}.nav{display:flex;gap:9px;align-items:center;flex-wrap:wrap}.nav a{padding:6px 10px;border:1px solid var(--border);border-radius:5px}
.container{max-width:1100px;margin:26px auto;padding:0 18px}.welcome{margin-bottom:20px}.welcome h1{font-size:27px;margin:0 0 4px}.welcome p{margin:0;color:var(--muted)}
.stats{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin:20px 0}.stat-card{background:var(--panel);border:1px solid var(--border);border-radius:8px;padding:17px}.stat-label{color:var(--muted);font-size:13px}.stat-value{font-size:27px;font-weight:bold;color:var(--green)}
.actions{display:flex;gap:10px;flex-wrap:wrap;margin:20px 0}.button{display:inline-block;background:var(--green);color:#102016;border:1px solid var(--green);border-radius:5px;padding:10px 15px;font-size:14px;font-weight:bold;cursor:pointer;text-align:center}.button:hover{background:#86e4a2;color:#102016;text-decoration:none}.button.secondary{background:transparent;color:var(--green)}.button.danger{background:#4a2424;border-color:#8b4a4a;color:#ffdada}
.panel{background:var(--panel);border:1px solid var(--border);border-radius:8px;margin:20px 0;overflow:hidden}.panel-header{padding:14px 18px;border-bottom:1px solid var(--border)}.panel-header h2{font-size:19px;margin:0}.panel-body{padding:18px}
.message{padding:11px 14px;border:1px solid #38794b;border-radius:5px;background:#1b3223;color:#b8f5c8;margin-bottom:16px}.message.error{background:#382020;border-color:#824545;color:#ffc4c4}
input,textarea{width:100%;background:#101713;border:1px solid var(--border);border-radius:5px;padding:11px 12px;color:var(--text);font:14px Arial,sans-serif}input:focus,textarea:focus{outline:none;border-color:var(--green)}textarea{min-height:125px;resize:vertical}label{display:block;margin-bottom:6px;font-size:14px;font-weight:bold}.form-group{margin-bottom:17px}.help{color:var(--muted);font-size:12px;margin-top:5px}
.search-form{display:flex;gap:10px;margin-bottom:16px}.search-form input{flex:1;min-width:0}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;min-width:650px}th{text-align:left;background:var(--panel2);color:var(--green);font-size:12px;text-transform:uppercase}th,td{padding:12px;border-bottom:1px solid var(--border)}td{font-size:14px}tbody tr:hover{background:#202a23}.empty{padding:25px;text-align:center;color:var(--muted)}
.badge{display:inline-block;padding:4px 9px;border-radius:4px;background:#243a2b;color:var(--green);font-size:12px}.detail-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.detail-item{background:#121914;border:1px solid var(--border);padding:13px;border-radius:5px;overflow-wrap:anywhere}.detail-label{color:var(--muted);font-size:12px;margin-bottom:4px}.detail-value{font-size:15px;font-weight:bold;white-space:pre-wrap}
.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-top:10px}.gallery img{width:100%;height:190px;object-fit:cover;border-radius:6px;border:1px solid var(--border);background:#0b100d}
.login-box{max-width:420px;margin:55px auto}.footer{border-top:1px solid var(--border);text-align:center;color:var(--muted);padding:20px;margin-top:36px;font-size:12px}
@media(max-width:650px){.container{margin-top:18px;padding:0 12px}.welcome h1{font-size:23px}.stats,.detail-grid{grid-template-columns:1fr}.panel-body{padding:13px}.search-form{flex-direction:column}.search-form .button{width:100%}}
</style></head><body>
<header class="header"><div class="header-inner"><div><div class="brand">● {{ t.title }}</div><div class="brand-subtitle">{{ t.subtitle }}</div></div>
<div class="nav">{% if logged_in %}<a href="{{ url_for('home',lang=lang) }}">{{ t.all_programs }}</a><a href="{{ url_for('add_program',lang=lang) }}">{{ t.add_program }}</a><a href="{{ url_for('logout',lang=lang) }}">{{ t.logout }}</a>{% endif %}
<a href="{{ url_for('login' if page == 'login' else 'home',lang='en') }}">English</a><a href="{{ url_for('login' if page == 'login' else 'home',lang='mr') }}">मराठी</a></div></div></header>
<main class="container">{% if message %}<div class="message {{ 'error' if error else '' }}">{{ message }}</div>{% endif %}
{% if page == 'login' %}
<div class="login-box"><section class="panel"><div class="panel-header"><h2>{{ t.login }}</h2></div><div class="panel-body">
{% if not admin_configured %}<div class="message error">{{ t.not_configured }}</div>{% endif %}
<form method="POST" action="{{ url_for('login',lang=lang) }}">
<input type="hidden" name="next" value="{{ next_url }}">
<div class="form-group"><label for="username">{{ t.username }}</label><input id="username" name="username" autocomplete="username" required autofocus></div>
<div class="form-group"><label for="password">{{ t.password }}</label><input id="password" type="password" name="password" autocomplete="current-password" required></div>
<button class="button" type="submit" {% if not admin_configured %}disabled{% endif %}>{{ t.sign_in }}</button>
</form></div></section></div>
{% elif page == 'home' %}
<section class="welcome"><h1>{{ t.welcome }}</h1><p>{{ t.intro }}</p></section>
<div class="stats"><div class="stat-card"><div class="stat-label">{{ t.total_programs }}</div><div class="stat-value">{{ total_programs }}</div></div><div class="stat-card"><div class="stat-label">{{ t.total_attendees }}</div><div class="stat-value">{{ total_attendees }}</div></div></div>
<div class="actions"><a class="button" href="{{ url_for('add_program',lang=lang) }}">+ {{ t.add_program }}</a></div>
<section class="panel"><div class="panel-header"><h2>{{ t.all_programs }}</h2></div><div class="panel-body">
<form class="search-form" method="GET" action="{{ url_for('home') }}"><input type="hidden" name="lang" value="{{ lang }}"><input name="q" value="{{ query }}" placeholder="{{ t.search }}"><button class="button" type="submit">{{ t.search_button }}</button></form>
{% if query %}<p><a href="{{ url_for('home',lang=lang) }}">{{ t.clear_search }}</a></p>{% endif %}
{% if programs %}<div class="table-wrap"><table><thead><tr><th>#</th><th>{{ t.date }}</th><th>{{ t.station }}</th><th>{{ t.place }}</th><th>{{ t.name }}</th><th>{{ t.attendees }}</th><th>{{ t.actions }}</th></tr></thead><tbody>
{% for p in programs %}<tr><td>{{ loop.index }}</td><td>{{ p.date }}</td><td>{{ p.station }}</td><td>{{ p.place }}</td><td>{{ p.name }}</td><td>{{ p.attendees }}</td><td><a class="badge" href="{{ url_for('program_details',program_id=p.id,lang=lang) }}">{{ t.view }}</a> <a class="badge" href="{{ url_for('edit_program',program_id=p.id,lang=lang) }}">{{ t.edit }}</a></td></tr>{% endfor %}
</tbody></table></div>{% else %}<div class="empty">{{ t.no_programs }}</div>{% endif %}</div></section>
{% elif page == 'form' %}
<section class="welcome"><h1>{{ t.add_program if mode == 'add' else t.edit }}</h1></section>
<section class="panel"><div class="panel-header"><h2>{{ t.add_program if mode == 'add' else t.edit }}</h2></div><div class="panel-body">
<form method="POST" enctype="multipart/form-data" action="{{ form_action }}">
<div class="form-group"><label>{{ t.date }} *</label><input type="date" name="date" value="{{ form.get('date','') }}" required></div>
<div class="form-group"><label>{{ t.station }} *</label><input name="station" value="{{ form.get('station','') }}" maxlength="150" placeholder="{{ t.station_placeholder }}" required></div>
<div class="form-group"><label>{{ t.place }} *</label><input name="place" value="{{ form.get('place','') }}" maxlength="200" placeholder="{{ t.place_placeholder }}" required></div>
<div class="form-group"><label>{{ t.name }} *</label><input name="name" value="{{ form.get('name','') }}" maxlength="200" placeholder="{{ t.name_placeholder }}" required></div>
<div class="form-group"><label>{{ t.attendees }} *</label><input type="number" name="attendees" value="{{ form.get('attendees','0') }}" min="0" max="10000000" required></div>
<div class="form-group"><label>{{ t.details }}</label><textarea name="details" maxlength="15000" placeholder="{{ t.details_placeholder }}">{{ form.get('details','') }}</textarea></div>
{% if mode == 'edit' and photos %}<div class="form-group"><label>{{ t.existing_photos }}</label><div class="gallery">{% for photo in photos %}<a href="{{ url_for('uploaded_file',filename=photo.filename) }}" target="_blank" rel="noopener"><img src="{{ url_for('uploaded_file',filename=photo.filename) }}" alt="Program photo"></a>{% endfor %}</div></div>{% endif %}
<div class="form-group"><label>{{ t.photos if mode == 'add' else t.add_more_photos }}</label><input type="file" name="photos" multiple accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"><div class="help">{{ t.photo_help }}</div></div>
<div class="actions"><button class="button" type="submit">{{ t.submit if mode == 'add' else t.save_changes }}</button><a class="button secondary" href="{{ url_for('home',lang=lang) }}">{{ t.cancel }}</a></div>
</form></div></section>
{% elif page == 'details' %}
<section class="welcome"><h1>{{ program.name }}</h1><p>{{ t.program_details }}</p></section><section class="panel"><div class="panel-header"><h2>{{ t.program_details }}</h2></div><div class="panel-body">
<div class="detail-grid"><div class="detail-item"><div class="detail-label">{{ t.date }}</div><div class="detail-value">{{ program.date }}</div></div><div class="detail-item"><div class="detail-label">{{ t.station }}</div><div class="detail-value">{{ program.station }}</div></div><div class="detail-item"><div class="detail-label">{{ t.place }}</div><div class="detail-value">{{ program.place }}</div></div><div class="detail-item"><div class="detail-label">{{ t.attendees }}</div><div class="detail-value">{{ program.attendees }}</div></div></div>
<div class="form-group" style="margin-top:18px"><label>{{ t.details }}</label><div style="white-space:pre-wrap;overflow-wrap:anywhere">{{ program.details or '—' }}</div></div>
<div class="form-group"><label>{{ t.photos }}</label>{% if photos %}<div class="gallery">{% for photo in photos %}<a href="{{ url_for('uploaded_file',filename=photo.filename) }}" target="_blank" rel="noopener"><img src="{{ url_for('uploaded_file',filename=photo.filename) }}" alt="Program photograph"></a>{% endfor %}</div>{% else %}<p>{{ t.no_photo }}</p>{% endif %}</div>
<div class="actions"><a class="button" href="{{ url_for('download_pdf',program_id=program.id,lang=lang) }}">{{ t.download_pdf }}</a><a class="button secondary" href="{{ url_for('edit_program',program_id=program.id,lang=lang) }}">{{ t.edit }}</a><a class="button secondary" href="{{ url_for('home',lang=lang) }}">{{ t.back }}</a>
<form method="POST" action="{{ url_for('delete_program',program_id=program.id,lang=lang) }}" onsubmit="return confirm({{ t.confirm_delete|tojson }});"><button class="button danger" type="submit">{{ t.delete }}</button></form></div>
</div></section>
{% endif %}</main><footer class="footer">{{ t.footer }}</footer></body></html>
"""

@app.route("/login", methods=["GET", "POST"])
def login():
    lang = get_language()
    if logged_in():
        return redirect(url_for("home", lang=lang))
    next_url = request.values.get("next", "")
    # Only permit local relative paths as the post-login destination.
    if not next_url.startswith("/") or next_url.startswith("//"):
        next_url = url_for("home", lang=lang)
    message = ""
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if not ADMIN_PASSWORD:
            message = TEXT[lang]["not_configured"]
        elif username == ADMIN_USERNAME and hmac.compare_digest(ADMIN_PASSWORD, password):
            session.clear()
            session["admin_logged_in"] = True
            session["admin_username"] = username
            session.permanent = True
            app.permanent_session_lifetime = timedelta(hours=8)
            return redirect(next_url)
        else:
            message = TEXT[lang]["login_error"]
    return render_page("login", lang, page_endpoint="login", next_url=next_url,
                       admin_configured=bool(ADMIN_PASSWORD), message=message, error=bool(message))

@app.route("/logout")
def logout():
    lang = get_language()
    session.clear()
    return redirect(url_for("login", lang=lang))

@app.route("/")
@login_required
def home():
    lang = get_language()
    query = request.args.get("q", "").strip()
    conn = get_db()
    total_programs = conn.execute("SELECT COUNT(*) FROM programs").fetchone()[0]
    total_attendees = conn.execute("SELECT COALESCE(SUM(attendees),0) FROM programs").fetchone()[0]
    if query:
        term = f"%{query}%"
        programs = conn.execute("""SELECT * FROM programs WHERE date LIKE ? OR station LIKE ? OR place LIKE ? OR name LIKE ? ORDER BY date DESC,id DESC""", (term, term, term, term)).fetchall()
    else:
        programs = conn.execute("SELECT * FROM programs ORDER BY date DESC,id DESC").fetchall()
    conn.close()
    message = ""
    if request.args.get("saved") == "1": message = TEXT[lang]["saved"]
    if request.args.get("updated") == "1": message = TEXT[lang]["updated"]
    if request.args.get("deleted") == "1": message = TEXT[lang]["deleted"]
    return render_page("home", lang, page_endpoint="home", programs=programs,
                       total_programs=total_programs, total_attendees=total_attendees,
                       query=query, message=message)

def validate_and_save_photos(files, existing_count=0):
    uploads = [f for f in files if f and f.filename]
    if existing_count + len(uploads) > MAX_PHOTOS:
        return None, "too_many"
    for f in uploads:
        if not allowed_file(f.filename):
            return None, "invalid_photo"
        f.stream.seek(0, os.SEEK_END)
        size = f.stream.tell()
        f.stream.seek(0)
        if size > MAX_PHOTO_SIZE:
            return None, "invalid_photo"
    names = []
    try:
        for f in uploads:
            ext = secure_filename(f.filename).rsplit(".", 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            f.save(os.path.join(UPLOAD_FOLDER, filename))
            names.append(filename)
    except Exception:
        for name in names:
            try: os.remove(os.path.join(UPLOAD_FOLDER, name))
            except OSError: pass
        raise
    return names, None

@app.route("/add", methods=["GET", "POST"])
@login_required
def add_program():
    lang = get_language()
    if request.method == "POST":
        form = request.form.to_dict()
        date = request.form.get("date", "").strip()
        station = request.form.get("station", "").strip()
        place = request.form.get("place", "").strip()
        name = request.form.get("name", "").strip()
        details = request.form.get("details", "").strip()
        try:
            datetime.strptime(date, "%Y-%m-%d")
            attendees = int(request.form.get("attendees", ""))
            if attendees < 0 or attendees > 10000000: raise ValueError
        except (ValueError, TypeError):
            return render_page("form", lang, page_endpoint="add_program", mode="add", form=form,
                               form_action=url_for("add_program", lang=lang),
                               message=TEXT[lang]["required"], error=True), 400
        if not all([station, place, name]):
            return render_page("form", lang, page_endpoint="add_program", mode="add", form=form,
                               form_action=url_for("add_program", lang=lang),
                               message=TEXT[lang]["required"], error=True), 400
        names, err = validate_and_save_photos(request.files.getlist("photos"))
        if err:
            return render_page("form", lang, page_endpoint="add_program", mode="add", form=form,
                               form_action=url_for("add_program", lang=lang),
                               message=TEXT[lang][err], error=True), 400
        conn = get_db()
        cur = conn.execute("INSERT INTO programs(date,station,place,name,attendees,details,photo) VALUES(?,?,?,?,?,?,?)",
                           (date, station, place, name, attendees, details, names[0] if names else ""))
        pid = cur.lastrowid
        for filename in names:
            conn.execute("INSERT INTO program_photos(program_id,filename) VALUES(?,?)", (pid, filename))
        conn.commit()
        conn.close()
        return redirect(url_for("home", lang=lang, saved=1))
    return render_page("form", lang, page_endpoint="add_program", mode="add", form={},
                       form_action=url_for("add_program", lang=lang))

@app.route("/program/<int:program_id>")
@login_required
def program_details(program_id):
    lang = get_language()
    conn = get_db()
    program = conn.execute("SELECT * FROM programs WHERE id=?", (program_id,)).fetchone()
    photos = conn.execute("SELECT filename FROM program_photos WHERE program_id=? ORDER BY id", (program_id,)).fetchall()
    conn.close()
    if program is None: abort(404)
    return render_page("details", lang, page_endpoint="program_details", program=program, photos=photos)

@app.route("/program/<int:program_id>/edit", methods=["GET", "POST"])
@login_required
def edit_program(program_id):
    lang = get_language()
    conn = get_db()
    program = conn.execute("SELECT * FROM programs WHERE id=?", (program_id,)).fetchone()
    photos = conn.execute("SELECT filename FROM program_photos WHERE program_id=? ORDER BY id", (program_id,)).fetchall()
    if program is None:
        conn.close()
        abort(404)
    if request.method == "POST":
        form = request.form.to_dict()
        date = request.form.get("date", "").strip()
        station = request.form.get("station", "").strip()
        place = request.form.get("place", "").strip()
        name = request.form.get("name", "").strip()
        details = request.form.get("details", "").strip()
        try:
            datetime.strptime(date, "%Y-%m-%d")
            attendees = int(request.form.get("attendees", ""))
            if attendees < 0 or attendees > 10000000: raise ValueError
        except (ValueError, TypeError):
            conn.close()
            return render_page("form", lang, page_endpoint="edit_program", mode="edit", form=form,
                               photos=photos, form_action=url_for("edit_program",program_id=program_id,lang=lang),
                               message=TEXT[lang]["required"], error=True), 400
        if not all([station, place, name]):
            conn.close()
            return render_page("form", lang, page_endpoint="edit_program", mode="edit", form=form,
                               photos=photos, form_action=url_for("edit_program",program_id=program_id,lang=lang),
                               message=TEXT[lang]["required"], error=True), 400
        names, err = validate_and_save_photos(request.files.getlist("photos"), existing_count=len(photos))
        if err:
            conn.close()
            return render_page("form", lang, page_endpoint="edit_program", mode="edit", form=form,
                               photos=photos, form_action=url_for("edit_program",program_id=program_id,lang=lang),
                               message=TEXT[lang][err], error=True), 400
        conn.execute("UPDATE programs SET date=?,station=?,place=?,name=?,attendees=?,details=? WHERE id=?",
                     (date, station, place, name, attendees, details, program_id))
        for filename in names:
            conn.execute("INSERT INTO program_photos(program_id,filename) VALUES(?,?)", (program_id, filename))
        # Keep legacy photo column aligned with the first photo if present.
        first = conn.execute("SELECT filename FROM program_photos WHERE program_id=? ORDER BY id LIMIT 1", (program_id,)).fetchone()
        conn.execute("UPDATE programs SET photo=? WHERE id=?", (first["filename"] if first else "", program_id))
        conn.commit()
        conn.close()
        return redirect(url_for("program_details", program_id=program_id, lang=lang))
    form = dict(program)
    conn.close()
    return render_page("form", lang, page_endpoint="edit_program", mode="edit", form=form, photos=photos,
                       form_action=url_for("edit_program",program_id=program_id,lang=lang))

@app.route("/program/<int:program_id>/delete", methods=["POST"])
@login_required
def delete_program(program_id):
    conn = get_db()
    program = conn.execute("SELECT id FROM programs WHERE id=?", (program_id,)).fetchone()
    photos = conn.execute("SELECT filename FROM program_photos WHERE program_id=?", (program_id,)).fetchall()
    if program is None:
        conn.close()
        abort(404)
    conn.execute("DELETE FROM program_photos WHERE program_id=?", (program_id,))
    conn.execute("DELETE FROM programs WHERE id=?", (program_id,))
    conn.commit()
    conn.close()
    for row in photos:
        try: os.remove(os.path.join(UPLOAD_FOLDER, row["filename"]))
        except OSError: pass
    return redirect(url_for("home", lang=get_language(), deleted=1))

@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    safe = os.path.basename(filename)
    if safe != filename: abort(404)
    return send_from_directory(UPLOAD_FOLDER, safe)

@app.route("/program/<int:program_id>/pdf")
@login_required
def download_pdf(program_id):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
    except ImportError:
        return "PDF support is not installed. Add reportlab to requirements.txt and redeploy.", 500
    lang = get_language()
    t = TEXT[lang]
    conn = get_db()
    program = conn.execute("SELECT * FROM programs WHERE id=?", (program_id,)).fetchone()
    photos = conn.execute("SELECT filename FROM program_photos WHERE program_id=? ORDER BY id", (program_id,)).fetchall()
    conn.close()
    if program is None: abort(404)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm,
                            topMargin=17*mm, bottomMargin=17*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CyberTitle", parent=styles["Title"], fontName="Helvetica-Bold",
                              fontSize=17, leading=22, alignment=1, textColor=colors.HexColor("#236b3b"), spaceAfter=8))
    styles.add(ParagraphStyle(name="CyberSmall", parent=styles["Normal"], fontSize=9, leading=13))
    styles.add(ParagraphStyle(name="CyberPhotoTitle", parent=styles["Heading2"], alignment=1,
                              textColor=colors.HexColor("#236b3b"), spaceAfter=10))
    story = [
        Paragraph(escape(t["report"]), styles["CyberTitle"]),
        Paragraph(escape(t["title"]), styles["Heading2"]),
        Spacer(1, 5*mm),
    ]
    rows = [
        [t["date"], program["date"]],
        [t["station"], program["station"]],
        [t["place"], program["place"]],
        [t["name"], program["name"]],
        [t["attendees"], str(program["attendees"])],
        [t["details"], program["details"] or "—"],
        [t["photo_count"] if "photo_count" in t else ("Photographs" if lang == "en" else "छायाचित्रे"), str(len(photos))],
    ]
    safe_rows = []
    for label, value in rows:
        safe_rows.append([
            Paragraph("<b>" + escape(str(label)) + "</b>", styles["CyberSmall"]),
            Paragraph(escape(str(value)).replace("\n", "<br/>"), styles["CyberSmall"])
        ])
    table = Table(safe_rows, colWidths=[42*mm, 125*mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#e8f3eb")),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#b8c9bc")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 8), ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 7), ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    story.append(table)
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(escape(t["page_info"]), styles["CyberSmall"]))
    if photos:
        story.append(PageBreak())
        story.append(Paragraph(escape(t["photo_page"]), styles["CyberPhotoTitle"]))
        # Start photos on page 2. Keep one photo per block; pages continue as needed.
        for index, photo in enumerate(photos, start=1):
            path = os.path.join(UPLOAD_FOLDER, photo["filename"])
            if not os.path.isfile(path):
                continue
            try:
                img = Image(path)
                img._restrictSize(165*mm, 220*mm)
                story.append(KeepTogether([
                    Paragraph(f"{escape(t['photos'])} {index}", styles["Heading3"]),
                    img,
                    Spacer(1, 5*mm)
                ]))
            except Exception:
                continue
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(escape(t["report_generated"]) + ": " + datetime.now().strftime("%Y-%m-%d %H:%M"),
                           styles["CyberSmall"]))
    doc.build(story)
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True,
                     download_name=f"program_report_{program_id}.pdf")

@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store"
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
