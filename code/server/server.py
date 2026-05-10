import socket
import threading
import json
from flask import Flask, render_template_string, jsonify

UDP_IP = "0.0.0.0"
UDP_PORT = 6767
SOUBOR_NA_DATA = "pozar_data_nbiot.txt"

app = Flask(__name__)

# =====================================================================
# =========================== HTML ŠABLONY =============================
# =====================================================================

# ---------------------- HLAVNÍ STRÁNKA (DASHBOARD) -------------------

HTML_MAIN = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <title>NB-IoT Detektor požárů – Dashboard</title>
    <style>
        body { font-family: Arial; margin: 40px; }
        h1, h2 { color: #333; }
        .menu a { margin-right: 20px; font-size: 18px; }
        table { border-collapse: collapse; width: 100%; max-width: 900px; }
        th, td { border: 1px solid #aaa; padding: 6px; font-size: 14px; }
        th { background: #ddd; }
        .alarm { color: #b30000; font-weight: bold; }
        .ok { color: #008000; font-weight: bold; }
        .box { border: 1px solid #aaa; padding: 10px; margin-bottom: 20px; max-width: 600px; }
        .label { font-weight: bold; }
    </style>
</head>
<body>

<div class="menu">
    <a href="/">🏠 Dashboard</a>
    <a href="/history">📄 Historie</a>
</div>

<h1>NB-IoT Detektor lesních požárů – Dashboard</h1>

<div class="box">
    <h2>Stav zařízení</h2>
    <p><span class="label">Device ID:</span> <span id="device_id">-</span></p>
    <p><span class="label">Výrobce:</span> <span id="manufacturer">-</span></p>
    <p><span class="label">FW verze:</span> <span id="fw">-</span></p>
    <p><span class="label">Technologie:</span> <span id="tech">-</span></p>
    <p><span class="label">GPS:</span> <span id="gps">-</span></p>
    <p><span class="label">CellID:</span> <span id="cellid">-</span>,
       <span class="label">TAC:</span> <span id="tac">-</span>,
       <span class="label">Band:</span> <span id="band">-</span>,
       <span class="label">EARFCN:</span> <span id="earfcn">-</span></p>
    <p><span class="label">RSRP:</span> <span id="rsrp">-</span> dBm,
       <span class="label">SINR:</span> <span id="sinr">-</span> dB</p>
</div>

<div class="box">
    <h2>Poslední měření</h2>
    <p><span class="label">Čas:</span> <span id="last_time">-</span></p>
    <p><span class="label">Teplota:</span> <span id="last_temp">-</span> °C</p>
    <p><span class="label">Vlhkost:</span> <span id="last_hum">-</span> %</p>
    <p><span class="label">RSRP:</span> <span id="last_rsrp">-</span> dBm,
       <span class="label">SINR:</span> <span id="last_sinr">-</span> dB</p>
    <p><span class="label">Stav:</span> <span id="alarm_state" class="ok">Neaktivní</span></p>
</div>

<h2>Graf teploty a vlhkosti</h2>
<canvas id="chart" width="900" height="400"></canvas>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<script>
let chart = null;

async function loadStartup() {
    const res = await fetch("/api/startup");
    const data = await res.json();
    if (!data || !data.device_id) return;

    document.getElementById("device_id").textContent = data.device_id || "-";
    document.getElementById("manufacturer").textContent = data.manufacturer || "-";
    document.getElementById("fw").textContent = data.fw || "-";
    document.getElementById("tech").textContent = data.tech || "-";

    const gps = (data.gps_lat !== undefined && data.gps_lon !== undefined)
        ? (data.gps_lat + ", " + data.gps_lon)
        : "-";
    document.getElementById("gps").textContent = gps;

    document.getElementById("cellid").textContent = data.cellid ?? "-";
    document.getElementById("tac").textContent = data.tac ?? "-";
    document.getElementById("band").textContent = data.band ?? "-";
    document.getElementById("earfcn").textContent = data.earfcn ?? "-";
    document.getElementById("rsrp").textContent = data.rsrp ?? "-";
    document.getElementById("sinr").textContent = data.sinr ?? "-";
}

async function loadLatest() {
    const res = await fetch("/api/latest");
    const data = await res.json();
    if (!data || !data.time) return;

    document.getElementById("last_time").textContent = data.time || "-";
    document.getElementById("last_temp").textContent = data.temp ?? "-";
    document.getElementById("last_hum").textContent = data.hum ?? "-";
    document.getElementById("last_rsrp").textContent = data.rsrp ?? "-";
    document.getElementById("last_sinr").textContent = data.sinr ?? "-";

    const alarmEl = document.getElementById("alarm_state");
    if (data.type === "ALARM") {
        alarmEl.textContent = "ALARM";
        alarmEl.className = "alarm";
    } else if (data.type === "FALSE_ALARM") {
        alarmEl.textContent = "Falešný alarm";
        alarmEl.className = "ok";
    } else {
        alarmEl.textContent = "Neaktivní";
        alarmEl.className = "ok";
    }
}

async function updateChart() {
    const res = await fetch("/api/history");
    const data = await res.json();

    const labels = data.map(d => d.time);
    const temps = data.map(d => d.temp);
    const hums = data.map(d => d.hum);

    const ctx = document.getElementById("chart").getContext("2d");

    if (chart !== null) {
        chart.data.labels = labels;
        chart.data.datasets[0].data = temps;
        chart.data.datasets[1].data = hums;
        chart.update();
        return;
    }

    chart = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Teplota (°C)",
                    data: temps,
                    borderColor: "red",
                    backgroundColor: "rgba(255,0,0,0.2)",
                    tension: 0.2
                },
                {
                    label: "Vlhkost (%)",
                    data: hums,
                    borderColor: "blue",
                    backgroundColor: "rgba(0,0,255,0.2)",
                    tension: 0.2
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                x: { title: { display: true, text: "Čas" } },
                y: { title: { display: true, text: "Hodnota" } }
            }
        }
    });
}

function refreshAll() {
    loadStartup();
    loadLatest();
    updateChart();
}

setInterval(refreshAll, 5000);
refreshAll();
</script>

</body>
</html>
"""

# ---------------------- STRÁNKA HISTORIE ------------------------------

HTML_HISTORY = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <title>NB-IoT Detektor – Historie</title>
    <style>
        body { font-family: Arial; margin: 40px; }
        h1 { color: #333; }
        .menu a { margin-right: 20px; font-size: 18px; }
        table { border-collapse: collapse; width: 100%; max-width: 1000px; margin-top: 20px; }
        th, td { border: 1px solid #aaa; padding: 6px; font-size: 14px; }
        th { background: #ddd; }
        .btn-clear { 
            background-color: #ff4d4d; 
            color: white; 
            border: none; 
            padding: 10px 15px; 
            cursor: pointer; 
            border-radius: 4px; 
            font-size: 14px;
        }
        .btn-clear:hover { background-color: #cc0000; }
    </style>
</head>
<body>

<div class="menu">
    <a href="/">🏠 Dashboard</a>
    <a href="/history">📄 Historie</a>
</div>

<h1>Historie měření</h1>

<button class="btn-clear" onclick="clearHistory()">🗑️ Promazat historii</button>

<table id="historyTable">
    <thead>
        <tr>
            <th>Typ</th>
            <th>Čas</th>
            <th>Teplota [°C]</th>
            <th>Vlhkost [%]</th>
            <th>RSRP [dBm]</th>
            <th>SINR [dB]</th>
        </tr>
    </thead>
    <tbody id="historyBody">
    </tbody>
</table>

<script>
async function loadHistory() {
    const res = await fetch("/api/history");
    const data = await res.json();

    const tbody = document.getElementById("historyBody");
    tbody.innerHTML = ""; // Vyčistit tabulku před načtením

    data.forEach(row => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${row.type}</td>
            <td>${row.time ?? "-"}</td>
            <td>${row.temp ?? "-"}</td>
            <td>${row.hum ?? "-"}</td>
            <td>${row.rsrp ?? "-"}</td>
            <td>${row.sinr ?? "-"}</td>
        `;
        tbody.appendChild(tr);
    });
}

async function clearHistory() {
    if (confirm("Opravdu chcete smazat všechna data v historii?")) {
        const res = await fetch("/api/clear", { method: "POST" });
        const result = await res.json();
        if (result.status === "ok") {
            location.reload(); // Znovu načte stránku
        } else {
            alert("Chyba: " + result.message);
        }
    }
}

loadHistory();
</script>

</body>
</html>
"""

# =====================================================================
# ======================== PARSOVÁNÍ ZPRÁV =============================
# =====================================================================

def parse_bulk_message(text: str):
    result = {"type": "BULK", "measurements": []}

    header, data_part = text.split("DATA=", 1)

    # Hlavička
    for p in header.split(";")[1:]:
        if "=" in p:
            key, val = p.split("=", 1)
            key = key.strip().lower()
            val = val.strip()
            try:
                val = float(val) if "." in val else int(val)
            except:
                pass
            result[key] = val

    # Odstranění hranatých závorek
    data_str = data_part.strip()
    if data_str.startswith("["):
        data_str = data_str[1:]
    if data_str.endswith("]"):
        data_str = data_str[:-1]

    # Rozdělení jednotlivých měření
    raw_items = data_str.split("},")

    for item in raw_items:
        item = item.strip()
        if item.startswith("{"):
            item = item[1:]
        if item.endswith("}"):
            item = item[:-1]

        measurement = {}
        for f in item.split(";"):
            if "=" in f:
                key, val = f.split("=", 1)
                key = key.strip().lower()
                val = val.strip()
                try:
                    val = float(val) if "." in val else int(val)
                except:
                    pass
                measurement[key] = val

        measurement["type"] = "DATA"
        result["measurements"].append(measurement)

    return result


def parse_message(raw: bytes):
    text = raw.decode().strip()

    if text.startswith("BULK;"):
        return parse_bulk_message(text)
     
    parts = text.split(";")
    msg_type = parts[0].strip().upper()
    result = {"type": msg_type}

    for p in parts[1:]:
        if "=" in p:
            key, val = p.split("=", 1)
            key = key.strip().lower()
            val = val.strip()
            try:
                val = float(val) if "." in val else int(val)
            except:
                pass
            result[key] = val

    return result


# =====================================================================
# ======================== UKLÁDÁNÍ ZPRÁV ==============================
# =====================================================================

alarm_active = False   # <<< přidej nahoru do souboru

def uloz_zpravu(obj):
    global alarm_active

    # Načteme existující záznamy pro kontrolu duplicit
    existujici = set()
    try:
        with open(SOUBOR_NA_DATA, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    z = json.loads(line)
                    if "time" in z:
                        existujici.add(z["time"])
                except:
                    pass
    except FileNotFoundError:
        pass

    with open(SOUBOR_NA_DATA, "a", encoding="utf-8") as f:

        if obj.get("type") == "STARTUP":
            obj["bulk"] = False
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
            return
        # -------------------------
        # ALARM zpráva
        # -------------------------
        if obj.get("type") == "ALARM":
            alarm_active = True
            obj["bulk"] = False
            if obj.get("time") not in existujici:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
            return

        # -------------------------
        # FALSE ALARM zpráva
        # -------------------------
        if obj.get("type") == "FALSE_ALARM":
            alarm_active = False
            obj["bulk"] = False
            if obj.get("time") not in existujici:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
            return

        # -------------------------
        # BULK zpráva
        # -------------------------
        if obj.get("type") == "BULK":
            for m in obj["measurements"]:
                if m.get("time") not in existujici:
                    m["bulk"] = True
                    f.write(json.dumps(m, ensure_ascii=False) + "\n")
            return

        # -------------------------
        # Obyčejná DATA zpráva
        # -------------------------
        obj["bulk"] = False
        if obj.get("time") not in existujici:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")



# =====================================================================
# ======================== API ENDPOINTY ===============================
# =====================================================================

def nacti_posledni_data():
    try:
        with open(SOUBOR_NA_DATA, "r", encoding="utf-8") as f:
            for line in reversed(f.readlines()):
                obj = json.loads(line)
                if obj.get("type") in ["DATA", "ALARM", "FALSE_ALARM"]:
                    return obj
    except:
        pass
    return {}

def nacti_startup():
    posledni = {}
    try:
        with open(SOUBOR_NA_DATA, "r", encoding="utf-8") as f:
            for line in f:
                obj = json.loads(line)
                if obj.get("type") == "STARTUP":
                    posledni = obj
    except:
        pass
    return posledni
    

from datetime import datetime

def nacti_historii():
    out = []
    try:
        with open(SOUBOR_NA_DATA, "r", encoding="utf-8") as f:
            for line in f:
                obj = json.loads(line)

                # Do grafu chceme jen měření z BULK zpráv
                if obj.get("bulk") == True:
                    out.append(obj)

    except:
        pass

    # NEŘADIT — zachovat pořadí, v jakém přišla BULK zpráva
    return out


@app.route("/api/clear", methods=["POST"])
def api_clear_data():
    try:
        # Otevření v režimu 'w' soubor vyprázdní
        with open(SOUBOR_NA_DATA, "w", encoding="utf-8") as f:
            f.write("") 
        return jsonify({"status": "ok", "message": "Historie byla smazána."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/")
def index():
    return render_template_string(HTML_MAIN)

@app.route("/history")
def history_page():
    return render_template_string(HTML_HISTORY)

@app.route("/api/latest")
def api_latest():
    global alarm_active

    posledni = nacti_posledni_data()

    # Pokud je aktivní ALARM, přepiš typ
    if alarm_active:
        posledni["type"] = "ALARM"

    return jsonify(posledni)


@app.route("/api/startup")
def api_startup():
    return jsonify(nacti_startup())

@app.route("/api/history")
def api_history():
    return jsonify(nacti_historii())


# =====================================================================
# ======================== UDP SERVER =================================
# =====================================================================

def udp_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))

    print(f"UDP server spuštěn na portu {UDP_PORT} (NB-IoT simulace)...")
    print(f"Data se ukládají do souboru: {SOUBOR_NA_DATA}")

    try:
        while True:
            data, addr = sock.recvfrom(4096)
            print(f"Přijata zpráva od {addr}: {data}")

            parsed = parse_message(data)
            if parsed is None:
                print("Nepodařilo se parsovat zprávu.")
                continue

            uloz_zpravu(parsed)

            sock.sendto(b"ACK", addr)
            print(f"ACK odeslán na {addr}")

    except KeyboardInterrupt:
        print("\nServer byl vypnut uživatelem.")
    finally:
        sock.close()


# =====================================================================
# ======================== SPUŠTĚNÍ SERVERU ============================
# =====================================================================

vlakno = threading.Thread(target=udp_server, daemon=True)
vlakno.start()

if __name__ == "__main__":
    print("Web rozhraní běží na http://0.0.0.0:9797")
    app.run(host="0.0.0.0", port=9797)
