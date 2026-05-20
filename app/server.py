from __future__ import annotations
import asyncio
import threading
from typing import Callable, Optional

from aiohttp import web

from .models import SharedFile


class FileServer:
    """HTTP server running in a daemon thread with its own asyncio event loop."""

    def __init__(self) -> None:
        self._shares: dict[str, SharedFile] = {}
        self._lock = threading.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._actual_port: Optional[int] = None
        self._ready = threading.Event()
        self.on_share_changed: Optional[Callable[[str], None]] = None

    @property
    def port(self) -> Optional[int]:
        return self._actual_port

    def start(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="dropshare-http"
        )
        self._thread.start()
        self._ready.wait(timeout=5.0)

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._init())
        self._loop.run_forever()

    async def _init(self) -> None:
        app = web.Application()
        app.router.add_get("/{token}/{filename:.+}", self._handle_dl)
        app.router.add_get("/api/shares", self._handle_list)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 0)
        await site.start()
        self._actual_port = site._server.sockets[0].getsockname()[1]
        self._ready.set()

    async def _handle_dl(self, req: web.Request) -> web.FileResponse:
        token = req.match_info["token"]
        with self._lock:
            share = self._shares.get(token)
            if not share or not share.active:
                raise web.HTTPNotFound(reason="Share not available")
            share.download_count += 1
            if share.max_downloads > 0 and share.download_count >= share.max_downloads:
                share.active = False

        if not share.path.exists():
            raise web.HTTPNotFound(reason="File missing on disk")

        if self.on_share_changed:
            self.on_share_changed(token)

        return web.FileResponse(
            share.path,
            headers={"Content-Disposition": f'attachment; filename="{share.path.name}"'},
        )

    async def _handle_list(self, _req: web.Request) -> web.Response:
        with self._lock:
            data = [
                {
                    "token": token,
                    "name": share.path.name,
                    "size": share.path.stat().st_size if share.path.exists() else 0,
                    "remaining": share.remaining,
                }
                for token, share in self._shares.items()
                if share.active
            ]
        return web.json_response(data)

    def add_share(self, share: SharedFile) -> None:
        with self._lock:
            self._shares[share.token] = share

    def remove_share(self, token: str) -> None:
        with self._lock:
            self._shares.pop(token, None)
