from flask import Flask, request, render_template_string, redirect, url_for
from datetime import datetime
from werkzeug.utils import secure_filename
import os
import sqlite3
import uuid

app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DATABASE = os.path.join(BASE_DIR, "programs.db")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

TEXT = {
    "en": {
        "title": "CyberPolice Assist",
        "subtitle": "Police Program Management System",
        "dashboard": "Dashboard",
        "add": "Add Program",
        "register": "Program Register",
        "search": "Search programs",
        "date": "Program Date",
        "station": "Police Station",
        "place": "Program Place",
        "name": "Program Name",
        "attendees": "Number of Attendees",
        "details": "Program Details",
        "photo": "Program Photo",
        "save": "Save Program",
        "all": "All Programs",
        "total": "Total Programs",
        "people": "Total Attendees",
        "find": "Search",
        "view": "View Details",
        "no": "No programs found.",
        "required": "Please complete all required fields.",
        "success": "Program saved successfully.",
        "back": "Back to Register",
        "language": "मराठी",
        "description": "Organize program records, photographs and reports.",
        "delete": "Delete",
        "confirm": "Delete this program?",
        "photo_note": "JPG, PNG or WEBP; maximum 5 MB.",
        "search_hint": "Search by date, station, place or program name",
        "details_title": "Program Information",
        "not_found": "Program not found.",
        "footer": "Digital Program Register",
        "upload_error": "Please upload a valid image under 5 MB."
    },
    "mr": {
        "title": "सायबर पोलीस सहाय्य",
        "subtitle": "पोलीस कार्यक्रम व्यवस्थापन प्रणाली",
        "dashboard": "मुख्यपृष्ठ",
        "add": "कार्यक्रम जोडा",
        "register": "कार्यक्रम नोंदवही",
        "search": "कार्यक्रम शोधा",
        "date": "कार्यक्रमाची तारीख",
        "station": "पोलीस स्टेशन",
        "place": "कार्यक्रमाचे ठिकाण",
        "name": "कार्यक्रमाचे नाव",
        "attendees": "उपस्थितांची संख्या",
        "details": "कार्यक्रमाचा तपशील",
        "photo": "कार्यक्रमाचा फोटो",
        "save": "कार्यक्रम जतन करा",
        "all": "सर्व कार्यक्रम",
        "total": "एकूण कार्यक्रम",
        "people": "एकूण उपस्थित",
        "find": "शोधा",
        "view": "तपशील पहा",
        "no": "कोणताही कार्यक्रम आढळला नाही.",
        "required": "कृपया सर्व आवश्यक माहिती भरा.",
        "success": "कार्यक्रम यशस्वीपणे जतन झाला.",
        "back": "नोंदवहीकडे परत जा",
        "language": "English",
        "description": "कार्यक्रमांची माहिती, फोटो आणि नोंदी व्यवस्थापित करा.",
        "delete": "हटवा",
        "confirm": "हा कार्यक्रम हटवायचा आहे का?",
        "photo_note": "JPG, PNG किंवा WEBP; कमाल ५ MB.",
        "search_hint": "तारीख, पोलीस स्टेशन, ठिकाण किंवा नावाने शोधा",
        "details_title": "कार्यक्रमाची माहिती",
        "not_found": "कार्यक्रम सापडला नाही.",
        "footer": "डिजिटल कार्यक्रम नोंदवही",
        "upload_error": "कृपया ५ MB पेक्षा कमी आकाराचा योग्य फोटो निवडा."
    }
}

def connect_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS programs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                station TEXT NOT NULL,
                place TEXT NOT NULL,
                name TEXT NOT NULL,
                attendees INTEGER NOT NULL DEFAULT 0,
                details TEXT NOT NULL,
                photo TEXT,
                created_at TEXT NOT NULL
            )
        """)

init_db()

PAGE = """
<!DOCTYPE html>
<html lang="{{ 'mr' if lang == 'mr' else 'en' }}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ t.title }}</title>
<style>
:root {
  --bg:#0b1220; --panel:#131e30; --panel2:#1a2940;
  --text:#eef4ff; --muted:#a6b6ce; --line:#30415c;
  --blue:#3182f6; --green:#1eb980; --red:#e45b68;
}
* {box-sizing:border-box}
body {
  margin:0;background:var(--bg);color:var(--text);
  font-family:Arial,"Noto Sans Devanagari",sans-serif;
}
header {
  padding:20px 5%;background:#111c2d;border-bottom:1px solid var(--line);
  display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap;
}
.brand {font-size:24px;font-weight:bold}
.brand span {color:#61a5ff}
.sub {font-size:13px;color:var(--muted);margin-top:7px}
a {color:inherit;text-decoration:none}
button,.btn {
  border:0;border-radius:9px;padding:12px 16px;
  font-weight:bold;cursor:pointer;display:inline-block;
}
.primary {background:var(--blue);color:white}
.secondary {background:var(--panel2);color:white;border:1px solid var(--line)}
.danger {background:#562833;color:#fff}
main {max-width:1150px;margin:25px auto;padding:0 18px}
.welcome {margin-bottom:22px}
.welcome h1 {font-size:27px;margin-bottom:8px}
.muted {color:var(--muted);line-height:1.6}
.stats {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:15px;margin:20px 0}
.stat,.card {
  background:var(--panel);border:1px solid var(--line);
  border-radius:15px;padding:20px;min-width:0;
}
.stat strong {display:block;font-size:28px;margin-top:12px}
.stat small {color:var(--muted)}
.actions {display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px}
h2 {font-size:20px;margin-top:0}
form {display:grid;gap:15px}
label {font-size:14px;font-weight:bold;display:block;margin-bottom:7px}
input,textarea {
  width:100%;padding:13px;border-radius:8px;border:1px solid var(--line);
  background:#0c1728;color:white;font-size:16px;
}
textarea {min-height:120px;resize:vertical}
input[type=file] {font-size:14px}
.grid {display:grid;grid-template-columns:1fr 1fr;gap:15px}
.searchbar {display:grid;grid-template-columns:1fr auto;gap:10px;margin-bottom:18px}
.tablewrap {overflow-x:auto}
table {width:100%;border-collapse:collapse;min-width:650px}
th,td {padding:13px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th {font-size:13px;color:#a9caff;background:#18263b}
td {font-size:14px}
.thumb {width:76px;height:58px;object-fit:cover;border-radius:7px}
.notice {padding:13px;border-radius:9px;background:#123d32;color:#b6ffdc;margin-bottom:16px}
.error {background:#54232c;color:#ffd6db}
.badge {background:#203b5e;padding:5px 8px;border-radius:7px}
.detail-photo {max-width:100%;max-height:420px;border-radius:12px}
footer {text-align:center;color:var(--muted);padding:30px 15px;font-size:13px}
@media(max-width:650px) {
  header {padding:16px}
  .brand {font-size:21px}
  main {padding:0 12px;margin-top:18px}
  .stats {grid-template-columns:1fr}
  .stat {padding:15px}
  .grid {grid-template-columns:1fr}
  .welcome h1 {font-size:23px}
}
</style>
</head>
<body>
<header>
  <div>
    <div class="brand">🚔 <span>CyberPolice</span> Assist</div>
    <div class="sub">{{ t.subtitle }}</div>
  </div>
  <a class="btn secondary" href="{{ url_for('home', lang='mr' if lang == 'en' else 'en') }}">
    🌐 {{ t.language }}
  </a>
</header>

<main>
  {% if message %}
    <div class="notice {{ 'error' if error else '' }}">{{ message }}</div>
  {% endif %}

  <section class="welcome">
    <h1>{{ t.dashboard }}</h1>
    <div class="muted">{{ t.description }}</div>
  </section>

  <section class="stats">
    <div class="stat"><small>{{ t.total }}</small><strong>{{ total }}</strong></div>
    <div class="stat"><small>{{ t.people }}</small><strong>{{ people }}</strong></div>
    <div class="stat"><small>{{ t.register }}</small><strong>📋</strong></div>
  </section>

  <div class="actions">
    <a class="btn primary" href="{{ url_for('add_program', lang=lang) }}">＋ {{ t.add }}</a>
    <a class="btn secondary" href="{{ url_for('home', lang=lang) }}">▤ {{ t.register }}</a>
  </div>

  {% if page == 'add' %}
  <section class="card">
    <h2>{{ t.add }}</h2>
    <form method="POST" enctype="multipart/form-data">
      <div class="grid">
        <div><label>{{ t.date }} *</label><input type="date" name="date" required></div>
        <div><label>{{ t.station }} *</label><input name="station" maxlength="120" required></div>
        <div><label>{{ t.place }} *</label><input name="place" maxlength="180" required></div>
        <div><label>{{ t.name }} *</label><input name="name" maxlength="180" required></div>
        <div><label>{{ t.attendees }} *</label><input type="number" name="attendees" min="0" max="1000000" value="0" required></div>
        <div><label>{{ t.photo }}</label><input type="file" name="photo" accept="image/png,image/jpeg,image/webp"><small class="muted">{{ t.photo_note }}</small></div>
      </div>
      <div><label>{{ t.details }} *</label><textarea name="details" maxlength="10000" required></textarea></div>
      <button class="primary" type="submit">{{ t.save }}</button>
    </form>
  </section>
  {% elif page == 'details' %}
  <section class="card">
    <h2>{{ t.details_title }}</h2>
    {% if program %}
      <p><b>{{ t.date }}:</b> {{ program.date }}</p>
      <p><b>{{ t.station }}:</b> {{ program.station }}</p>
      <p><b>{{ t.place }}:</b> {{ program.place }}</p>
      <p><b>{{ t.name }}:</b> {{ program.name }}</p>
      <p><b>{{ t.attendees }}:</b> {{ program.attendees }}</p>
      <p><b>{{ t.details }}:</b><br>{{ program.details }}</p>
      {% if program.photo %}<p><img class="detail-photo" src="{{ url_for('uploaded_file', filename=program.photo) }}" alt="Program photograph"></p>{% endif %}
      <a class="btn secondary" href="{{ url_for('home', lang=lang) }}">{{ t.back }}</a>
    {% else %}
      <p>{{ t.not_found }}</p>
    {% endif %}
  </section>
  {% else %}
  <section class="card">
    <h2>{{ t.all }}</h2>
    <form class="searchbar" method="GET" action="{{ url_for('home') }}">
      <input type="hidden" name="lang" value="{{ lang }}">
      <input type="search" name="q" value="{{ query }}" placeholder="{{ t.search_hint }}">
      <button class="primary" type="submit">{{ t.find }}</button>
    </form>
    <div class="tablewrap">
      <table>
        <thead><tr>
          <th>#</th><th>{{ t.date }}</th><th>{{ t.station }}</th>
          <th>{{ t.place }}</th><th>{{ t.name }}</th>
          <th>{{ t.attendees }}</th><th>{{ t.photo }}</th><th></th>
        </tr></thead>
        <tbody>
        {% for p in programs %}
          <tr>
            <td>{{ p.id }}</td><td>{{ p.date }}</td><td>{{ p.station }}</td>
            <td>{{ p.place }}</td><td>{{ p.name }}</td><td>{{ p.attendees }}</td>
            <td>{% if p.photo %}<img class="thumb" src="{{ url_for('uploaded_file', filename=p.photo) }}" alt="Program photo">{% else %}—{% endif %}</td>
            <td><a class="btn secondary" href="{{ url_for('program_details', program_id=p.id, lang=lang) }}">{{ t.view }}</a></td>
          </tr>
        {% else %}
          <tr><td colspan="8">{{ t.no }}</td></tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
  </section>
  {% endif %}
</main>
<footer>{{ t.footer }} · CyberPolice Assist</footer>
</body>
</html>
"""

def render_page(page="home", lang="en", programs=None, program=None,
                query="", message="", error=False, total=0, people=0):
    lang = "mr" if lang == "mr" else "en"
    return render_template_string(
        PAGE, page=page, lang=lang, t=TEXT[lang],
        programs=programs or [], program=program, query=query,
        message=message, error=error, total=total, people=people
    )

@app.route("/")
def home():
    lang = request.args.get("lang", "en")
    query = request.args.get("q", "").strip()
    with connect_db() as conn:
        if query:
            pattern = "%" + query + "%"
            programs = conn.execute("""
                SELECT * FROM programs
                WHERE date LIKE ? OR station LIKE ? OR place LIKE ? OR name LIKE ?
                ORDER BY date DESC, id DESC
            """, (pattern, pattern, pattern, pattern)).fetchall()
        else:
            programs = conn.execute(
                "SELECT * FROM programs ORDER BY date DESC, id DESC"
            ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM programs").fetchone()[0]
        people = conn.execute(
            "SELECT COALESCE(SUM(attendees),0) FROM programs"
        ).fetchone()[0]
    return render_page(programs=programs, query=query, lang=lang,
                       total=total, people=people)

@app.route("/add", methods=["GET", "POST"])
def add_program():
    lang = request.args.get("lang", "en")
    if request.method == "POST":
        date = request.form.get("date", "").strip()
        station = request.form.get("station", "").strip()
        place = request.form.get("place", "").strip()
        name = request.form.get("name", "").strip()
        details = request.form.get("details", "").strip()

        try:
            attendees = int(request.form.get("attendees", "0"))
            valid_attendees = 0 <= attendees <= 1000000
        except ValueError:
            attendees = 0
            valid_attendees = False

        try:
            datetime.strptime(date, "%Y-%m-%d")
            valid_date = True
        except ValueError:
            valid_date = False

        if not all([date, station, place, name, details]) or not valid_date or not valid_attendees:
            return render_page(page="add", lang=lang,
                               message=TEXT[lang]["required"], error=True)

        photo = request.files.get("photo")
        photo_name = None
        if photo and photo.filename:
            if photo.mimetype not in ("image/jpeg", "image/png", "image/webp") or not photo.mimetype.startswith("image/"):
                return render_page(page="add", lang=lang,
                                   message=TEXT[lang]["upload_error"], error=True)
            photo_bytes = photo.read(5 * 1024 * 1024 + 1)
            if len(photo_bytes) > 5 * 1024 * 1024:
                return render_page(page="add", lang=lang,
                                   message=TEXT[lang]["upload_error"], error=True)
            extension = {
                "image/jpeg": ".jpg",
                "image/png": ".png",
                "image/webp": ".webp"
            }.get(photo.mimetype)
            photo_name = uuid.uuid4().hex + extension
            with open(os.path.join(UPLOAD_FOLDER, secure_filename(photo_name)), "wb") as f:
                f.write(photo_bytes)

        with connect_db() as conn:
            conn.execute("""
                INSERT INTO programs
                (date, station, place, name, attendees, details, photo, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (date, station, place, name, attendees, details, photo_name,
                  datetime.utcnow().isoformat()))

        return redirect(url_for("home", lang=lang, saved="1"))

    return render_page(page="add", lang=lang)

@app.route("/program/<int:program_id>")
def program_details(program_id):
    lang = request.args.get("lang", "en")
    with connect_db() as conn:
        program = conn.execute(
            "SELECT * FROM programs WHERE id = ?", (program_id,)
        ).fetchone()
        total = conn.execute("SELECT COUNT(*) FROM programs").fetchone()[0]
        people = conn.execute(
            "SELECT COALESCE(SUM(attendees),0) FROM programs"
        ).fetchone()[0]
    return render_page(page="details", lang=lang, program=program,
                       total=total, people=people)

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    from flask import send_from_directory
    return send_from_directory(UPLOAD_FOLDER, secure_filename(filename))

@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
