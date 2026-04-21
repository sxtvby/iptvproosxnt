from flask import Flask, render_template, request, jsonify
import requests, time
from db import get_db, init_db

app = Flask(__name__)

init_db()

# ===== FORMATO =====
def format_output(c):
    return f"""╭───✦ HIT HUNTER
├● 👑 ᴜꜱᴇʀ : {c['user']}
├● 🔐 ᴩᴀꜱꜱ : {c['pass']}
├● ✅ ꜱᴛᴀᴛᴜꜱ : Active
├● 📶 ᴀᴄᴛɪᴠᴇ : {c['active']}
├● 📡 ᴍᴀx : {c['max']}
├● ⏰ ᴄʀᴇᴀᴛᴇᴅ : {c['created']}
├● 📅 ᴇxᴘɪʀᴀᴛɪᴏɴ : {c['exp']}
├● 🌐 ꜱᴇʀᴠᴇʀ : {c['server']}
├● 🌍 ᴘᴀɪꜱ : {c['pais']}
├● 📡 ɪꜱᴘ : {c['isp']}
├● ⚡ ʟᴀᴛᴇɴᴄʏ : {c['latency']} ms
├● 🕰️ ᴛɪᴍᴇᴢᴏɴᴇ : {c['timezone']}
├● 📺 ᴄᴀɴᴀʟᴇꜱ : {c['canales']}
├● 👤 нιт вʏ : PANEL PRO
╰───✦ 🚀

🌐 ᴍ3ᴜ : {c['url']}
"""

# ===== VERIFICACIÓN REAL =====
def verificar(url):
    try:
        if "username=" not in url:
            return None

        base = url.split("/get.php")[0]
        user = url.split("username=")[1].split("&")[0]
        password = url.split("password=")[1].split("&")[0]

        api = f"{base}/player_api.php?username={user}&password={password}"

        t1 = time.time()
        r = requests.get(api, timeout=6)

        if r.status_code != 200:
            return None

        data = r.json()
        latency = int((time.time() - t1)*1000)

        info = data.get("user_info", {})
        server = data.get("server_info", {})

        if info.get("auth") != 1:
            return None

        canales = 0
        try:
            m3u = requests.get(url, timeout=6).text
            canales = m3u.count("#EXTINF")
        except:
            pass

        return {
            "user": user,
            "pass": password,
            "active": info.get("active_cons", 0),
            "max": info.get("max_connections", 0),
            "created": info.get("created_at","N/A"),
            "exp": info.get("exp_date","N/A"),
            "server": base,
            "timezone": server.get("timezone","N/A"),
            "pais": server.get("country","N/A"),
            "isp": server.get("url","N/A"),
            "latency": latency,
            "canales": canales,
            "url": url
        }

    except:
        return None

# ===== ADD =====
@app.route("/add", methods=["POST"])
def add():
    urls = request.json["urls"].split("\n")
    db = get_db()

    for url in urls:
        url = url.strip()
        if url:
            try:
                db.execute("INSERT INTO listas (url,estado) VALUES (?,?)",(url,"NEW"))
            except:
                pass

    db.commit()
    return jsonify({"ok":True})

# ===== SCAN CONTROLADO =====
@app.route("/scan")
def scan():
    db = get_db()
    listas = db.execute("SELECT * FROM listas WHERE estado='NEW' OR estado='RUN'").fetchall()

    for l in listas:
        db.execute("UPDATE listas SET estado='RUN' WHERE id=?", (l[0],))
        db.commit()

        result = verificar(l[1])

        if result:
            texto = format_output(result)
            db.execute("UPDATE listas SET estado='OK', resultado=? WHERE id=?",
                       (texto, l[0]))
        else:
            db.execute("UPDATE listas SET estado='BAD', resultado='❌ INVALID' WHERE id=?",
                       (l[0],))

        db.commit()
        time.sleep(1)

    return jsonify({"ok":True})

# ===== GET RESULTADOS =====
@app.route("/results")
def results():
    db = get_db()
    listas = db.execute("SELECT * FROM listas").fetchall()

    data = []
    for l in listas:
        data.append({
            "url": l[1],
            "estado": l[2],
            "resultado": l[3]
        })

    return jsonify(data)

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run()
