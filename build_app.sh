#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "→ Baue DropShare.app …"
pyinstaller dropshare.spec --noconfirm --clean

echo "→ Kopiere nach /Applications …"
rm -rf /Applications/DropShare.app
cp -R dist/DropShare.app /Applications/DropShare.app

echo "→ Signiere App (macOS 26 Kompatibilität) …"
codesign --force --deep --sign - /Applications/DropShare.app

echo "→ Räume auf …"
rm -rf build dist

echo "✓ Fertig — DropShare.app liegt in /Applications"
