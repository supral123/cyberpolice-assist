from flask import Flask, request, render_template_string, redirect, url_for
from datetime import datetime
from werkzeug.utils import secure_filename
from markupsafe import escape
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
        "subtitle": "CYBER CRIME MANAGEMENT SYSTEM",
        "dashboard": "Cyber Operations Center",
        "add": "Add Program",
        "register": "Program Register",
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
        "required": "Please complete all required fields correctly.",
        "success": "Program saved successfully.",
        "back": "Back to Register",
        "language": "मराठी",
        "description": "Manage cyber awareness programs, photographs and reports.",
        "photo_note": "JPG, PNG or WEBP; maximum 5 MB.",
        "search_hint": "Search by date, station, place or program name",
        "details_title": "Program Information",
        "not_found": "Program not found.",
        "footer": "Digital Program Register",
        "upload_error": "Please upload a valid image under 5 MB.",
        "online": "INTERFACE ONLINE",
        "terminal": "SYSTEM TERMINAL",
        "ready": "Program management interface ready.",
        "programs_label": "PROGRAM DATABASE",
        "attendees_label": "REGISTERED ATTENDEES"
    },
    "mr": {
        "title": "सायबर पोलीस सहाय्य",
        "subtitle": "सायबर गुन्हे व्यवस्थापन प्रणाली",
        "dashboard": "सायबर ऑपरेशन्स केंद्र",
        "add": "कार्यक्रम जोडा",
        "register": "कार्यक्रम नोंदवही",
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
        "required": "कृपया सर्व आवश्यक माहिती योग्यरित्या भरा.",
        "success": "कार्यक्रम यशस्वीपणे जतन झाला.",
        "back": "नोंदवहीकडे परत जा",
        "language": "English",
        "description": "कार्यक्रम, फोटो आणि नोंदी व्यवस्थापित करा.",
        "photo_note": "JPG, PNG किंवा WEBP; कमाल ५ MB.",
        "search_hint": "तारीख, पोलीस स्टेशन, ठिकाण किंवा नावाने शोधा",
        "details_title": "कार्यक्रमाची माहिती",
        "not_found": "कार्यक्रम सापडला नाही.",
        "footer": "डिजिटल कार्यक्रम नोंदवही",
        "upload_error": "कृपया ५ MB पेक्षा कमी आकाराचा योग्य फोटो निवडा.",
        "online": "प्रणाली सुरू आहे",
        "terminal": "प्रणाली माहिती",
        "ready": "कार्यक्रम व्यवस्थापन प्रणाली तयार आहे.",
        "programs_label": "कार्यक्रम नोंदी",
        "attendees_label": "नोंदणीकृत उपस्थित"
    }
}

def connect_db():
    conn = sqlite3.connect(DATABASE, timeout=20)
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


PAGE = r"""
<!DOCTYPE html>
<html lang="{{ 'mr' if lang == 'mr' else 'en' }}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#030705">
<title>{{ t.title }}</title>

<style>
:root {
    --bg: #030705;
    --panel: #09130d;
    --panel2: #0d1e13;
    --green: #00ff88;
    --text: #e4ffed;
    --muted: #8cac98;
    --border: #19472f;
    --red: #ff6677;
}

* {
    box-sizing: border-box;
}

html {
    scroll-behavior: smooth;
}

body {
    margin: 0;
    min-height: 100vh;
    background-color: var(--bg);
    background-image:
        linear-gradient(#00ff8808 1px, transparent 1px),
        linear-gradient(90deg, #00ff8808 1px, transparent 1px);
    background-size: 30px 30px;
    color: var(--text);
    font-family: Consolas, "Courier New", monospace;
}

a {
    color: var(--green);
    text-decoration: none;
}

header {
    position: relative;
    padding: 22px 5%;
    background: #050b07;
    border-bottom: 1px solid var(--green);
    box-shadow: 0 3px 25px #00ff8810;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 18px;
}

.brand {
    font-size: 25px;
    font-weight: bold;
    letter-spacing: 1px;
}

.brand span {
    color: var(--green);
    text-shadow: 0 0 14px #00ff8870;
}

.sub {
    margin-top: 8px;
    font-size: 11px;
    color: var(--muted);
    letter-spacing: 1.5px;
}

.status {
    margin-top: 10px;
    color: var(--green);
    font-size: 11px;
}

.status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 10px var(--green);
    margin-right: 7px;
}

button, .btn {
    display: inline-block;
    padding: 12px 16px;
    border: 1px solid var(--green);
    border-radius: 5px;
    background: transparent;
    color: var(--green);
    font-family: inherit;
    font-size: 13px;
    font-weight: bold;
    cursor: pointer;
    transition: .2s ease;
}

button:hover, .btn:hover {
    background: var(--green);
    color: #00170a;
    box-shadow: 0 0 18px #00ff8850;
}

.primary {
    background: var(--green);
    color: #00170a;
}

.secondary {
    background: var(--panel2);
}

main {
    max-width: 1200px;
    margin: 32px auto;
    padding: 0 22px;
}

.welcome {
    margin-bottom: 26px;
}

.eyebrow {
    color: var(--green);
    font-size: 11px;
    letter-spacing: 2px;
}

h1 {
    margin: 12px 0;
    font-size: 29px;
    color: var(--green);
    text-shadow: 0 0 15px #00ff8825;
}

h2 {
    color: var(--green);
    font-size: 19px;
}

.muted {
    color: var(--muted);
    line-height: 1.7;
}

.stats {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 18px;
    margin: 24px 0;
}

.stat, .card {
    min-width: 0;
    padding: 23px;
    background: linear-gradient(145deg, #0c1b11, #050b07);
    border: 1px solid var(--border);
    border-radius: 8px;
    box-shadow: 0 0 18px #00ff8808;
    transition: border-color .2s, box-shadow .2s;
}

.stat:hover, .card:hover {
    border-color: var(--green);
    box-shadow: 0 0 18px #00ff8815;
}

.stat small {
    color: var(--muted);
    font-size: 11px;
    letter-spacing: 1px;
    text-transform: uppercase;
}

.stat strong {
    display: block;
    margin-top: 16px;
    color: var(--green);
    font-size: 32px;
    overflow-wrap: anywhere;
}

.stat-icon {
    float: right;
    font-size: 22px;
    color: #1a7546;
}

.actions {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin: 25px 0;
}

form {
    display: grid;
    gap: 16px;
}

label {
    display: block;
    margin-bottom: 8px;
    color: var(--green);
    font-size: 13px;
}

input, textarea, select {
    width: 100%;
    min-width: 0;
    padding: 13px;
    border: 1px solid var(--border);
    border-radius: 5px;
    background: #030906;
    color: var(--text);
    font-family: inherit;
    font-size: 15px;
}

input:focus, textarea:focus, select:focus {
    outline: 1px solid var(--green);
    box-shadow: 0 0 10px #00ff8820;
}

input[type="file"] {
    font-size: 12px;
}

textarea {
    min-height: 120px;
    resize: vertical;
}

.grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
}

.searchbar {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 10px;
    margin-bottom: 20px;
}

.tablewrap {
    overflow-x: auto;
}

table {
    width: 100%;
    min-width: 680px;
    border-collapse: collapse;
}

th, td {
    padding: 13px 10px;
    border-bottom: 1px solid var(--border);
    text-align: left;
    vertical-align: top;
}

th {
    color: var(--green);
    background: #0d2014;
    font-size: 11px;
    text-transform: uppercase;
}

td {
    font-size: 12px;
    overflow-wrap: anywhere;
}

tr:hover td {
    background: #00ff8808;
}

.thumb {
    width: 75px;
    height: 58px;
    object-fit: cover;
    border: 1px solid var(--border);
    border-radius: 4px;
}

.detail-photo {
    max-width: 100%;
    max-height: 420px;
    border: 1px solid var(--green);
    border-radius: 7px;
}

.notice {
    padding: 14px;
    margin-bottom: 18px;
    border: 1px solid #176c42;
    background: #0b2516;
    color: var(--green);
    border-radius: 5px;
}

.error {
    border-color: #a92e40;
    background: #2b1015;
    color: #ffabb5;
}

.terminal {
    margin-top: 27px;
    padding: 21px;
    border: 1px solid var(--border);
    border-radius: 7px;
    background: #020503;
    overflow-wrap: anywhere;
}

.terminal-heading {
    color: var(--green);
    margin-bottom: 16px;
}

.terminal p {
    font-size: 12px;
    line-height: 1.8;
}

.terminal .ok {
    color: var(--green);
}

.cursor {
    animation: blink 1s steps(2, start) infinite;
}

@keyframes blink {
    to { visibility: hidden; }
}

footer {
    padding: 28px 15px;
    text-align: center;
    color: var(--muted);
    font-size: 11px;
    border-top: 1px solid var(--border);
}

@media(max-width: 700px) {
    header {
        padding: 18px;
    }

    .brand {
        font-size: 21px;
    }

    main {
        margin-top: 22px;
        padding: 0 13px;
    }

    .stats {
        grid-template-columns: 1fr;
    }

    .grid {
        grid-template-columns: 1fr;
    }

    .welcome h1 {
        font-size: 23px;
    }

    .searchbar {
        grid-template-columns: 1fr;
    }

    .stat, .card {
        padding: 17px;
    }

    .actions .btn {
        text-align: center;
    }
}

@media(prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation: none !important;
        transition: none !important;
        scroll-behavior: auto !important;
    }
}
</style>
</head>

<body>

<header>
    <div>
        <div class="brand">⬡ <span>CYBERPOLICE</span> ASSIST</div>
        <div class="sub">{{ t.subtitle }}</div>
        <div class="status">
            <span class="status-dot"></span>{{ t.online }}
        </div>
    </div>

    <a class="btn secondary"
       href="{{ url_for('home', lang='mr' if lang == 'en' else 'en') }}">
        🌐 {{ t.language }}
    </a>
</header>

<main>

{% if message %}
<div class="notice {{ 'error' if error else '' }}">{{ message }}</div>
{% endif %}

<section class="welcome">
    <div class="eyebrow">SECURE INTERFACE / PROGRAM MANAGEMENT</div>
    <h1>&gt; {{ t.dashboard }}</h1>
    <div class="muted">{{ t.description }}</div>
</section>

<section class="stats">
    <div class="stat">
        <span class="stat-icon">▤</span>
        <small>{{ t.total }}</small>
        <strong>{{ total }}</strong>
    </div>

    <div class="stat">
        <span class="stat-icon">◉</span>
        <small>{{ t.people }}</small>
        <strong>{{ people }}</strong>
    </div>

    <div class="stat">
        <span class="stat-icon">⌘</span>
        <small>{{ t.register }}</small>
        <strong>READY</strong>
    </div>
</section>

<div class="actions">
    <a class="btn primary"
       href="{{ url_for('add_program', lang=lang) }}">
       + {{ t.add }}
    </a>

    <a class="btn secondary"
       href="{{ url_for('home', lang=lang) }}">
       ▤ {{ t.register }}
    </a>
</div>

{% if page == 'add' %}

<section class="card">
    <h2>&gt; {{ t.add }}</h2>

    <form method="POST" enctype="multipart/form-data">
        <div class="grid">
            <div>
                <label>{{ t.date }} *</label>
                <input type="date" name="date" required>
            </div>

            <div>
                <label>{{ t.station }} *</label>
                <input name="station" maxlength="120" required>
            </div>

            <div>
                <label>{{ t.place }} *</label>
                <input name="place" maxlength="180" required>
            </div>

            <div>
                <label>{{ t.name }} *</label>
                <input name="name" maxlength="180" required>
            </div>

            <div>
                <label>{{ t.attendees }} *</label>
                <input type="number" name="attendees"
                       min="0" max="1000000" value="0" required>
            </div>

            <div>
                <label>{{ t.photo }}</label>
                <input type="file" name="photo"
                       accept="image/png,image/jpeg,image/webp">
                <small class="muted">{{ t.photo_note }}</small>
            </div>
        </div>

        <div>
            <label>{{ t.details }} *</label>
            <textarea name="details" maxlength="10000" required></textarea>
        </div>

        <button class="primary" type="submit">{{ t.save }}</button>
    </form>
</section>

{% elif page == 'details' %}

<section class="card">
    <h2>&gt; {{ t.details_title }}</h2>

    {% if program %}
        <p><b>{{ t.date }}:</b> {{ program.date }}</p>
        <p><b>{{ t.station }}:</b> {{ program.station }}</p>
        <p><b>{{ t.place }}:</b> {{ program.place }}</p>
        <p><b>{{ t.name }}:</b> {{ program.name }}</p>
        <p><b>{{ t.attendees }}:</b> {{ program.attendees }}</p>
        <p><b>{{ t.details }}:</b><br>{{ program.details }}</p>

        {% if program.photo %}
        <p>
            <img class="detail-photo"
                 src="{{ url_for('uploaded_file', filename=program.photo) }}"
                 alt="Program photograph">
        </p>
        {% endif %}

        <a class="btn secondary"
           href="{{ url_for('home', lang=lang) }}">
            {{ t.back }}
        </a>
    {% else %}
        <p>{{ t.not_found }}</p>
    {% endif %}
</section>

{% else %}

<section class="card">
    <h2>&gt; {{ t.all }}</h2>

    <form class="searchbar" method="GET" action="{{ url_for('home') }}">
        <input type="hidden" name="lang" value="{{ lang }}">

        <input type="search" name="q" value="{{ query }}"
               placeholder="{{ t.search_hint }}">

        <button class="primary" type="submit">{{ t.find }}</button>
    </form>

    <div class="tablewrap">
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>{{ t.date }}</th>
                    <th>{{ t.station }}</th>
                    <th>{{ t.place }}</th>
                    <th>{{ t.name }}</th>
                    <th>{{ t.attendees }}</th>
                    <th>{{ t.photo }}</th>
                    <th></th>
                </tr>
            </thead>

            <tbody>
                {% for p in programs %}
                <tr>
                    <td>{{ p.id }}</td>
                    <td>{{ p.date }}</td>
                    <td>{{ p.station }}</td>
                    <td>{{ p.place }}</td>
                    <td>{{ p.name }}</td>
                    <td>{{ p.attendees }}</td>

                    <td>
                        {% if p.photo %}
                        <img class="thumb"
                             src="{{ url_for('uploaded_file', filename=p.photo) }}"
                             alt="Program photo">
                        {% else %}
                        —
                        {% endif %}
                    </td>

                    <td>
                        <a class="btn secondary"
                           href="{{ url_for('program_details',
                                           program_id=p.id, lang=lang) }}">
                            {{ t.view }}
                        </a>
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="8">{{ t.no }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</section>

{% endif %}

<section class="terminal">
    <div class="terminal-heading">// {{ t.terminal }}</div>
    <p><span class="ok">[OK]</span> CyberPolice Assist interface loaded.</p>
    <p><span class="ok">[OK]</span> Program management module ready.</p>
    <p><span class="ok">[INFO]</span> {{ t.ready }}</p>
    <p><span class="ok">admin@cyberpolice:~$</span> <span class="cursor">_</span></p>
</section>

</main>

<footer>
    {{ t.footer }} &middot; CYBERPOLICE ASSIST
</footer>

</body>
</html>
"""


def render_page(page="home", lang="en", programs=None, program=None,
                query="", message="", error=False, total=0, people=0):
    lang = "mr" if lang == "mr" else "en"

    return render_template_string(
        PAGE,
        page=page,
        lang=lang,
        t=TEXT[lang],
        programs=programs or [],
        program=program,
        query=query,
        message=message,
        error=error,
        total=total,
        people=people
    )


@app.route("/")
def home():
    lang = request.args.get("lang", "en")
    lang = "mr" if lang == "mr" else "en"
    query = request.args.get("q", "").strip()

    with connect_db() as conn:
        if query:
            pattern = "%" + query + "%"
            programs = conn.execute("""
                SELECT * FROM programs
                WHERE date LIKE ?
                   OR station LIKE ?
                   OR place LIKE ?
                   OR name LIKE ?
                ORDER BY date DESC, id DESC
            """, (pattern, pattern, pattern, pattern)).fetchall()
        else:
            programs = conn.execute("""
                SELECT * FROM programs
                ORDER BY date DESC, id DESC
            """).fetchall()

        total = conn.execute(
            "SELECT COUNT(*) FROM programs"
        ).fetchone()[0]

        people = conn.execute(
            "SELECT COALESCE(SUM(attendees), 0) FROM programs"
        ).fetchone()[0]

    message = TEXT[lang]["success"] if request.args.get("saved") == "1" else ""

    return render_page(
        programs=programs,
        query=query,
        lang=lang,
        total=total,
        people=people,
        message=message
    )


@app.route("/add", methods=["GET", "POST"])
def add_program():
    lang = request.args.get("lang", "en")
    lang = "mr" if lang == "mr" else "en"

    if request.method == "POST":
        date = request.form.get("date", "").strip()
        station = request.form.get("station", "").strip()
        place = request.form.get("place", "").strip()
        name = request.form.get("name", "").strip()
        details = request.form.get("details", "").strip()

        try:
            attendees = int(request.form.get("attendees", "0"))
            valid_attendees = 0 <= attendees <= 1000000
        except (ValueError, TypeError):
            attendees = 0
            valid_attendees = False

        try:
            datetime.strptime(date, "%Y-%m-%d")
            valid_date = True
        except ValueError:
            valid_date = False

        if (
            not all([date, station, place, name, details])
            or not valid_date
            or not valid_attendees
        ):
            return render_page(
                page="add",
                lang=lang,
                message=TEXT[lang]["required"],
                error=True
            ), 400

        photo = request.files.get("photo")
        photo_name = None

        if photo and photo.filename:
            if photo.mimetype not in (
                "image/jpeg", "image/png", "image/webp"
            ):
                return render_page(
                    page="add",
                    lang=lang,
                    message=TEXT[lang]["upload_error"],
                    error=True
                ), 400

            photo_bytes = photo.read(5 * 1024 * 1024 + 1)

            if len(photo_bytes) > 5 * 1024 * 1024:
                return render_page(
                    page="add",
                    lang=lang,
                    message=TEXT[lang]["upload_error"],
                    error=True
                ), 400

            extension = {
                "image/jpeg": ".jpg",
                "image/png": ".png",
                "image/webp": ".webp"
            }[photo.mimetype]

            photo_name = uuid.uuid4().hex + extension
            safe_name = secure_filename(photo_name)

            with open(os.path.join(UPLOAD_FOLDER, safe_name), "wb") as f:
                f.write(photo_bytes)

        try:
            with connect_db() as conn:
                conn.execute("""
                    INSERT INTO programs
                    (date, station, place, name, attendees,
                     details, photo, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    date, station, place, name, attendees,
                    details, photo_name, datetime.utcnow().isoformat()
                ))
        except sqlite3.Error:
            app.logger.exception("Could not save program")
            return render_page(
                page="add",
                lang=lang,
                message="Database error. Please try again.",
                error=True
            ), 500

        return redirect(url_for("home", lang=lang, saved="1"))

    return render_page(page="add", lang=lang)


@app.route("/program/<int:program_id>")
def program_details(program_id):
    lang = request.args.get("lang", "en")
    lang = "mr" if lang == "mr" else "en"

    with connect_db() as conn:
        program = conn.execute(
            "SELECT * FROM programs WHERE id = ?",
            (program_id,)
        ).fetchone()

        total = conn.execute(
            "SELECT COUNT(*) FROM programs"
        ).fetchone()[0]

        people = conn.execute(
            "SELECT COALESCE(SUM(attendees), 0) FROM programs"
        ).fetchone()[0]

    if program is None:
        return render_page(
            page="details",
            lang=lang,
            program=None,
            total=total,
            people=people,
            message=TEXT[lang]["not_found"],
            error=True
        ), 404

    return render_page(
        page="details",
        lang=lang,
        program=program,
        total=total,
        people=people
    )


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    from flask import send_from_directory

    return send_from_directory(
        UPLOAD_FOLDER,
        secure_filename(filename),
        max_age=3600
    )


@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
