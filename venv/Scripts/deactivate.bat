from flask import Flask, request, redirect, url_for, render_template_string, flash, session, send_file, abort
import csv, os
from datetime import datetime
from io import StringIO

app = Flask(__name__)
app.secret_key = "zelo_tajno_geslo"   # spremeni

ADMIN_PASS = "tutor2025"              # geslo za /admin
CSV_PATH = "prijave.csv"              # kam shranjujemo

# (koda, naziv)
PREDMETI = [
    ("mat", "Matematika"),
    ("fiz", "Fizika"),
    ("ang", "Angleščina"),
    ("inf", "Informatika"),
    ("kem", "Kemija"),
    ("nem", "Nemščina"),
    ("slo", "Slovenščina"),
    ("bio", "Biologija"),
    ("zgod","Zgodovina"),
    ("geo", "Geografija"),
    ("spa", "Španščina"),
    ("ita", "Italijanščina"),
    ("fra", "Francoščina"),
]

# ---------- POMOČNE ----------
def append_rows(rows):
    """rows = seznam vrstic (seznamov) za zapis v CSV"""
    new_file = not os.path.isfile(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["Datum","Ime","Priimek","E-pošta","Razred","Oddelek","Predmet","Učitelj"])
        w.writerows(rows)

def read_all():
    if not os.path.isfile(CSV_PATH):
        return []
    with open(CSV_PATH, "r", newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r, None)  # preskoči glavo
        return list(r)

def admin_ok():
    return session.get("admin") is True

# ---------- UI TEMPLATES ----------
FORM_HTML = """
<!doctype html>
<html lang="sl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Prijava na tutorstvo</title>
<style>
  body{font-family:system-ui,sans-serif;background:#f5f5f5;margin:0;padding:20px;color:#222}
  .wrap{max-width:760px;margin:0 auto;background:#fff;padding:24px;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,.1)}
  h1{margin:0 0 10px;text-align:center}
  label{display:block;margin-top:12px;font-weight:600}
  input,select{width:100%;padding:8px;margin-top:4px;border-radius:6px;border:1px solid #ccc}
  fieldset{border:1px solid #ddd;border-radius:8px;margin-top:16px;padding:12px}
  legend{font-weight:700}
  .subject{display:grid;grid-template-columns:24px 1fr;column-gap:8px;align-items:center;margin:6px 0}
  .subject input[type=checkbox]{width:18px;height:18px;margin:0;align-self:center}
  .teacher{margin-left:calc(24px + 8px);display:none}
  .msg{padding:8px;border-radius:6px;margin-bottom:8px}
  .ok{background:#e8f6ec;border:1px solid #bfe7cc}
  .error{background:#fdecea;border:1px solid #f5c2c0}
  button{margin-top:18px;padding:10px 16px;border:none;background:#0077cc;color:#fff;border-radius:6px;cursor:pointer}
  button:hover{background:#005fa3}
  .hint{font-size:12px;color:#666;margin-top:8px}
</style>
</head><body>
<div class="wrap">
  <h1>Prijava na tutorstvo</h1>

  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, m in messages %}
      <div class="msg {{cat}}">{{ m }}</div>
    {% endfor %}
  {% endwith %}

  <form method="post" action="{{ url_for('prijava') }}">
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
      <legend>Predmeti (ob izbiri je učitelj obvezen)</legend>
      {% for code, label in predmeti %}
        <div class="subject">
          <input type="checkbox" id="chk_{{code}}" name="chk_{{code}}">
          <label for="chk_{{code}}">{{label}}</label>
        </div>
        <div class="teacher" id="tab_{{code}}">
          <label>Učitelj {{label}} <input name="teacher_{{code}}"></label>
        </div>
      {% endfor %}
    </fieldset>

    <button type="submit">Oddaj prijavo</button>
    <p class="hint">Admin: <a href="{{ url_for('admin') }}">/admin</a></p>
  </form>
</div>

<script>
  // pokaži/skrij polja za učitelje in nastavi required le, ko je predmet izbran
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
</body></html>
"""

ADMIN_LOGIN_HTML = """
<!doctype html>
<html lang="sl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Admin prijava</title>
<style>
  body{font-family:system-ui,sans-serif;background:#fafafa;margin:0;padding:20px}
  .wrap{max-width:420px;margin:10vh auto;background:#fff;padding:24px;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,.1)}
  .msg{padding:8px;border-radius:6px;margin-bottom:8px;background:#fdecea;border:1px solid #f5c2c0}
  input,button{width:100%;padding:10px;margin-top:8px;border-radius:6px;border:1px solid #ccc}
  button{background:#0077cc;color:#fff;border:none;cursor:pointer}
</style>
</head><body>
<div class="wrap">
  <h1>Admin</h1>
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, m in messages %}<div class="msg">{{ m }}</div>{% endfor %}
  {% endwith %}
  <form method="post">
    <input type="password" name="password" placeholder="Geslo" required>
    <button type="submit">Prijava</button>
  </form>
</div>
</body></html>
"""

ADMIN_TABLE_HTML = """
<!doctype html>
<html lang="sl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pregled prijav</title>
<style>
  body{font-family:system-ui,sans-serif;background:#fafafa;margin:0;padding:20px}
  .wrap{max-width:1100px;margin:0 auto;background:#fff;padding:20px;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,.1)}
  .actions{display:flex;gap:8px;margin-bottom:12px}
  a.btn,form button{display:inline-block;padding:8px 12px;background:#0077cc;color:#fff;text-decoration:none;border-radius:6px;border:none;cursor:pointer}
  table{width:100%;border-collapse:collapse}
  th,td{border:1px solid #ddd;padding:8px;text-align:left;vertical-align:top}
  th{background:#f0f0f0}
</style>
</head><body>
<div class="wrap">
  <h1>Pregled prijav</h1>
  <div class="actions">
    <a class="btn" href="{{ url_for('izvoz_csv') }}">Izvozi CSV (Excel)</a>
    <form method="post" action="{{ url_for('admin_logout') }}"><button>Odjava</button></form>
  </div>
  <table>
    <thead>
      <tr>
        <th>Datum</th><th>Ime</th><th>Priimek</th><th>E-pošta</th>
        <th>Razred</th><th>Oddelek</th><th>Predmet</th><th>Učitelj</th>
      </tr>
    </thead>
    <tbody>
      {% for r in rows %}
        <tr>
        {% for c in r %}<td>{{ c }}</td>{% endfor %}
        </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
</body></html>
"""

# ---------- RUTE ----------
@app.route("/", methods=["GET", "POST"])
def prijava():
    if request.method == "POST":
        f = request.form
        ime = f.get("ime","").strip()
        priimek = f.get("priimek","").strip()
        email = f.get("email","").strip()
        razred = f.get("razred","").strip()
        oddelek = f.get("oddelek","").strip()

        if not all([ime, priimek, email, razred, oddelek]):
            flash("Izpolnite vsa obvezna polja (ime, priimek, e-pošta, razred, oddelek).", "error")
            return redirect(url_for("prijava"))

        # zberi izbrane predmete + obvezne učitelje
        zapis_vrstice = []
        for code, label in PREDMETI:
            if f.get(f"chk_{code}") == "on":
                teach = f.get(f"teacher_{code}","").strip()
                if not teach:
                    flash(f"Učitelj je obvezen za predmet: {label}", "error")
                    return redirect(url_for("prijava"))
                zapis_vrstice.append([
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    ime, priimek, email, razred, oddelek, label, teach
                ])

        if not zapis_vrstice:
            flash("Izberi vsaj en predmet.", "error")
            return redirect(url_for("prijava"))

        append_rows(zapis_vrstice)
        flash("Prijava uspešno oddana. Hvala!", "ok")
        return redirect(url_for("prijava"))

    return render_template_string(FORM_HTML, predmeti=PREDMETI)

# --- ADMIN ---
@app.route("/admin", methods=["GET","POST"])
def admin():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASS:
            session["admin"] = True
            return redirect(url_for("pregled"))
        flash("Napačno geslo.", "error")
    return render_template_string(ADMIN_LOGIN_HTML)

@app.route("/pregled")
def pregled():
    if not admin_ok():
        return redirect(url_for("admin"))
    rows = read_all()
    return render_template_string(ADMIN_TABLE_HTML, rows=rows)

@app.post("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin"))

@app.route("/izvoz")
def izvoz_csv():
    if not admin_ok():
        return redirect(url_for("admin"))
    if not os.path.isfile(CSV_PATH):
        abort(404)
    # pošlji kot prenos
    return send_file(CSV_PATH, mimetype="text/csv", as_attachment=True, download_name="prijave_tutorstvo.csv")

# favicon (da ne moti 404 v logih)
@app.route("/favicon.ico")
def favicon():
    return ("", 204)

if __name__ == "__main__":
    app.run(debug=True)
