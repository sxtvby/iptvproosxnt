from flask import Flask, render_template, request, jsonify, redirect, session, send_file
import requests, time
from datetime import datetime
from db import get_db, init_db
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecret"

init_db()

# ===== CREAR ADMIN =====
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

# ===== VERIFICACIÓN REAL =====
def verificar(url):
    try:
        if "username=" in url and "password=" in url:

            base = url.split("/get.php")[0]
            user = url.split("username=")[1].split("&")[0]
            password = url.split("password=")[1].split("&")[0]

            api = f"{base}/player_api.php?username={user}&password={password}"

            r = requests.get(api, timeout=8)

            if r.status_code != 200:
                return None

            data = r.json()
            info = data.get("user_info", {})
            server = data.get("server_info", {})

            if info.get("auth") != 1:
                return None

            # ===== VALIDAR CANALES =====
            try:
                m3u = requests.get(url, timeout=8).text
                canales = m3u.count("#EXTINF")
                if canales < 5:
                    return None
            except:
                return None

            return {
                "user": user,
                "pass": password,
                "exp": format_fecha(info.get("exp_date")),
                "created": format_fecha(info.get("created_at")),
                "active": info.get("active_cons", 0),
                "max": info.get("max_connections", 0),
                "timezone": server.get("timezone", "N/A"),
                "server": base,
                "m3u": url
            }

        return None

    except:
        return None

# ===== HOME =====
@app.route("/")
def home():
    if not auth():
        return redirect("/login")

    return render_template("index.html")

# ===== SCAN =====
@app.route("/scan", methods=["POST"])
def scan():
    if not auth():
        return jsonify({"error":"login"})

    urls = request.json["urls"].split("\n")

    resultados = []

    for url in urls:
        url = url.strip()
        if not url:
            continue

        data = verificar(url)

        if data:
            resultados.append(data)

        time.sleep(1.5)  # 🔥 MODO HUMANO

    return jsonify(resultados)

# ===== EXPORT =====
@app.route("/export", methods=["POST"])
def export():
    data = request.json

    with open("hits.txt","w",encoding="utf-8") as f:
        for c in data:
            f.write(f"""╭───✦ HIT HUNTER
├● 👑 ᴜꜱᴇʀ : {c['user']}
├● 🔐 ᴩᴀꜱꜱ : {c['pass']}
├● ✅ ꜱᴛᴀᴛᴜꜱ : Active
├● 📶 ᴀᴄᴛɪᴠᴇ : {c['active']}
├● 📡 ᴍᴀx : {c['max']}
├● ⏰ ᴄʀᴇᴀᴛᴇᴅ : {c['created']}
├● 📅 ᴇxᴘɪʀᴀᴛɪᴏɴ : {c['exp']}
├● 🌐 ꜱᴇʀᴠᴇʀ : {c['server']}
├● 🕰️ ᴛɪᴍᴇᴢᴏɴᴇ : {c['timezone']}
├● ⚡ ꜱᴄᴀɴᴛʏᴩᴇ : panel
├● 👤 нιт вʏ : PANEL PRO
╰───✦ 🚀

🌐 ᴍ3ᴜ : {c['m3u']}


""")

    return send_file("hits.txt", as_attachment=True)

if __name__ == "__main__":
    app.run()
 
