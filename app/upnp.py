from __future__ import annotations
import os
import threading
from typing import Callable, Optional


def _silence_c_stderr():
    """Context manager that suppresses C-level stderr (fd 2)."""
    import contextlib

    class _Silence:
        def __enter__(self):
            self._old_fd = os.dup(2)
            self._devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(self._devnull, 2)

        def __exit__(self, *_):
            os.dup2(self._old_fd, 2)
            os.close(self._old_fd)
            os.close(self._devnull)

    return _Silence()


def setup_upnp_async(
    port: int,
    callback: Callable[[bool, Optional[str], Optional[int]], None],
) -> None:
    """Start UPnP setup in a background thread.

    Calls callback(success, public_ip, external_port) from the same thread.
    The caller must marshal the result back to the main/UI thread.
    """

    def _run() -> None:
        try:
            import miniupnpc  # type: ignore
        except ImportError:
            callback(False, None, None)
            return

        try:
            with _silence_c_stderr():
                upnp = miniupnpc.UPnP()
                upnp.discoverdelay = 500
                found = upnp.discover()

            if not found:
                callback(False, None, None)
                return

            upnp.selectigd()
            external_ip: str = upnp.externalipaddress()
            if not external_ip:
                callback(False, None, None)
                return

            ok = upnp.addportmapping(
                port, "TCP", upnp.lanaddr, port, "DropShare", ""
            )
            if ok:
                callback(True, external_ip, port)
            else:
                callback(False, external_ip, None)
        except Exception:
            callback(False, None, None)

    threading.Thread(target=_run, daemon=True, name="dropshare-upnp").start()
