#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "→ Baue DropShare.app …"
pyinstaller dropshare.spec --noconfirm --clean

echo "→ Patche QtCore für macOS 26 …"
python3 - <<'PYEOF'
import subprocess, sys

path = "dist/DropShare.app/Contents/Frameworks/PyQt6/QtCore.abi3.so"
result = subprocess.run(["nm", path], capture_output=True, text=True)
offset = None
for line in result.stdout.split("\n"):
    if "__GLOBAL__sub_I_qdarwinpermissionplugin_location.mm" in line and " t " in line:
        offset = int(line.split()[0], 16)
        break

if offset is None:
    print("WARNUNG: Symbol nicht gefunden, Patch übersprungen")
    sys.exit(0)

with open(path, "r+b") as f:
    f.seek(offset)
    before = f.read(4)
    if before == bytes([0xC0, 0x03, 0x5F, 0xD6]):
        print(f"Patch bereits angewendet bei 0x{offset:x}")
        sys.exit(0)
    f.seek(offset)
    f.write(bytes([0xC0, 0x03, 0x5F, 0xD6]))  # ARM64 RET
    print(f"✓ Patch angewendet bei 0x{offset:x} (war: {before.hex()})")
PYEOF

echo "→ Kopiere nach /Applications …"
rm -rf /Applications/DropShare.app
cp -R dist/DropShare.app /Applications/DropShare.app

echo "→ Signiere App (macOS 26 Kompatibilität) …"
find /Applications/DropShare.app -name "*.so" -o -name "*.dylib" | \
  xargs -I{} codesign --force --sign - {} 2>/dev/null
codesign --force --deep --sign - /Applications/DropShare.app

echo "→ Räume auf …"
rm -rf build dist

echo "✓ Fertig — DropShare.app liegt in /Applications"
