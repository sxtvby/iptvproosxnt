from flask import Flask, render_template, request, jsonify, redirect, session, send_file
import requests, time, random
from datetime import datetime
from db import get_db, init_db
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecret"

init_db()

# ===== ADMIN =====
db = get_db()
try:
    db.execute("INSERT INTO users (username,password) VALUES (?,?)",
               ("admin", generate_password_hash("admin123")))
    db.commit()
except:
    pass

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

# ===== FORMATO FECHA =====
def format_fecha(ts):
    try:
        return datetime.fromtimestamp(int(ts)).strftime('%d/%m/%Y')
    except:
        return "N/A"

# ===== TEST STREAM REAL =====
def probar_stream(base, user, password):
    try:
        api = f"{base}/player_api.php?username={user}&password={password}&action=get_live_streams"
        r = requests.get(api, timeout=6)
        data = r.json()

        if not data:
            return False

        canal = random.choice(data)
        stream_id = canal.get("stream_id")

        if not stream_id:
            return False

        stream_url = f"{base}/live/{user}/{password}/{stream_id}.ts"

        r = requests.get(stream_url, timeout=6, stream=True)

        return r.status_code == 200

    except:
        return False

# ===== VERIFICACIÓN PRO REAL =====
def verificar(url):
    try:
        if "get.php" not in url:
            return "❌ ERROR - URL inválida"

        base = url.split("/get.php")[0]
        user = url.split("username=")[1].split("&")[0]
        password = url.split("password=")[1].split("&")[0]

        api = f"{base}/player_api.php?username={user}&password={password}"

        start = time.time()
        r = requests.get(api, timeout=8)
        latency = int((time.time() - start) * 1000)

        data = r.json()
        info = data.get("user_info", {})
        server = data.get("server_info", {})

        if info.get("auth") != 1:
            return "❌ ERROR - Cuenta inválida"

        # 🔥 FILTRO REAL
        stream_ok = probar_stream(base, user, password)

        if not stream_ok:
            return f"❌ ERROR STREAM (no cargan canales)\n{url}"

        resultado = f"""╭───✦ HIT HUNTER
├● 👑 ᴜꜱᴇʀ : {user}
├● 🔐 ᴩᴀꜱꜱ : {password}
├● ✅ ꜱᴛᴀᴛᴜꜱ : Active
├● 📶 ᴀᴄᴛɪᴠᴇ : {info.get('active_cons', 'N/A')}
├● 📡 ᴍᴀx : {info.get('max_connections', 'N/A')}
├● ⏰ ᴄʀᴇᴀᴛᴇᴅ : {format_fecha(info.get('created_at'))}
├● 📅 ᴇxᴘɪʀᴀᴛɪᴏɴ : {format_fecha(info.get('exp_date'))}
├● 🌐 ꜱᴇʀᴠᴇʀ : {base}
├● 🕰️ ᴛɪᴍᴇᴢᴏɴᴇ : {server.get('timezone', 'N/A')}
├● ⚡ ꜱᴄᴀɴᴛʏᴩᴇ : panel
├● ⚡ ʟᴀᴛᴇɴᴄʏ : {latency} ms
├● 👤 нιт вʏ : PANEL PRO
╰───✦ 🚀

🌐 ᴍ3ᴜ : {url}
"""
        return resultado

    except:
        return "❌ ERROR GENERAL"

# ===== HOME =====
@app.route("/")
def home():
    if not auth():
        return redirect("/login")

    db = get_db()
    listas = db.execute("SELECT * FROM listas").fetchall()

    return render_template("index.html", listas=listas)

# ===== AÑADIR + LIMPIAR =====
@app.route("/add", methods=["POST"])
def add():
    if not auth():
        return jsonify({"error":"login"})

    db = get_db()
    db.execute("DELETE FROM listas")

    urls = request.json["urls"].split("\n")

    for url in urls:
        url = url.strip()
        if url:
            resultado = verificar(url)
            db.execute("INSERT INTO listas (url,resultado) VALUES (?,?)",(url,resultado))

    db.commit()
    return jsonify({"ok":True})

# ===== EXPORT =====
@app.route("/export")
def export():
    db = get_db()
    listas = db.execute("SELECT resultado FROM listas").fetchall()

    with open("resultados.txt","w",encoding="utf-8") as f:
        for l in listas:
            f.write(l[0] + "\n\n")

    return send_file("resultados.txt", as_attachment=True)

# ===== RUN =====
if __name__ == "__main__":
    app.run()
