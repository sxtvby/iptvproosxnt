from flask import Flask, render_template, request, jsonify, redirect, session, send_file
import requests, time, random
from datetime import datetime
from db import get_db, init_db
from werkzeug.security import generate_password_hash, check_password_hash
from threading import Thread

app = Flask(__name__)
app.secret_key = "supersecretkey"

init_db()

# ===== CREAR USUARIO =====
db = get_db()
try:
    db.execute("INSERT INTO users (username,password) VALUES (?,?)",
               ("admin", generate_password_hash("admin123")))
    db.commit()
except:
    pass

# ===== CONFIG ANTI-BAN =====
MIN_DELAY = 2
MAX_DELAY = 5

queue = []
processing = False

# ===== LOGIN =====
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = request.form["user"]
        password = request.form["password"]

        db = get_db()
        u = db.execute("SELECT * FROM users WHERE username=?", (user,)).fetchone()

        if u and check_password_hash(u[2], password):
            session["user"] = user
            return redirect("/")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

def auth():
    return "user" in session

# ===== VERIFICADOR =====
def check_url(url):
    try:
        start = time.time()
        r = requests.get(url, timeout=10)
        t = round(time.time() - start, 2)

        if r.status_code == 200:
            return "ONLINE", t
        return "DOWN", t
    except:
        return "ERROR", 0

# ===== PROCESADOR DE COLA =====
def worker():
    global processing

    while queue:
        item = queue.pop(0)
        url = item["url"]
        id_ = item["id"]

        status, t = check_url(url)

        db = get_db()
        db.execute("""
        UPDATE urls 
        SET status=?, response_time=?, last_check=? 
        WHERE id=?
        """,(status, t, datetime.now().strftime("%H:%M:%S"), id_))
        db.commit()

        delay = random.randint(MIN_DELAY, MAX_DELAY)
        time.sleep(delay)

    processing = False

# ===== HOME =====
@app.route("/")
def home():
    if not auth():
        return redirect("/login")

    db = get_db()
    data = db.execute("SELECT * FROM urls").fetchall()
    return render_template("index.html", data=data)

# ===== ADD =====
@app.route("/add", methods=["POST"])
def add():
    if not auth():
        return jsonify({"error":"login"})

    urls = request.json["urls"].split("\n")
    db = get_db()

    for u in urls:
        u = u.strip()
        if u:
            try:
                db.execute("INSERT INTO urls (url,status) VALUES (?,?)",(u,"NEW"))
            except:
                pass

    db.commit()
    return jsonify({"ok":True})

# ===== SCAN (COLA) =====
@app.route("/scan")
def scan():
    global processing

    if not auth():
        return jsonify({"error":"login"})

    db = get_db()
    urls = db.execute("SELECT * FROM urls").fetchall()

    for u in urls:
        queue.append({"id":u[0], "url":u[1]})

    if not processing:
        processing = True
        Thread(target=worker).start()

    return jsonify({"ok":True})

# ===== EXPORT =====
@app.route("/export")
def export():
    db = get_db()
    urls = db.execute("SELECT * FROM urls WHERE status='ONLINE'").fetchall()

    with open("validas.txt","w") as f:
        for u in urls:
            f.write(f"{u[1]} | {u[2]} | {u[3]}s\n")

    return send_file("validas.txt", as_attachment=True)

# ===== RUN =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
