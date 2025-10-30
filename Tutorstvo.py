# Tutorstvo.py
from flask import Flask, request, redirect, url_for, render_template_string, flash, session, send_file
import sqlite3, os, io, csv
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

# === Google Sheets povezava ===
SHEET_ID = "1l8fwVCei-w-QfUzHUHTpss4d6Texgz4B7NA7LLE-tiw"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_JSON_PATH = "/etc/secrets/service_account.json"
if not os.path.isfile(SERVICE_JSON_PATH):
    SERVICE_JSON_PATH = "service_account.json"
CREDS = Credentials.from_service_account_file(SERVICE_JSON_PATH, scopes=SCOPES)
_gc = gspread.authorize(CREDS)
_sheet = _gc.open_by_key(SHEET_ID).sheet1

app = Flask(__name__)
app.secret_key = "change_me_secret"  # zamenjaj po želji

DB_PATH = "tutorstvo.db"

# (code, label)
PREDMETI = [
    ("mat", "Matematika"), ("fiz", "Fizika"), ("ang", "Angleščina"),
    ("inf", "Informatika"), ("kem", "Kemija"), ("nem", "Nemščina"),
    ("slo", "Slovenščina"), ("bio", "Biologija"), ("zgod", "Zgodovina"),
    ("geo", "Geografija"), ("spa", "Španščina"), ("ita", "Italijanščina"),
    ("fra", "Francoščina"),
]

ADMIN_PASS = "tutor2025"  # spremeni po želji


# ---------- BAZA ----------
def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS prijave (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datum TEXT NOT NULL,
            ime TEXT NOT NULL,
            priimek TEXT NOT NULL,
            email TEXT NOT NULL,
            razred TEXT NOT NULL,
            oddelek TEXT NOT NULL,
            predmeti TEXT NOT NULL
        )
    """)
    con.commit()
    con.close()


def add_prijava(ime, priimek, email, razred, oddelek, predmeti_str):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO prijave (datum, ime, priimek, email, razred, oddelek, predmeti) VALUES (?,?,?,?,?,?,?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M"), ime, priimek, email, razred, oddelek, predmeti_str)
    )
    con.commit()
    con.close()


def get_all_prijave():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT datum, ime, priimek, email, razred, oddelek, predmeti FROM prijave ORDER BY id DESC")
    rows = cur.fetchall()
    con.close()
    return rows


# ---------- HTML ----------
FORM_HTML = """
<!doctype html>
<html lang="sl">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Prijava na tutorstvo</title>
  <style>
    body{font-family:system-ui,sans-serif;background:#f5f5f5;margin:0;padding:20px;color:#222}
    .wrap{max-width:760px;margin:0 auto;background:#fff;padding:24px;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,.1)}
    h1{text-align:center;margin:0 0 10px}
    label{display:block;margin-top:12px;font-weight:600}
    input,select{width:100%;padding:8px;margin-top:4px;border-radius:6px;border:1px solid #ccc}
    fieldset{border:1px solid #ddd;border-radius:8px;margin-top:16px;padding:12px}
    legend{font-weight:bold}
    .subject{display:grid;grid-template-columns:24px 1fr;column-gap:8px;align-items:center;margin:6px 0}
    .subject input[type="checkbox"]{width:18px;height:18px;margin:0;justify-self:start;align-self:center}
    .teacher-tab{margin-left:calc(24px + 8px);margin-top:4px;display:none}
    .msg{padding:8px;border-radius:6px;margin-bottom:8px}
    .ok{background:#e8f6ec;border:1px solid #bfe7cc}
    .error{background:#fdecea;border:1px solid #f5c2c0}
    button{margin-top:20px;padding:10px 16px;border:none;background:#0077cc;color:#fff;border-radius:6px;cursor:pointer}
    button:hover{background:#005fa3}
    .hint{font-size:12px;color:#666}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Prijava na tutorstvo</h1>

    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for cat, m in messages %}
          <div class="msg {{cat}}">{{ m }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <form method="post" action="{{ url_for('oddaj') }}">
      <label>Ime <input name="ime" required></label>
      <label>Priimek <input name="priimek" required></label>
      <label>E-pošta <input type="email" name="email" required></label>
      <label>Razred
        <select name="razred" required>
          <option value="">— izberi —</option>
          <option>1. letnik</option><option>2. letnik</option>
          <option>3. letnik</option><option>4. letnik</option>
        </select>
      </label>
      <label>Oddelek
        <select name="oddelek" required>
          <option value="">— izberi —</option>
          <option>a</option><option>b</option><option>c</option>
          <option>d</option><option>e</option><option>f</option>
        </select>
      </label>

      <fieldset>
        <legend>Predmeti za inštrukcije</legend>
        {% for code, label in predmeti %}
          <div class="subject">
            <input type="checkbox" id="chk_{{code}}" name="chk_{{code}}">
            <label for="chk_{{code}}">{{label}}</label>
          </div>
          <div class="teacher-tab" id="tab_{{code}}">
            <label>Učitelj {{label}} <input name="teacher_{{code}}"></label>
          </div>
        {% endfor %}
      </fieldset>

      <button type="submit">Oddaj prijavo</button>
      <p class="hint">Admin pregled: <a href="{{ url_for('admin_login') }}">/admin</a></p>
    </form>
  </div>

  <script>
    // pokaži/skrij polje za učitelja in ga naredi obveznega, ko je predmet izbran
    document.querySelectorAll('input[type="checkbox"][id^="chk_"]').forEach(cb=>{
      const code = cb.id.replace('chk_','');
      const tab = document.getElementById('tab_'+code);
      const input = tab.querySelector('input');
      const sync = ()=>{
        const show = cb.checked;
        tab.style.display = show ? 'block' : 'none';
        if(show){ input.setAttribute('required','required'); }
        else { input.removeAttribute('required'); input.value=''; }
      };
      cb.addEventListener('change', sync);
      sync();
    });
  </script>
</body>
</html>
"""

# ---------- RUTE ----------
@app.get("/")
def index():
    return render_template_string(FORM_HTML, predmeti=PREDMETI)

@app.post("/oddaj")
def oddaj():
    f = request.form
    ime = f.get("ime","").strip()
    priimek = f.get("priimek","").strip()
    email = f.get("email","").strip()
    razred = f.get("razred","").strip()
    oddelek = f.get("oddelek","").strip()

    if not all([ime, priimek, email, razred, oddelek]):
        flash("Izpolnite vsa obvezna polja (ime, priimek, e-pošta, razred, oddelek).", "error")
        return redirect(url_for("index"))

    pari = []
    for code, label in PREDMETI:
        if f.get(f"chk_{code}") == "on":
            teach = f.get(f"teacher_{code}","").strip()
            if not teach:
                flash(f"Učitelj je obvezen pri predmetu: {label}", "error")
                return redirect(url_for("index"))
            pari.append(f"{label} ({teach})")

    predmeti_str = "; ".join(pari) if pari else "—"

    # shranimo v SQLite
    add_prijava(ime, priimek, email, razred, oddelek, predmeti_str)

    # --- Zapiši tudi v Google Sheets ---
    try:
        worksheet = _sheet
        worksheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            ime, priimek, email, razred, oddelek, predmeti_str
        ])
    except Exception as e:
        print("Napaka pri zapisu v Google Sheets:", e)

    flash("Prijava uspešno oddana. Hvala!", "ok")
    return redirect(url_for("index"))

# --- ADMIN ---
def admin_ok():
    return session.get("admin_ok") is True

@app.get("/admin")
def admin_login():
    if admin_ok():
        return redirect(url_for("admin_panel"))
    LOGIN_HTML = """
    <h2>Admin prijava</h2>
    <form method='post'><input type='password' name='password'><button>Prijava</button></form>
    """
    return render_template_string(LOGIN_HTML)

@app.post("/admin")
def admin_do_login():
    if request.form.get("password") == ADMIN_PASS:
        session["admin_ok"] = True
        return redirect(url_for("admin_panel"))
    flash("Napačno geslo.", "error")
    return redirect(url_for("admin_login"))

@app.get("/admin/panel")
def admin_panel():
    if not admin_ok():
        return redirect(url_for("admin_login"))
    prijave = get_all_prijave()
    ADMIN_HTML = "<h2>Prijave</h2><table border='1'><tr><th>Datum</th><th>Ime</th><th>Priimek</th><th>Email</th><th>Razred</th><th>Oddelek</th><th>Predmeti</th></tr>"
    for r in prijave:
        ADMIN_HTML += f"<tr>{''.join(f'<td>{c}</td>' for c in r)}</tr>"
    ADMIN_HTML += "</table>"
    ADMIN_HTML += "<p><a href='/export'>Izvozi CSV</a></p>"
    return ADMIN_HTML

@app.get("/export")
def export_csv():
    if not admin_ok():
        return redirect(url_for("admin_login"))
    rows = get_all_prijave()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Datum","Ime","Priimek","E-pošta","Razred","Oddelek","Predmeti"])
    for r in rows:
        w.writerow(list(r))
    data = buf.getvalue().encode("utf-8-sig")
    return send_file(io.BytesIO(data), mimetype="text/csv", as_attachment=True, download_name="prijave_tutorstvo.csv")

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
