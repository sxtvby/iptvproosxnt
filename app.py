from flask import Flask, render_template, request, jsonify, send_file
import requests
from datetime import datetime
from db import get_db, init_db
import time

app = Flask(__name__)
init_db()

# ===== LIMPIAR DB AUTOMATICAMENTE =====
def limpiar_db():
    db = get_db()
    db.execute("DELETE FROM listas")
    db.commit()

# ===== FORMATO FECHA =====
def format_fecha(ts):
    try:
        return datetime.fromtimestamp(int(ts)).strftime('%d/%m/%Y')
    except:
        return "N/A"

# ===== VERIFICAR CANAL REAL =====
def check_stream(m3u):
    try:
        r = requests.get(m3u, timeout=8)
        if "#EXTINF" in r.text:
            lines = r.text.split("\n")
            for l in lines:
                if "http" in l:
                    test = requests.get(l.strip(), timeout=5, stream=True)
                    return test.status_code == 200
        return False
    except:
        return False

# ===== VERIFICACION PRINCIPAL =====
def verificar(url):

    try:
        base = url.split("/get.php")[0]
        user = url.split("username=")[1].split("&")[0]
        password = url.split("password=")[1].split("&")[0]

        api = f"{base}/player_api.php?username={user}&password={password}"

        r = requests.get(api, timeout=10)
        data = r.json()

        info = data.get("user_info", {})
        server = data.get("server_info", {})

        if info.get("auth") != 1:
            return "❌ ERROR"

        exp = format_fecha(info.get("exp_date"))
        created = format_fecha(info.get("created_at"))
        active = info.get("active_cons", "0")
        maxc = info.get("max_connections", "0")
        timezone = server.get("timezone", "N/A")

        m3u = url

        # 🔥 CHECK REAL DE CANAL
        canal_ok = check_stream(m3u)

        if not canal_ok:
            return "❌ ERROR (sin señal)"

        resultado = f"""╭───✦ HIT HUNTER
├● 👑 ᴜꜱᴇʀ : {user}
├● 🔐 ᴩᴀꜱꜱ : {password}
├● ✅ ꜱᴛᴀᴛᴜꜱ : Active
├● 📶 ᴀᴄᴛɪᴠᴇ : {active}
├● 📡 ᴍᴀx : {maxc}
├● ⏰ ᴄʀᴇᴀᴛᴇᴅ : {created}
├● 📅 ᴇxᴘɪʀᴀᴛɪᴏɴ : {exp}
├● 🌐 ꜱᴇʀᴠᴇʀ : {base}
├● 🕰️ ᴛɪᴍᴇᴢᴏɴᴇ : {timezone}
├● ⚡ ꜱᴄᴀɴᴛʏᴩᴇ : panel
├● 👤 нιт вʏ : PANEL PRO
╰───✦ 🚀

🌐 ᴍ3ᴜ : {m3u}
"""

        return resultado

    except:
        return "❌ ERROR"

# ===== HOME =====
@app.route("/")
def home():
    db = get_db()
    listas = db.execute("SELECT * FROM listas").fetchall()
    return render_template("index.html", listas=listas)

# ===== AÑADIR + LIMPIAR =====
@app.route("/add", methods=["POST"])
def add():
    limpiar_db()  # 🔥 BORRA ANTES DE NUEVO SCAN

    urls = request.json["urls"].split("\n")
    db = get_db()

    for url in urls:
        url = url.strip()
        if url:
            db.execute("INSERT INTO listas (url,estado) VALUES (?,?)",(url,"NEW"))

    db.commit()
    return jsonify({"ok":True})

# ===== VERIFICAR =====
@app.route("/scan")
def scan():

    db = get_db()
    listas = db.execute("SELECT * FROM listas").fetchall()

    for l in listas:

        res = verificar(l[1])

        estado = "OK" if "HIT HUNTER" in res else "ERROR"

        db.execute("UPDATE listas SET estado=?, resultado=? WHERE id=?",
                   (estado, res, l[0]))

        db.commit()

        time.sleep(1)  # 🔥 anti bloqueo

    return jsonify({"ok":True})

# ===== EXPORTAR =====
@app.route("/export")
def export():
    db = get_db()
    listas = db.execute("SELECT resultado FROM listas WHERE estado='OK'").fetchall()

    with open("hits.txt","w",encoding="utf-8") as f:
        for l in listas:
            f.write(l[0] + "\n\n")

    return send_file("hits.txt", as_attachment=True)

# ===== RUN =====
if __name__ == "__main__":
    app.run()
