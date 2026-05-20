from __future__ import annotations
import socket
from typing import Callable, Optional

try:
    from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser  # type: ignore
    _HAS_ZEROCONF = True
except ImportError:
    _HAS_ZEROCONF = False

SERVICE_TYPE = "_dropshare._tcp.local."


def _local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


class LanDiscovery:
    """Announces this DropShare instance via mDNS and discovers peers."""

    def __init__(
        self,
        port: int,
        node_id: str,
        on_peer_added: Optional[Callable[[str, str, int], None]] = None,
        on_peer_removed: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._port = port
        self._node_id = node_id
        self.on_peer_added = on_peer_added
        self.on_peer_removed = on_peer_removed
        self._zc: Optional[Zeroconf] = None
        self._info: Optional[ServiceInfo] = None
        self._browser = None
        self._peers: dict[str, tuple[str, int]] = {}

    @property
    def available(self) -> bool:
        return _HAS_ZEROCONF

    def start(self) -> None:
        if not _HAS_ZEROCONF:
            return
        self._zc = Zeroconf()
        ip = _local_ip()
        self._info = ServiceInfo(
            SERVICE_TYPE,
            f"{self._node_id}.{SERVICE_TYPE}",
            addresses=[socket.inet_aton(ip)],
            port=self._port,
            properties={"version": "1"},
        )
        self._zc.register_service(self._info)
        self._browser = ServiceBrowser(self._zc, SERVICE_TYPE, self)

    def add_service(self, zc: Zeroconf, stype: str, name: str) -> None:
        if name == f"{self._node_id}.{SERVICE_TYPE}":
            return
        info = zc.get_service_info(stype, name)
        if info and info.addresses:
            ip = socket.inet_ntoa(info.addresses[0])
            self._peers[name] = (ip, info.port)
            if self.on_peer_added:
                self.on_peer_added(name, ip, info.port)

    def update_service(self, zc: Zeroconf, stype: str, name: str) -> None:
        self.add_service(zc, stype, name)

    def remove_service(self, zc: Zeroconf, stype: str, name: str) -> None:
        self._peers.pop(name, None)
        if self.on_peer_removed:
            self.on_peer_removed(name)

    def stop(self) -> None:
        if not self._zc:
            return
        if self._info:
            try:
                self._zc.unregister_service(self._info)
            except Exception:
                pass
        try:
            self._zc.close()
        except Exception:
            pass
