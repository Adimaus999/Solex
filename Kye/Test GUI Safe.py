from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QDial, QLabel, QProgressBar, QPushButton, QTextEdit
from PyQt6.QtCore import QTimer
import sys
import socket
import signal
from datetime import datetime

class SecondWindow(QMainWindow):
    def __init__(self, main_window, battery_charge, battery_error, battery_status, rpm, current, voltage, temperature, throttle_position, solar_current, solar_voltage, solar_power, latitude, longitude, speed, acceleration, range_, remaining):
        super().__init__()
        self.main_window = main_window
        uic.loadUi("Diagnostics Panel.ui", self)  # Load the second UI file

        # Find and set the QTextEdit widgets
        self.set_text_edit('textEdit', battery_charge)
        self.set_text_edit('textEdit_3', battery_error)
        self.set_text_edit('textEdit_2', rpm)
        self.set_text_edit('textEdit_4', current)
        self.set_text_edit('textEdit_5', voltage)
        self.set_text_edit('textEdit_6', temperature)
        self.set_text_edit('textEdit_7', throttle_position)
        self.set_text_edit('textEdit_8', solar_current)
        self.set_text_edit('textEdit_9', solar_voltage)
        self.set_text_edit('textEdit_10', solar_power)
        self.set_text_edit('textEdit_11', latitude)
        self.set_text_edit('textEdit_12', longitude)
        self.set_text_edit('textEdit_13', speed)
        self.set_text_edit('textEdit_14', acceleration)
        self.set_text_edit('textEdit_15', range_)
        self.set_text_edit('textEdit_16', remaining)

        # Update button colors based on battery status
        self.update_button_colors(battery_status)

        # Find the QPushButton widget for returning to the main window
        self.pushButton_5 = self.findChild(QPushButton, 'pushButton_5')
        if self.pushButton_5 is None:
            print("QPushButton_5 not found!")
        else:
            print("QPushButton_5 found!")
            self.pushButton_5.clicked.connect(self.return_to_main_window)

    def set_text_edit(self, object_name, value):
        text_edit = self.findChild(QTextEdit, object_name)
        if text_edit is None:
            print(f"{object_name} not found!")
        else:
            print(f"{object_name} found!")
            text_edit.setPlainText(f"{value}")

    def update_button_colors(self, battery_status):
        print(f"Updating button colors for battery status: {battery_status}")
        pushButton_1 = self.findChild(QPushButton, 'pushButton')
        pushButton_2 = self.findChild(QPushButton, 'pushButton_2')
        pushButton_3 = self.findChild(QPushButton, 'pushButton_3')

        if pushButton_1 is None or pushButton_2 is None or pushButton_3 is None:
            print("One or more push buttons not found!")
            return

        if battery_status == "Charging":
            pushButton_1.setStyleSheet("background-color: rgb(0, 255, 16)")
            pushButton_2.setStyleSheet("background-color: rgb(128, 128, 128)")
            pushButton_3.setStyleSheet("background-color: rgb(128, 128, 128)")
        elif battery_status == "Equilibrium":
            pushButton_1.setStyleSheet("background-color: rgb(128, 128, 128)")
            pushButton_2.setStyleSheet("background-color: rgb(0, 255, 16)")
            pushButton_3.setStyleSheet("background-color: rgb(128, 128, 128)")
        elif battery_status == "Discharging":
            pushButton_1.setStyleSheet("background-color: rgb(128, 128, 128)")
            pushButton_2.setStyleSheet("background-color: rgb(128, 128, 128)")
            pushButton_3.setStyleSheet("background-color: rgb(0, 255, 16)")
        else:
            pushButton_1.setStyleSheet("background-color: rgb(128, 128, 128)")
            pushButton_2.setStyleSheet("background-color: rgb(128, 128, 128)")
            pushButton_3.setStyleSheet("background-color: rgb(128, 128, 128)")

        print(f"Battery status: {battery_status}, button colors updated")

    def return_to_main_window(self):
        self.hide()
        self.main_window.show()

class MyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("TestGUI.ui", self)  # Load the UI file

        # Find the QDial widget
        self.dial = self.findChild(QDial, 'dial')  # Replace 'dial' with the object name of your QDial in the .ui file
        if self.dial is None:
            print("QDial not found!")
        else:
            print("QDial found!")

        self.dial.setMaximum(20)  # Set the maximum value of the dial to 20

        # Initialize the Speed variable
        self.Speed = 10

        # Set the initial value of the dial to the Speed value
        self.dial.setValue(self.Speed)

        # Find the QLabel widget for Speed
        self.label = self.findChild(QLabel, 'label_20')  # Replace 'label_20' with the object name of your QLabel in the .ui file
        if self.label is None:
            print("QLabel not found!")
        else:
            print("QLabel found!")

        # Update the label to show the initial Speed value
        self.label.setText(f"{self.Speed} km/h")

        # Connect the dial's valueChanged signal to a slot
        self.dial.valueChanged.connect(self.update_speed)
        print("Connected valueChanged signal to update_speed slot")

        # Find the QProgressBar widget
        self.progressBar = self.findChild(QProgressBar, 'progressBar')  # Replace 'progressBar' with the object name of your QProgressBar in the .ui file
        if self.progressBar is None:
            print("QProgressBar not found!")
        else:
            print("QProgressBar found!")

        self.progressBar.setMaximum(100)  # Set the maximum value of the progress bar to 100

        # Initialize the BatteryCharge variable
        self.BatteryCharge = 69

        # Set the initial value of the progress bar to the BatteryCharge value
        self.progressBar.setValue(self.BatteryCharge)

        # Initialize the Range variable
        self.Range = 69

        # Find the QLabel widget for Range
        self.range_label = self.findChild(QLabel, 'label_2')  # Replace 'label_2' with the object name of your QLabel in the .ui file
        if self.range_label is None:
            print("Range QLabel not found!")
        else:
            print("Range QLabel found!")

        # Update the label to show the initial Range value
        self.range_label.setText(f"{self.Range} km")

        # Initialize the Remaining variable
        self.Remaining = 69

        # Find the QLabel widget for Remaining
        self.remaining_label = self.findChild(QLabel, 'label_19')  # Replace 'label_19' with the object name of your QLabel in the .ui file
        if self.remaining_label is None:
            print("Remaining QLabel not found!")
        else:
            print("Remaining QLabel found!")

        # Update the label to show the initial Remaining value
        self.remaining_label.setText(f"{self.Remaining} km")

        # Initialize the BatteryError variable
        self.BatteryError = "No Error"

        # Initialize the BatteryStatus variable
        self.BatteryStatus = "Charging"  # Example status, you can change this as needed

        # Initialize the RPM variable
        self.RPM = 3000  # Example value, you can change this as needed

        # Initialize the Current variable
        self.Current = 50  # Example value, you can change this as needed

        # Initialize the Voltage variable
        self.Voltage = 12.5  # Example value, you can change this as needed

        # Initialize the Temperature variable
        self.Temperature = 25  # Example value, you can change this as needed

        # Initialize the Throttle Position variable
        self.ThrottlePosition = 75  # Example value, you can change this as needed

        # Initialize the SolarCurrent variable
        self.SolarCurrent = 10  # Example value, you can change this as needed

        # Initialize the SolarVoltage variable
        self.SolarVoltage = 18.5  # Example value, you can change this as needed

        # Initialize the SolarPower variable
        self.SolarPower = 185  # Example value, you can change this as needed

        # Initialize the Latitude variable
        self.Latitude = 51  # Example value, you can change this as needed

        # Initialize the Longitude variable
        self.Longitude = -1  # Example value, you can change this as needed

        # Initialize the Acceleration variable
        self.Acceleration = 3.5  # Example value, you can change this as needed

        # Find the QPushButton widget
        self.pushButton = self.findChild(QPushButton, 'pushButton')  # Replace 'pushButton' with the object name of your QPushButton in the .ui file
        if self.pushButton is None:
            print("QPushButton not found!")
        else:
            print("QPushButton found!")

        # Connect the button's clicked signal to a slot
        self.pushButton.clicked.connect(self.open_second_window)
        print("Connected clicked signal to open_second_window slot")

        # Set up a QTimer to send latitude and longitude to OpenCPN periodically
        self.timer = QTimer(self)
        self.timer.timeout.connect(lambda: self.send_to_opencpn(self.Latitude, self.Longitude))
        self.timer.start(1000)  # Send data every 1000 milliseconds (1 second)
        print("QTimer started to send latitude and longitude every 1 second")

    def update_speed(self, value):
        self.Speed = value
        print(f"Updating label to: {self.Speed} km/h")
        self.label.setText(f"{self.Speed} km/h")
        print(f"Speed is now: {self.Speed}")

    def open_second_window(self):
        battery_charge = self.BatteryCharge  # Pass the BatteryCharge value
        battery_error = self.BatteryError  # Pass the BatteryError value
        battery_status = self.BatteryStatus  # Pass the BatteryStatus value
        rpm = self.RPM  # Pass the RPM value
        current = self.Current  # Pass the Current value
        voltage = self.Voltage  # Pass the Voltage value
        temperature = self.Temperature  # Pass the Temperature value
        throttle_position = self.ThrottlePosition  # Pass the Throttle Position value
        solar_current = self.SolarCurrent  # Pass the SolarCurrent value
        solar_voltage = self.SolarVoltage  # Pass the SolarVoltage value
        solar_power = self.SolarPower  # Pass the SolarPower value
        latitude = self.Latitude  # Pass the Latitude value
        longitude = self.Longitude  # Pass the Longitude value
        speed = self.Speed  # Pass the Speed value
        acceleration = self.Acceleration  # Pass the Acceleration value
        range_ = self.Range  # Pass the Range value
        remaining = self.Remaining  # Pass the Remaining value
        self.second_window = SecondWindow(self, battery_charge, battery_error, battery_status, rpm, current, voltage, temperature, throttle_position, solar_current, solar_voltage, solar_power, latitude, longitude, speed, acceleration, range_, remaining)
        self.second_window.show()
        self.hide()
        print("Opened second window")

    def send_to_opencpn(self, latitude, longitude):
        print(f"Sending latitude: {latitude}, longitude: {longitude} to OpenCPN")
        # Format latitude and longitude into NMEA sentences
        nmea_lat = self.format_nmea_latitude(latitude)
        nmea_lon = self.format_nmea_longitude(longitude)
        time_str = datetime.utcnow().strftime("%H%M%S.00")
        nmea_sentence = f"GPGLL,{nmea_lat},{nmea_lon},{time_str},A"
        checksum = self.calculate_checksum(nmea_sentence)
        nmea_sentence = f"${nmea_sentence}*{checksum}\r\n"

        # Send NMEA sentence to OpenCPN via UDP
        udp_ip = "127.0.0.1"  # OpenCPN IP address
        udp_port = 10110  # OpenCPN UDP port
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(nmea_sentence.encode(), (udp_ip, udp_port))
            print(f"Sent NMEA sentence to OpenCPN: {nmea_sentence}")
        except Exception as e:
            print(f"Failed to send NMEA sentence: {e}")

    def format_nmea_latitude(self, latitude):
        degrees = int(latitude)
        minutes = (latitude - degrees) * 60
        direction = 'N' if latitude >= 0 else 'S'
        return f"{abs(degrees):02d}{abs(minutes):07.4f},{direction}"

    def format_nmea_longitude(self, longitude):
        degrees = int(longitude)
        minutes = (longitude - degrees) * 60
        direction = 'E' if longitude >= 0 else 'W'
        return f"{abs(degrees):03d}{abs(minutes):07.4f},{direction}"

    def calculate_checksum(self, sentence):
        checksum = 0
        for char in sentence:
            checksum ^= ord(char)
        return f"{checksum:02X}"

def signal_handler(sig, frame):
    print("Exiting...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    app = QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec())