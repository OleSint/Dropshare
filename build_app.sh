#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "→ Baue DropShare.app …"
pyinstaller dropshare.spec --noconfirm --clean

echo "→ Kopiere nach /Applications …"
cp -R dist/DropShare.app /Applications/DropShare.app

echo "→ Räume auf …"
rm -rf build dist

echo "✓ Fertig — DropShare.app liegt in /Applications"
