import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt6 import uic  # ✅ Correct way to load .ui file in PyQt6

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("Main_Window.ui", self)  # ✅ Load UI file dynamically

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
