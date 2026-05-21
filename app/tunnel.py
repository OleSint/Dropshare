from __future__ import annotations
import platform
import re
import subprocess
import sys
import tarfile
import tempfile
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


def _download_info() -> tuple[str, bool]:
    """Returns (url, is_tgz)."""
    machine = platform.machine().lower()
    base = "https://github.com/cloudflare/cloudflared/releases/latest/download"
    if sys.platform == "darwin":
        arch = "arm64" if machine in ("arm64", "aarch64") else "amd64"
        return f"{base}/cloudflared-darwin-{arch}.tgz", True
    if sys.platform == "win32":
        return f"{base}/cloudflared-windows-amd64.exe", False
    arch = "arm64" if machine in ("arm64", "aarch64") else "amd64"
    return f"{base}/cloudflared-linux-{arch}", False


def _ensure_binary(on_status: Callable[[str], None]) -> Optional[Path]:
    path = _binary_path()
    if path.exists():
        return path
    on_status("cloudflared wird heruntergeladen (einmalig ~30 MB) …")
    try:
        url, is_tgz = _download_info()
        if is_tgz:
            with tempfile.NamedTemporaryFile(suffix=".tgz", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            urllib.request.urlretrieve(url, tmp_path)
            with tarfile.open(tmp_path, "r:gz") as tar:
                # The archive contains a single binary named "cloudflared"
                member = next(
                    m for m in tar.getmembers()
                    if m.isfile() and "cloudflared" in m.name
                )
                extracted = tar.extractfile(member)
                path.write_bytes(extracted.read())
            tmp_path.unlink(missing_ok=True)
        else:
            urllib.request.urlretrieve(url, path)
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
