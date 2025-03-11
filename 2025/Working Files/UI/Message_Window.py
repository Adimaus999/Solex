from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow, QLabel
from PyQt6.QtCore import QTimer

class MessageWindow(QMainWindow):
    def __init__(self, message, parent_window):
        super().__init__()
        print("Initializing MessageWindow")  # Debug print statement
        uic.loadUi("Message.ui", self)  # Ensure the Message.ui file is in the correct location
        self.message_label = self.findChild(QLabel, 'label_3')  # Ensure the QLabel is named 'label_3' in the .ui file
        if self.message_label:
            print(f"Setting message: {message}")  # Debug print statement
            self.message_label.setText(message)
        else:
            print("QLabel 'label_3' not found in Message.ui")
        self.parent_window = parent_window
        QTimer.singleShot(10000, self.close_message_window)  # Close the window after 10 seconds

    def close_message_window(self):
        print("Closing MessageWindow")  # Debug print statement
        self.close()
        self.parent_window.show()
