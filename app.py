import os
import sqlite3
import uuid
from datetime import datetime

from flask import (
    Flask,
    request,
    redirect,
    url_for,
    render_template_string,
    send_from_directory,
    abort,
)
from werkzeug.utils import secure_filename


app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "programs.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


# --------------------------------------------------
# LANGUAGE TEXT
# --------------------------------------------------

TEXT = {
    "en": {
        "title": "CyberPolice Assist",
        "subtitle": "Cyber Awareness Program Management",
        "home": "Home",
        "add_program": "Add Program",
        "view_programs": "View Programs",
        "all_programs": "All Programs",
        "total_programs": "Total Programs",
        "total_attendees": "Total Attendees",
        "date": "Date",
        "station": "Police Station",
        "place": "Place",
        "name": "Program Name",
        "attendees": "Number of Attendees",
        "details": "Program Details",
        "photo": "Program Photograph",
        "actions": "Actions",
        "search": "Search by date, station, place or program name",
        "search_button": "Search",
        "submit": "Save Program",
        "cancel": "Cancel",
        "view": "View",
        "back": "Back to Programs",
        "no_programs": "No programs found.",
        "required": "Please fill in all required fields.",
        "saved": "Program saved successfully.",
        "not_found": "Program not found.",
        "invalid_photo": "Please upload a JPG, PNG, or WEBP image.",
        "photo_too_large": "The photograph must be smaller than 5 MB.",
        "footer": "Cyber Awareness • Community Safety",
        "register": "Program Registration",
        "photo_optional": "Optional — JPG, PNG or WEBP, maximum 5 MB",
        "details_placeholder": "Enter program details...",
        "station_placeholder": "Enter police station name",
        "place_placeholder": "Enter program location",
        "name_placeholder": "Enter program name",
        "attendees_placeholder": "Enter number of attendees",
        "no_photo": "No photograph uploaded",
        "program_details": "Program Information",
        "clear_search": "Clear Search",
    },
    "mr": {
        "title": "सायबरपोलीस सहाय्य",
        "subtitle": "सायबर जनजागृती कार्यक्रम व्यवस्थापन",
        "home": "मुख्यपृष्ठ",
        "add_program": "कार्यक्रम जोडा",
        "view_programs": "कार्यक्रम पहा",
        "all_programs": "सर्व कार्यक्रम",
        "total_programs": "एकूण कार्यक्रम",
        "total_attendees": "एकूण सहभागी",
        "date": "दिनांक",
        "station": "पोलीस स्टेशन",
        "place": "ठिकाण",
        "name": "कार्यक्रमाचे नाव",
        "attendees": "सहभागी संख्या",
        "details": "कार्यक्रमाची माहिती",
        "photo": "कार्यक्रमाचे छायाचित्र",
        "actions": "कृती",
        "search": "दिनांक, स्टेशन, ठिकाण किंवा नाव शोधा",
        "search_button": "शोधा",
        "submit": "कार्यक्रम जतन करा",
        "cancel": "रद्द करा",
        "view": "पहा",
        "back": "कार्यक्रमांकडे परत जा",
        "no_programs": "कोणताही कार्यक्रम आढळला नाही.",
        "required": "कृपया आवश्यक माहिती भरा.",
        "saved": "कार्यक्रम यशस्वीपणे जतन झाला.",
        "not_found": "कार्यक्रम आढळला नाही.",
        "invalid_photo": "कृपया JPG, PNG किंवा WEBP छायाचित्र अपलोड करा.",
        "photo_too_large": "छायाचित्राचा आकार 5 MB पेक्षा कमी असावा.",
        "footer": "सायबर जनजागृती • समुदाय सुरक्षा",
        "register": "कार्यक्रम नोंदणी",
        "photo_optional": "पर्यायी — JPG, PNG किंवा WEBP, कमाल 5 MB",
        "details_placeholder": "कार्यक्रमाची माहिती लिहा...",
        "station_placeholder": "पोलीस स्टेशनचे नाव लिहा",
        "place_placeholder": "कार्यक्रमाचे ठिकाण लिहा",
        "name_placeholder": "कार्यक्रमाचे नाव लिहा",
        "attendees_placeholder": "सहभागी संख्या लिहा",
        "no_photo": "छायाचित्र अपलोड केलेले नाही",
        "program_details": "कार्यक्रमाची माहिती",
        "clear_search": "शोध काढा",
    },
}


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_db()

    connection.execute("""
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

    connection.commit()
    connection.close()


init_db()


# --------------------------------------------------
# COMMON PAGE TEMPLATE
# --------------------------------------------------

PAGE = r"""
<!DOCTYPE html>
<html lang="{{ 'mr' if lang == 'mr' else 'en' }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>{{ t.title }}</title>

    <style>
        :root {
            --background: #101512;
            --panel: #19221c;
            --panel-light: #202b23;
            --green: #69d68b;
            --green-dark: #25844a;
            --text: #edf3ee;
            --muted: #a9b7ac;
            --border: #34443a;
            --danger: #ff8585;
        }

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            background: var(--background);
            color: var(--text);
            font-family: Arial, Helvetica, sans-serif;
            font-size: 15px;
            line-height: 1.6;
        }

        a {
            color: var(--green);
            text-decoration: none;
        }

        a:hover {
            text-decoration: underline;
        }

        .header {
            background: #171e19;
            border-bottom: 1px solid var(--border);
            padding: 17px 24px;
        }

        .header-inner {
            max-width: 1100px;
            margin: auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            flex-wrap: wrap;
        }

        .brand {
            font-size: 23px;
            font-weight: bold;
            color: var(--green);
        }

        .brand-subtitle {
            color: var(--muted);
            font-size: 12px;
            margin-top: 2px;
        }

        .language {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .language a {
            display: inline-block;
            padding: 6px 12px;
            border: 1px solid var(--border);
            border-radius: 5px;
            color: var(--text);
            font-size: 13px;
        }

        .language a.active {
            border-color: var(--green);
            color: var(--green);
        }

        .container {
            max-width: 1100px;
            margin: 28px auto;
            padding: 0 20px;
        }

        .welcome {
            margin-bottom: 22px;
        }

        .welcome h1 {
            margin: 0 0 5px;
            font-size: 27px;
            font-weight: 600;
        }

        .welcome p {
            color: var(--muted);
            margin: 0;
        }

        .stats {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 16px;
            margin: 22px 0;
        }

        .stat-card {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 18px;
        }

        .stat-label {
            color: var(--muted);
            font-size: 13px;
            margin-bottom: 8px;
        }

        .stat-value {
            font-size: 27px;
            font-weight: bold;
            color: var(--green);
        }

        .actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin: 22px 0;
        }

        .button {
            display: inline-block;
            background: var(--green);
            color: #102016;
            border: 1px solid var(--green);
            border-radius: 5px;
            padding: 10px 16px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            text-align: center;
        }

        .button:hover {
            background: #86e4a2;
            color: #102016;
            text-decoration: none;
        }

        .button.secondary {
            background: transparent;
            color: var(--green);
        }

        .button.secondary:hover {
            background: var(--panel-light);
        }

        .panel {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 8px;
            margin: 20px 0;
            overflow: hidden;
        }

        .panel-header {
            padding: 16px 18px;
            border-bottom: 1px solid var(--border);
        }

        .panel-header h2 {
            font-size: 19px;
            margin: 0;
        }

        .panel-body {
            padding: 20px;
        }

        .message {
            padding: 12px 15px;
            border: 1px solid #38794b;
            border-radius: 5px;
            background: #1b3223;
            color: #b8f5c8;
            margin-bottom: 18px;
        }

        .message.error {
            background: #382020;
            border-color: #824545;
            color: #ffc4c4;
        }

        .search-form {
            display: flex;
            gap: 10px;
            margin-bottom: 18px;
        }

        .search-form input {
            flex: 1;
            min-width: 0;
        }

        input,
        textarea,
        select {
            width: 100%;
            background: #101713;
            border: 1px solid var(--border);
            border-radius: 5px;
            padding: 11px 12px;
            color: var(--text);
            font-family: inherit;
            font-size: 14px;
        }

        input:focus,
        textarea:focus,
        select:focus {
            outline: none;
            border-color: var(--green);
        }

        textarea {
            min-height: 120px;
            resize: vertical;
        }

        label {
            display: block;
            margin-bottom: 7px;
            font-size: 14px;
            font-weight: bold;
        }

        .form-group {
            margin-bottom: 18px;
        }

        .help {
            color: var(--muted);
            font-size: 12px;
            margin-top: 5px;
        }

        .table-wrap {
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            min-width: 650px;
        }

        th {
            text-align: left;
            background: var(--panel-light);
            color: var(--green);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }

        th, td {
            padding: 13px 14px;
            border-bottom: 1px solid var(--border);
        }

        td {
            font-size: 14px;
        }

        tbody tr:hover {
            background: #202a23;
        }

        .empty {
            padding: 25px;
            text-align: center;
            color: var(--muted);
        }

        .badge {
            display: inline-block;
            padding: 4px 9px;
            border-radius: 4px;
            background: #243a2b;
            color: var(--green);
            font-size: 12px;
        }

        .detail-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 18px;
        }

        .detail-item {
            background: #121914;
            border: 1px solid var(--border);
            padding: 14px;
            border-radius: 5px;
            overflow-wrap: anywhere;
        }

        .detail-label {
            color: var(--muted);
            font-size: 12px;
            margin-bottom: 5px;
        }

        .detail-value {
            font-size: 15px;
            font-weight: bold;
        }

        .photo {
            display: block;
            width: 100%;
            max-width: 650px;
            max-height: 450px;
            object-fit: contain;
            background: #0b100d;
            border: 1px solid var(--border);
            border-radius: 6px;
            margin-top: 10px;
        }

        .footer {
            border-top: 1px solid var(--border);
            text-align: center;
            color: var(--muted);
            padding: 22px 15px;
            margin-top: 40px;
            font-size: 12px;
        }

        @media (max-width: 650px) {
            .header {
                padding: 14px;
            }

            .container {
                margin-top: 20px;
                padding: 0 13px;
            }

            .welcome h1 {
                font-size: 23px;
            }

            .stats,
            .detail-grid {
                grid-template-columns: 1fr;
            }

            .panel-body {
                padding: 14px;
            }

            .search-form {
                flex-direction: column;
            }

            .search-form .button {
                width: 100%;
            }
        }
    </style>
</head>

<body>

<header class="header">
    <div class="header-inner">
        <div>
            <div class="brand">● {{ t.title }}</div>
            <div class="brand-subtitle">{{ t.subtitle }}</div>
        </div>

        <div class="language">
            <a href="{{ url_for('home', lang='en') }}"
               class="{{ 'active' if lang == 'en' else '' }}">English</a>

            <a href="{{ url_for('home', lang='mr') }}"
               class="{{ 'active' if lang == 'mr' else '' }}">मराठी</a>
        </div>
    </div>
</header>

<main class="container">

    {% if message %}
        <div class="message {{ 'error' if error else '' }}">
            {{ message }}
        </div>
    {% endif %}

    {% if page == 'home' %}

        <section class="welcome">
            <h1>{{ t.title }}</h1>
            <p>{{ t.subtitle }}</p>
        </section>

        <section class="stats">
            <div class="stat-card">
                <div class="stat-label">{{ t.total_programs }}</div>
                <div class="stat-value">{{ total_programs }}</div>
            </div>

            <div class="stat-card">
                <div class="stat-label">{{ t.total_attendees }}</div>
                <div class="stat-value">{{ total_attendees }}</div>
            </div>
        </section>

        <div class="actions">
            <a class="button" href="{{ url_for('add_program', lang=lang) }}">
                + {{ t.add_program }}
            </a>

            <a class="button secondary" href="#programs">
                {{ t.view_programs }}
            </a>
        </div>

        <section class="panel" id="programs">
            <div class="panel-header">
                <h2>{{ t.all_programs }}</h2>
            </div>

            <div class="panel-body">

                <form class="search-form" method="GET"
                      action="{{ url_for('home') }}">
                    <input type="hidden" name="lang" value="{{ lang }}">

                    <input type="text"
                           name="q"
                           value="{{ query }}"
                           placeholder="{{ t.search }}">

                    <button class="button" type="submit">
                        {{ t.search_button }}
                    </button>
                </form>

                {% if query %}
                    <p>
                        <a href="{{ url_for('home', lang=lang) }}">
                            {{ t.clear_search }}
                        </a>
                    </p>
                {% endif %}

                {% if programs %}
                    <div class="table-wrap">
                        <table>
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>{{ t.date }}</th>
                                    <th>{{ t.station }}</th>
                                    <th>{{ t.place }}</th>
                                    <th>{{ t.name }}</th>
                                    <th>{{ t.attendees }}</th>
                                    <th>{{ t.actions }}</th>
                                </tr>
                            </thead>

                            <tbody>
                                {% for p in programs %}
                                    <tr>
                                        <td>{{ loop.index }}</td>
                                        <td>{{ p.date }}</td>
                                        <td>{{ p.station }}</td>
                                        <td>{{ p.place }}</td>
                                        <td>{{ p.name }}</td>
                                        <td>{{ p.attendees }}</td>
                                        <td>
                                            <a class="badge"
                                               href="{{ url_for('program_details', program_id=p.id, lang=lang) }}">
                                                {{ t.view }}
                                            </a>
                                        </td>
                                    </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                {% else %}
                    <div class="empty">{{ t.no_programs }}</div>
                {% endif %}

            </div>
        </section>

    {% elif page == 'add' %}

        <section class="welcome">
            <h1>{{ t.add_program }}</h1>
            <p>{{ t.subtitle }}</p>
        </section>

        <section class="panel">
            <div class="panel-header">
                <h2>{{ t.register }}</h2>
            </div>

            <div class="panel-body">
                <form method="POST"
                      action="{{ url_for('add_program', lang=lang) }}"
                      enctype="multipart/form-data">

                    <input type="hidden" name="lang" value="{{ lang }}">

                    <div class="form-group">
                        <label for="date">{{ t.date }} *</label>
                        <input id="date" type="date" name="date"
                               value="{{ form.get('date', '') }}" required>
                    </div>

                    <div class="form-group">
                        <label for="station">{{ t.station }} *</label>
                        <input id="station" type="text" name="station"
                               value="{{ form.get('station', '') }}"
                               placeholder="{{ t.station_placeholder }}"
                               maxlength="150" required>
                    </div>

                    <div class="form-group">
                        <label for="place">{{ t.place }} *</label>
                        <input id="place" type="text" name="place"
                               value="{{ form.get('place', '') }}"
                               placeholder="{{ t.place_placeholder }}"
                               maxlength="200" required>
                    </div>

                    <div class="form-group">
                        <label for="name">{{ t.name }} *</label>
                        <input id="name" type="text" name="name"
                               value="{{ form.get('name', '') }}"
                               placeholder="{{ t.name_placeholder }}"
                               maxlength="200" required>
                    </div>

                    <div class="form-group">
                        <label for="attendees">{{ t.attendees }} *</label>
                        <input id="attendees" type="number" name="attendees"
                               value="{{ form.get('attendees', '0') }}"
                               placeholder="{{ t.attendees_placeholder }}"
                               min="0" max="10000000" required>
                    </div>

                    <div class="form-group">
                        <label for="details">{{ t.details }}</label>
                        <textarea id="details" name="details"
                                  placeholder="{{ t.details_placeholder }}"
                                  maxlength="10000">{{ form.get('details', '') }}</textarea>
                    </div>

                    <div class="form-group">
                        <label for="photo">{{ t.photo }}</label>
                        <input id="photo" type="file" name="photo"
                               accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp">
                        <div class="help">{{ t.photo_optional }}</div>
                    </div>

                    <div class="actions">
                        <button class="button" type="submit">
                            {{ t.submit }}
                        </button>

                        <a class="button secondary"
                           href="{{ url_for('home', lang=lang) }}">
                            {{ t.cancel }}
                        </a>
                    </div>

                </form>
            </div>
        </section>

    {% elif page == 'details' %}

        <section class="welcome">
            <h1>{{ program.name }}</h1>
            <p>{{ t.program_details }}</p>
        </section>

        <section class="panel">
            <div class="panel-header">
                <h2>{{ t.program_details }}</h2>
            </div>

            <div class="panel-body">

                <div class="detail-grid">
                    <div class="detail-item">
                        <div class="detail-label">{{ t.date }}</div>
                        <div class="detail-value">{{ program.date }}</div>
                    </div>

                    <div class="detail-item">
                        <div class="detail-label">{{ t.station }}</div>
                        <div class="detail-value">{{ program.station }}</div>
                    </div>

                    <div class="detail-item">
                        <div class="detail-label">{{ t.place }}</div>
                        <div class="detail-value">{{ program.place }}</div>
                    </div>

                    <div class="detail-item">
                        <div class="detail-label">{{ t.attendees }}</div>
                        <div class="detail-value">{{ program.attendees }}</div>
                    </div>
                </div>

                <div class="form-group" style="margin-top:20px">
                    <label>{{ t.details }}</label>
                    <div style="white-space:pre-wrap;overflow-wrap:anywhere">{{ program.details or '—' }}</div>
                </div>

                <div class="form-group">
                    <label>{{ t.photo }}</label>

                    {% if program.photo %}
                        <img class="photo"
                             src="{{ url_for('uploaded_file', filename=program.photo) }}"
                             alt="Program photograph">
                    {% else %}
                        <p>{{ t.no_photo }}</p>
                    {% endif %}
                </div>

                <div class="actions">
                    <a class="button"
                       href="{{ url_for('home', lang=lang) }}">
                        {{ t.back }}
                    </a>
                </div>

            </div>
        </section>

    {% endif %}

</main>

<footer class="footer">
    {{ t.footer }}
</footer>

</body>
</html>
"""


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def get_language():
    lang = request.values.get("lang", "en")
    return lang if lang in TEXT else "en"


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def render_page(page, lang="en", **kwargs):
    return render_template_string(
        PAGE,
        page=page,
        lang=lang,
        t=TEXT[lang],
        message=kwargs.pop("message", ""),
        error=kwargs.pop("error", False),
        **kwargs,
    )


# --------------------------------------------------
# HOME PAGE AND SEARCH
# --------------------------------------------------

@app.route("/")
def home():
    lang = get_language()
    query = request.args.get("q", "").strip()

    connection = get_db()

    total_programs = connection.execute(
        "SELECT COUNT(*) FROM programs"
    ).fetchone()[0]

    total_attendees = connection.execute(
        "SELECT COALESCE(SUM(attendees), 0) FROM programs"
    ).fetchone()[0]

    if query:
        search_term = f"%{query}%"

        programs = connection.execute("""
            SELECT * FROM programs
            WHERE date LIKE ?
               OR station LIKE ?
               OR place LIKE ?
               OR name LIKE ?
            ORDER BY date DESC, id DESC
        """, (
            search_term,
            search_term,
            search_term,
            search_term,
        )).fetchall()
    else:
        programs = connection.execute("""
            SELECT * FROM programs
            ORDER BY date DESC, id DESC
        """).fetchall()

    connection.close()

    message = ""
    if request.args.get("saved") == "1":
        message = TEXT[lang]["saved"]

    return render_page(
        "home",
        lang=lang,
        programs=programs,
        total_programs=total_programs,
        total_attendees=total_attendees,
        query=query,
        message=message,
    )


# --------------------------------------------------
# ADD PROGRAM
# --------------------------------------------------

@app.route("/add", methods=["GET", "POST"])
def add_program():
    lang = get_language()
    form = {}

    if request.method == "POST":
        form = request.form.to_dict()

        date = request.form.get("date", "").strip()
        station = request.form.get("station", "").strip()
        place = request.form.get("place", "").strip()
        name = request.form.get("name", "").strip()
        attendees_text = request.form.get("attendees", "0").strip()
        details = request.form.get("details", "").strip()

        if not all([date, station, place, name, attendees_text]):
            return render_page(
                "add",
                lang=lang,
                form=form,
                message=TEXT[lang]["required"],
                error=True,
            ), 400

        try:
            datetime.strptime(date, "%Y-%m-%d")
            attendees = int(attendees_text)

            if attendees < 0 or attendees > 10000000:
                raise ValueError

        except ValueError:
            return render_page(
                "add",
                lang=lang,
                form=form,
                message=TEXT[lang]["required"],
                error=True,
            ), 400

        photo_name = ""
        photo = request.files.get("photo")

        if photo and photo.filename:
            if not allowed_file(photo.filename):
                return render_page(
                    "add",
                    lang=lang,
                    form=form,
                    message=TEXT[lang]["invalid_photo"],
                    error=True,
                ), 400

            extension = secure_filename(
                photo.filename
            ).rsplit(".", 1)[1].lower()

            photo_name = f"{uuid.uuid4().hex}.{extension}"
            photo_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                photo_name,
            )

            photo.save(photo_path)

        connection = get_db()

        connection.execute("""
            INSERT INTO programs
                (date, station, place, name, attendees, details, photo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            date,
            station,
            place,
            name,
            attendees,
            details,
            photo_name,
        ))

        connection.commit()
        connection.close()

        return redirect(url_for("home", lang=lang, saved=1))

    return render_page(
        "add",
        lang=lang,
        form=form,
    )


# --------------------------------------------------
# PROGRAM DETAILS
# --------------------------------------------------

@app.route("/program/<int:program_id>")
def program_details(program_id):
    lang = get_language()

    connection = get_db()

    program = connection.execute(
        "SELECT * FROM programs WHERE id = ?",
        (program_id,),
    ).fetchone()

    connection.close()

    if program is None:
        return render_page(
            "home",
            lang=lang,
            programs=[],
            total_programs=0,
            total_attendees=0,
            query="",
            message=TEXT[lang]["not_found"],
            error=True,
        ), 404

    return render_page(
        "details",
        lang=lang,
        program=program,
    )


# --------------------------------------------------
# SERVE UPLOADED PHOTOGRAPHS
# --------------------------------------------------

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    safe_name = os.path.basename(filename)

    if safe_name != filename:
        abort(404)

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        safe_name,
    )


# --------------------------------------------------
# BASIC SECURITY HEADERS
# --------------------------------------------------

@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False,
    )
