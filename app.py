import os
import sqlite3
import uuid
from datetime import datetime
from io import BytesIO

from flask import (
    Flask, request, redirect, url_for, render_template_string,
    send_from_directory, send_file, abort
)
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024 * 10  # up to 50 MB per request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "programs.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_PHOTOS = 10
MAX_PHOTO_SIZE = 5 * 1024 * 1024

TEXT = {
    "en": {
        "title": "CyberPolice Assist",
        "subtitle": "Cyber Awareness Program Management",
        "welcome": "Welcome to CyberPolice Assist",
        "intro": "Manage cyber awareness programs, photographs and reports in one place.",
        "home": "Home", "add_program": "Add Program", "view_programs": "View Programs",
        "all_programs": "All Programs", "total_programs": "Total Programs",
        "total_attendees": "Total Attendees", "date": "Date", "station": "Police Station",
        "place": "Place", "name": "Program Name", "attendees": "Number of Attendees",
        "details": "Program Details", "photos": "Program Photographs", "actions": "Actions",
        "search": "Search by date, station, place or program name", "search_button": "Search",
        "submit": "Save Program", "cancel": "Cancel", "view": "View", "back": "Back to Programs",
        "no_programs": "No programs found. Add your first program to get started.",
        "required": "Please fill in all required fields correctly.",
        "saved": "Program saved successfully.", "not_found": "Program not found.",
        "invalid_photo": "Please upload JPG, PNG or WEBP images only.",
        "too_many": "You can upload up to 10 photographs for one program.",
        "photo_help": "Optional. Select up to 10 JPG, PNG or WEBP images, maximum 5 MB each.",
        "details_placeholder": "Enter program details, topics covered, officers' names, outcomes, etc.",
        "station_placeholder": "Enter police station name", "place_placeholder": "Enter program location",
        "name_placeholder": "Enter program name", "attendees_placeholder": "Enter number of attendees",
        "no_photo": "No photographs uploaded", "program_details": "Program Information",
        "clear_search": "Clear Search", "download_pdf": "Download PDF Report",
        "upload_home": "Homepage Banner Photo", "banner_help": "Optional. This photo appears on the homepage.",
        "save_banner": "Upload Homepage Photo", "banner_saved": "Homepage photo updated.",
        "banner_error": "Please choose a JPG, PNG or WEBP image under 5 MB.",
        "created": "Created", "report": "CYBER AWARENESS PROGRAM REPORT",
        "report_generated": "Generated", "footer": "Cyber Awareness • Community Safety",
        "photo_count": "Photographs", "remove_banner": "Use default homepage",
    },
    "mr": {
        "title": "सायबरपोलीस सहाय्य",
        "subtitle": "सायबर जनजागृती कार्यक्रम व्यवस्थापन",
        "welcome": "सायबरपोलीस सहाय्य मध्ये आपले स्वागत आहे",
        "intro": "सायबर जनजागृती कार्यक्रम, छायाचित्रे आणि अहवाल एकाच ठिकाणी व्यवस्थापित करा.",
        "home": "मुख्यपृष्ठ", "add_program": "कार्यक्रम जोडा", "view_programs": "कार्यक्रम पहा",
        "all_programs": "सर्व कार्यक्रम", "total_programs": "एकूण कार्यक्रम",
        "total_attendees": "एकूण सहभागी", "date": "दिनांक", "station": "पोलीस स्टेशन",
        "place": "ठिकाण", "name": "कार्यक्रमाचे नाव", "attendees": "सहभागी संख्या",
        "details": "कार्यक्रमाची माहिती", "photos": "कार्यक्रमाची छायाचित्रे", "actions": "कृती",
        "search": "दिनांक, स्टेशन, ठिकाण किंवा नाव शोधा", "search_button": "शोधा",
        "submit": "कार्यक्रम जतन करा", "cancel": "रद्द करा", "view": "पहा",
        "back": "कार्यक्रमांकडे परत जा",
        "no_programs": "कार्यक्रम आढळला नाही. सुरू करण्यासाठी पहिला कार्यक्रम जोडा.",
        "required": "कृपया सर्व आवश्यक माहिती योग्यरीत्या भरा.",
        "saved": "कार्यक्रम यशस्वीपणे जतन झाला.", "not_found": "कार्यक्रम आढळला नाही.",
        "invalid_photo": "फक्त JPG, PNG किंवा WEBP छायाचित्रे अपलोड करा.",
        "too_many": "एका कार्यक्रमासाठी जास्तीत जास्त 10 छायाचित्रे अपलोड करू शकता.",
        "photo_help": "पर्यायी. कमाल 10 JPG, PNG किंवा WEBP छायाचित्रे, प्रत्येक 5 MB पर्यंत.",
        "details_placeholder": "कार्यक्रमाची माहिती, विषय, अधिकाऱ्यांची नावे, निष्कर्ष इत्यादी लिहा.",
        "station_placeholder": "पोलीस स्टेशनचे नाव लिहा", "place_placeholder": "कार्यक्रमाचे ठिकाण लिहा",
        "name_placeholder": "कार्यक्रमाचे नाव लिहा", "attendees_placeholder": "सहभागी संख्या लिहा",
        "no_photo": "छायाचित्रे अपलोड केलेली नाहीत", "program_details": "कार्यक्रमाची माहिती",
        "clear_search": "शोध काढा", "download_pdf": "PDF अहवाल डाउनलोड करा",
        "upload_home": "मुख्यपृष्ठाचे छायाचित्र", "banner_help": "पर्यायी. हे छायाचित्र मुख्यपृष्ठावर दिसेल.",
        "save_banner": "मुख्यपृष्ठाचे छायाचित्र अपलोड करा", "banner_saved": "मुख्यपृष्ठाचे छायाचित्र बदलले.",
        "banner_error": "कृपया 5 MB पेक्षा कमी JPG, PNG किंवा WEBP छायाचित्र निवडा.",
        "created": "तयार केले", "report": "सायबर जनजागृती कार्यक्रम अहवाल",
        "report_generated": "अहवाल तयार केला", "footer": "सायबर जनजागृती • समुदाय सुरक्षा",
        "photo_count": "छायाचित्रे", "remove_banner": "मूळ मुख्यपृष्ठ वापरा",
    }
}

# A simple homepage banner can be changed through the home page form.
DEFAULT_BANNER = ""

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
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
            FOREIGN KEY(program_id) REFERENCES programs(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT DEFAULT ''
        )
    """)
    # Migrate any legacy single photo into the multiple-photo table.
    old_rows = conn.execute(
        "SELECT id, photo FROM programs WHERE COALESCE(photo, '') != ''"
    ).fetchall()
    for row in old_rows:
        exists = conn.execute(
            "SELECT 1 FROM program_photos WHERE program_id=? AND filename=?",
            (row["id"], row["photo"])
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO program_photos(program_id, filename) VALUES (?, ?)",
                (row["id"], row["photo"])
            )
    conn.commit()
    conn.close()

init_db()

def get_language():
    lang = request.values.get("lang", "en")
    return lang if lang in TEXT else "en"

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def render_page(page, lang="en", **kwargs):
    values = {
        "page": page, "lang": lang, "t": TEXT[lang],
        "message": kwargs.pop("message", ""),
        "error": kwargs.pop("error", False),
        "banner": kwargs.pop("banner", ""),
    }
    values.update(kwargs)
    return render_template_string(PAGE, **values)

PAGE = r"""
<!DOCTYPE html>
<html lang="{{ 'mr' if lang == 'mr' else 'en' }}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ t.title }}</title>
<style>
:root{--bg:#101512;--panel:#19221c;--panel2:#202b23;--green:#69d68b;--text:#edf3ee;--muted:#a9b7ac;--border:#34443a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:Arial,Helvetica,sans-serif;line-height:1.6}
a{color:var(--green);text-decoration:none}a:hover{text-decoration:underline}
.header{background:#171e19;border-bottom:1px solid var(--border);padding:16px 22px}
.header-inner{max-width:1100px;margin:auto;display:flex;align-items:center;justify-content:space-between;gap:15px;flex-wrap:wrap}
.brand{font-size:23px;font-weight:bold;color:var(--green)}.brand-subtitle{color:var(--muted);font-size:12px}
.language{display:flex;gap:8px}.language a{padding:5px 11px;border:1px solid var(--border);border-radius:5px;color:var(--text);font-size:13px}.language a.active{border-color:var(--green);color:var(--green)}
.container{max-width:1100px;margin:26px auto;padding:0 18px}.welcome{margin-bottom:20px}.welcome h1{font-size:27px;margin:0 0 4px}.welcome p{margin:0;color:var(--muted)}
.banner{width:100%;max-height:280px;object-fit:cover;border-radius:8px;border:1px solid var(--border);margin:8px 0 20px}
.stats{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin:20px 0}
.stat-card{background:var(--panel);border:1px solid var(--border);border-radius:8px;padding:17px}.stat-label{color:var(--muted);font-size:13px}.stat-value{font-size:27px;font-weight:bold;color:var(--green)}
.actions{display:flex;gap:10px;flex-wrap:wrap;margin:20px 0}
.button{display:inline-block;background:var(--green);color:#102016;border:1px solid var(--green);border-radius:5px;padding:10px 15px;font-size:14px;font-weight:bold;cursor:pointer;text-align:center}
.button:hover{background:#86e4a2;color:#102016;text-decoration:none}.button.secondary{background:transparent;color:var(--green)}.button.secondary:hover{background:var(--panel2)}
.panel{background:var(--panel);border:1px solid var(--border);border-radius:8px;margin:20px 0;overflow:hidden}.panel-header{padding:14px 18px;border-bottom:1px solid var(--border)}.panel-header h2{font-size:19px;margin:0}.panel-body{padding:18px}
.message{padding:11px 14px;border:1px solid #38794b;border-radius:5px;background:#1b3223;color:#b8f5c8;margin-bottom:16px}.message.error{background:#382020;border-color:#824545;color:#ffc4c4}
.search-form{display:flex;gap:10px;margin-bottom:16px}.search-form input{flex:1;min-width:0}
input,textarea{width:100%;background:#101713;border:1px solid var(--border);border-radius:5px;padding:11px 12px;color:var(--text);font:14px Arial,sans-serif}
input:focus,textarea:focus{outline:none;border-color:var(--green)}textarea{min-height:130px;resize:vertical}
label{display:block;margin-bottom:6px;font-size:14px;font-weight:bold}.form-group{margin-bottom:17px}.help{color:var(--muted);font-size:12px;margin-top:5px}
.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;min-width:650px}th{text-align:left;background:var(--panel2);color:var(--green);font-size:12px;text-transform:uppercase}th,td{padding:12px;border-bottom:1px solid var(--border)}td{font-size:14px}tbody tr:hover{background:#202a23}.empty{padding:25px;text-align:center;color:var(--muted)}
.badge{display:inline-block;padding:4px 9px;border-radius:4px;background:#243a2b;color:var(--green);font-size:12px}
.detail-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.detail-item{background:#121914;border:1px solid var(--border);padding:13px;border-radius:5px;overflow-wrap:anywhere}.detail-label{color:var(--muted);font-size:12px;margin-bottom:4px}.detail-value{font-size:15px;font-weight:bold;white-space:pre-wrap}
.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-top:10px}.gallery img{width:100%;height:190px;object-fit:cover;border-radius:6px;border:1px solid var(--border);background:#0b100d}
.footer{border-top:1px solid var(--border);text-align:center;color:var(--muted);padding:20px;margin-top:36px;font-size:12px}
@media(max-width:650px){.container{margin-top:18px;padding:0 12px}.welcome h1{font-size:23px}.stats,.detail-grid{grid-template-columns:1fr}.panel-body{padding:13px}.search-form{flex-direction:column}.search-form .button{width:100%}}
</style>
</head>
<body>
<header class="header"><div class="header-inner">
<div><div class="brand">● {{ t.title }}</div><div class="brand-subtitle">{{ t.subtitle }}</div></div>
<div class="language">
<a href="{{ url_for('home', lang='en') }}" class="{{ 'active' if lang=='en' else '' }}">English</a>
<a href="{{ url_for('home', lang='mr') }}" class="{{ 'active' if lang=='mr' else '' }}">मराठी</a>
</div></div></header>
<main class="container">
{% if message %}<div class="message {{ 'error' if error else '' }}">{{ message }}</div>{% endif %}
{% if page == 'home' %}
<section class="welcome"><h1>{{ t.welcome }}</h1><p>{{ t.intro }}</p></section>
{% if banner %}<img class="banner" src="{{ url_for('uploaded_file', filename=banner) }}" alt="Homepage banner">{% endif %}
<div class="stats">
<div class="stat-card"><div class="stat-label">{{ t.total_programs }}</div><div class="stat-value">{{ total_programs }}</div></div>
<div class="stat-card"><div class="stat-label">{{ t.total_attendees }}</div><div class="stat-value">{{ total_attendees }}</div></div>
</div>
<div class="actions">
<a class="button" href="{{ url_for('add_program', lang=lang) }}">+ {{ t.add_program }}</a>
<a class="button secondary" href="#programs">{{ t.view_programs }}</a>
</div>
<section class="panel"><div class="panel-header"><h2>{{ t.all_programs }}</h2></div><div class="panel-body">
<form class="search-form" method="GET" action="{{ url_for('home') }}">
<input type="hidden" name="lang" value="{{ lang }}"><input name="q" value="{{ query }}" placeholder="{{ t.search }}">
<button class="button" type="submit">{{ t.search_button }}</button></form>
{% if query %}<p><a href="{{ url_for('home', lang=lang) }}">{{ t.clear_search }}</a></p>{% endif %}
{% if programs %}<div class="table-wrap"><table><thead><tr><th>#</th><th>{{ t.date }}</th><th>{{ t.station }}</th><th>{{ t.place }}</th><th>{{ t.name }}</th><th>{{ t.attendees }}</th><th>{{ t.actions }}</th></tr></thead><tbody>
{% for p in programs %}<tr><td>{{ loop.index }}</td><td>{{ p.date }}</td><td>{{ p.station }}</td><td>{{ p.place }}</td><td>{{ p.name }}</td><td>{{ p.attendees }}</td><td><a class="badge" href="{{ url_for('program_details', program_id=p.id, lang=lang) }}">{{ t.view }}</a></td></tr>{% endfor %}
</tbody></table></div>{% else %}<div class="empty">{{ t.no_programs }}</div>{% endif %}
</div></section>
<section class="panel"><div class="panel-header"><h2>{{ t.upload_home }}</h2></div><div class="panel-body">
<form method="POST" action="{{ url_for('set_banner', lang=lang) }}" enctype="multipart/form-data">
<div class="form-group"><label for="banner_photo">{{ t.upload_home }}</label><input id="banner_photo" type="file" name="banner_photo" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"><div class="help">{{ t.banner_help }}</div></div>
<div class="actions"><button class="button" type="submit">{{ t.save_banner }}</button><button class="button secondary" type="submit" name="reset" value="1">{{ t.remove_banner }}</button></div>
</form></div></section>
{% elif page == 'add' %}
<section class="welcome"><h1>{{ t.add_program }}</h1><p>{{ t.subtitle }}</p></section>
<section class="panel"><div class="panel-header"><h2>{{ t.add_program }}</h2></div><div class="panel-body">
<form method="POST" action="{{ url_for('add_program', lang=lang) }}" enctype="multipart/form-data">
<div class="form-group"><label for="date">{{ t.date }} *</label><input id="date" type="date" name="date" value="{{ form.get('date','') }}" required></div>
<div class="form-group"><label for="station">{{ t.station }} *</label><input id="station" name="station" value="{{ form.get('station','') }}" placeholder="{{ t.station_placeholder }}" maxlength="150" required></div>
<div class="form-group"><label for="place">{{ t.place }} *</label><input id="place" name="place" value="{{ form.get('place','') }}" placeholder="{{ t.place_placeholder }}" maxlength="200" required></div>
<div class="form-group"><label for="name">{{ t.name }} *</label><input id="name" name="name" value="{{ form.get('name','') }}" placeholder="{{ t.name_placeholder }}" maxlength="200" required></div>
<div class="form-group"><label for="attendees">{{ t.attendees }} *</label><input id="attendees" type="number" name="attendees" value="{{ form.get('attendees','0') }}" min="0" max="10000000" required></div>
<div class="form-group"><label for="details">{{ t.details }}</label><textarea id="details" name="details" maxlength="15000" placeholder="{{ t.details_placeholder }}">{{ form.get('details','') }}</textarea></div>
<div class="form-group"><label for="photos">{{ t.photos }}</label><input id="photos" type="file" name="photos" multiple accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"><div class="help">{{ t.photo_help }}</div></div>
<div class="actions"><button class="button" type="submit">{{ t.submit }}</button><a class="button secondary" href="{{ url_for('home',lang=lang) }}">{{ t.cancel }}</a></div>
</form></div></section>
{% elif page == 'details' %}
<section class="welcome"><h1>{{ program.name }}</h1><p>{{ t.program_details }}</p></section>
<section class="panel"><div class="panel-header"><h2>{{ t.program_details }}</h2></div><div class="panel-body">
<div class="detail-grid">
<div class="detail-item"><div class="detail-label">{{ t.date }}</div><div class="detail-value">{{ program.date }}</div></div>
<div class="detail-item"><div class="detail-label">{{ t.station }}</div><div class="detail-value">{{ program.station }}</div></div>
<div class="detail-item"><div class="detail-label">{{ t.place }}</div><div class="detail-value">{{ program.place }}</div></div>
<div class="detail-item"><div class="detail-label">{{ t.attendees }}</div><div class="detail-value">{{ program.attendees }}</div></div>
</div>
<div class="form-group" style="margin-top:18px"><label>{{ t.details }}</label><div style="white-space:pre-wrap;overflow-wrap:anywhere">{{ program.details or '—' }}</div></div>
<div class="form-group"><label>{{ t.photos }}</label>
{% if photos %}<div class="gallery">{% for photo in photos %}<a href="{{ url_for('uploaded_file',filename=photo.filename) }}" target="_blank" rel="noopener"><img src="{{ url_for('uploaded_file',filename=photo.filename) }}" alt="Program photograph"></a>{% endfor %}</div>{% else %}<p>{{ t.no_photo }}</p>{% endif %}
</div>
<div class="actions"><a class="button" href="{{ url_for('download_pdf',program_id=program.id,lang=lang) }}">{{ t.download_pdf }}</a><a class="button secondary" href="{{ url_for('home',lang=lang) }}">{{ t.back }}</a></div>
</div></section>
{% endif %}
</main><footer class="footer">{{ t.footer }}</footer>
</body></html>
"""

@app.route("/")
def home():
    lang = get_language()
    query = request.args.get("q", "").strip()
    conn = get_db()
    total_programs = conn.execute("SELECT COUNT(*) FROM programs").fetchone()[0]
    total_attendees = conn.execute("SELECT COALESCE(SUM(attendees),0) FROM programs").fetchone()[0]
    if query:
        term = f"%{query}%"
        programs = conn.execute("""SELECT * FROM programs
            WHERE date LIKE ? OR station LIKE ? OR place LIKE ? OR name LIKE ?
            ORDER BY date DESC, id DESC""", (term, term, term, term)).fetchall()
    else:
        programs = conn.execute("SELECT * FROM programs ORDER BY date DESC,id DESC").fetchall()
    setting = conn.execute("SELECT value FROM settings WHERE key='homepage_banner'").fetchone()
    conn.close()
    msg = TEXT[lang]["saved"] if request.args.get("saved") == "1" else ""
    if request.args.get("banner_saved") == "1":
        msg = TEXT[lang]["banner_saved"]
    return render_page("home", lang, programs=programs, total_programs=total_programs,
                       total_attendees=total_attendees, query=query,
                       banner=setting["value"] if setting else "", message=msg)

@app.route("/add", methods=["GET", "POST"])
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
            if attendees < 0 or attendees > 10000000:
                raise ValueError
        except (ValueError, TypeError):
            return render_page("add", lang, form=form, message=TEXT[lang]["required"], error=True), 400
        if not all([station, place, name]):
            return render_page("add", lang, form=form, message=TEXT[lang]["required"], error=True), 400
        uploads = [f for f in request.files.getlist("photos") if f and f.filename]
        if len(uploads) > MAX_PHOTOS:
            return render_page("add", lang, form=form, message=TEXT[lang]["too_many"], error=True), 400
        for f in uploads:
            if not allowed_file(f.filename):
                return render_page("add", lang, form=form, message=TEXT[lang]["invalid_photo"], error=True), 400
            f.stream.seek(0, os.SEEK_END)
            size = f.stream.tell()
            f.stream.seek(0)
            if size > MAX_PHOTO_SIZE:
                return render_page("add", lang, form=form, message=TEXT[lang]["invalid_photo"], error=True), 400
        saved_files = []
        try:
            for f in uploads:
                ext = secure_filename(f.filename).rsplit(".", 1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"
                f.save(os.path.join(UPLOAD_FOLDER, filename))
                saved_files.append(filename)
            conn = get_db()
            cur = conn.execute("""INSERT INTO programs(date,station,place,name,attendees,details,photo)
                VALUES(?,?,?,?,?,?,?)""", (date, station, place, name, attendees, details,
                                             saved_files[0] if saved_files else ""))
            program_id = cur.lastrowid
            for filename in saved_files:
                conn.execute("INSERT INTO program_photos(program_id,filename) VALUES(?,?)",
                             (program_id, filename))
            conn.commit()
            conn.close()
        except Exception:
            for filename in saved_files:
                try:
                    os.remove(os.path.join(UPLOAD_FOLDER, filename))
                except OSError:
                    pass
            raise
        return redirect(url_for("home", lang=lang, saved=1))
    return render_page("add", lang, form={})

@app.route("/program/<int:program_id>")
def program_details(program_id):
    lang = get_language()
    conn = get_db()
    program = conn.execute("SELECT * FROM programs WHERE id=?", (program_id,)).fetchone()
    photos = conn.execute("SELECT filename FROM program_photos WHERE program_id=? ORDER BY id",
                          (program_id,)).fetchall()
    conn.close()
    if program is None:
        abort(404)
    return render_page("details", lang, program=program, photos=photos)

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    safe = os.path.basename(filename)
    if safe != filename:
        abort(404)
    return send_from_directory(UPLOAD_FOLDER, safe)

@app.route("/settings/banner", methods=["POST"])
def set_banner():
    lang = get_language()
    conn = get_db()
    if request.form.get("reset") == "1":
        conn.execute("DELETE FROM settings WHERE key='homepage_banner'")
        conn.commit()
        conn.close()
        return redirect(url_for("home", lang=lang, banner_saved=1))
    f = request.files.get("banner_photo")
    if not f or not f.filename or not allowed_file(f.filename):
        conn.close()
        return redirect(url_for("home", lang=lang))
    f.stream.seek(0, os.SEEK_END)
    size = f.stream.tell()
    f.stream.seek(0)
    if size > MAX_PHOTO_SIZE:
        conn.close()
        return redirect(url_for("home", lang=lang))
    ext = secure_filename(f.filename).rsplit(".", 1)[1].lower()
    filename = f"banner_{uuid.uuid4().hex}.{ext}"
    f.save(os.path.join(UPLOAD_FOLDER, filename))
    conn.execute("""INSERT INTO settings(key,value) VALUES('homepage_banner',?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value""", (filename,))
    conn.commit()
    conn.close()
    return redirect(url_for("home", lang=lang, banner_saved=1))

@app.route("/program/<int:program_id>/pdf")
def download_pdf(program_id):
    # ReportLab must be listed in requirements.txt.
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
        )
    except ImportError:
        return ("PDF support is not installed. Add 'reportlab' to requirements.txt and redeploy.", 500)

    lang = get_language()
    t = TEXT[lang]
    conn = get_db()
    program = conn.execute("SELECT * FROM programs WHERE id=?", (program_id,)).fetchone()
    photos = conn.execute("SELECT filename FROM program_photos WHERE program_id=? ORDER BY id",
                          (program_id,)).fetchall()
    conn.close()
    if program is None:
        abort(404)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm,
                            topMargin=17*mm, bottomMargin=17*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitleCustom", parent=styles["Title"],
                              fontName="Helvetica-Bold", fontSize=17, leading=22,
                              alignment=TA_CENTER, textColor=colors.HexColor("#236b3b"),
                              spaceAfter=8))
    styles.add(ParagraphStyle(name="SmallCustom", parent=styles["Normal"],
                              fontSize=9, leading=13, textColor=colors.HexColor("#444444")))
    story = [
        Paragraph(t["report"], styles["ReportTitleCustom"]),
        Paragraph(t["title"], styles["Heading2"]),
        Spacer(1, 5*mm),
    ]
    rows = [
        [t["date"], program["date"]],
        [t["station"], program["station"]],
        [t["place"], program["place"]],
        [t["name"], program["name"]],
        [t["attendees"], str(program["attendees"])],
        [t["details"], (program["details"] or "—").replace("\n", "<br/>")],
        [t["photo_count"], str(len(photos))],
    ]
    safe_rows = []
    from xml.sax.saxutils import escape
    for label, value in rows:
        safe_rows.append([
            Paragraph(f"<b>{escape(str(label))}</b>", styles["SmallCustom"]),
            Paragraph(escape(str(value)).replace("\n", "<br/>"), styles["SmallCustom"])
        ])
    table = Table(safe_rows, colWidths=[42*mm, 125*mm], repeatRows=0)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#e8f3eb")),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#b8c9bc")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    story.extend([table, Spacer(1, 7*mm)])
    for index, photo in enumerate(photos, start=1):
        path = os.path.join(UPLOAD_FOLDER, photo["filename"])
        if os.path.isfile(path):
            try:
                img = Image(path)
                img._restrictSize(165*mm, 85*mm)
                story.append(Paragraph(f"{t['photos']} {index}", styles["Heading3"]))
                story.append(img)
                story.append(Spacer(1, 4*mm))
            except Exception:
                pass
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph(f"{t['report_generated']}: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                           styles["SmallCustom"]))
    doc.build(story)
    buffer.seek(0)
    filename = f"program_report_{program_id}.pdf"
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=filename)

@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
