# Tutorstvo.py
from flask import Flask, request, redirect, url_for, render_template_string, flash, session, send_file
import sqlite3, os, io, csv
from datetime import datetime

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

# ---------- HTML (inline) ----------
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

LOGIN_HTML = """
<!doctype html>
<html lang="sl">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Admin prijava</title>
  <style>
    body{font-family:system-ui,sans-serif;background:#fafafa;margin:0;padding:20px;color:#222}
    .wrap{max-width:420px;margin:10vh auto;background:#fff;padding:24px;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,.1)}
    .msg{padding:8px;border-radius:6px;margin-bottom:8px;background:#fdecea;border:1px solid #f5c2c0}
    input,button{width:100%;padding:10px;margin-top:8px;border-radius:6px;border:1px solid #ccc}
    button{background:#0077cc;color:#fff;border:none;cursor:pointer}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Admin</h1>
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}{% for cat, m in messages %}<div class="msg">{{ m }}</div>{% endfor %}{% endif %}
    {% endwith %}
    <form method="post">
      <input type="password" name="password" placeholder="Geslo" required>
      <button type="submit">Prijava</button>
    </form>
  </div>
</body>
</html>
"""

ADMIN_HTML = """
<!doctype html>
<html lang="sl">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Pregled prijav</title>
  <style>
    body{font-family:system-ui,sans-serif;background:#fafafa;margin:0;padding:20px;color:#222}
    .wrap{max-width:1000px;margin:0 auto;background:#fff;padding:24px;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,.1)}
    table{width:100%;border-collapse:collapse;margin-top:12px}
    th,td{border:1px solid #ddd;padding:8px;text-align:left;vertical-align:top}
    th{background:#f0f0f0}
    .actions{display:flex;gap:8px;margin-top:10px}
    a.btn,form button{display:inline-block;padding:8px 12px;background:#0077cc;color:#fff;text-decoration:none;border-radius:6px;border:none;cursor:pointer}
    form{display:inline}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Pregled prijav</h1>
    <div class="actions">
      <a class="btn" href="{{ url_for('export_csv') }}">Izvozi CSV (Excel)</a>
      <form method="post" action="{{ url_for('admin_logout') }}"><button>Odjava</button></form>
    </div>
    <table>
      <thead>
        <tr><th>Datum</th><th>Ime</th><th>Priimek</th><th>E-pošta</th><th>Razred</th><th>Oddelek</th><th>Predmeti (učitelj)</th></tr>
      </thead>
      <tbody>
        {% for r in prijave %}
        <tr>
          <td>{{ r[0] }}</td>
          <td>{{ r[1] }}</td>
          <td>{{ r[2] }}</td>
          <td>{{ r[3] }}</td>
          <td>{{ r[4] }}</td>
          <td>{{ r[5] }}</td>
          <td>{{ r[6] }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
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

    # izbrani predmeti + učitelji
    pari = []
    for code, label in PREDMETI:
        if f.get(f"chk_{code}") == "on":
            teach = f.get(f"teacher_{code}","").strip()
            if not teach:
                flash(f"Učitelj je obvezen pri predmetu: {label}", "error")
                return redirect(url_for("index"))
            pari.append(f"{label} ({teach})")

    predmeti_str = "; ".join(pari) if pari else "—"
    add_prijava(ime, priimek, email, razred, oddelek, predmeti_str)
    flash("Prijava uspešno oddana. Hvala!", "ok")
    return redirect(url_for("index"))

# --- ADMIN auth (preprosto) ---
def admin_ok():
    return session.get("admin_ok") is True

@app.get("/admin")
def admin_login():
    if admin_ok():
        return redirect(url_for("admin_panel"))
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
    return render_template_string(ADMIN_HTML, prijave=prijave)

@app.post("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))

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
    return send_file(
        io.BytesIO(data),
        mimetype="text/csv",
        as_attachment=True,
        download_name="prijave_tutorstvo.csv"
    )

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
