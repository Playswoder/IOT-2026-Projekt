import machine
import time
import BG77
import ahtx0

# =============================================================================
# KONFIGURACE
# =============================================================================
VUT_ID      = "211518"
DEVICE_ID   = "METEO-UNIT-01"
FW_VERSION  = "v2.1.0-beta"

SERVER_IP   = "147.229.148.105"
SERVER_PORT = 7006

TEMP_THRESHOLD  = 40.0  # [°C] 27.0 pro testy
TEMP_HYSTERESIS = 1.0

MEASURE_INTERVAL = 30 * 60      # 30 minut [s]
BULK_SIZE        = 12

APN = "lpwa.vodafone.iot"

LAT = "49.226"
LON = "16.575"

# =============================================================================
# PSM KONFIGURACE 
# =============================================================================

PSM_T3324 = "00000010"   # 4 sekundy


PSM_T3412 = "00000011"  # 6 hodin "00100110" 30minut "00000011" 10minut "00000001"

# =============================================================================
# INICIALIZACE HW
# =============================================================================

mod_en = machine.Pin(25, machine.Pin.OUT, value=1)
time.sleep(2)

i2c = machine.SoftI2C(scl=machine.Pin(15), sda=machine.Pin(14), freq=100000)
sensor = ahtx0.AHT10(i2c)

bg_uart = machine.UART(0, baudrate=115200, tx=machine.Pin(0), rx=machine.Pin(1))
modem = BG77.BG77(bg_uart, verbose=True, radio=True)
pon_trig = machine.Pin(9,machine.Pin.OUT)
# =============================================================================
# FUNKCE
# =============================================================================

def setup_modem():
    modem.setAPN(APN)
    modem.setRATType(BG77.RAT_NB_IOT_ONLY, 1)
    modem.setOperator(BG77.COPS_MANUAL,op_plmn = BG77.Operator.CZ_VODAFONE)
    while not modem.isRegistered():
        print("Cekam na registraci...")
        time.sleep(5)

        


def enable_psm():

    cmd = 'AT+CPSMS=1,,,\"{}\",\"{}\"\r\n'.format(PSM_T3412, PSM_T3324)
    resp = modem.sendCommand(cmd, exit_condition="OK\r\n", timeout=5)

    if "OK" in resp:
        print("PSM zapnuto: T3324=4s aktivni, T3412=6h spanek")
        return True
    else:
        print("PSM se nepodarilo zapnout:", resp)
        return False


def disable_psm():
    """Vypne PSM - uzitecne pri debugovani."""
    resp = modem.sendCommand("AT+CPSMS=0\r\n", exit_condition="OK\r\n", timeout=5)
    return "OK" in resp


def safe_nwinfo():
    try:
        nw = modem.getNWInfo()
        if nw is None:
            return (-120, 0)
        return (nw.RSRP, nw.SINR)
    except:
        return (-120, 0)

def ensureRRC():
    # Zkusíme modem probudit do RRC Connected
    modem.sendCommand("AT+QCSCON=1\r\n", timeout=2)

    # Ověříme stav
    resp = modem.sendCommand("AT+QCSCON?\r\n", timeout=2)
    if "1" in resp:
        print("RRC: CONNECTED")
        return True
    print("RRC: IDLE (QCSCON?) =", resp)
    return False


def send_udp(payload, alarm=False):

    # 1) Probuzení RRC
    ensureRRC()

    # 2) Ověření registrace (opravené)
    if not modem.isRegistered():
        print("Modem neni registrovan, nelze odeslat UDP.")
        return

    # 3) Socket
    res, sock = modem.socket(BG77.AF_INET, BG77.SOCK_DGRAM)
    if not res:
        print("Nelze otevrit socket.")
        return

    sock.settimeout(10)

    if sock.connect(SERVER_IP, SERVER_PORT):
        rai = 1 if alarm else 0
        sock.send(payload, rai=rai)

    sock.close()



def get_timestamp():
    t = time.localtime()
    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        t[0], t[1], t[2], t[3], t[4], t[5]
    )


def wait_for_network_ready(timeout=60):
    start = time.time()

    while time.time() - start < timeout:
        try:
            res, sock = modem.socket(BG77.AF_INET, BG77.SOCK_DGRAM)
            if res:
                sock.close()
                print("Sit pripravena")
                return True
        except:
            pass

        print("Cekam na sit...")
        time.sleep(3)

    return False

def psm_sleep(seconds):

    print("PSM spanek na {} minut...".format(seconds // 60))

    # Pošli modem do PSM
    modem.sendCommand('AT+CPSMS=1,,,\"{}\",\"{}\"'.format(PSM_T3412, PSM_T3324))

    # MCU spí
    time.sleep(seconds)

    print("Probuzeni, cekam na modem...")

    # Probuzení modemu (WAKEUP_IN nebo PWRKEY)
    pon_trig.value(1)
    time.sleep(0.1)
    pon_trig.value(0)

    # Opravená registrace
    attempts = 0
    while True:
        if modem.isRegistered():
            print("Modem registrovan po PSM.")
            break

        print("Modem se registruje po PSM... ({})".format(attempts))
        attempts += 1
        time.sleep(3)

        if attempts > 20:
            print("Restart modemu...")
            modem.modemSWReset()
            time.sleep(10)
            setup_modem()
            break

    #  Automatický RRC wake-up po PSM
    ensureRRC()


# =============================================================================
# STARTUP
# =============================================================================

setup_modem()
time.sleep(20)
wait_for_network_ready()

# PSM zapneme po úspěšné registraci - modem si ho vyjedná se sítí
enable_psm()

rsrp, sinr = safe_nwinfo()
nw = modem.getNWInfo()

cellid = nw.CellID if nw else 0
tac    = nw.TAC    if nw else 0
band   = nw.Band   if nw else 0
earfcn = nw.EARFCN if nw else 0

startup_msg  = "STARTUP;"
startup_msg += "DEVICE_ID={};".format(DEVICE_ID)
startup_msg += "FW={};".format(FW_VERSION)
startup_msg += "MANUFACTURER={};".format(VUT_ID)
startup_msg += "GPS_LAT={};".format(LAT)
startup_msg += "GPS_LON={};".format(LON)
startup_msg += "TECH=NB-IoT;"
startup_msg += "CELLID={};".format(cellid)
startup_msg += "TAC={};".format(tac)
startup_msg += "BAND={};".format(band)
startup_msg += "EARFCN={};".format(earfcn)
startup_msg += "RSRP={};".format(rsrp)
startup_msg += "SINR={}".format(sinr)

send_udp(startup_msg, alarm=True)

# =============================================================================
# HLAVNÍ SMYČKA
# =============================================================================

bulk_buffer  = []
alarm_active = False

while True:
    try:
        
        t = sensor.temperature
        h = sensor.relative_humidity
        rsrp, sinr = safe_nwinfo()
        ts = get_timestamp()

        print("Mereni: {}  T={:.2f}C  H={:.2f}%  RSRP={}  SINR={}".format(
            ts, t, h, rsrp, sinr
        ))

        # ALARM
        if t > TEMP_THRESHOLD and not alarm_active:
            alarm_msg  = "ALARM;"
            alarm_msg += "DEVICE_ID={};".format(DEVICE_ID)
            alarm_msg += "TEMP={:.2f};".format(t)
            alarm_msg += "HUM={:.2f};".format(h)
            alarm_msg += "TIME={};".format(ts)
            alarm_msg += "TECH=NB-IoT;"
            alarm_msg += "RSRP={};".format(rsrp)
            alarm_msg += "SINR={}".format(sinr)

            send_udp(alarm_msg, alarm=True)
            alarm_active = True

        # FALSE ALARM
        elif alarm_active and t <= (TEMP_THRESHOLD - TEMP_HYSTERESIS):
            fa_msg  = "FALSE_ALARM;"
            fa_msg += "DEVICE_ID={};".format(DEVICE_ID)
            fa_msg += "TEMP={:.2f};".format(t)
            fa_msg += "HUM={:.2f};".format(h)
            fa_msg += "TIME={};".format(ts)
            fa_msg += "TECH=NB-IoT;"
            fa_msg += "RSRP={};".format(rsrp)
            fa_msg += "SINR={}".format(sinr)

            send_udp(fa_msg)
            alarm_active = False

        # BUFFER
        bulk_buffer.append({
            "time": ts,
            "temp": round(t, 2),
            "hum":  round(h, 2),
            "rsrp": rsrp,
            "sinr": sinr
        })

        # BULK SEND
        if len(bulk_buffer) >= BULK_SIZE:
            data_items = []

            for m in bulk_buffer:
                item = "{{TIME={};TEMP={};HUM={};RSRP={};SINR={}}}".format(
                    m["time"], m["temp"], m["hum"], m["rsrp"], m["sinr"]
                )
                data_items.append(item)

            bulk_msg  = "BULK;"
            bulk_msg += "DEVICE_ID={};".format(DEVICE_ID)
            bulk_msg += "COUNT={};".format(len(bulk_buffer))
            bulk_msg += "DATA=[{}]".format(",".join(data_items))

            print("ODESILAM BULK:")
            print(bulk_msg)

            send_udp(bulk_msg)
            bulk_buffer = []

    except Exception as e:
        print("Chyba:", e)

    # Spánek s PSM - BG77 i RP2040 jdou do low-power stavu
    psm_sleep(MEASURE_INTERVAL)

