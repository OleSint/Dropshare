from __future__ import annotations
import json
import shutil
import subprocess
from typing import Optional


def _binary() -> Optional[str]:
    """Pfad zur tailscale-CLI, falls installiert, sonst None.

    Wir installieren Tailscale nicht selbst: tailscaled braucht erhöhte
    Rechte (sudo/Admin) um ein Netzwerk-Interface anzulegen. Das setzen
    wir voraus -- DropShare nutzt nur eine bereits laufende Verbindung.
    """
    return shutil.which("tailscale")


def is_available() -> bool:
    return _binary() is not None


def get_status() -> Optional[dict]:
    binary = _binary()
    if not binary:
        return None
    try:
        result = subprocess.run(
            [binary, "status", "--json"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except Exception:
        return None


def get_ip() -> Optional[str]:
    """IPv4-Adresse dieses Geräts im Tailnet, oder None wenn nicht verbunden."""
    status = get_status()
    if not status:
        return None
    self_info = status.get("Self") or {}
    for ip in self_info.get("TailscaleIPs") or []:
        if "." in ip:
            return ip
    return None
