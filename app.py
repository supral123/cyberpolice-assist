import os
import mimetypes
import hmac
import uuid
from datetime import datetime, timedelta
from functools import wraps
from io import BytesIO
from xml.sax.saxutils import escape

from flask import (
    Flask, request, redirect, url_for, render_template_string,
    send_from_directory, send_file, abort, session, Response
)
from werkzeug.utils import secure_filename
from supabase import create_client

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or (uuid.uuid4().hex + uuid.uuid4().hex)
app.permanent_session_lifetime = timedelta(hours=8)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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

# Supabase is the cloud database. Set SUPABASE_URL and SUPABASE_SECRET_KEY
# in Render's Environment settings. Never expose the secret key in browser code.
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY", "").strip()
STORAGE_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET", "program-photos").strip() or "program-photos"
supabase = None

if SUPABASE_URL and SUPABASE_SECRET_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)
    except Exception:
        app.logger.exception("Could not initialize Supabase client")

def get_supabase():
    if supabase is None:
        raise RuntimeError(
            "Supabase is not configured. Set SUPABASE_URL and "
            "SUPABASE_SECRET_KEY in Render Environment settings."
        )
    return supabase

def init_db():
    # Tables are created in Supabase SQL Editor; do not create a local SQLite DB.
    pass

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

def format_display_date(value):
    """Format stored ISO dates as DD-MM-YYYY without changing database values."""
    if not value:
        return "—"
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").strftime("%d-%m-%Y")
    except (ValueError, TypeError):
        return str(value)


def render_page(page, lang="en", **kwargs):
    values = {"page":page, "lang":lang, "t":TEXT[lang], "message":kwargs.pop("message",""),
              "error":kwargs.pop("error",False), "logged_in":logged_in()}
    values.update(kwargs)
    values["format_display_date"] = format_display_date
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
.hero{min-height:calc(100vh - 80px);display:grid;place-items:center;text-align:center;padding:35px 20px;position:relative;isolation:isolate}.hero-content{max-width:1100px;width:100%;animation:rise .9s both}.namaste-welcome-art{display:block;width:min(100%,980px);height:auto;margin:0 auto 22px;border:1px solid #42e8ff88;border-radius:22px;box-shadow:0 25px 70px #0009,0 0 38px #42e8ff28;transform-style:preserve-3d;animation:namasteEntrance 1.25s cubic-bezier(.16,.8,.25,1) both,namasteFloat 6s ease-in-out 1.25s infinite;transition:filter .35s ease,box-shadow .35s ease}.namaste-welcome-art:hover{filter:saturate(1.12) brightness(1.04);box-shadow:0 30px 80px #000a,0 0 55px #42e8ff48}.namaste-caption{font-size:clamp(24px,4vw,42px);font-weight:850;letter-spacing:-.7px;margin:0 0 8px;color:#fff;text-shadow:0 0 22px #42e8ff44}.namaste-caption span{color:#ffd76a;text-shadow:0 0 24px #ffcb4c55}.namaste-subtitle{margin:0 auto 22px;color:#aeeeff;font-size:clamp(15px,2vw,20px)}@keyframes namasteEntrance{0%{opacity:0;transform:perspective(1100px) rotateY(-10deg) rotateX(7deg) translateY(30px) scale(.93);filter:blur(5px)}70%{opacity:1;transform:perspective(1100px) rotateY(2deg) rotateX(-1deg) translateY(-3px) scale(1.01);filter:blur(0)}100%{opacity:1;transform:perspective(1100px) rotateY(0) rotateX(0) translateY(0) scale(1)}}@keyframes namasteFloat{0%,100%{transform:perspective(1100px) translateY(0) rotateX(0)}50%{transform:perspective(1100px) translateY(-7px) rotateX(1deg)}}.hero-orb{width:150px;height:150px;margin:0 auto 28px;position:relative;display:grid;place-items:center;border-radius:42px;transform:rotate(-8deg);background:linear-gradient(145deg,#153d7d,#07142d);border:1px solid #50e8ff99;box-shadow:0 0 35px #2dd9ff35,inset 0 0 25px #2dd9ff15;animation:float 4s ease-in-out infinite}.hero-orb:before,.hero-orb:after{content:"";position:absolute;inset:-14px;border:1px solid #43dfff60;border-radius:48px;animation:orbit 12s linear infinite}.hero-orb:after{inset:-26px;border-color:#7a75ff55;border-style:dashed;animation-direction:reverse;animation-duration:20s}.hero-orb span{font-size:76px;filter:drop-shadow(0 0 16px #42e8ff70);transform:rotate(8deg)}.hero h1{font-size:clamp(34px,7vw,66px);line-height:1.08;margin:0 0 17px;letter-spacing:-2px;background:linear-gradient(90deg,#fff,#77eaff 55%,#9b9cff);color:transparent;background-clip:text}.hero p{max-width:620px;margin:0 auto 27px;color:#b7c8e5;font-size:16px}.hero .button{padding:15px 23px;font-size:13px;letter-spacing:1px}.hero-tag{display:inline-block;color:var(--cyan);border:1px solid var(--line);background:#0b1a35aa;border-radius:30px;padding:7px 13px;font-size:10px;letter-spacing:2px;margin-bottom:20px}.glow-dot{position:absolute;width:5px;height:5px;border-radius:50%;background:var(--cyan);box-shadow:0 0 15px var(--cyan);animation:blink 2s infinite}.glow-dot.d1{left:12%;top:25%}.glow-dot.d2{right:13%;top:31%;animation-delay:.6s}.glow-dot.d3{left:22%;bottom:18%;animation-delay:1s}.glow-dot.d4{right:23%;bottom:22%;animation-delay:1.4s}
@keyframes float{0%,100%{transform:translateY(0) rotate(-8deg)}50%{transform:translateY(-12px) rotate(-5deg)}}@keyframes orbit{to{transform:rotate(360deg)}}@keyframes rise{from{opacity:0;transform:translateY(15px)}to{opacity:1;transform:translateY(0)}}@keyframes blink{0%,100%{opacity:.3}50%{opacity:1}}

/* EXTRA CYBER MOTION EFFECTS */
#cyber-canvas{position:fixed;inset:0;width:100%;height:100%;pointer-events:none;z-index:0;opacity:.72}
/* Slow, visible cyber scan beam moving down the page */
.cyber-scanline{position:fixed;left:0;right:0;top:-24vh;height:20vh;pointer-events:none;z-index:0;opacity:.38;background:linear-gradient(180deg,transparent,rgba(66,232,255,.055) 35%,rgba(66,232,255,.13) 50%,rgba(83,136,255,.06) 65%,transparent);filter:blur(2px);animation:scanSweep 16s linear infinite}
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
@keyframes scanSweep{0%{transform:translateY(-5vh);opacity:0}12%{opacity:.38}85%{opacity:.3}100%{transform:translateY(150vh);opacity:0}}
/* Smooth reveal as the visitor scrolls through dashboard sections */
.motion-reveal{opacity:0;transform:translateY(22px) scale(.99);transition:opacity .7s ease,transform .7s cubic-bezier(.2,.75,.25,1)}
.motion-reveal.motion-visible{opacity:1;transform:translateY(0) scale(1)}
@media(max-width:700px){ #cyber-canvas{opacity:.4}.cyber-scanline{opacity:.22}.panel:before{animation:none}.hero:before{inset:0}}
@media(prefers-reduced-motion:reduce){ #cyber-canvas,.cyber-scanline{display:none}body:after,.hero:before,.hero-orb span,.logo,.namaste-welcome-art{animation:none!important}.panel:before{animation:none!important}.motion-reveal{opacity:1;transform:none;transition:none}}

@media(max-width:650px){.namaste-welcome-art{border-radius:13px;margin-bottom:16px}.header-inner{padding:12px}.brand{font-size:17px}.brand-subtitle{font-size:9px;letter-spacing:1px}.logo{width:38px;height:38px}.container{margin-top:18px;padding:0 12px}.welcome h1{font-size:26px}.stats,.detail-grid{grid-template-columns:1fr}.panel-body{padding:14px}.search-form{flex-direction:column}.search-form .button{width:100%}.hero-orb{width:120px;height:120px;border-radius:34px}.hero-orb span{font-size:60px}.hero p{font-size:14px}.nav{gap:5px}.nav a{padding:6px 8px;font-size:11px}}
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

/* Playful 3D field reactions for the Add Program experience */
.program-magic{position:relative;height:112px;animation:magicPanelIn .9s cubic-bezier(.16,.8,.25,1) both;margin:0 0 18px;border:1px solid #42e8ff42;border-radius:16px;overflow:hidden;isolation:isolate;background:radial-gradient(ellipse at 50% 120%,#174a8c88,transparent 65%),linear-gradient(120deg,#071329,#0b1e3d 55%,#111638);box-shadow:inset 0 0 28px #42e8ff0d}
.program-magic:before{content:"";position:absolute;inset:0;background:linear-gradient(105deg,transparent 20%,#42e8ff12 48%,transparent 70%);transform:translateX(-100%);animation:magicSweep 4s ease-in-out infinite}
.magic-grid{position:absolute;inset:0;opacity:.25;background-image:linear-gradient(#42e8ff22 1px,transparent 1px),linear-gradient(90deg,#42e8ff22 1px,transparent 1px);background-size:22px 22px;transform:perspective(160px) rotateX(20deg) scale(1.3);transform-origin:bottom}
.magic-caption{position:absolute;left:15px;bottom:10px;font-size:9px;letter-spacing:2px;color:#91eaff;text-transform:uppercase}
.magic-person{position:absolute;left:50%;top:9px;font-size:42px;filter:drop-shadow(0 0 12px #42e8ff8c);transform:translateX(-50%);animation:lookAround 3s ease-in-out infinite;transform-origin:50% 80%;z-index:2}
.magic-person:after{content:"◉";position:absolute;font-size:12px;color:#b9fbff;top:12px;left:18px;text-shadow:0 0 9px #42e8ff;animation:eyeBlink 3.5s infinite}
.magic-orbit{position:absolute;left:50%;top:46px;width:75px;height:24px;border:1px solid #42e8ff88;border-radius:50%;transform:translate(-50%,-50%) rotateX(65deg);box-shadow:0 0 14px #42e8ff2b;animation:orbit 5s linear infinite}
.magic-creatures{position:absolute;inset:0;pointer-events:none;overflow:hidden;z-index:4}
.magic-creature{position:absolute;left:-45px;top:20px;font-size:27px;opacity:0;filter:drop-shadow(0 0 8px #7feaff88);will-change:transform,opacity}
.program-magic.birds-active .magic-bird{animation:birdFly 2.2s cubic-bezier(.2,.65,.3,1) both}
.program-magic.people-active .magic-crowd{animation:peoplePop 1.8s cubic-bezier(.15,.8,.25,1) both}
.magic-bird.b2{top:48px;animation-delay:.12s!important;font-size:22px}.magic-bird.b3{top:8px;animation-delay:.24s!important;font-size:19px}
.magic-crowd.p2{left:auto;right:-40px;top:28px;animation-delay:.14s!important}.magic-crowd.p3{top:48px;left:46%;animation-delay:.28s!important}
#programForm .form-group{position:relative;transition:transform .28s ease,filter .28s ease}
#programForm .form-group.field-active{transform:translateZ(0) scale(1.012);filter:drop-shadow(0 0 9px #42e8ff17)}
#programForm .form-group.field-active input,#programForm .form-group.field-active textarea,#programForm .form-group.field-active select{border-color:#42e8ff;box-shadow:0 0 0 3px #42e8ff16,0 0 20px #42e8ff16;transition:box-shadow .25s,border-color .25s}
#programForm .form-group.typing-burst:after{content:"✦  ✧  ✦";position:absolute;right:12px;top:5px;color:#8ef5ff;letter-spacing:7px;pointer-events:none;animation:typeSpark .7s ease-out both;text-shadow:0 0 10px #42e8ff}
#programForm .form-group.field-active label{color:#8ef5ff;text-shadow:0 0 12px #42e8ff3d}
@keyframes magicPanelIn{0%{opacity:0;transform:perspective(850px) rotateX(-22deg) rotateY(9deg) translateY(24px) scale(.92);filter:blur(5px)}65%{opacity:1;filter:blur(0);transform:perspective(850px) rotateX(3deg) rotateY(-2deg) translateY(-2px) scale(1.01)}100%{opacity:1;transform:perspective(850px) rotateX(0) rotateY(0) translateY(0) scale(1)}}
@keyframes magicSweep{0%,25%{transform:translateX(-100%)}65%,100%{transform:translateX(100%)}}
@keyframes lookAround{0%,100%{transform:translateX(-50%) rotateY(-14deg) rotateZ(-2deg) translateY(0)}30%{transform:translateX(-50%) rotateY(18deg) rotateZ(2deg) translateY(-4px)}65%{transform:translateX(-50%) rotateY(-7deg) rotateZ(0) translateY(1px)}}
@keyframes eyeBlink{0%,44%,48%,100%{opacity:1;transform:scaleY(1)}46%{opacity:.1;transform:scaleY(.1)}}
@keyframes birdFly{0%{opacity:0;transform:translate3d(0,18px,0) scale(.45) rotate(-12deg)}15%{opacity:1}65%{opacity:1;transform:translate3d(48vw,-18px,35px) scale(1.15) rotate(8deg)}100%{opacity:0;transform:translate3d(105vw,-8px,60px) scale(.72) rotate(18deg)}}
@keyframes peoplePop{0%{opacity:0;transform:translate3d(0,45px,-60px) scale(.2) rotateX(35deg)}25%{opacity:1;transform:translate3d(0,-8px,20px) scale(1.25) rotateX(0)}55%{opacity:1;transform:translate3d(0,0,0) scale(1)}100%{opacity:0;transform:translate3d(0,-28px,35px) scale(.8)}}
@keyframes typeSpark{0%{opacity:0;transform:translateY(8px) scale(.6)}30%{opacity:1}100%{opacity:0;transform:translateY(-10px) scale(1.15)}}
@media(prefers-reduced-motion:reduce){.program-magic:before,.magic-person,.magic-orbit,.magic-creature{animation:none!important}.program-magic{display:none}#programForm .form-group{transition:none}}

.existing-photo-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:14px;margin-top:12px}.existing-photo-card{min-width:0;padding:10px;border:1px solid var(--line);border-radius:14px;background:#071329}.existing-photo-card img{display:block;width:100%;height:115px;object-fit:cover;border-radius:9px}.remove-existing-photo{display:flex;align-items:center;gap:7px;margin-top:9px;color:#ff9da8;font-size:12px;font-weight:750;cursor:pointer}.remove-existing-photo input{width:16px;height:16px;accent-color:#ef476f}.existing-photo-card:has(input:checked){border-color:#ff667f;box-shadow:0 0 0 2px #ff667f22}.existing-photo-card:has(input:checked) img{opacity:.48}
</style></head><body>
<canvas id="cyber-canvas" aria-hidden="true"></canvas>
<div class="cyber-scanline" aria-hidden="true"></div>
<div id="photo-lightbox" role="dialog" aria-modal="true" aria-label="Photograph preview"><button type="button" aria-label="Close photograph">×</button><img alt="Expanded program photograph"></div>
<header class="header"><div class="header-inner"><a href="{{ url_for('welcome',lang=lang) }}" class="brand-wrap"><div class="logo">🛡️</div><div><div class="brand">{{ t.title }}</div><div class="brand-subtitle">{{ t.subtitle }}</div></div></a>
<div class="nav">{% if logged_in %}<a href="{{ url_for('home',lang=lang) }}">{{ t.all_programs }}</a><a href="{{ url_for('add_program',lang=lang) }}">+ {{ t.add_program }}</a><a href="{{ url_for('logout',lang=lang) }}">{{ t.logout }}</a>{% elif page != 'login' %}<a href="{{ url_for('login',lang=lang) }}">{{ t.sign_in }}</a>{% endif %}
<a href="{{ url_for(page_link,lang='en') }}">English</a><a href="{{ url_for(page_link,lang='mr') }}">मराठी</a></div></div></header>
<main class="{% if page == 'welcome' %}hero{% else %}container{% endif %}">
{% if message %}<div class="message {{ 'error' if error else '' }}">{{ message }}</div>{% endif %}
{% if page == 'welcome' %}
<span class="glow-dot d1"></span><span class="glow-dot d2"></span><span class="glow-dot d3"></span><span class="glow-dot d4"></span>
<div class="hero-content"><img class="namaste-welcome-art" src="{{ url_for('static', filename='welcome_namaste.png') }}" alt="Cyber Police officer greeting Ali Sir with joined hands in Namaste"><div class="hero-tag">{{ t.welcome_tag }}</div>
<h1 class="namaste-caption">Welcome, <span>Ali Sir!</span></h1><p class="namaste-subtitle">Have a Good Day Ahead!</p><p>{{ t.intro }}</p><a class="button" href="{{ url_for('login',lang=lang) }}">{{ t.enter }} &nbsp; ↗</a></div>
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
{% for p in programs %}<tr><td>{{ loop.index }}</td><td>{{ format_display_date(p.date) }}</td><td>{{ p.station }}</td><td>{{ p.place }}</td><td>{{ p.name }}</td><td>{{ p.attendees }}</td><td><a class="badge" href="{{ url_for('program_details',program_id=p.id,lang=lang) }}">{{ t.view }}</a> <a class="badge" href="{{ url_for('edit_program',program_id=p.id,lang=lang) }}">{{ t.edit }}</a></td></tr>{% endfor %}
</tbody></table></div>{% else %}<div class="empty">{{ t.no_programs }}</div>{% endif %}</div></section>
{% elif page == 'form' %}
<section class="welcome"><div class="eyebrow">PROGRAM MANAGEMENT</div><h1>{{ t.add_program if mode == 'add' else t.edit }}</h1><p>{{ t.intro }}</p></section>
<section class="panel"><div class="panel-header"><h2>{{ t.add_program if mode == 'add' else t.edit }}</h2></div><div class="panel-body">
<div class="program-magic" id="programMagic" aria-hidden="true"><div class="magic-grid"></div><div class="magic-orbit"></div><div class="magic-person">🕵️</div><div class="magic-creatures"><span class="magic-creature magic-bird">🕊️</span><span class="magic-creature magic-bird b2">🐦</span><span class="magic-creature magic-bird b3">🕊️</span><span class="magic-creature magic-crowd">🧍</span><span class="magic-creature magic-crowd p2">👮</span><span class="magic-creature magic-crowd p3">🧑‍🤝‍🧑</span></div><div class="magic-caption" id="magicCaption">3D PROGRAM INTERFACE · READY</div></div>
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
{% if mode == 'edit' and photos %}<div class="form-group"><label>{{ t.existing_photos }}</label><div class="existing-photo-grid">{% for photo in photos %}<div class="existing-photo-card" data-existing-photo><a href="{{ url_for('uploaded_file',filename=photo.filename) }}" target="_blank" rel="noopener"><img src="{{ url_for('uploaded_file',filename=photo.filename) }}" alt="Program photo"></a><label class="remove-existing-photo"><input type="checkbox" name="remove_photos" value="{{ photo.filename }}" data-remove-existing> 🗑️ Remove photo</label></div>{% endfor %}</div><div class="help">Select photos to remove, then click Save Changes. Removal is applied only after saving.</div></div>{% endif %}
<div class="form-group"><label>{{ t.photos if mode == 'add' else t.add_more_photos }}</label><input type="file" id="photoPicker" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp" multiple>
<div class="help">{{ t.photo_help }}</div><p id="photoCount">0 / {{ 10 - (photos|length if mode == 'edit' else 0) }} {{ t.photo_count }}</p><div id="photoPreview" class="photo-preview-grid"></div><div id="uploadInputs"></div>
<button class="button secondary" type="button" id="addPhotoButton">{{ t.add_photo }}</button></div>
<div class="actions"><button class="button" type="submit">{{ t.submit if mode == 'add' else t.save_changes }}</button><a class="button secondary" href="{{ url_for('home',lang=lang) }}">{{ t.cancel }}</a></div>
</form></div></section>
<script>
(function(){const form=document.getElementById('programForm'),picker=document.getElementById('photoPicker'),preview=document.getElementById('photoPreview'),count=document.getElementById('photoCount'),inputs=document.getElementById('uploadInputs'),addButton=document.getElementById('addPhotoButton'),magic=document.getElementById('programMagic'),magicCaption=document.getElementById('magicCaption');let maxAllowed={{ 10 - (photos|length if mode == 'edit' else 0) }};let selected=[],idCounter=1;
if(form&&magic){
  // The investigator appears when Add Program opens.
  requestAnimationFrame(()=>{magic.classList.add('magic-open');magicCaption.textContent='3D SCENE ACTIVE · ENTER PROGRAM DETAILS'});
  const placeField=form.querySelector('[name="place"]'),nameField=form.querySelector('[name="name"]');
  function replay(className){magic.classList.remove('birds-active','people-active');void magic.offsetWidth;magic.classList.add(className);window.setTimeout(()=>magic.classList.remove(className),2300)}
  function activateField(field,scene){form.querySelectorAll('.form-group').forEach(g=>g.classList.remove('field-active'));const group=field.closest('.form-group');if(group)group.classList.add('field-active');magicCaption.textContent=scene==='birds-active'?'PROGRAM NAME · BIRDS IN FLIGHT':scene==='people-active'?'PROGRAM PLACE · PEOPLE ARRIVE':'CYBER PROGRAM · FIELD ACTIVE';if(scene)replay(scene)}
  if(nameField){nameField.addEventListener('focus',()=>activateField(nameField,'birds-active'));nameField.addEventListener('input',()=>{const g=nameField.closest('.form-group');if(g){g.classList.remove('typing-burst');void g.offsetWidth;g.classList.add('typing-burst');setTimeout(()=>g.classList.remove('typing-burst'),750)}})}
  if(placeField){placeField.addEventListener('focus',()=>activateField(placeField,'people-active'));placeField.addEventListener('input',()=>{const g=placeField.closest('.form-group');if(g){g.classList.remove('typing-burst');void g.offsetWidth;g.classList.add('typing-burst');setTimeout(()=>g.classList.remove('typing-burst'),750)}})}
  form.querySelectorAll('input:not([type=file]),textarea,select').forEach(field=>{field.addEventListener('focus',()=>{const g=field.closest('.form-group');if(g)g.classList.add('field-active')});field.addEventListener('input',()=>{const g=field.closest('.form-group');if(g){g.classList.remove('typing-burst');void g.offsetWidth;g.classList.add('typing-burst');setTimeout(()=>g.classList.remove('typing-burst'),750)}})});
  form.addEventListener('focusout',e=>{if(!form.contains(e.relatedTarget)){form.querySelectorAll('.form-group').forEach(g=>g.classList.remove('field-active'));magicCaption.textContent='3D PROGRAM INTERFACE · READY'}})
}
function render(){preview.replaceChildren();inputs.replaceChildren();selected.forEach(item=>{const card=document.createElement('div');card.className='photo-preview';const img=document.createElement('img');img.alt=item.file.name;const objectUrl=URL.createObjectURL(item.file);img.src=objectUrl;img.onload=()=>URL.revokeObjectURL(objectUrl);const name=document.createElement('div');name.className='filename';name.textContent=item.file.name;const remove=document.createElement('button');remove.type='button';remove.className='button danger';remove.textContent={{ t.remove_photo|tojson }};remove.addEventListener('click',()=>{selected=selected.filter(x=>x.id!==item.id);render()});card.append(img,name,remove);preview.appendChild(card);const dt=new DataTransfer();dt.items.add(item.file);const input=document.createElement('input');input.type='file';input.name='photos';input.hidden=true;input.files=dt.files;inputs.appendChild(input)});count.textContent=selected.length+' / '+maxAllowed+' {{ t.photo_count }}';picker.disabled=selected.length>=maxAllowed;addButton.disabled=selected.length>=maxAllowed}
const existingPhotoChecks=Array.from(form.querySelectorAll('[data-remove-existing]'));
function refreshPhotoLimit(){maxAllowed=10-existingPhotoChecks.filter(cb=>!cb.checked).length;render()}
existingPhotoChecks.forEach(cb=>cb.addEventListener('change',refreshPhotoLimit));
function addFiles(files){for(const file of files){if(selected.length>=maxAllowed){alert('Maximum photo count reached.');break}const ext=file.name.split('.').pop().toLowerCase();if(!['jpg','jpeg','png','webp'].includes(ext)){alert(file.name+' is not a supported image.');continue}selected.push({id:idCounter++,file})}render()}
picker.addEventListener('change',()=>{addFiles(Array.from(picker.files||[]));picker.value=''});addButton.addEventListener('click',()=>{if(selected.length<maxAllowed)picker.click()});form.addEventListener('submit',e=>{if(selected.length>maxAllowed){e.preventDefault();alert('Maximum photo count exceeded.')}})})();
(function(){const details=document.getElementById('programDetails'),language=document.getElementById('voiceLanguage'),start=document.getElementById('startVoice'),stop=document.getElementById('stopVoice'),status=document.getElementById('voiceStatus'),stage=document.getElementById('voiceStage'),stageLabel=document.querySelector('#voiceStage .voice-stage-label'),SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SpeechRecognition){start.disabled=true;status.textContent={{ t.voice_unsupported|tojson }};return}const recognition=new SpeechRecognition();recognition.continuous=true;recognition.interimResults=true;recognition.maxAlternatives=1;let listening=false,baseText='',finalText='';
start.addEventListener('click',()=>{if(listening)return;baseText=details.value.trimEnd();finalText='';recognition.lang=language.value;try{recognition.start()}catch(e){status.textContent='Could not start microphone. Please try again.'}});stop.addEventListener('click',()=>{if(listening)recognition.stop()});recognition.onstart=()=>{listening=true;start.disabled=true;stop.disabled=false;stage.classList.add('active');stageLabel.textContent='LISTENING — SPEAK NOW';status.textContent={{ t.voice_listening|tojson }}};recognition.onresult=event=>{let interim='';for(let i=event.resultIndex;i<event.results.length;i++){const spoken=event.results[i][0].transcript;if(event.results[i].isFinal)finalText+=spoken+' ';else interim+=spoken}const spoken=finalText+interim;details.value=baseText?(baseText+'\\n'+spoken):spoken};recognition.onerror=event=>{status.textContent='Voice recognition error: '+event.error};recognition.onend=()=>{listening=false;start.disabled=false;stop.disabled=true;stage.classList.remove('active');stageLabel.textContent='MICROPHONE READY';status.textContent={{ t.voice_stopped|tojson }}}})();
</script>
{% elif page == 'details' %}
<section class="welcome"><div class="eyebrow">PROGRAM RECORD</div><h1>{{ program.name }}</h1><p>{{ t.program_details }}</p></section>
<section class="panel"><div class="panel-header"><h2>{{ t.program_details }}</h2></div><div class="panel-body">
<div class="detail-grid"><div class="detail-item"><div class="detail-label">{{ t.date }}</div><div class="detail-value">{{ format_display_date(program.date) }}</div></div><div class="detail-item"><div class="detail-label">{{ t.station }}</div><div class="detail-value">{{ program.station }}</div></div><div class="detail-item"><div class="detail-label">{{ t.place }}</div><div class="detail-value">{{ program.place }}</div></div><div class="detail-item"><div class="detail-label">{{ t.attendees }}</div><div class="detail-value">{{ program.attendees }}</div></div></div>
<div class="form-group" style="margin-top:18px"><label>{{ t.details }}</label><div style="white-space:pre-wrap;overflow-wrap:anywhere">{{ program.details or '—' }}</div></div>
<div class="form-group"><label>{{ t.photos }}</label>{% if photos %}<div class="gallery">{% for photo in photos %}<a href="{{ url_for('uploaded_file',filename=photo.filename) }}" target="_blank" rel="noopener"><img src="{{ url_for('uploaded_file',filename=photo.filename) }}" alt="Program photograph"></a>{% endfor %}</div>{% else %}<p>{{ t.no_photo }}</p>{% endif %}</div>
<div class="actions"><a class="button" href="{{ url_for('download_pdf',program_id=program.id,lang=lang) }}">{{ t.download_pdf }}</a><a class="button secondary" href="{{ url_for('edit_program',program_id=program.id,lang=lang) }}">{{ t.edit }}</a><a class="button secondary" href="{{ url_for('home',lang=lang) }}">{{ t.back }}</a>
<form method="POST" action="{{ url_for('delete_program',program_id=program.id,lang=lang) }}" onsubmit="return confirm({{ t.confirm_delete|tojson }});"><button class="button danger" type="submit">{{ t.delete }}</button></form></div>
</div></section>
{% endif %}</main><footer class="footer">{{ t.footer }}</footer>
<script>
/* Lightweight animated network particles + gentle 3D card tilt. */
(function(){
 const reduceMotion=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
 const revealTargets=document.querySelectorAll('main.container > .welcome, main.container > .stats, main.container > .panel, main.container > .actions');
 if(reduceMotion){revealTargets.forEach(el=>el.classList.add('motion-visible'));}
 else if('IntersectionObserver' in window){
   const revealObserver=new IntersectionObserver(entries=>entries.forEach(entry=>{
     if(entry.isIntersecting){entry.target.classList.add('motion-visible');revealObserver.unobserve(entry.target);}
   }),{threshold:.08,rootMargin:'0px 0px -25px 0px'});
   revealTargets.forEach((el,index)=>{el.classList.add('motion-reveal');el.style.transitionDelay=Math.min(index*70,280)+'ms';revealObserver.observe(el);});
 }else{revealTargets.forEach(el=>el.classList.add('motion-visible'));}
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
    try:
        db = get_supabase()
        all_rows = db.table("programs").select("*").order("date", desc=True).order("id", desc=True).execute().data or []
        total_programs = len(all_rows)
        total_attendees = sum(int(row.get("attendees") or 0) for row in all_rows)
        if query:
            needle = query.casefold()
            programs = [
                row for row in all_rows
                if any(needle in str(row.get(field) or "").casefold()
                       for field in ("date", "station", "place", "name"))
            ]
        else:
            programs = list(all_rows)

        # Stable sorts: newest date first, then Place A-Z within each date.
        programs.sort(key=lambda row: str(row.get("place") or "").strip().casefold())
        programs.sort(key=lambda row: str(row.get("date") or "")[:10], reverse=True)
    except Exception:
        app.logger.exception("Could not load programs from Supabase")
        return "Database connection failed. Check Render logs and Supabase setup.", 500

    message = ""
    if request.args.get("saved") == "1": message = TEXT[lang]["saved"]
    if request.args.get("updated") == "1": message = TEXT[lang]["updated"]
    if request.args.get("deleted") == "1": message = TEXT[lang]["deleted"]
    return render_page("home", lang, page_link="home", programs=programs, total_programs=total_programs,
                       total_attendees=total_attendees, query=query, message=message)

def delete_stored_photos(names):
    """Delete uploaded objects from the private Supabase Storage bucket."""
    names = [os.path.basename(str(name)) for name in names if name]
    if not names:
        return
    try:
        get_supabase().storage.from_(STORAGE_BUCKET).remove(names)
    except Exception:
        app.logger.exception("Could not remove photographs from Supabase Storage")


def validate_and_save_photos(files, existing_count=0):
    """Upload images to Supabase Storage; Render's local disk is not persistent."""
    uploads = [f for f in files if f and f.filename]
    if existing_count + len(uploads) > MAX_PHOTOS:
        return None, "too_many"
    for f in uploads:
        if not allowed_file(f.filename):
            return None, "invalid_photo"

    names = []
    storage = get_supabase().storage.from_(STORAGE_BUCKET)
    try:
        for f in uploads:
            safe_name = secure_filename(f.filename)
            if not safe_name or "." not in safe_name:
                raise ValueError("Invalid filename")
            ext = safe_name.rsplit(".", 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            file_bytes = f.read()
            if not file_bytes:
                raise ValueError("Uploaded photograph is empty")
            storage.upload(filename, file_bytes, file_options={
                "content-type": content_type,
                "cache-control": "3600",
                "upsert": "false"
            })
            names.append(filename)
    except Exception:
        delete_stored_photos(names)
        app.logger.exception("Could not upload photographs to Supabase Storage")
        raise
    return names, None

@app.route("/add", methods=["GET","POST"])
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
            return render_page("form", lang, page_link="home", mode="add", form=form, photos=[],
                               form_action=url_for("add_program", lang=lang),
                               message=TEXT[lang]["required"], error=True), 400
        if not all([station, place, name]):
            return render_page("form", lang, page_link="home", mode="add", form=form, photos=[],
                               form_action=url_for("add_program", lang=lang),
                               message=TEXT[lang]["required"], error=True), 400
        names, err = validate_and_save_photos(request.files.getlist("photos"))
        if err:
            return render_page("form", lang, page_link="home", mode="add", form=form, photos=[],
                               form_action=url_for("add_program", lang=lang),
                               message=TEXT[lang][err], error=True), 400
        try:
            db = get_supabase()
            inserted = db.table("programs").insert({
                "date": date, "station": station, "place": place, "name": name,
                "attendees": attendees, "details": details,
                "photo": names[0] if names else ""
            }).execute().data
            if not inserted:
                raise RuntimeError("Supabase did not return the inserted program.")
            pid = inserted[0]["id"]
            if names:
                db.table("program_photos").insert([
                    {"program_id": pid, "filename": filename} for filename in names
                ]).execute()
        except Exception:
            delete_stored_photos(names)
            app.logger.exception("Could not save program to Supabase")
            return render_page("form", lang, page_link="home", mode="add", form=form, photos=[],
                               form_action=url_for("add_program", lang=lang),
                               message="Could not save program. Check Supabase configuration and try again.",
                               error=True), 500
        return redirect(url_for("home", lang=lang, saved=1))
    return render_page("form", lang, page_link="home", mode="add", form={}, photos=[],
                       form_action=url_for("add_program", lang=lang))

@app.route("/program/<int:program_id>")
@login_required
def program_details(program_id):
    lang = get_language()
    try:
        db = get_supabase()
        result = db.table("programs").select("*").eq("id", program_id).limit(1).execute().data or []
        program = result[0] if result else None
        photos = db.table("program_photos").select("filename").eq("program_id", program_id).order("id").execute().data or []
    except Exception:
        app.logger.exception("Could not load program details from Supabase")
        return "Database connection failed. Check Render logs and Supabase setup.", 500
    if program is None: abort(404)
    return render_page("details", lang, page_link="home", program=program, photos=photos)

@app.route("/program/<int:program_id>/edit", methods=["GET","POST"])
@login_required
def edit_program(program_id):
    lang = get_language()
    try:
        db = get_supabase()
        found = db.table("programs").select("*").eq("id", program_id).limit(1).execute().data or []
        program = found[0] if found else None
        photos = db.table("program_photos").select("filename").eq("program_id", program_id).order("id").execute().data or []
    except Exception:
        app.logger.exception("Could not load program for editing")
        return "Database connection failed. Check Render logs and Supabase setup.", 500
    if program is None: abort(404)

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
            return render_page("form", lang, page_link="home", mode="edit", form=form, photos=photos,
                               form_action=url_for("edit_program", program_id=program_id, lang=lang),
                               message=TEXT[lang]["required"], error=True), 400
        if not all([station, place, name]):
            return render_page("form", lang, page_link="home", mode="edit", form=form, photos=photos,
                               form_action=url_for("edit_program", program_id=program_id, lang=lang),
                               message=TEXT[lang]["required"], error=True), 400
        # Only permit removing filenames already linked to this program.
        current_filenames = {str(row.get("filename", "")) for row in photos}
        removed_names = list(set(request.form.getlist("remove_photos")) & current_filenames)
        remaining_count = len(photos) - len(removed_names)
        names, err = validate_and_save_photos(
            request.files.getlist("photos"), existing_count=remaining_count
        )
        if err:
            return render_page("form", lang, page_link="home", mode="edit", form=form, photos=photos,
                               form_action=url_for("edit_program", program_id=program_id, lang=lang),
                               message=TEXT[lang][err], error=True), 400
        try:
            db.table("programs").update({
                "date": date, "station": station, "place": place, "name": name,
                "attendees": attendees, "details": details
            }).eq("id", program_id).execute()

            # Remove selected photo rows only when Save Changes is submitted.
            if removed_names:
                db.table("program_photos").delete().eq("program_id", program_id).in_("filename", removed_names).execute()

            if names:
                db.table("program_photos").insert([
                    {"program_id": program_id, "filename": filename} for filename in names
                ]).execute()

            updated_photos = db.table("program_photos").select("filename").eq("program_id", program_id).order("id").execute().data or []
            db.table("programs").update({"photo": updated_photos[0]["filename"] if updated_photos else ""}).eq("id", program_id).execute()
        except Exception:
            delete_stored_photos(names)
            app.logger.exception("Could not update program in Supabase")
            return render_page("form", lang, page_link="home", mode="edit", form=form, photos=photos,
                               form_action=url_for("edit_program", program_id=program_id, lang=lang),
                               message="Could not update program. Check Supabase configuration and try again.",
                               error=True), 500

        # Delete storage objects after database references have been updated.
        if removed_names:
            delete_stored_photos(removed_names)
        return redirect(url_for("program_details", program_id=program_id, lang=lang))

    return render_page("form", lang, page_link="home", mode="edit", form=program, photos=photos,
                       form_action=url_for("edit_program", program_id=program_id, lang=lang))

@app.route("/program/<int:program_id>/delete", methods=["POST"])
@login_required
def delete_program(program_id):
    try:
        db = get_supabase()
        found = db.table("programs").select("id").eq("id", program_id).limit(1).execute().data or []
        if not found: abort(404)
        photos = db.table("program_photos").select("filename").eq("program_id", program_id).execute().data or []
        db.table("program_photos").delete().eq("program_id", program_id).execute()
        db.table("programs").delete().eq("id", program_id).execute()
    except Exception:
        app.logger.exception("Could not delete program from Supabase")
        return "Could not delete program. Check Supabase configuration and logs.", 500
    delete_stored_photos([row.get("filename") for row in photos])
    return redirect(url_for("home", lang=get_language(), deleted=1))

@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    safe = os.path.basename(filename)
    if safe != filename:
        abort(404)
    try:
        image_bytes = get_supabase().storage.from_(STORAGE_BUCKET).download(safe)
    except Exception:
        app.logger.exception("Photograph not found in Supabase Storage: %s", safe)
        abort(404)
    mime_type = mimetypes.guess_type(safe)[0] or "application/octet-stream"
    return send_file(BytesIO(image_bytes), mimetype=mime_type, download_name=safe, max_age=0)

@app.route("/program/<int:program_id>/pdf")
@login_required
def download_pdf(program_id):
    """Create a one-page program summary followed by photo pages (4 photos/page)."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_LEFT, TA_CENTER
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.platypus import Paragraph
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        return "PDF support is not installed. Add reportlab to requirements.txt and redeploy.", 500

    # Bundle this font with the app (fonts/Lohit-Devanagari.ttf) so mixed
    # Marathi/Devanagari + English text is embedded in generated PDFs on Render.
    unicode_font_path = os.path.join(BASE_DIR, "fonts", "Lohit-Devanagari.ttf")
    pdf_font_regular = "Helvetica"
    pdf_font_bold = "Helvetica-Bold"
    if os.path.isfile(unicode_font_path):
        try:
            if "CyberPoliceUnicode" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("CyberPoliceUnicode", unicode_font_path, shapable=True))
            # Use one embedded Unicode font for both weights; glyph coverage is
            # more important than synthetic bold for mixed-script program data.
            pdf_font_regular = "CyberPoliceUnicode"
            pdf_font_bold = "CyberPoliceUnicode"
        except Exception:
            app.logger.exception("Could not register the bundled Unicode PDF font")

    lang = get_language()
    t = TEXT[lang]
    try:
        db = get_supabase()
        found = db.table("programs").select("*").eq("id", program_id).limit(1).execute().data or []
        program = found[0] if found else None
        photos = db.table("program_photos").select("filename").eq("program_id", program_id).order("id").execute().data or []
    except Exception:
        app.logger.exception("Could not load PDF report data from Supabase")
        return "Database connection failed. Check Render logs and Supabase setup.", 500

    if program is None:
        abort(404)

    # Always load photo bytes from persistent Supabase Storage, never Render local disk.
    photo_files = []
    storage = get_supabase().storage.from_(STORAGE_BUCKET)
    for photo in photos:
        filename = os.path.basename(str(photo.get("filename", "")))
        if not filename:
            continue
        try:
            image_bytes = storage.download(filename)
            if image_bytes:
                photo_files.append((filename, image_bytes))
        except Exception:
            app.logger.exception("Could not download photograph from Supabase Storage: %s", filename)

    page_w, page_h = A4
    margin = 15 * mm
    content_w = page_w - 2 * margin
    navy = colors.HexColor("#0A1730")
    navy2 = colors.HexColor("#10294A")
    cyan = colors.HexColor("#11A9C8")
    ink = colors.HexColor("#18283D")
    muted = colors.HexColor("#62748A")
    pale = colors.HexColor("#F1F7FB")
    border = colors.HexColor("#D4E1EC")
    white = colors.white

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4, pageCompression=1)
    pdf.setTitle(f"{program.get('name', 'Program')} - Cyber Awareness Report")
    pdf.setAuthor("CyberPolice Assist")

    def para(text, size, leading=None, color=ink, bold=False, alignment=TA_LEFT):
        safe_text = escape(str(text if text is not None else "—")).replace("\n", "<br/>")
        return Paragraph(safe_text, ParagraphStyle(
            name=f"p_{size}_{bold}_{alignment}", fontName=pdf_font_bold if bold else pdf_font_regular,
            fontSize=size, leading=leading or size * 1.35, textColor=color, alignment=alignment,
            splitLongWords=1, spaceAfter=0, spaceBefore=0, shaping=1
        ))

    def draw_paragraph(p, x, top_y, width):
        _, height = p.wrap(width, page_h)
        p.drawOn(pdf, x, top_y - height)
        return height

    # -------------------- PAGE 1: ALL PROGRAM INFORMATION --------------------
    pdf.setFillColor(navy)
    pdf.rect(0, page_h - 91, page_w, 91, fill=1, stroke=0)
    pdf.setFillColor(cyan)
    pdf.rect(0, page_h - 95, page_w, 4, fill=1, stroke=0)
    pdf.setFillColor(white)
    pdf.setFont(pdf_font_bold, 9)
    pdf.drawString(margin, page_h - 25, "CYBERPOLICE ASSIST  /  PROGRAM MANAGEMENT", shaping=True)
    pdf.setFont(pdf_font_bold, 19)
    report_title = t["report"]
    pdf.drawString(margin, page_h - 52, report_title[:70], shaping=True)
    pdf.setFont(pdf_font_regular, 8)
    pdf.setFillColor(colors.HexColor("#C9D9EA"))
    pdf.drawString(margin, page_h - 72, "OFFICIAL PROGRAM RECORD", shaping=True)
    pdf.setFillColor(ink)

    top = page_h - 113
    gap = 10
    col_w = (content_w - gap) / 2
    details_text = str(program.get("details") or "—")
    meta = [
        (t["date"], format_display_date(program.get("date"))),
        (t["station"], str(program.get("station") or "—")),
        (t["place"], str(program.get("place") or "—")),
        (t["attendees"], str(program.get("attendees", "—"))),
        (t["name"], str(program.get("name") or "—")),
        ("Photographs" if lang == "en" else "छायाचित्रे", str(len(photos))),
    ]

    # Dynamically compact text so even long details are fitted onto the single
    # information page. The content is never intentionally flowed to a new page.
    chosen = None
    for font_size in [10, 9, 8, 7, 6, 5, 4.5, 4, 3.5, 3, 2.7]:
        label_size = max(5.2, font_size * 0.78)
        value_leading = max(3.2, font_size * 1.24)
        label_leading = label_size * 1.15
        meta_heights = []
        for i in range(0, len(meta), 2):
            row_h = 0
            for label, value in meta[i:i + 2]:
                lp = para(label.upper(), label_size, label_leading, muted, True)
                vp = para(value, font_size, value_leading, ink, True)
                _, lh = lp.wrap(col_w - 18, page_h)
                _, vh = vp.wrap(col_w - 18, page_h)
                row_h = max(row_h, 12 + lh + 4 + vh + 9)
            meta_heights.append(row_h)
        details_label = para(t["details"].upper(), label_size, label_leading, muted, True)
        details_para = para(details_text, font_size, value_leading, ink, False)
        _, dl_h = details_label.wrap(content_w - 20, page_h)
        _, dv_h = details_para.wrap(content_w - 20, page_h)
        details_h = 14 + dl_h + 4 + dv_h + 10
        total_h = sum(meta_heights) + 9 * (len(meta_heights) - 1) + 10 + details_h
        if total_h <= top - (margin + 30):
            chosen = (font_size, label_size, value_leading, label_leading, meta_heights, details_h)
            break
    if chosen is None:
        # At the supported form limit this should rarely be needed; use the
        # smallest layout size as a final fit fallback.
        chosen = (2.5, 5.2, 3.1, 5.98, [], 0)

    font_size, label_size, value_leading, label_leading, meta_heights, details_h = chosen
    y = top
    for row_index, row_start in enumerate(range(0, len(meta), 2)):
        row_items = meta[row_start:row_start + 2]
        row_h = meta_heights[row_index] if row_index < len(meta_heights) else 35
        for col, (label, value) in enumerate(row_items):
            x = margin + col * (col_w + gap)
            pdf.setFillColor(pale)
            pdf.roundRect(x, y - row_h, col_w, row_h, 7, fill=1, stroke=0)
            pdf.setStrokeColor(border)
            pdf.setLineWidth(0.6)
            pdf.roundRect(x, y - row_h, col_w, row_h, 7, fill=0, stroke=1)
            inner_x = x + 9
            inner_top = y - 9
            lp = para(label.upper(), label_size, label_leading, muted, True)
            lh = draw_paragraph(lp, inner_x, inner_top, col_w - 18)
            vp = para(value, font_size, value_leading, ink, True)
            draw_paragraph(vp, inner_x, inner_top - lh - 4, col_w - 18)
        y -= row_h + 9

    y -= 1
    pdf.setFillColor(white)
    pdf.roundRect(margin, y - details_h, content_w, details_h, 8, fill=1, stroke=0)
    pdf.setStrokeColor(border)
    pdf.roundRect(margin, y - details_h, content_w, details_h, 8, fill=0, stroke=1)
    inner_x = margin + 10
    inner_top = y - 9
    details_label = para(t["details"].upper(), label_size, label_leading, muted, True)
    dh = draw_paragraph(details_label, inner_x, inner_top, content_w - 20)
    details_para = para(details_text, font_size, value_leading, ink, False)
    draw_paragraph(details_para, inner_x, inner_top - dh - 4, content_w - 20)

    # Reclaim the unused lower half of page 1 for photographs. The details
    # section remains intact; up to four images are placed here when space allows.
    first_page_photo_count = 0
    if photo_files:
        details_bottom = y - details_h
        photo_grid_top = details_bottom - 12
        photo_grid_bottom = margin + 27
        photo_available_h = photo_grid_top - photo_grid_bottom
        photo_rows = 2 if photo_available_h >= 190 else (1 if photo_available_h >= 90 else 0)
        first_page_photo_count = min(len(photo_files), photo_rows * 2)
        if first_page_photo_count:
            grid_gap_x = 8 * mm
            grid_gap_y = 5 * mm
            photo_cols = 2
            photo_cell_w = (content_w - grid_gap_x) / photo_cols
            photo_cell_h = (photo_available_h - grid_gap_y * (photo_rows - 1)) / photo_rows
            image_pad = 6
            caption_h = 15
            pdf.setFillColor(navy2)
            pdf.setFont(pdf_font_bold, 8)
            pdf.drawString(margin, photo_grid_top + 1, "PROGRAM PHOTOGRAPHS" if lang == "en" else "कार्यक्रमाची छायाचित्रे", shaping=True)
            for local_index, (filename, path) in enumerate(photo_files[:first_page_photo_count]):
                col = local_index % 2
                row = local_index // 2
                x = margin + col * (photo_cell_w + grid_gap_x)
                cell_top = photo_grid_top - 10 - row * (photo_cell_h + grid_gap_y)
                cell_bottom = cell_top - photo_cell_h
                pdf.setFillColor(white)
                pdf.roundRect(x, cell_bottom, photo_cell_w, photo_cell_h, 7, fill=1, stroke=0)
                pdf.setStrokeColor(border)
                pdf.setLineWidth(0.6)
                pdf.roundRect(x, cell_bottom, photo_cell_w, photo_cell_h, 7, fill=0, stroke=1)
                try:
                    reader = ImageReader(BytesIO(image_bytes))
                    iw, ih = reader.getSize()
                    image_w = photo_cell_w - 2 * image_pad
                    image_h = photo_cell_h - caption_h - 2 * image_pad
                    if iw > 0 and ih > 0 and image_w > 0 and image_h > 0:
                        scale = min(image_w / iw, image_h / ih)
                        draw_w, draw_h = iw * scale, ih * scale
                        img_x = x + (photo_cell_w - draw_w) / 2
                        img_y = cell_bottom + caption_h + image_pad + (image_h - draw_h) / 2
                        pdf.drawImage(reader, img_x, img_y, width=draw_w, height=draw_h, preserveAspectRatio=True, mask="auto")
                except Exception:
                    app.logger.exception("Could not embed first-page photograph %s in PDF", filename)
                pdf.setFillColor(navy2)
                pdf.setFont(pdf_font_bold, 7)
                pdf.drawString(x + image_pad, cell_bottom + 5, f"PHOTO {local_index + 1:02d}", shaping=True)

    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    pdf.setStrokeColor(border)
    pdf.line(margin, margin + 13, page_w - margin, margin + 13)
    pdf.setFillColor(muted)
    pdf.setFont(pdf_font_regular, 7)
    pdf.drawString(margin, margin, f"{t['report_generated']}: {generated}", shaping=True)
    pdf.drawRightString(page_w - margin, margin, "PAGE 1  •  PROGRAM INFORMATION", shaping=True)
    pdf.showPage()

    # -------------------- PHOTO PAGES: EXACTLY 4 PHOTOS PER PAGE --------------------
    remaining_photo_files = photo_files[first_page_photo_count:]
    if remaining_photo_files:
        photo_title = t["photo_page"]
        cols = 2
        grid_gap_x = 10 * mm
        grid_gap_y = 10 * mm
        cell_w = (content_w - grid_gap_x) / 2
        header_h = 62
        grid_top = page_h - margin - header_h
        footer_y = margin
        grid_bottom = margin + 24
        cell_h = (grid_top - grid_bottom - grid_gap_y) / 2
        image_pad = 8
        caption_h = 23
        image_w = cell_w - 2 * image_pad
        image_h = cell_h - caption_h - 2 * image_pad

        for start in range(0, len(remaining_photo_files), 4):
            chunk = remaining_photo_files[start:start + 4]
            page_number = 2 + start // 4
            pdf.setFillColor(navy)
            pdf.rect(0, page_h - 82, page_w, 82, fill=1, stroke=0)
            pdf.setFillColor(cyan)
            pdf.rect(0, page_h - 86, page_w, 4, fill=1, stroke=0)
            pdf.setFillColor(white)
            pdf.setFont(pdf_font_bold, 15)
            pdf.drawString(margin, page_h - 35, photo_title[:75], shaping=True)
            pdf.setFillColor(colors.HexColor("#C9D9EA"))
            pdf.setFont(pdf_font_regular, 8)
            pdf.drawString(margin, page_h - 55, str(program.get("name") or t["title"])[:100], shaping=True)
            pdf.drawRightString(page_w - margin, page_h - 55, f"{len(photo_files)} PHOTOS", shaping=True)

            for local_index, (filename, path) in enumerate(chunk):
                col = local_index % 2
                row = local_index // 2
                x = margin + col * (cell_w + grid_gap_x)
                cell_top = grid_top - row * (cell_h + grid_gap_y)
                cell_bottom = cell_top - cell_h
                pdf.setFillColor(white)
                pdf.roundRect(x, cell_bottom, cell_w, cell_h, 9, fill=1, stroke=0)
                pdf.setStrokeColor(border)
                pdf.setLineWidth(0.8)
                pdf.roundRect(x, cell_bottom, cell_w, cell_h, 9, fill=0, stroke=1)

                try:
                    reader = ImageReader(BytesIO(image_bytes))
                    iw, ih = reader.getSize()
                    if iw > 0 and ih > 0:
                        scale = min(image_w / iw, image_h / ih)
                        draw_w, draw_h = iw * scale, ih * scale
                        img_x = x + (cell_w - draw_w) / 2
                        img_y = cell_bottom + caption_h + image_pad + (image_h - draw_h) / 2
                        pdf.drawImage(reader, img_x, img_y, width=draw_w, height=draw_h, preserveAspectRatio=True, mask="auto")
                except Exception:
                    app.logger.exception("Could not embed photograph %s in PDF", filename)
                    pdf.setFillColor(muted)
                    pdf.setFont(pdf_font_regular, 9)
                    pdf.drawCentredString(x + cell_w / 2, cell_bottom + cell_h / 2, "Photograph unavailable", shaping=True)

                photo_number = first_page_photo_count + start + local_index + 1
                pdf.setFillColor(navy2)
                pdf.setFont(pdf_font_bold, 8)
                caption = f"PHOTO {photo_number:02d}"
                pdf.drawString(x + image_pad, cell_bottom + 9, caption, shaping=True)
                pdf.setFillColor(muted)
                pdf.setFont(pdf_font_regular, 6.5)
                display_name = filename if len(filename) <= 34 else filename[:31] + "..."
                pdf.drawRightString(x + cell_w - image_pad, cell_bottom + 9, display_name, shaping=True)

            pdf.setStrokeColor(border)
            pdf.line(margin, margin + 14, page_w - margin, margin + 14)
            pdf.setFillColor(muted)
            pdf.setFont(pdf_font_regular, 7)
            pdf.drawString(margin, margin, f"{t['report_generated']}: {generated}", shaping=True)
            pdf.drawRightString(page_w - margin, margin, f"PAGE {page_number}  •  PHOTOGRAPHS", shaping=True)
            pdf.showPage()

    pdf.save()
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True,
                     download_name=f"program_report_{program_id}.pdf")

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
