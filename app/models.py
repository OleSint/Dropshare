from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import uuid


@dataclass
class SharedFile:
    path: Path
    token: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    max_downloads: int = 0      # 0 = unlimited
    download_count: int = 0
    share_type: str = ""        # "" | "lan" | "http" | "tailscale"
    active: bool = False
    link: str = ""              # vollständiger HTTP-Link nach Freigabe

    @property
    def is_shared(self) -> bool:
        return self.active

    @property
    def remaining(self) -> int:
        """Returns remaining downloads, -1 means unlimited."""
        if self.max_downloads == 0:
            return -1
        return max(0, self.max_downloads - self.download_count)

    @property
    def badge_text(self) -> str:
        if not self.active:
            return ""
        if self.max_downloads == 0:
            return "∞"
        return f"{self.remaining}/{self.max_downloads}"
