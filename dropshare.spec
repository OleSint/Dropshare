# -*- mode: python ; coding: utf-8 -*-
import sys

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        "aiohttp.web_urldispatcher",
        "aiohttp.web_exceptions",
        "aiohttp.web_fileresponse",
        "aiohttp.web_protocol",
        "aiohttp.web_runner",
        "aiohttp.web_server",
        "aiohttp.connector",
        "aiohttp.client",
        "aiohttp.resolver",
        "zeroconf._handlers",
        "zeroconf._services",
        "zeroconf._services.browser",
        "zeroconf._services.info",
        "zeroconf._dns",
        "zeroconf._engine",
        "zeroconf._exceptions",
        "zeroconf._utils",
        "zeroconf._utils.net",
        "asyncio.runners",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── Windows: einzelne .exe ────────────────────────────────────────────────────
if IS_WIN:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name="DropShare",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,          # kein Konsolenfenster
        icon=None,
    )

# ── macOS: .app Bundle ────────────────────────────────────────────────────────
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="DropShare",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        name="DropShare",
    )

    app = BUNDLE(
        coll,
        name="DropShare.app",
        icon=None,
        bundle_identifier="de.dropshare.app",
        info_plist={
            "NSHighResolutionCapable": True,
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
            "NSRequiresAquaSystemAppearance": False,
            "LSMinimumSystemVersion": "10.14",
        },
    )
