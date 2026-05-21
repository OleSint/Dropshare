import sys
import ctypes

# Auf macOS muss NSApplicationLoad() aufgerufen werden, BEVOR Qt geladen wird.
# Sonst gibt CFBundleGetMainBundle() auf macOS 26 (Tahoe) NULL zurück und
# Qt's statischer Initializer für die Permission-Plugins crasht beim Start.
if sys.platform == "darwin":
    try:
        AppKit = ctypes.CDLL("/System/Library/Frameworks/AppKit.framework/AppKit")
        AppKit.NSApplicationLoad()
    except Exception:
        pass
