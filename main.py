import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from app.gui.main_window import MainWindow


def main() -> None:
    # Must be set before QApplication is constructed
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("DropShare")
    app.setApplicationVersion("1.0.0")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
