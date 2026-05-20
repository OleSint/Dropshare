# DropShare

Dateien per Drag & Drop freigeben — direkt über das Internet, ohne Cloud-Dienste.

---

## Was ist DropShare?

DropShare ist eine kleine Desktop-App für macOS und Windows. Man zieht Dateien ins Fenster und gibt sie per Rechtsklick frei. Andere können die Datei dann über einen Link herunterladen — ganz ohne Dropbox, WeTransfer oder ähnliche Dienste. Der eigene Rechner ist der Server.

**Zwei Freigabe-Arten:**
- **LAN** — andere DropShare-Nutzer im selben Netzwerk sehen die Datei automatisch
- **Internet** — ein HTTP-Link, der in jedem Browser funktioniert

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

### Internet-Freigabe

DropShare versucht beim Start automatisch per **UPnP** einen Port am Router freizuschalten. Das funktioniert bei den meisten Heimroutern ohne weiteres Zutun. Steht in der Statusleiste `UPnP: ✓`, ist alles eingerichtet und der generierte Link funktioniert sofort.

Zeigt die Statusleiste `UPnP: nicht verfügbar`, muss im Router eine manuelle Portweiterleitung eingerichtet werden. Der Dialog zeigt den benötigten Port und die lokale IP-Adresse an.

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

git tag v1.0.0
git push origin v1.0.0
```

GitHub baut dann automatisch `DropShare-macOS.zip` und `DropShare-Windows.zip` und legt sie unter Releases ab.

---

## Technisches

| Komponente | Beschwindigkeit |
|---|---|
| GUI | PyQt6 |
| HTTP-Server | aiohttp (läuft eingebettet im Hintergrund) |
| LAN-Erkennung | Zeroconf / mDNS |
| UPnP | miniupnpc |
| Paketierung | PyInstaller |

Es werden keine externen Server kontaktiert. Alle Daten laufen direkt zwischen den Geräten.

---

## Lizenz

MIT
