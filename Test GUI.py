import sys
import os
from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QLCDNumber  # Ensure QWidget is imported

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Load the .ui file
        uic.loadUi("TestGUI.ui", self)

        # Find the label by its object name (make sure the object name in Qt Designer is 'label')
        self.lcdNumber = self.findChild(QLCDNumber, "lcdNumber")  # Updated to QLabel

        # Variable to display
        distance_remaining = 50  # This is the variable holding the value to display
        
        # Update the label text
        if self.lcdNumber:
            self.lcdNumber.display(distance_remaining)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()  # Display the window
    sys.exit(app.exec())  # Start the application event loop
