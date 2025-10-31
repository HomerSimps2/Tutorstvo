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
app.secret_key = "change_me_secret"

DB_PATH = "tutorstvo.db"

PREDMETI = [
    ("mat", "Matematika"), ("fiz", "Fizika"), ("ang", "Angleščina"),
    ("inf", "Informatika"), ("kem", "Kemija"), ("nem", "Nemščina"),
    ("slo", "Slovenščina"), ("bio", "Biologija"), ("zgod", "Zgodovina"),
    ("geo", "Geografija"), ("spa", "Španščina"), ("ita", "Italijanščina"),
    ("fra", "Francoščina"),
]

ADMIN_PASS = "tutor2025"

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
    cur.execute("SELECT id, datum, ime, priimek, email, razred, oddelek, predmeti FROM prijave ORDER BY id DESC")
    rows = cur.fetchall()
    con.close()
    return rows

def delete_prijava_by_id(pid):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("DELETE FROM prijave WHERE id=?", (pid,))
    con.commit()
    con.close()

# ---------- BRISANJE IZ GOOGLE SHEETS ----------
def delete_from_sheet(email, datum):
    try:
        all_rows = _sheet.get_all_values()
        for i, row in enumerate(all_rows, start=1):
            if len(row) >= 4 and row[0] == datum and row[3] == email:
                _sheet.delete_rows(i)
                print(f"Izbrisana vrstica {i} iz Google Sheets.")
                return True
    except Exception as e:
        print("Napaka pri brisanju iz Google Sheets:", e)
    return False

# ---------- HTML OBRAZEC ----------
FORM_HTML = """ ... (tvoj obrazec ostane enak) ... """

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
        flash("Izpolnite vsa obvezna polja.", "error")
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
    datum = datetime.now().strftime("%Y-%m-%d %H:%M")

    add_prijava(ime, priimek, email, razred, oddelek, predmeti_str)

    try:
        _sheet.append_row([datum, ime, priimek, email, razred, oddelek, predmeti_str])
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
    return render_template_string("""
    <h2>Admin prijava</h2>
    <form method='post'>
      <input type='password' name='password' placeholder='Geslo'>
      <button>Prijava</button>
    </form>
    """)

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
    ADMIN_HTML = """
    <html><head><style>
    body{font-family:sans-serif;background:#f9f9f9;padding:20px;}
    table{border-collapse:collapse;width:100%;background:#fff;}
    th,td{border:1px solid #ddd;padding:8px;text-align:left;}
    th{background:#eee;}
    .btn{background:#0077cc;color:#fff;padding:6px 10px;border-radius:4px;text-decoration:none;}
    .del{background:#cc0000;}
    </style></head><body>
    <h2>Prijave</h2>
    <p>
      <a class='btn' href='/export'>Izvozi CSV</a>
      <a class='btn' href='https://docs.google.com/spreadsheets/d/1l8fwVCei-w-QfUzHUHTpss4d6Texgz4B7NA7LLE-tiw' target='_blank'>Odpri Google preglednico</a>
    </p>
    <table>
    <tr><th>Datum</th><th>Ime</th><th>Priimek</th><th>Email</th><th>Razred</th><th>Oddelek</th><th>Predmeti</th><th>Dejanje</th></tr>
    """
    for r in prijave:
        rid, datum, ime, priimek, email, razred, oddelek, predmeti = r
        ADMIN_HTML += f"<tr><td>{datum}</td><td>{ime}</td><td>{priimek}</td><td>{email}</td><td>{razred}</td><td>{oddelek}</td><td>{predmeti}</td><td><form method='post' action='/admin/delete/{rid}'><input type='hidden' name='datum' value='{datum}'><input type='hidden' name='email' value='{email}'><button class='btn del'>Izbriši</button></form></td></tr>"
    ADMIN_HTML += "</table></body></html>"
    return ADMIN_HTML

@app.post("/admin/delete/<int:pid>")
def admin_delete(pid):
    if not admin_ok():
        return redirect(url_for("admin_login"))

    datum = request.form.get("datum")
    email = request.form.get("email")

    # izbriši iz SQLite
    delete_prijava_by_id(pid)

    # izbriši iz Google Sheets
    delete_from_sheet(email, datum)

    flash("Prijava izbrisana.", "ok")
    return redirect(url_for("admin_panel"))

@app.get("/export")
def export_csv():
    if not admin_ok():
        return redirect(url_for("admin_login"))
    rows = get_all_prijave()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Datum","Ime","Priimek","E-pošta","Razred","Oddelek","Predmeti"])
    for r in rows:
        w.writerow(r[1:])
    data = buf.getvalue().encode("utf-8-sig")
    return send_file(io.BytesIO(data), mimetype="text/csv", as_attachment=True, download_name="prijave_tutorstvo.csv")

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
