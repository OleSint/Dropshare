# Dateien sicher übers eigene Netzwerk teilen — mit Tailscale

Diese Anleitung erklärt, was Tailscale ist, warum es für DropShare nützlich ist, und wie man es in wenigen Minuten einrichtet. Man braucht dafür **keine Vorkenntnisse**.

---

## Was ist Tailscale überhaupt?

Stell dir vor, all deine Geräte — dein Laptop, dein Handy, dein PC zuhause — wären über ein unsichtbares, privates Kabel miteinander verbunden. Egal ob sie im selben WLAN stehen oder hunderte Kilometer voneinander entfernt sind: Sie können sich gegenseitig erreichen, als wären sie im selben Raum.

Genau das macht Tailscale. Es baut ein **eigenes, privates Netzwerk** (ein sogenanntes *Tailnet*) zwischen deinen Geräten auf — verschlüsselt, sodass niemand sonst mitlesen kann, auch nicht Tailscale selbst.

**Wichtig:** Tailscale ist kostenlos für private Nutzung (bis zu 100 Geräte) und erfordert nur ein Login z. B. mit deinem Google- oder Microsoft-Konto.

---

## Warum gibt es das in DropShare?

DropShare bietet bereits zwei Wege, eine Datei zu teilen:

| Art | Wie funktioniert's | Wer sieht den Inhalt? |
|---|---|---|
| **LAN** | Funktioniert nur, wenn beide Geräte im selben WLAN sind | Niemand außer euch |
| **Internet (Cloudflare)** | Erzeugt einen öffentlichen Link, der von überall funktioniert | Die Datei läuft technisch über Cloudflare-Server |
| **Tailscale** *(neu)* | Erzeugt einen Link, der nur innerhalb deines privaten Tailscale-Netzwerks funktioniert | Niemand außer deinen eigenen Geräten — Ende-zu-Ende verschlüsselt |

Tailscale ist also der goldene Mittelweg: Man ist **nicht aufs gleiche WLAN beschränkt** wie bei LAN, aber die Datei läuft auch **nicht über einen fremden Server** wie beim Cloudflare-Link. Ideal zum Beispiel, um vom Büro-PC schnell eine Datei aufs Handy zu schicken, oder zwischen zwei eigenen Rechnern an unterschiedlichen Orten.

---

## Einrichtung in 3 Schritten

### Schritt 1: Tailscale herunterladen und installieren

Auf **jedem Gerät**, mit dem du Dateien teilen möchtest (z. B. Laptop und Handy):

1. Gehe auf **[tailscale.com/download](https://tailscale.com/download)**
2. Lade die Version für dein Betriebssystem herunter (Windows, macOS, iOS, Android, Linux)
3. Installiere sie wie jede normale App

### Schritt 2: Einloggen

1. Öffne Tailscale nach der Installation
2. Logge dich mit einem Konto ein, das du bereits hast — z. B. **Google**, **Microsoft** oder **GitHub**
3. Wiederhole das auf jedem weiteren Gerät mit **demselben Konto**

Das war's — die Geräte sind jetzt automatisch miteinander verbunden. Im Tailscale-Fenster bzw. -Menü siehst du alle deine verbundenen Geräte mit ihrem Namen.

### Schritt 3: DropShare neu starten

Starte DropShare einmal neu, nachdem Tailscale läuft. DropShare erkennt automatisch, dass Tailscale aktiv ist — es ist keine zusätzliche Einstellung in DropShare nötig.

---

## Datei über Tailscale teilen

1. Datei per Drag & Drop in DropShare ziehen
2. Rechtsklick auf die Datei → **Freigeben…**
3. Im Freigabe-Dialog die Option **„Über Tailscale"** auswählen
   - Ist diese Option ausgegraut, läuft Tailscale auf diesem Gerät nicht oder es ist noch nicht eingeloggt (siehe Schritt 1–2)
4. Den erzeugten Link kopieren und an dich selbst schicken (z. B. per Mail, Notiz-App, Messenger) oder direkt auf dem anderen Gerät öffnen
5. Der Link funktioniert **nur auf Geräten, die ebenfalls in deinem Tailscale-Netzwerk eingeloggt sind**

---

## Warum installiert DropShare Tailscale nicht automatisch?

Eine berechtigte Frage — DropShare lädt für die Internet-Freigabe (`cloudflared`) ja auch automatisch im Hintergrund herunter. Bei Tailscale geht das nicht ganz so einfach:

Tailscale muss ein eigenes Netzwerk-Interface auf deinem Computer anlegen, damit der Datenverkehr überhaupt fließen kann. Das ist ein tieferer Eingriff ins System, für den **Administrator-Rechte** nötig sind (bei macOS dein Passwort, bei Windows die "Als Administrator ausführen"-Bestätigung). Aus Sicherheitsgründen lässt DropShare solche Eingriffe nicht automatisch im Hintergrund zu — du behältst die volle Kontrolle und installierst es bewusst selbst, einmalig.

Sobald es einmal eingerichtet ist, läuft es aber dauerhaft im Hintergrund — DropShare muss sich um nichts mehr kümmern.

---

## Häufige Fragen

**Kostet Tailscale etwas?**
Nein, für private Nutzung mit bis zu 100 Geräten ist es kostenlos.

**Sieht Tailscale meine Dateien?**
Nein. Tailscale baut nur die Verbindung auf (vergleichbar mit einem Kabel). Die eigentliche Datei läuft direkt zwischen deinen Geräten und ist durchgehend verschlüsselt.

**Was, wenn ich Tailscale nicht installieren will?**
Kein Problem — die LAN- und Internet-Freigabe über Cloudflare funktionieren weiterhin ganz normal, unabhängig davon.

**Die Option „Über Tailscale" ist ausgegraut — was tun?**
1. Prüfen, ob Tailscale installiert ist und läuft (Symbol in der Menüleiste bzw. Taskleiste)
2. Prüfen, ob man eingeloggt ist (im Tailscale-Fenster sollte der eigene Gerätename mit grünem Punkt erscheinen)
3. DropShare einmal neu starten

**Funktioniert das auch vom Handy aus?**
Ja — sobald die Tailscale-App auf dem Handy mit demselben Konto eingeloggt ist, kann man den DropShare-Link im Handy-Browser öffnen.

---

## Mehr erfahren

- Offizielle Tailscale-Seite: [tailscale.com](https://tailscale.com)
- Wie Tailscale technisch funktioniert (WireGuard-basiert): [tailscale.com/blog](https://tailscale.com/blog)
