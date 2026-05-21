from __future__ import annotations
import platform
import re
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path
from typing import Callable, Optional


_URL_RE = re.compile(r'https://[a-z0-9-]+\.trycloudflare\.com')


def _config_dir() -> Path:
    d = Path.home() / ".dropshare"
    d.mkdir(exist_ok=True)
    return d


def _binary_path() -> Path:
    name = "cloudflared.exe" if sys.platform == "win32" else "cloudflared"
    return _config_dir() / name


def _binary_url() -> str:
    machine = platform.machine().lower()
    if sys.platform == "darwin":
        arch = "arm64" if machine in ("arm64", "aarch64") else "amd64"
        return (
            f"https://github.com/cloudflare/cloudflared/releases/latest"
            f"/download/cloudflared-darwin-{arch}"
        )
    if sys.platform == "win32":
        return (
            "https://github.com/cloudflare/cloudflared/releases/latest"
            "/download/cloudflared-windows-amd64.exe"
        )
    arch = "arm64" if machine in ("arm64", "aarch64") else "amd64"
    return (
        f"https://github.com/cloudflare/cloudflared/releases/latest"
        f"/download/cloudflared-linux-{arch}"
    )


def _ensure_binary(on_status: Callable[[str], None]) -> Optional[Path]:
    path = _binary_path()
    if path.exists():
        return path
    on_status("cloudflared wird heruntergeladen (einmalig ~30 MB) …")
    try:
        urllib.request.urlretrieve(_binary_url(), path)
        if sys.platform != "win32":
            path.chmod(0o755)
        return path
    except Exception as exc:
        on_status(f"Download fehlgeschlagen: {exc}")
        return None


class CloudflareTunnel:
    """Manages a cloudflared quick-tunnel subprocess."""

    def __init__(self, port: int) -> None:
        self._port = port
        self._proc: Optional[subprocess.Popen] = None
        self._url: Optional[str] = None
        self._thread: Optional[threading.Thread] = None
        self.on_ready:  Optional[Callable[[str], None]] = None   # base URL
        self.on_status: Optional[Callable[[str], None]] = None   # status text
        self.on_error:  Optional[Callable[[str], None]] = None

    @property
    def url(self) -> Optional[str]:
        return self._url

    @property
    def is_ready(self) -> bool:
        return self._url is not None

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="dropshare-tunnel"
        )
        self._thread.start()

    def _run(self) -> None:
        def _status(msg: str) -> None:
            if self.on_status:
                self.on_status(msg)

        binary = _ensure_binary(_status)
        if not binary:
            if self.on_error:
                self.on_error("cloudflared konnte nicht heruntergeladen werden.")
            return

        _status("Tunnel wird aufgebaut …")
        cmd = [
            str(binary),
            "tunnel",
            "--url", f"http://localhost:{self._port}",
            "--no-autoupdate",
        ]
        popen_kwargs: dict = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "text": True,
        }
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        try:
            self._proc = subprocess.Popen(cmd, **popen_kwargs)
            for line in self._proc.stdout:
                match = _URL_RE.search(line)
                if match:
                    self._url = match.group(0)
                    if self.on_ready:
                        self.on_ready(self._url)
                    break
            # drain stdout so the process doesn't block
            if self._proc.stdout:
                for _ in self._proc.stdout:
                    pass
        except Exception as exc:
            if self.on_error:
                self.on_error(str(exc))

    def stop(self) -> None:
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None
        self._url = None
