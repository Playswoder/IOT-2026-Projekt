# 🌲 BPC‑IoT Projekt #4: Detektor lesních požárů

Tento projekt se zaměřuje na vývoj energeticky efektivního IoT zařízení pro včasnou detekci lesních požárů v národních parcích a lesích ČR/SR.  
Systém monitoruje environmentální data a kritické stavy reportuje v reálném čase.

---

## 📋 Přehled funkcí

### 🔁 Periodické měření
- Snímání teploty a vlhkosti každých 30 minut.

### 📡 Dávkový přenos dat
- Odesílání naměřených dat na server v intervalu 6 hodin  
  → výrazná úspora energie.

### 🚨 Okamžitý ALARM
- Při překročení prahové hodnoty (40 °C) se odešle okamžitá varovná zpráva.
- Alarm nečeká na další dávkový interval.

### 🔄 False Alarm Recovery
- Automatická notifikace při návratu teploty do bezpečných hodnot.

### 📶 Diagnostika sítě
- Odesílání technických parametrů NB‑IoT:
  - RSRP
  - SINR
  - CellID
  - TAC
  - Band

### 🔋 Energetický management
- Podpora režimů:
  - Deep Sleep
  - PSM (Power Saving Mode)

---

## 🛠 Technické řešení

### 📡 Konektivita: NB‑IoT

Důvody výběru:
- Vynikající prostupnost signálu  
  → vhodné pro husté lesy, skalní útvary, rokle.
- Energetická efektivita  
  → eDRX a PSM umožňují provoz na baterii několik let.
- Licencované pásmo  
  → vyšší spolehlivost a garantovaná QoS oproti LoRaWAN.

---

## 🔗 Protokoly

### Transportní
- UDP  
  → minimální overhead, nízká spotřeba energie.

### Aplikační
- LwM2M nebo MQTT (dle backendu)
- Custom Binary Payload  
  → maximální komprese dat, úspora bytů v NB‑IoT paketu.

<img width="1920" height="1152" alt="image" src="https://github.com/user-attachments/assets/058a1b1f-40b0-4e3c-9ab7-c96093af683f" />

