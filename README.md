# DropShare

Dateien per Drag & Drop freigeben — direkt über das Internet, ohne Cloud-Dienste.

---

## Was ist DropShare?

DropShare ist eine kleine Desktop-App für macOS und Windows. Man zieht Dateien ins Fenster und gibt sie per Rechtsklick frei. Andere können die Datei dann über einen Link herunterladen — ganz ohne Dropbox, WeTransfer oder ähnliche Dienste. Der eigene Rechner ist der Server.

**Drei Freigabe-Arten:**
- **LAN** — andere DropShare-Nutzer im selben Netzwerk sehen die Datei automatisch (AutoDiscover)
- **Internet** — ein öffentlicher HTTPS-Link über einen Cloudflare-Tunnel, der in jedem Browser funktioniert
- **Tailscale** — ein privater, verschlüsselter Link, der nur auf den eigenen Geräten funktioniert, egal wo sie stehen (siehe [TAILSCALE.md](TAILSCALE.md))

**Download-Limit:** Man kann einstellen, wie oft eine Datei heruntergeladen werden darf. Danach wird die Freigabe automatisch beendet.

---

## Screenshots

> *(folgen)*

---

## Download

Die aktuellen Versionen gibt es unter [Releases](../../releases):

| Plattform | Datei |
|---|---|
| macOS | `DropShare-macOS.zip` → entzippen → `DropShare.app` doppelklicken |
| Windows | `DropShare-Windows.zip` → entzippen → `DropShare.exe` doppelklicken |

Eine Installation ist nicht nötig.

---

## Benutzung

1. App starten
2. Dateien per Drag & Drop ins Fenster ziehen
3. Rechtsklick auf eine Datei → **Freigeben…**
4. Freigabe-Art wählen und optional ein Download-Limit setzen
5. Link kopieren und verschicken

Am grünen Badge neben jeder Datei sieht man auf einen Blick, wie viele Downloads noch möglich sind (z.B. `2/3`) oder ob die Freigabe unbegrenzt läuft (`∞`).

### Internet-Freigabe via Cloudflare Tunnel

Beim ersten Start lädt DropShare das Tool `cloudflared` einmalig (~30 MB) herunter und startet es im Hintergrund. Es baut automatisch einen verschlüsselten Tunnel zu Cloudflare auf und erzeugt einen öffentlichen HTTPS-Link — ohne Router-Konfiguration oder UPnP.

Die Statusleiste zeigt den aktuellen Tunnel-Status:
- `Tunnel: wird heruntergeladen …` — einmaliger Download beim ersten Start
- `Tunnel: wird aufgebaut …` — dauert einige Sekunden
- `Tunnel: ✓  bereit` — Internet-Freigaben sind ab jetzt möglich

Der generierte Link sieht so aus:
```
https://zufaelliger-name.trycloudflare.com/TOKEN/dateiname.pdf
```

**Hinweis zur Privatsphäre:** Cloudflare fungiert als Durchleitung und kann technisch den Inhalt übertragener Dateien einsehen. Für vertrauliche Dateien empfiehlt sich daher ausschließlich die LAN-Freigabe.

### Private Freigabe via Tailscale

Eine ausführliche, leicht verständliche Anleitung dazu gibt es in [TAILSCALE.md](TAILSCALE.md).

### AutoDiscover im LAN

Andere DropShare-Instanzen im selben WLAN erscheinen automatisch im unteren Bereich des Fensters. Dort freigegebene Dateien können per Doppelklick oder Rechtsklick direkt heruntergeladen werden — ohne Link.

### Link herunterladen

Über den Button **↓ Link herunterladen** (oben rechts) kann ein empfangener DropShare- oder HTTP-Link direkt in der App eingefügt werden. Die Datei wird dann ohne Browser in `~/Downloads/` gespeichert.

---

## Selbst bauen

### Voraussetzungen

- Python 3.11 oder neuer
- pip

### Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

### Direkt starten (ohne Build)

```bash
python main.py
```

### Als App bauen

**macOS:**
```bash
./build_app.sh
# → /Applications/DropShare.app
```

**Windows:**
```
build_app.bat doppelklicken
# → dist\DropShare.exe
```

### Automatischer Build per GitHub Actions

Einen neuen Release mit fertigen Downloads für beide Plattformen erzeugt man so:

```bash
git add . && git commit -m "Update"
git push

git tag v1.1.0
git push origin v1.1.0
```

GitHub baut dann automatisch `DropShare-macOS.zip` und `DropShare-Windows.zip` und legt sie unter Releases ab.

---

## Technisches

| Komponente | Verwendung |
|---|---|
| GUI | PyQt6 |
| HTTP-Server | aiohttp (läuft eingebettet im Hintergrund) |
| Internet-Tunnel | cloudflared (Cloudflare Quick Tunnel) |
| LAN-Erkennung | Zeroconf / mDNS |
| UPnP | miniupnpc (Fallback falls verfügbar) |
| Paketierung | PyInstaller |

Es wird kein Cloud-Speicher genutzt. Alle Dateien verbleiben auf dem eigenen Rechner und werden direkt übertragen. Der Cloudflare-Tunnel dient ausschließlich als verschlüsselte Durchleitung für Internet-Freigaben.

---

## Lizenz

MIT
