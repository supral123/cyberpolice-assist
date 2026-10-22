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
    send_from_directory, send_file, abort, session
)
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or (uuid.uuid4().hex + uuid.uuid4().hex)
app.permanent_session_lifetime = timedelta(hours=8)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "programs.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_PHOTOS = 10
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

TEXT = {
    "en": {
        "title":"CyberPolice Assist","subtitle":"CYBER AWARENESS • PROGRAM MANAGEMENT",
        "login":"Administrator Login","username":"Username","password":"Password","sign_in":"Sign In",
        "logout":"Log Out","login_error":"Invalid username or password.","welcome":"Welcome to CyberPolice Assist",
        "intro":"A secure workspace for cyber-awareness programs, photographs and reports.",
        "enter":"ENTER CYBERPOLICE ASSIST","add_program":"Add Program","all_programs":"All Programs",
        "total_programs":"Total Programs","total_attendees":"Total Attendees","date":"Date",
        "station":"Police Station","place":"Place","name":"Program Name","attendees":"Number of Attendees",
        "details":"Program Details","photos":"Program Photographs","actions":"Actions",
        "search":"Search by date, station, place or program name","search_button":"Search",
        "submit":"Save Program","save_changes":"Save Changes","cancel":"Cancel","view":"View","edit":"Edit",
        "delete":"Delete","back":"Back to Programs","no_programs":"No programs found. Add your first program to get started.",
        "required":"Please fill in all required fields correctly.","saved":"Program saved successfully.",
        "updated":"Program updated successfully.","not_found":"Program not found.",
        "invalid_photo":"Upload JPG, PNG or WEBP images only.",
        "too_many":"You can upload up to 10 photographs for one program in total.",
        "photo_help":"Optional. Select up to 10 JPG, PNG or WEBP images. The total request limit is 50 MB.",
        "details_placeholder":"Enter program details, topics covered, officers' names, outcomes, etc.",
        "station_placeholder":"Enter police station name","place_placeholder":"Enter program location",
        "name_placeholder":"Enter program name","no_photo":"No photographs uploaded",
        "program_details":"Program Information","clear_search":"Clear Search","download_pdf":"Download PDF Report",
        "confirm_delete":"Delete this program and its photographs? This cannot be undone.",
        "deleted":"Program deleted.","existing_photos":"Existing photographs","add_more_photos":"Add more photographs",
        "footer":"PRIVATE ADMIN AREA • CYBER AWARENESS","not_configured":"Admin password is not configured. Set ADMIN_PASSWORD in your hosting environment.",
        "created":"Created","report":"CYBER AWARENESS PROGRAM REPORT","report_generated":"Generated",
        "photo_page":"PROGRAM PHOTOGRAPHS","page_info":"Program information is on the first page. Photographs start on the next page.",
        "photo_count":"Photographs selected","add_photo":"Add Another Photo","remove_photo":"Remove",
        "voice_language":"Voice Typing Language","start_voice":"🎤 Start Speaking","stop_voice":"⏹ Stop Speaking",
        "voice_listening":"Listening. Please speak.","voice_stopped":"Voice typing stopped.",
        "voice_unsupported":"Voice typing is not supported in this browser. Try a compatible browser or your keyboard microphone.",
        "welcome_tag":"SECURE • SMART • CONNECTED","secure_note":"Your cyber-awareness workspace",
    },
    "mr": {
        "title":"सायबरपोलीस सहाय्य","subtitle":"सायबर जनजागृती • कार्यक्रम व्यवस्थापन",
        "login":"प्रशासक लॉगिन","username":"वापरकर्तानाव","password":"पासवर्ड","sign_in":"लॉगिन करा",
        "logout":"लॉगआउट","login_error":"वापरकर्तानाव किंवा पासवर्ड चुकीचा आहे.",
        "welcome":"सायबरपोलीस सहाय्य मध्ये आपले स्वागत आहे",
        "intro":"सायबर जनजागृती कार्यक्रम, छायाचित्रे आणि अहवालांसाठी सुरक्षित कार्यक्षेत्र.",
        "enter":"सायबरपोलीस सहाय्य सुरू करा","add_program":"कार्यक्रम जोडा","all_programs":"सर्व कार्यक्रम",
        "total_programs":"एकूण कार्यक्रम","total_attendees":"एकूण सहभागी","date":"दिनांक",
        "station":"पोलीस स्टेशन","place":"ठिकाण","name":"कार्यक्रमाचे नाव","attendees":"सहभागी संख्या",
        "details":"कार्यक्रमाची माहिती","photos":"कार्यक्रमाची छायाचित्रे","actions":"कृती",
        "search":"दिनांक, स्टेशन, ठिकाण किंवा नाव शोधा","search_button":"शोधा",
        "submit":"कार्यक्रम जतन करा","save_changes":"बदल जतन करा","cancel":"रद्द करा","view":"पहा",
        "edit":"संपादित करा","delete":"हटवा","back":"कार्यक्रमांकडे परत जा",
        "no_programs":"कार्यक्रम आढळला नाही. पहिला कार्यक्रम जोडा.",
        "required":"कृपया सर्व आवश्यक माहिती योग्यरीत्या भरा.","saved":"कार्यक्रम यशस्वीपणे जतन झाला.",
        "updated":"कार्यक्रम अद्ययावत झाला.","not_found":"कार्यक्रम आढळला नाही.",
        "invalid_photo":"फक्त JPG, PNG किंवा WEBP छायाचित्रे अपलोड करा.",
        "too_many":"एका कार्यक्रमासाठी एकूण जास्तीत जास्त 10 छायाचित्रे अपलोड करू शकता.",
        "photo_help":"पर्यायी. कमाल 10 JPG, PNG किंवा WEBP छायाचित्रे निवडा. एकूण विनंती 50 MB पर्यंत आहे.",
        "details_placeholder":"कार्यक्रमाची माहिती, विषय, अधिकाऱ्यांची नावे, निष्कर्ष इत्यादी लिहा.",
        "station_placeholder":"पोलीस स्टेशनचे नाव लिहा","place_placeholder":"कार्यक्रमाचे ठिकाण लिहा",
        "name_placeholder":"कार्यक्रमाचे नाव लिहा","no_photo":"छायाचित्रे अपलोड केलेली नाहीत",
        "program_details":"कार्यक्रमाची माहिती","clear_search":"शोध काढा","download_pdf":"PDF अहवाल डाउनलोड करा",
        "confirm_delete":"हा कार्यक्रम आणि छायाचित्रे हटवायची? ही कृती पूर्ववत करता येणार नाही.",
        "deleted":"कार्यक्रम हटवला.","existing_photos":"सध्याची छायाचित्रे","add_more_photos":"अधिक छायाचित्रे जोडा",
        "footer":"खासगी प्रशासक विभाग • सायबर जनजागृती",
        "not_configured":"प्रशासक पासवर्ड सेट केलेला नाही. होस्टिंग सेटिंग्जमध्ये ADMIN_PASSWORD सेट करा.",
        "created":"तयार केले","report":"सायबर जनजागृती कार्यक्रम अहवाल","report_generated":"अहवाल तयार केला",
        "photo_page":"कार्यक्रमाची छायाचित्रे","page_info":"पहिल्या पानावर कार्यक्रमाची माहिती आहे. पुढील पानावर छायाचित्रे सुरू होतील.",
        "photo_count":"निवडलेली छायाचित्रे","add_photo":"आणखी छायाचित्र जोडा","remove_photo":"काढा",
        "voice_language":"आवाजाची भाषा","start_voice":"🎤 बोलणे सुरू करा","stop_voice":"⏹ बोलणे थांबवा",
        "voice_listening":"ऐकत आहे. कृपया बोला.","voice_stopped":"आवाजातून टायपिंग थांबले.",
        "voice_unsupported":"या ब्राउझरमध्ये आवाज ओळख उपलब्ध नाही. समर्थित ब्राउझर किंवा कीबोर्डचा मायक्रोफोन वापरा.",
        "welcome_tag":"सुरक्षित • स्मार्ट • जोडलेले","secure_note":"तुमचे सायबर जनजागृती कार्यक्षेत्र",
    }
}

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS programs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, station TEXT NOT NULL,
        place TEXT NOT NULL, name TEXT NOT NULL, attendees INTEGER NOT NULL DEFAULT 0,
        details TEXT DEFAULT '', photo TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS program_photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, program_id INTEGER NOT NULL, filename TEXT NOT NULL,
        FOREIGN KEY(program_id) REFERENCES programs(id) ON DELETE CASCADE
    )""")
    conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT DEFAULT '')")
    old_rows = conn.execute("SELECT id, photo FROM programs WHERE COALESCE(photo,'') != ''").fetchall()
    for row in old_rows:
        found = conn.execute("SELECT 1 FROM program_photos WHERE program_id=? AND filename=?",
                             (row["id"], row["photo"])).fetchone()
        if not found:
            conn.execute("INSERT INTO program_photos(program_id,filename) VALUES (?,?)",
                         (row["id"], row["photo"]))
    conn.commit()
    conn.close()

init_db()

def logged_in():
    return session.get("admin_logged_in") is True

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not logged_in():
            return redirect(url_for("login", next=request.path, lang=get_language()))
        return fn(*args, **kwargs)
    return wrapped

def get_language():
    lang = request.values.get("lang", request.args.get("lang", "en"))
    return lang if lang in TEXT else "en"

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def render_page(page, lang="en", **kwargs):
    values = {"page":page, "lang":lang, "t":TEXT[lang], "message":kwargs.pop("message",""),
              "error":kwargs.pop("error",False), "logged_in":logged_in()}
    values.update(kwargs)
    return render_template_string(PAGE, **values)

PAGE = r"""
<!doctype html><html lang="{{ 'mr' if lang == 'mr' else 'en' }}"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#050b1b"><title>{{ t.title }}</title>
<style>
:root{--bg:#050b1b;--panel:rgba(12,23,49,.82);--panel2:#101d3b;--cyan:#42e8ff;--blue:#5388ff;--text:#eff7ff;--muted:#a5b5d1;--line:rgba(91,160,255,.24);--pink:#d56dff}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;min-height:100vh;color:var(--text);font-family:Inter,Segoe UI,Arial,sans-serif;line-height:1.6;background:radial-gradient(ellipse at 15% 0%,#102b5c 0,transparent 38%),radial-gradient(ellipse at 90% 20%,#21164d 0,transparent 34%),var(--bg);overflow-x:hidden}
body:before{content:"";position:fixed;inset:0;pointer-events:none;z-index:-1;background-image:linear-gradient(rgba(74,151,255,.045) 1px,transparent 1px),linear-gradient(90deg,rgba(74,151,255,.045) 1px,transparent 1px);background-size:42px 42px;mask-image:linear-gradient(to bottom,#000,transparent 90%)}
a{color:var(--cyan);text-decoration:none}a:hover{color:#fff}.header{position:sticky;top:0;z-index:5;background:rgba(4,10,25,.86);backdrop-filter:blur(18px);border-bottom:1px solid var(--line);box-shadow:0 8px 35px #0003}
.header-inner{max-width:1180px;margin:auto;padding:14px 22px;display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap}.brand-wrap{display:flex;align-items:center;gap:12px}.logo{width:43px;height:43px;border-radius:14px;display:grid;place-items:center;background:linear-gradient(145deg,#142f65,#071327);border:1px solid #4cdfff88;box-shadow:0 0 22px #28cfff35;font-size:23px}.brand{font-size:20px;font-weight:850;letter-spacing:.3px;background:linear-gradient(90deg,#fff,var(--cyan));color:transparent;background-clip:text}.brand-subtitle{font-size:10px;letter-spacing:1.8px;color:var(--muted)}.nav{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.nav a{font-size:12px;border:1px solid var(--line);border-radius:10px;padding:7px 11px;background:#0b1730aa}.nav a:hover{border-color:var(--cyan);box-shadow:0 0 15px #42e8ff25}
.container{max-width:1180px;margin:30px auto;padding:0 20px}.welcome{position:relative;margin:8px 0 24px;padding:26px 0}.welcome h1{font-size:clamp(26px,4vw,42px);line-height:1.15;margin:0 0 9px;letter-spacing:-1px}.welcome p{margin:0;color:var(--muted)}.eyebrow{font-size:11px;font-weight:800;letter-spacing:2.7px;color:var(--cyan);text-transform:uppercase;margin-bottom:12px}
.stats{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin:20px 0}.stat-card{position:relative;overflow:hidden;background:linear-gradient(135deg,rgba(17,37,77,.92),rgba(8,17,39,.88));border:1px solid var(--line);border-radius:17px;padding:20px;box-shadow:0 14px 40px #0002;animation:rise .7s both}.stat-card:after{content:"";position:absolute;width:120px;height:120px;border-radius:50%;right:-45px;top:-55px;background:#42e8ff16;filter:blur(2px)}.stat-label{font-size:12px;color:var(--muted);letter-spacing:.6px}.stat-value{font-size:34px;font-weight:850;color:var(--cyan);text-shadow:0 0 22px #42e8ff35}
.actions{display:flex;gap:10px;flex-wrap:wrap;margin:20px 0}.button{display:inline-flex;align-items:center;justify-content:center;gap:7px;background:linear-gradient(110deg,#27c8ed,#6b8dff);color:#061126;border:1px solid #71eaff;border-radius:11px;padding:11px 16px;font-size:13px;font-weight:800;cursor:pointer;text-align:center;box-shadow:0 7px 24px #27c8ed20;transition:transform .2s,box-shadow .2s}.button:hover{transform:translateY(-2px);box-shadow:0 10px 28px #27c8ed38;color:#04101e;text-decoration:none}.button.secondary{background:rgba(12,26,54,.8);border-color:var(--line);color:var(--cyan);box-shadow:none}.button.danger{background:#421d37;border-color:#a84c7e;color:#ffd9eb}.button:disabled{opacity:.45;cursor:not-allowed;transform:none}
.panel{background:linear-gradient(145deg,rgba(13,26,55,.92),rgba(7,15,34,.94));border:1px solid var(--line);border-radius:18px;margin:20px 0;overflow:hidden;box-shadow:0 18px 55px #0002;backdrop-filter:blur(10px)}.panel-header{padding:16px 20px;border-bottom:1px solid var(--line);background:linear-gradient(90deg,#142b552e,transparent)}.panel-header h2{font-size:17px;margin:0}.panel-body{padding:20px}
.message{padding:12px 15px;border:1px solid #39cba4;border-radius:10px;background:#0e392f;color:#b8ffeb;margin-bottom:16px}.message.error{background:#401d35;border-color:#b85b8c;color:#ffd5e8}
input,textarea,select{width:100%;background:#061126;border:1px solid #263d67;border-radius:10px;padding:12px 13px;color:var(--text);font:14px Arial,sans-serif}input:focus,textarea:focus,select:focus{outline:none;border-color:var(--cyan);box-shadow:0 0 0 3px #42e8ff12}input[type=file]{padding:10px}textarea{min-height:125px;resize:vertical}label{display:block;margin-bottom:7px;font-size:13px;font-weight:750;color:#dceaff}.form-group{margin-bottom:18px}.help{color:var(--muted);font-size:12px;margin-top:6px}.search-form{display:flex;gap:10px;margin-bottom:16px}.search-form input{flex:1;min-width:0}.search-form .button{width:auto}
.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;min-width:650px}th{text-align:left;background:#0c1b39;color:var(--cyan);font-size:11px;text-transform:uppercase;letter-spacing:.7px}th,td{padding:13px;border-bottom:1px solid var(--line)}td{font-size:13px}tbody tr:hover{background:#1a2b4a77}.empty{padding:28px;text-align:center;color:var(--muted)}.badge{display:inline-block;margin:2px;padding:5px 9px;border-radius:7px;background:#10294a;border:1px solid var(--line);color:var(--cyan);font-size:11px}
.detail-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}.detail-item{background:#07142b;border:1px solid var(--line);padding:14px;border-radius:12px;overflow-wrap:anywhere}.detail-label{color:var(--muted);font-size:11px;margin-bottom:4px}.detail-value{font-size:15px;font-weight:750;white-space:pre-wrap}.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-top:10px}.gallery img{width:100%;height:190px;object-fit:cover;border-radius:11px;border:1px solid var(--line);background:#061126}.photo-preview-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(125px,1fr));gap:10px;margin-top:12px}.photo-preview{border:1px solid var(--line);border-radius:11px;padding:8px;min-width:0;background:#07142b}.photo-preview img{width:100%;height:100px;object-fit:cover;border-radius:7px}.photo-preview .filename{font-size:11px;overflow-wrap:anywhere;margin:5px 0}.photo-preview button{width:100%;padding:7px}
.login-box{max-width:440px;margin:45px auto}.footer{border-top:1px solid var(--line);text-align:center;color:var(--muted);padding:22px;margin-top:42px;font-size:11px;letter-spacing:1px}
.hero{min-height:calc(100vh - 80px);display:grid;place-items:center;text-align:center;padding:35px 20px;position:relative;isolation:isolate}.hero-content{max-width:800px;animation:rise .9s both}.hero-orb{width:150px;height:150px;margin:0 auto 28px;position:relative;display:grid;place-items:center;border-radius:42px;transform:rotate(-8deg);background:linear-gradient(145deg,#153d7d,#07142d);border:1px solid #50e8ff99;box-shadow:0 0 35px #2dd9ff35,inset 0 0 25px #2dd9ff15;animation:float 4s ease-in-out infinite}.hero-orb:before,.hero-orb:after{content:"";position:absolute;inset:-14px;border:1px solid #43dfff60;border-radius:48px;animation:orbit 12s linear infinite}.hero-orb:after{inset:-26px;border-color:#7a75ff55;border-style:dashed;animation-direction:reverse;animation-duration:20s}.hero-orb span{font-size:76px;filter:drop-shadow(0 0 16px #42e8ff70);transform:rotate(8deg)}.hero h1{font-size:clamp(34px,7vw,66px);line-height:1.08;margin:0 0 17px;letter-spacing:-2px;background:linear-gradient(90deg,#fff,#77eaff 55%,#9b9cff);color:transparent;background-clip:text}.hero p{max-width:620px;margin:0 auto 27px;color:#b7c8e5;font-size:16px}.hero .button{padding:15px 23px;font-size:13px;letter-spacing:1px}.hero-tag{display:inline-block;color:var(--cyan);border:1px solid var(--line);background:#0b1a35aa;border-radius:30px;padding:7px 13px;font-size:10px;letter-spacing:2px;margin-bottom:20px}.glow-dot{position:absolute;width:5px;height:5px;border-radius:50%;background:var(--cyan);box-shadow:0 0 15px var(--cyan);animation:blink 2s infinite}.glow-dot.d1{left:12%;top:25%}.glow-dot.d2{right:13%;top:31%;animation-delay:.6s}.glow-dot.d3{left:22%;bottom:18%;animation-delay:1s}.glow-dot.d4{right:23%;bottom:22%;animation-delay:1.4s}
@keyframes float{0%,100%{transform:translateY(0) rotate(-8deg)}50%{transform:translateY(-12px) rotate(-5deg)}}@keyframes orbit{to{transform:rotate(360deg)}}@keyframes rise{from{opacity:0;transform:translateY(15px)}to{opacity:1;transform:translateY(0)}}@keyframes blink{0%,100%{opacity:.3}50%{opacity:1}}

/* EXTRA CYBER MOTION EFFECTS */
#cyber-canvas{position:fixed;inset:0;width:100%;height:100%;pointer-events:none;z-index:0;opacity:.72}
.header,.container,.hero,.footer{position:relative;z-index:1}
body:after{content:"";position:fixed;width:38vw;height:38vw;min-width:260px;min-height:260px;left:-12vw;top:35vh;border-radius:50%;background:radial-gradient(circle,#1b6cff22,transparent 68%);filter:blur(15px);pointer-events:none;z-index:0;animation:nebulaDrift 18s ease-in-out infinite alternate}
.hero:before{content:"";position:absolute;inset:8% 5%;border-radius:50%;background:radial-gradient(ellipse,#173c7c1a,transparent 68%);pointer-events:none;animation:pulseGlow 6s ease-in-out infinite}
.hero-orb{transform-style:preserve-3d;perspective:800px;box-shadow:0 0 35px #2dd9ff35,inset 0 0 25px #2dd9ff15,0 24px 55px #0006}
.hero-orb span{transform:translateZ(32px) rotate(8deg);animation:shieldPulse 3.5s ease-in-out infinite}
.panel,.stat-card,.detail-item,.photo-preview{transform-style:preserve-3d;transition:transform .25s ease,border-color .25s ease,box-shadow .25s ease}
.panel{position:relative}
.panel:before{content:"";position:absolute;inset:0;border-radius:inherit;padding:1px;background:linear-gradient(115deg,transparent 10%,#42e8ff55 45%,#8d72ff55 60%,transparent 85%);-webkit-mask:linear-gradient(#fff 0 0) content-box,linear-gradient(#fff 0 0);-webkit-mask-composite:xor;mask-composite:exclude;pointer-events:none;opacity:.45;background-size:220% 100%;animation:borderSweep 8s linear infinite}
.stat-card:hover,.detail-item:hover,.photo-preview:hover{border-color:#42e8ff88;box-shadow:0 18px 45px #0004,0 0 22px #42e8ff12}
.button{position:relative;overflow:hidden;isolation:isolate}
.button:before{content:"";position:absolute;top:-80%;left:-45%;width:35%;height:260%;transform:rotate(25deg);background:linear-gradient(90deg,transparent,#ffffff80,transparent);transition:left .65s ease;z-index:-1}
.button:hover:before{left:130%}
.logo{animation:logoFloat 5s ease-in-out infinite}
@keyframes nebulaDrift{0%{transform:translate3d(0,0,0) scale(1)}100%{transform:translate3d(25vw,-12vh,0) scale(1.3)}}
@keyframes pulseGlow{0%,100%{opacity:.35;transform:scale(.94)}50%{opacity:.9;transform:scale(1.06)}}
@keyframes shieldPulse{0%,100%{filter:drop-shadow(0 0 12px #42e8ff55)}50%{filter:drop-shadow(0 0 26px #42e8ffbb)}}
@keyframes borderSweep{0%{background-position:200% 0;opacity:.2}50%{opacity:.7}100%{background-position:-20% 0;opacity:.2}}
@keyframes logoFloat{0%,100%{transform:translateY(0) rotate(0)}50%{transform:translateY(-3px) rotate(3deg)}}
@media(max-width:700px){ #cyber-canvas{opacity:.4}.panel:before{animation:none}.hero:before{inset:0}}
@media(prefers-reduced-motion:reduce){ #cyber-canvas{display:none}body:after,.hero:before,.hero-orb span,.logo{animation:none!important}.panel:before{animation:none!important}}

@media(max-width:650px){.header-inner{padding:12px}.brand{font-size:17px}.brand-subtitle{font-size:9px;letter-spacing:1px}.logo{width:38px;height:38px}.container{margin-top:18px;padding:0 12px}.welcome h1{font-size:26px}.stats,.detail-grid{grid-template-columns:1fr}.panel-body{padding:14px}.search-form{flex-direction:column}.search-form .button{width:100%}.hero-orb{width:120px;height:120px;border-radius:34px}.hero-orb span{font-size:60px}.hero p{font-size:14px}.nav{gap:5px}.nav a{padding:6px 8px;font-size:11px}}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation-duration:.01ms!important;animation-iteration-count:1!important;scroll-behavior:auto!important;transition:none!important}}


/* Animated hand-held microphone and live sound waves */
.voice-controls{display:flex;gap:9px;flex-wrap:wrap;margin-top:12px;align-items:center}.mic-button-icon{display:inline-block;font-size:18px;margin-right:3px}
.voice-stage{display:none;position:relative;min-height:185px;margin:18px 0 8px;border:1px solid #42e8ff44;border-radius:18px;overflow:hidden;background:radial-gradient(ellipse at center,#12376a99,#061126ee 70%);align-items:center;justify-content:center;flex-direction:column;isolation:isolate}
.voice-stage.active{display:flex;animation:voiceAppear .35s ease-out both}.voice-rings span{position:absolute;left:50%;top:70px;width:76px;height:76px;border:1px solid #42e8ff88;border-radius:50%;transform:translate(-50%,-50%) scale(.7);opacity:0}
.voice-stage.active .voice-rings span{animation:voiceRing 2.1s ease-out infinite}.voice-stage.active .voice-rings span:nth-child(2){animation-delay:.7s}.voice-stage.active .voice-rings span:nth-child(3){animation-delay:1.4s}
.voice-hand{position:absolute;top:24px;left:calc(50% - 44px);font-size:34px;transform:rotate(-28deg) translateY(8px);filter:drop-shadow(0 0 10px #42e8ff55);z-index:2}.voice-microphone{position:relative;z-index:3;font-size:49px;line-height:1;margin-top:12px;filter:drop-shadow(0 0 12px #42e8ff88);transform-origin:bottom center}
.voice-stage.active .voice-microphone{animation:micHeld 1.1s ease-in-out infinite alternate}.voice-waves{height:28px;display:flex;align-items:center;justify-content:center;gap:4px;margin-top:10px}.voice-waves i{width:4px;height:7px;border-radius:5px;background:#42e8ff;box-shadow:0 0 8px #42e8ff66}
.voice-stage.active .voice-waves i{animation:soundWave .65s ease-in-out infinite alternate}.voice-waves i:nth-child(2),.voice-waves i:nth-child(6){animation-delay:.12s}.voice-waves i:nth-child(3),.voice-waves i:nth-child(5){animation-delay:.24s}.voice-waves i:nth-child(4){animation-delay:.36s}
.voice-stage-label{font-size:10px;letter-spacing:2px;color:#8ceeff;margin:3px 0 12px}.voice-stage.active .voice-stage-label{color:#9affd8}
@keyframes voiceRing{0%{transform:translate(-50%,-50%) scale(.65);opacity:.85}100%{transform:translate(-50%,-50%) scale(2.5);opacity:0}}@keyframes micHeld{from{transform:rotate(-7deg) translateY(1px)}to{transform:rotate(7deg) translateY(-5px)}}@keyframes soundWave{from{height:5px;opacity:.55}to{height:25px;opacity:1}}@keyframes voiceAppear{from{opacity:0;transform:translateY(8px) scale(.98)}to{opacity:1;transform:translateY(0) scale(1)}}
@media(prefers-reduced-motion:reduce){.voice-stage.active .voice-rings span,.voice-stage.active .voice-microphone,.voice-stage.active .voice-waves i{animation:none!important}}

/* Premium motion, live status, animated chart and image viewer */
.hero .button{background:linear-gradient(110deg,#f8fdff,#9beeff,#ffffff);color:#09203b;border:1px solid #a8f5ff;box-shadow:0 0 18px #42e8ff55,0 0 45px #42e8ff22;animation:enterGlow 2.8s ease-in-out infinite}
.hero .button:hover{transform:translateY(-4px) scale(1.035);box-shadow:0 0 25px #42e8ffbb,0 0 65px #42e8ff55}
.hero-orb{animation:float 4s ease-in-out infinite,orbSpin 12s ease-in-out infinite}
.activity-top,.activity-foot{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;color:var(--muted);font-size:11px;letter-spacing:.8px}
.status-live{color:#80ffcf;display:flex;align-items:center;gap:7px}.status-live i{width:7px;height:7px;border-radius:50%;background:#47ffc1;box-shadow:0 0 12px #47ffc1;animation:blink 1.4s infinite}
.chart-bars{height:150px;display:flex;align-items:end;justify-content:space-around;gap:10px;padding:18px 4px 6px;margin:8px 0 14px;border-bottom:1px solid var(--line);background:repeating-linear-gradient(to bottom,transparent 0,transparent 36px,#4d8bd51c 37px)}
.chart-bars span{height:100%;width:9%;display:flex;flex-direction:column;justify-content:end;align-items:center;gap:7px}.chart-bars b{display:block;width:100%;height:var(--bar);min-height:8px;border-radius:7px 7px 2px 2px;background:linear-gradient(to top,#246bff,#42e8ff,#b6faff);box-shadow:0 0 16px #42e8ff44;transform-origin:bottom;animation:barRise 1.2s cubic-bezier(.2,.8,.2,1) both;position:relative;overflow:hidden}.chart-bars b:after{content:"";position:absolute;inset:-100% 0;background:linear-gradient(transparent,#ffffff88,transparent);animation:barShine 3s linear infinite}.chart-bars small{font-size:9px;color:var(--muted)}.activity-foot{font-size:9px;letter-spacing:1.3px}
.gallery a{display:block;overflow:hidden;border-radius:11px;box-shadow:0 8px 22px #0004;cursor:zoom-in}.gallery img{transition:transform .45s ease,filter .45s ease}.gallery a:hover img{transform:scale(1.09);filter:brightness(1.13) saturate(1.15)}
#photo-lightbox{position:fixed;inset:0;z-index:1000;background:#020817ed;display:none;align-items:center;justify-content:center;padding:25px;backdrop-filter:blur(12px)}#photo-lightbox.open{display:flex;animation:rise .2s both}#photo-lightbox img{max-width:min(94vw,1200px);max-height:86vh;object-fit:contain;border-radius:12px;border:1px solid #42e8ff88;box-shadow:0 0 45px #42e8ff25}#photo-lightbox button{position:absolute;top:18px;right:20px;border:1px solid #42e8ff88;background:#0b1a35;color:#fff;border-radius:50%;width:44px;height:44px;font-size:25px;cursor:pointer}
@keyframes enterGlow{0%,100%{box-shadow:0 0 18px #42e8ff55,0 0 35px #42e8ff15}50%{box-shadow:0 0 28px #42e8ff99,0 0 60px #42e8ff35}}
@keyframes orbSpin{0%,100%{filter:hue-rotate(0deg)}50%{filter:hue-rotate(18deg)}}@keyframes barRise{from{transform:scaleY(.08);opacity:.25}to{transform:scaleY(1);opacity:1}}@keyframes barShine{to{transform:translateY(220%)}}@media(max-width:650px){.chart-bars{height:115px}.activity-top,.activity-foot{font-size:9px}}
</style></head><body>
<canvas id="cyber-canvas" aria-hidden="true"></canvas>
<div id="photo-lightbox" role="dialog" aria-modal="true" aria-label="Photograph preview"><button type="button" aria-label="Close photograph">×</button><img alt="Expanded program photograph"></div>
<header class="header"><div class="header-inner"><a href="{{ url_for('welcome',lang=lang) }}" class="brand-wrap"><div class="logo">🛡️</div><div><div class="brand">{{ t.title }}</div><div class="brand-subtitle">{{ t.subtitle }}</div></div></a>
<div class="nav">{% if logged_in %}<a href="{{ url_for('home',lang=lang) }}">{{ t.all_programs }}</a><a href="{{ url_for('add_program',lang=lang) }}">+ {{ t.add_program }}</a><a href="{{ url_for('logout',lang=lang) }}">{{ t.logout }}</a>{% elif page != 'login' %}<a href="{{ url_for('login',lang=lang) }}">{{ t.sign_in }}</a>{% endif %}
<a href="{{ url_for(page_link,lang='en') }}">English</a><a href="{{ url_for(page_link,lang='mr') }}">मराठी</a></div></div></header>
<main class="{% if page == 'welcome' %}hero{% else %}container{% endif %}">
{% if message %}<div class="message {{ 'error' if error else '' }}">{{ message }}</div>{% endif %}
{% if page == 'welcome' %}
<span class="glow-dot d1"></span><span class="glow-dot d2"></span><span class="glow-dot d3"></span><span class="glow-dot d4"></span>
<div class="hero-content"><div class="hero-orb"><span>🛡️</span></div><div class="hero-tag">{{ t.welcome_tag }}</div>
<h1>{{ t.title }}</h1><p>{{ t.intro }}</p><a class="button" href="{{ url_for('login',lang=lang) }}">{{ t.enter }} &nbsp; ↗</a></div>
{% elif page == 'login' %}
<div class="login-box"><section class="panel"><div class="panel-header"><h2>🔐 {{ t.login }}</h2></div><div class="panel-body">
{% if not admin_configured %}<div class="message error">{{ t.not_configured }}</div>{% endif %}
<form method="POST" action="{{ url_for('login',lang=lang) }}"><input type="hidden" name="next" value="{{ next_url }}">
<div class="form-group"><label for="username">{{ t.username }}</label><input id="username" name="username" autocomplete="username" required autofocus></div>
<div class="form-group"><label for="password">{{ t.password }}</label><input id="password" type="password" name="password" autocomplete="current-password" required></div>
<button class="button" type="submit" {% if not admin_configured %}disabled{% endif %}>{{ t.sign_in }} →</button></form></div></section></div>
{% elif page == 'home' %}
<section class="welcome"><div class="eyebrow">CONTROL CENTER / DASHBOARD</div><h1>{{ t.welcome }}</h1><p>{{ t.intro }}</p></section>
<div class="stats"><div class="stat-card"><div class="stat-label">{{ t.total_programs }}</div><div class="stat-value">{{ total_programs }}</div></div><div class="stat-card"><div class="stat-label">{{ t.total_attendees }}</div><div class="stat-value">{{ total_attendees }}</div></div></div>
<section class="panel analytics-panel"><div class="panel-header"><h2>✦ CYBER ACTIVITY OVERVIEW</h2></div><div class="panel-body"><div class="activity-top"><span>Program management system</span><span class="status-live"><i></i> SYSTEM ACTIVE</span></div><div class="chart-bars" aria-label="Decorative activity visualization"><span style="--bar:35%"><b></b><small>01</small></span><span style="--bar:58%"><b></b><small>02</small></span><span style="--bar:44%"><b></b><small>03</small></span><span style="--bar:78%"><b></b><small>04</small></span><span style="--bar:62%"><b></b><small>05</small></span><span style="--bar:92%"><b></b><small>06</small></span><span style="--bar:70%"><b></b><small>07</small></span></div><div class="activity-foot"><span>SECURE WORKSPACE</span><span id="liveClock">Loading time…</span></div></div></section>
<div class="actions"><a class="button" href="{{ url_for('add_program',lang=lang) }}">＋ {{ t.add_program }}</a></div>
<section class="panel"><div class="panel-header"><h2>▤ {{ t.all_programs }}</h2></div><div class="panel-body">
<form class="search-form" method="GET" action="{{ url_for('home') }}"><input type="hidden" name="lang" value="{{ lang }}"><input name="q" value="{{ query }}" placeholder="{{ t.search }}"><button class="button" type="submit">{{ t.search_button }} ⌕</button></form>
{% if query %}<p><a href="{{ url_for('home',lang=lang) }}">{{ t.clear_search }}</a></p>{% endif %}
{% if programs %}<div class="table-wrap"><table><thead><tr><th>#</th><th>{{ t.date }}</th><th>{{ t.station }}</th><th>{{ t.place }}</th><th>{{ t.name }}</th><th>{{ t.attendees }}</th><th>{{ t.actions }}</th></tr></thead><tbody>
{% for p in programs %}<tr><td>{{ loop.index }}</td><td>{{ p.date }}</td><td>{{ p.station }}</td><td>{{ p.place }}</td><td>{{ p.name }}</td><td>{{ p.attendees }}</td><td><a class="badge" href="{{ url_for('program_details',program_id=p.id,lang=lang) }}">{{ t.view }}</a> <a class="badge" href="{{ url_for('edit_program',program_id=p.id,lang=lang) }}">{{ t.edit }}</a></td></tr>{% endfor %}
</tbody></table></div>{% else %}<div class="empty">{{ t.no_programs }}</div>{% endif %}</div></section>
{% elif page == 'form' %}
<section class="welcome"><div class="eyebrow">PROGRAM MANAGEMENT</div><h1>{{ t.add_program if mode == 'add' else t.edit }}</h1><p>{{ t.intro }}</p></section>
<section class="panel"><div class="panel-header"><h2>{{ t.add_program if mode == 'add' else t.edit }}</h2></div><div class="panel-body">
<form id="programForm" method="POST" enctype="multipart/form-data" action="{{ form_action }}">
<div class="form-group"><label>{{ t.date }} *</label><input type="date" name="date" value="{{ form.get('date','') }}" required></div>
<div class="form-group"><label>{{ t.station }} *</label><input name="station" value="{{ form.get('station','') }}" maxlength="150" placeholder="{{ t.station_placeholder }}" required></div>
<div class="form-group"><label>{{ t.place }} *</label><input name="place" value="{{ form.get('place','') }}" maxlength="200" placeholder="{{ t.place_placeholder }}" required></div>
<div class="form-group"><label>{{ t.name }} *</label><input name="name" value="{{ form.get('name','') }}" maxlength="200" placeholder="{{ t.name_placeholder }}" required></div>
<div class="form-group"><label>{{ t.attendees }} *</label><input type="number" name="attendees" value="{{ form.get('attendees','0') }}" min="0" max="10000000" required></div>
<div class="form-group"><label for="programDetails">{{ t.details }}</label><textarea id="programDetails" name="details" maxlength="15000" placeholder="{{ t.details_placeholder }}">{{ form.get('details','') }}</textarea>
<label for="voiceLanguage" style="margin-top:10px">{{ t.voice_language }}</label><select id="voiceLanguage"><option value="en-IN">English</option><option value="mr-IN">Marathi</option><option value="hi-IN">Hindi</option></select>
<div class="voice-controls"><button class="button mic-button" type="button" id="startVoice"><span class="mic-button-icon">🎤</span> {{ t.start_voice }}</button> <button class="button secondary" type="button" id="stopVoice" disabled>{{ t.stop_voice }}</button></div>
<div id="voiceStage" class="voice-stage" aria-hidden="true"><div class="voice-rings"><span></span><span></span><span></span></div><div class="voice-hand">✋</div><div class="voice-microphone">🎤</div><div class="voice-waves"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div><div class="voice-stage-label">MICROPHONE READY</div></div><p id="voiceStatus" class="help" aria-live="polite"></p></div>
{% if mode == 'edit' and photos %}<div class="form-group"><label>{{ t.existing_photos }}</label><div class="gallery">{% for photo in photos %}<a href="{{ url_for('uploaded_file',filename=photo.filename) }}" target="_blank" rel="noopener"><img src="{{ url_for('uploaded_file',filename=photo.filename) }}" alt="Program photo"></a>{% endfor %}</div><div class="help">Existing photos count toward the maximum of 10.</div></div>{% endif %}
<div class="form-group"><label>{{ t.photos if mode == 'add' else t.add_more_photos }}</label><input type="file" id="photoPicker" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp" multiple>
<div class="help">{{ t.photo_help }}</div><p id="photoCount">0 / {{ 10 - (photos|length if mode == 'edit' else 0) }} {{ t.photo_count }}</p><div id="photoPreview" class="photo-preview-grid"></div><div id="uploadInputs"></div>
<button class="button secondary" type="button" id="addPhotoButton">{{ t.add_photo }}</button></div>
<div class="actions"><button class="button" type="submit">{{ t.submit if mode == 'add' else t.save_changes }}</button><a class="button secondary" href="{{ url_for('home',lang=lang) }}">{{ t.cancel }}</a></div>
</form></div></section>
<script>
(function(){const form=document.getElementById('programForm'),picker=document.getElementById('photoPicker'),preview=document.getElementById('photoPreview'),count=document.getElementById('photoCount'),inputs=document.getElementById('uploadInputs'),addButton=document.getElementById('addPhotoButton');const maxAllowed={{ 10 - (photos|length if mode == 'edit' else 0) }};let selected=[],idCounter=1;
function render(){preview.replaceChildren();inputs.replaceChildren();selected.forEach(item=>{const card=document.createElement('div');card.className='photo-preview';const img=document.createElement('img');img.alt=item.file.name;const objectUrl=URL.createObjectURL(item.file);img.src=objectUrl;img.onload=()=>URL.revokeObjectURL(objectUrl);const name=document.createElement('div');name.className='filename';name.textContent=item.file.name;const remove=document.createElement('button');remove.type='button';remove.className='button danger';remove.textContent={{ t.remove_photo|tojson }};remove.addEventListener('click',()=>{selected=selected.filter(x=>x.id!==item.id);render()});card.append(img,name,remove);preview.appendChild(card);const dt=new DataTransfer();dt.items.add(item.file);const input=document.createElement('input');input.type='file';input.name='photos';input.hidden=true;input.files=dt.files;inputs.appendChild(input)});count.textContent=selected.length+' / '+maxAllowed+' {{ t.photo_count }}';picker.disabled=selected.length>=maxAllowed;addButton.disabled=selected.length>=maxAllowed}
function addFiles(files){for(const file of files){if(selected.length>=maxAllowed){alert('Maximum photo count reached.');break}const ext=file.name.split('.').pop().toLowerCase();if(!['jpg','jpeg','png','webp'].includes(ext)){alert(file.name+' is not a supported image.');continue}selected.push({id:idCounter++,file})}render()}
picker.addEventListener('change',()=>{addFiles(Array.from(picker.files||[]));picker.value=''});addButton.addEventListener('click',()=>{if(selected.length<maxAllowed)picker.click()});form.addEventListener('submit',e=>{if(selected.length>maxAllowed){e.preventDefault();alert('Maximum photo count exceeded.')}})})();
(function(){const details=document.getElementById('programDetails'),language=document.getElementById('voiceLanguage'),start=document.getElementById('startVoice'),stop=document.getElementById('stopVoice'),status=document.getElementById('voiceStatus'),stage=document.getElementById('voiceStage'),stageLabel=document.querySelector('#voiceStage .voice-stage-label'),SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SpeechRecognition){start.disabled=true;status.textContent={{ t.voice_unsupported|tojson }};return}const recognition=new SpeechRecognition();recognition.continuous=true;recognition.interimResults=true;recognition.maxAlternatives=1;let listening=false,baseText='',finalText='';
start.addEventListener('click',()=>{if(listening)return;baseText=details.value.trimEnd();finalText='';recognition.lang=language.value;try{recognition.start()}catch(e){status.textContent='Could not start microphone. Please try again.'}});stop.addEventListener('click',()=>{if(listening)recognition.stop()});recognition.onstart=()=>{listening=true;start.disabled=true;stop.disabled=false;stage.classList.add('active');stageLabel.textContent='LISTENING — SPEAK NOW';status.textContent={{ t.voice_listening|tojson }}};recognition.onresult=event=>{let interim='';for(let i=event.resultIndex;i<event.results.length;i++){const spoken=event.results[i][0].transcript;if(event.results[i].isFinal)finalText+=spoken+' ';else interim+=spoken}const spoken=finalText+interim;details.value=baseText?(baseText+'\\n'+spoken):spoken};recognition.onerror=event=>{status.textContent='Voice recognition error: '+event.error};recognition.onend=()=>{listening=false;start.disabled=false;stop.disabled=true;stage.classList.remove('active');stageLabel.textContent='MICROPHONE READY';status.textContent={{ t.voice_stopped|tojson }}}})();
</script>
{% elif page == 'details' %}
<section class="welcome"><div class="eyebrow">PROGRAM RECORD</div><h1>{{ program.name }}</h1><p>{{ t.program_details }}</p></section>
<section class="panel"><div class="panel-header"><h2>{{ t.program_details }}</h2></div><div class="panel-body">
<div class="detail-grid"><div class="detail-item"><div class="detail-label">{{ t.date }}</div><div class="detail-value">{{ program.date }}</div></div><div class="detail-item"><div class="detail-label">{{ t.station }}</div><div class="detail-value">{{ program.station }}</div></div><div class="detail-item"><div class="detail-label">{{ t.place }}</div><div class="detail-value">{{ program.place }}</div></div><div class="detail-item"><div class="detail-label">{{ t.attendees }}</div><div class="detail-value">{{ program.attendees }}</div></div></div>
<div class="form-group" style="margin-top:18px"><label>{{ t.details }}</label><div style="white-space:pre-wrap;overflow-wrap:anywhere">{{ program.details or '—' }}</div></div>
<div class="form-group"><label>{{ t.photos }}</label>{% if photos %}<div class="gallery">{% for photo in photos %}<a href="{{ url_for('uploaded_file',filename=photo.filename) }}" target="_blank" rel="noopener"><img src="{{ url_for('uploaded_file',filename=photo.filename) }}" alt="Program photograph"></a>{% endfor %}</div>{% else %}<p>{{ t.no_photo }}</p>{% endif %}</div>
<div class="actions"><a class="button" href="{{ url_for('download_pdf',program_id=program.id,lang=lang) }}">{{ t.download_pdf }}</a><a class="button secondary" href="{{ url_for('edit_program',program_id=program.id,lang=lang) }}">{{ t.edit }}</a><a class="button secondary" href="{{ url_for('home',lang=lang) }}">{{ t.back }}</a>
<form method="POST" action="{{ url_for('delete_program',program_id=program.id,lang=lang) }}" onsubmit="return confirm({{ t.confirm_delete|tojson }});"><button class="button danger" type="submit">{{ t.delete }}</button></form></div>
</div></section>
{% endif %}</main><footer class="footer">{{ t.footer }}</footer>
<script>
/* Lightweight animated network particles + gentle 3D card tilt. */
(function(){
 const canvas=document.getElementById('cyber-canvas');
 if(!canvas || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
 const ctx=canvas.getContext('2d'); if(!ctx)return;
 let w=0,h=0,dpr=1,points=[],mouse={x:-1000,y:-1000};
 function resize(){dpr=Math.min(window.devicePixelRatio||1,1.7);w=innerWidth;h=innerHeight;canvas.width=w*dpr;canvas.height=h*dpr;canvas.style.width=w+'px';canvas.style.height=h+'px';ctx.setTransform(dpr,0,0,dpr,0,0);const count=Math.min(75,Math.max(28,Math.floor(w/18)));points=Array.from({length:count},()=>({x:Math.random()*w,y:Math.random()*h,vx:(Math.random()-.5)*.42,vy:(Math.random()-.5)*.42,r:Math.random()*1.7+.5}));}
 function draw(){ctx.clearRect(0,0,w,h);for(let i=0;i<points.length;i++){const p=points[i];p.x+=p.vx;p.y+=p.vy;if(p.x<0||p.x>w)p.vx*=-1;if(p.y<0||p.y>h)p.vy*=-1;const dx=mouse.x-p.x,dy=mouse.y-p.y,dist=Math.hypot(dx,dy);if(dist<110){p.x-=dx*.0008;p.y-=dy*.0008}ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);ctx.fillStyle='rgba(66,232,255,.72)';ctx.fill();for(let j=i+1;j<points.length;j++){const q=points[j],dd=Math.hypot(p.x-q.x,p.y-q.y);if(dd<115){ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(q.x,q.y);ctx.strokeStyle='rgba(75,150,255,'+(1-dd/115)*.19+')';ctx.lineWidth=.7;ctx.stroke()}}}requestAnimationFrame(draw)}
 window.addEventListener('resize',resize,{passive:true});window.addEventListener('pointermove',e=>{mouse.x=e.clientX;mouse.y=e.clientY},{passive:true});resize();draw();
})();
(function(){if(!window.matchMedia('(hover:hover) and (pointer:fine)').matches||window.matchMedia('(prefers-reduced-motion: reduce)').matches)return;document.querySelectorAll('.stat-card,.detail-item,.photo-preview').forEach(el=>{el.addEventListener('pointermove',e=>{const r=el.getBoundingClientRect(),x=(e.clientX-r.left)/r.width,y=(e.clientY-r.top)/r.height;el.style.transform='perspective(850px) rotateX('+((.5-y)*5)+'deg) rotateY('+((x-.5)*6)+'deg) translateY(-2px)'});el.addEventListener('pointerleave',()=>{el.style.transform=''});});})();

(function(){const clock=document.getElementById('liveClock');if(clock){function tick(){clock.textContent=new Date().toLocaleString(undefined,{dateStyle:'medium',timeStyle:'medium'})}tick();setInterval(tick,1000)}})();
(function(){const box=document.getElementById('photo-lightbox');if(!box)return;const big=box.querySelector('img'),close=box.querySelector('button');document.querySelectorAll('.gallery a').forEach(a=>{a.addEventListener('click',e=>{e.preventDefault();const img=a.querySelector('img');big.src=img?img.src:a.href;big.alt=img?img.alt:'Program photograph';box.classList.add('open')})});function shut(){box.classList.remove('open');big.removeAttribute('src')}close.addEventListener('click',shut);box.addEventListener('click',e=>{if(e.target===box)shut()});document.addEventListener('keydown',e=>{if(e.key==='Escape')shut()})})();
(function(){document.querySelectorAll('.stat-value').forEach(el=>{const target=Number((el.textContent||'').replace(/,/g,''));if(!Number.isFinite(target)||target<0)return;const start=performance.now(),duration=1100;function step(now){const p=Math.min(1,(now-start)/duration);el.textContent=Math.round(target*(1-Math.pow(1-p,3))).toLocaleString();if(p<1)requestAnimationFrame(step)}el.textContent='0';requestAnimationFrame(step)})})();
</script></body></html>
"""

@app.route("/")
def welcome():
    lang = get_language()
    if logged_in():
        return redirect(url_for("home", lang=lang))
    return render_page("welcome", lang, page_link="welcome")

@app.route("/login", methods=["GET", "POST"])
def login():
    lang = get_language()
    if logged_in():
        return redirect(url_for("home", lang=lang))
    next_url = request.values.get("next", "")
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
            return redirect(next_url)
        else:
            message = TEXT[lang]["login_error"]
    return render_page("login", lang, page_link="login", next_url=next_url,
                       admin_configured=bool(ADMIN_PASSWORD), message=message, error=bool(message))

@app.route("/logout")
def logout():
    lang = get_language()
    session.clear()
    return redirect(url_for("welcome", lang=lang))

@app.route("/dashboard")
@login_required
def home():
    lang = get_language()
    query = request.args.get("q", "").strip()
    conn = get_db()
    total_programs = conn.execute("SELECT COUNT(*) FROM programs").fetchone()[0]
    total_attendees = conn.execute("SELECT COALESCE(SUM(attendees),0) FROM programs").fetchone()[0]
    if query:
        term = f"%{query}%"
        programs = conn.execute("SELECT * FROM programs WHERE date LIKE ? OR station LIKE ? OR place LIKE ? OR name LIKE ? ORDER BY date DESC,id DESC",
                                (term,term,term,term)).fetchall()
    else:
        programs = conn.execute("SELECT * FROM programs ORDER BY date DESC,id DESC").fetchall()
    conn.close()
    message = ""
    if request.args.get("saved") == "1": message = TEXT[lang]["saved"]
    if request.args.get("updated") == "1": message = TEXT[lang]["updated"]
    if request.args.get("deleted") == "1": message = TEXT[lang]["deleted"]
    return render_page("home", lang, page_link="home", programs=programs, total_programs=total_programs,
                       total_attendees=total_attendees, query=query, message=message)

def validate_and_save_photos(files, existing_count=0):
    uploads = [f for f in files if f and f.filename]
    if existing_count + len(uploads) > MAX_PHOTOS: return None, "too_many"
    for f in uploads:
        if not allowed_file(f.filename): return None, "invalid_photo"
    names = []
    try:
        for f in uploads:
            safe_name = secure_filename(f.filename)
            if not safe_name or "." not in safe_name: raise ValueError("Invalid filename")
            ext = safe_name.rsplit(".",1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            f.save(os.path.join(UPLOAD_FOLDER,filename)); names.append(filename)
    except Exception:
        for name in names:
            try: os.remove(os.path.join(UPLOAD_FOLDER,name))
            except OSError: pass
        raise
    return names, None

@app.route("/add", methods=["GET","POST"])
@login_required
def add_program():
    lang = get_language()
    if request.method == "POST":
        form=request.form.to_dict(); date=request.form.get("date","").strip()
        station=request.form.get("station","").strip(); place=request.form.get("place","").strip()
        name=request.form.get("name","").strip(); details=request.form.get("details","").strip()
        try:
            datetime.strptime(date,"%Y-%m-%d"); attendees=int(request.form.get("attendees",""))
            if attendees<0 or attendees>10000000: raise ValueError
        except (ValueError,TypeError):
            return render_page("form",lang,page_link="home",mode="add",form=form,photos=[],form_action=url_for("add_program",lang=lang),message=TEXT[lang]["required"],error=True),400
        if not all([station,place,name]):
            return render_page("form",lang,page_link="home",mode="add",form=form,photos=[],form_action=url_for("add_program",lang=lang),message=TEXT[lang]["required"],error=True),400
        names,err=validate_and_save_photos(request.files.getlist("photos"))
        if err:
            return render_page("form",lang,page_link="home",mode="add",form=form,photos=[],form_action=url_for("add_program",lang=lang),message=TEXT[lang][err],error=True),400
        try:
            conn=get_db()
            cur=conn.execute("INSERT INTO programs(date,station,place,name,attendees,details,photo) VALUES(?,?,?,?,?,?,?)",
                              (date,station,place,name,attendees,details,names[0] if names else ""))
            pid=cur.lastrowid
            for filename in names: conn.execute("INSERT INTO program_photos(program_id,filename) VALUES(?,?)",(pid,filename))
            conn.commit(); conn.close()
        except Exception:
            for filename in names:
                try: os.remove(os.path.join(UPLOAD_FOLDER,filename))
                except OSError: pass
            app.logger.exception("Could not save program")
            return render_page("form",lang,page_link="home",mode="add",form=form,photos=[],form_action=url_for("add_program",lang=lang),message="Could not save program. Please try again.",error=True),500
        return redirect(url_for("home",lang=lang,saved=1))
    return render_page("form",lang,page_link="home",mode="add",form={},photos=[],form_action=url_for("add_program",lang=lang))

@app.route("/program/<int:program_id>")
@login_required
def program_details(program_id):
    lang=get_language(); conn=get_db()
    program=conn.execute("SELECT * FROM programs WHERE id=?",(program_id,)).fetchone()
    photos=conn.execute("SELECT filename FROM program_photos WHERE program_id=? ORDER BY id",(program_id,)).fetchall()
    conn.close()
    if program is None: abort(404)
    return render_page("details",lang,page_link="home",program=program,photos=photos)

@app.route("/program/<int:program_id>/edit",methods=["GET","POST"])
@login_required
def edit_program(program_id):
    lang=get_language(); conn=get_db()
    program=conn.execute("SELECT * FROM programs WHERE id=?",(program_id,)).fetchone()
    photos=conn.execute("SELECT filename FROM program_photos WHERE program_id=? ORDER BY id",(program_id,)).fetchall()
    if program is None: conn.close(); abort(404)
    if request.method=="POST":
        form=request.form.to_dict(); date=request.form.get("date","").strip()
        station=request.form.get("station","").strip(); place=request.form.get("place","").strip()
        name=request.form.get("name","").strip(); details=request.form.get("details","").strip()
        try:
            datetime.strptime(date,"%Y-%m-%d"); attendees=int(request.form.get("attendees",""))
            if attendees<0 or attendees>10000000: raise ValueError
        except (ValueError,TypeError):
            conn.close()
            return render_page("form",lang,page_link="home",mode="edit",form=form,photos=photos,form_action=url_for("edit_program",program_id=program_id,lang=lang),message=TEXT[lang]["required"],error=True),400
        if not all([station,place,name]):
            conn.close()
            return render_page("form",lang,page_link="home",mode="edit",form=form,photos=photos,form_action=url_for("edit_program",program_id=program_id,lang=lang),message=TEXT[lang]["required"],error=True),400
        names,err=validate_and_save_photos(request.files.getlist("photos"),existing_count=len(photos))
        if err:
            conn.close()
            return render_page("form",lang,page_link="home",mode="edit",form=form,photos=photos,form_action=url_for("edit_program",program_id=program_id,lang=lang),message=TEXT[lang][err],error=True),400
        try:
            conn.execute("UPDATE programs SET date=?,station=?,place=?,name=?,attendees=?,details=? WHERE id=?",
                         (date,station,place,name,attendees,details,program_id))
            for filename in names: conn.execute("INSERT INTO program_photos(program_id,filename) VALUES(?,?)",(program_id,filename))
            first=conn.execute("SELECT filename FROM program_photos WHERE program_id=? ORDER BY id LIMIT 1",(program_id,)).fetchone()
            conn.execute("UPDATE programs SET photo=? WHERE id=?",(first["filename"] if first else "",program_id))
            conn.commit(); conn.close()
        except Exception:
            conn.close()
            for filename in names:
                try: os.remove(os.path.join(UPLOAD_FOLDER,filename))
                except OSError: pass
            app.logger.exception("Could not update program")
            return render_page("form",lang,page_link="home",mode="edit",form=form,photos=photos,form_action=url_for("edit_program",program_id=program_id,lang=lang),message="Could not update program. Please try again.",error=True),500
        return redirect(url_for("program_details",program_id=program_id,lang=lang))
    form=dict(program); conn.close()
    return render_page("form",lang,page_link="home",mode="edit",form=form,photos=photos,form_action=url_for("edit_program",program_id=program_id,lang=lang))

@app.route("/program/<int:program_id>/delete",methods=["POST"])
@login_required
def delete_program(program_id):
    conn=get_db(); program=conn.execute("SELECT id FROM programs WHERE id=?",(program_id,)).fetchone()
    photos=conn.execute("SELECT filename FROM program_photos WHERE program_id=?",(program_id,)).fetchall()
    if program is None: conn.close(); abort(404)
    conn.execute("DELETE FROM program_photos WHERE program_id=?",(program_id,))
    conn.execute("DELETE FROM programs WHERE id=?",(program_id,)); conn.commit(); conn.close()
    for row in photos:
        try: os.remove(os.path.join(UPLOAD_FOLDER,row["filename"]))
        except OSError: pass
    return redirect(url_for("home",lang=get_language(),deleted=1))

@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    safe=os.path.basename(filename)
    if safe!=filename: abort(404)
    return send_from_directory(UPLOAD_FOLDER,safe)

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
        return "PDF support is not installed. Add reportlab to requirements.txt and redeploy.",500
    lang=get_language(); t=TEXT[lang]; conn=get_db()
    program=conn.execute("SELECT * FROM programs WHERE id=?",(program_id,)).fetchone()
    photos=conn.execute("SELECT filename FROM program_photos WHERE program_id=? ORDER BY id",(program_id,)).fetchall()
    conn.close()
    if program is None: abort(404)
    buffer=BytesIO(); doc=SimpleDocTemplate(buffer,pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=17*mm,bottomMargin=17*mm)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CyberTitle",parent=styles["Title"],fontName="Helvetica-Bold",fontSize=17,leading=22,alignment=1,textColor=colors.HexColor("#236b9b"),spaceAfter=8))
    styles.add(ParagraphStyle(name="CyberSmall",parent=styles["Normal"],fontSize=9,leading=13))
    styles.add(ParagraphStyle(name="CyberPhotoTitle",parent=styles["Heading2"],alignment=1,textColor=colors.HexColor("#236b9b"),spaceAfter=10))
    story=[Paragraph(escape(t["report"]),styles["CyberTitle"]),Paragraph(escape(t["title"]),styles["Heading2"]),Spacer(1,5*mm)]
    photo_label="Photographs" if lang=="en" else "छायाचित्रे"
    rows=[[t["date"],program["date"]],[t["station"],program["station"]],[t["place"],program["place"]],
          [t["name"],program["name"]],[t["attendees"],str(program["attendees"])],
          [t["details"],program["details"] or "—"],[photo_label,str(len(photos))]]
    safe_rows=[[Paragraph("<b>"+escape(str(label))+"</b>",styles["CyberSmall"]),
                Paragraph(escape(str(value)).replace("\n","<br/>"),styles["CyberSmall"])] for label,value in rows]
    table=Table(safe_rows,colWidths=[42*mm,125*mm])
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(0,-1),colors.HexColor("#e8f3fb")),("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#b8c9dc")),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)]))
    story.extend([table,Spacer(1,4*mm),Paragraph(escape(t["page_info"]),styles["CyberSmall"])])
    if photos:
        story.extend([PageBreak(),Paragraph(escape(t["photo_page"]),styles["CyberPhotoTitle"])])
        for index,photo in enumerate(photos,start=1):
            path=os.path.join(UPLOAD_FOLDER,photo["filename"])
            if not os.path.isfile(path): continue
            try:
                img=Image(path); img._restrictSize(165*mm,220*mm)
                story.append(KeepTogether([Paragraph(f"{escape(t['photos'])} {index}",styles["Heading3"]),img,Spacer(1,5*mm)]))
            except Exception: continue
    story.extend([Spacer(1,3*mm),Paragraph(escape(t["report_generated"])+": "+datetime.now().strftime("%Y-%m-%d %H:%M"),styles["CyberSmall"])])
    doc.build(story); buffer.seek(0)
    return send_file(buffer,mimetype="application/pdf",as_attachment=True,download_name=f"program_report_{program_id}.pdf")

@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["X-Frame-Options"]="SAMEORIGIN"
    response.headers["Referrer-Policy"]="strict-origin-when-cross-origin"
    response.headers["Cache-Control"]="no-store"
    return response

@app.errorhandler(413)
def too_large(error):
    return "The complete upload request is too large. The current application limit is 50 MB total for the form and all photographs. Please choose smaller/compressed photos.",413

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)),debug=False)
