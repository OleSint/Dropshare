import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QStyleFactory

from app.gui.main_window import MainWindow


def main() -> None:
    # Must be set before QApplication is constructed
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("DropShare")
    app.setApplicationVersion("1.0.0")

    # On Windows the native style can override stylesheet colours for some
    # widgets.  Fusion is cross-platform and respects stylesheets reliably.
    if sys.platform == "win32":
        app.setStyle(QStyleFactory.create("Fusion"))

    # Force dark text globally so widgets without explicit colours stay readable
    # on light backgrounds regardless of the OS colour scheme.
    app.setStyleSheet(
        "QLabel       { color: #2C3E50; }"
        "QRadioButton { color: #2C3E50; }"
        "QGroupBox    { color: #2C3E50; }"
        "QCheckBox    { color: #2C3E50; }"
        "QSpinBox     { color: #2C3E50; }"
        "QLineEdit    { color: #2C3E50; }"
    )
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
