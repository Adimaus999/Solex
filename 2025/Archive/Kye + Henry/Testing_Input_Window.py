# Import necessary modules
import time
import numpy as np
import os
import requests
import datetime
from datetime import datetime
from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QDial, QLabel, QProgressBar, QPushButton, QTextEdit, QWidget, QVBoxLayout, QSizePolicy, QLineEdit
from PyQt6.QtCore import QTimer, QUrl, QMetaObject, Qt, Q_ARG, QEvent, QObject
from PyQt6.QtWebEngineWidgets import QWebEngineView
import pyqtgraph as pg
from collections import deque
import sys
import socket
import signal
import threading
from MessageWindow import MessageWindow  # Ensure the MessageWindow class is imported
import subprocess
import logging

logging.basicConfig(level=logging.DEBUG)

ADAFRUIT_AIO_USERNAME = "kyebarwell"
ADAFRUIT_AIO_KEY = "aio_tqjd74FoxeVXDrFdzCIij5wqJ6Kf"
ADAFRUIT_FEED_KEY = "battery-soc"
ADAFRUIT_FEED_KEYS = {
    "battery": "battery-soc",
    "speed": "speed",
    "range": "range",
    "range_fast": "range-fast",
    "range_slow": "range-slow",
    "map": "map"
}

class RemainingWindow(QMainWindow):
    def __init__(self, main_window):
        super().__init__()
        try:
            uic.loadUi("Remaining.ui", self)  # Load the Remaining UI file
        except Exception as e:
            logging.error(f"Failed to load Remaining.ui: {e}")
            raise
        self.main_window = main_window

        # Set the window modality to application modal
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Find the QLineEdit widget for inputting the new Remaining value
        self.remaining_input = self.findChild(QLineEdit, 'lineEdit')
        assert self.remaining_input is not None, "QLineEdit for remaining input not found!"
        self.remaining_input.returnPressed.connect(self.update_remaining)

        # Find the QPushButton widget for returning to the main window
        self.pushButton = self.findChild(QPushButton, 'pushButton')
        assert self.pushButton is not None, "QPushButton not found!"
        self.pushButton.clicked.connect(self.return_to_main_window)

    def showEvent(self, event):
        super().showEvent(event)
        if self.remaining_input is not None:
            self.remaining_input.setFocus()
            self.open_osk()

    def open_osk(self):
        try:
            os.system('start osk')
            logging.info("On-screen keyboard opened")
        except OSError as e:
            logging.error(f"OS error: {e}")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")

    def close_osk(self):
        try:
            os.system('taskkill /IM osk.exe /F')
            logging.info("On-screen keyboard closed")
        except OSError as e:
            logging.error(f"OS error: {e}")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")

    def update_remaining(self):
        if self.remaining_input is not None:
            try:
                new_remaining = int(self.remaining_input.text())
                assert new_remaining >= 0, "Remaining value cannot be negative"
                self.main_window.Remaining = new_remaining
                self.main_window.remaining_label.setText(f"{self.main_window.Remaining} km")
                self.main_window.update_label_21_color()
                logging.info(f"Remaining updated to: {self.main_window.Remaining}")
                self.close_osk()
                self.close()
                self.main_window.show()
            except ValueError:
                logging.info("Invalid input for Remaining")
            except AssertionError as e:
                logging.error(f"Assertion error: {e}")

    def return_to_main_window(self):
        self.close()
        self.main_window.show()

# Commit restart
class BatteryTimePlotWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        try:
            uic.loadUi("BatteryTimePlot.ui", self)  # Load the BatteryTimePlot UI file
        except Exception as e:
            logging.error(f"Failed to load BatteryTimePlot.ui: {e}")
            raise
        self.plot_widget = self.findChild(QWidget, 'widget')
        self.plot_layout = QVBoxLayout(self.plot_widget)
        self.plot = pg.PlotWidget()
        self.plot_layout.addWidget(self.plot)
        self.plot.setLabel('left', 'Battery Charge')
        self.plot.setLabel('bottom', 'Time (seconds)')
        self.plot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.plot_widget.setLayout(self.plot_layout)
        self.data = deque(maxlen=200)
        self.start_time = datetime.now()  # Store the start time
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(1000)  # Update every second

    def update_plot(self):
        try:
            logging.debug("update_plot called")
            self.plot.clear()
            if self.data:
                logging.debug(f"Data in deque: {self.data}")
                elapsed_times = [(x[1] - self.start_time).total_seconds() for x in self.data]
                charges = [x[0] for x in self.data]
                logging.debug(f"Elapsed times: {elapsed_times}")
                logging.debug(f"Charges: {charges}")
                self.plot.plot(elapsed_times, charges, pen=pg.mkPen(color='w', width=2))
        except Exception as e:
            logging.error(f"Error updating plot: {e}")

class MapWindow(QMainWindow):
    def __init__(self, latitude, longitude, main_window, second_window):
        super().__init__()
        try:
            uic.loadUi("Map.ui", self)  # Load the map UI file
        except Exception as e:
            logging.error(f"Failed to load Map.ui: {e}")
            raise
        self.latitude = latitude
        self.longitude = longitude
        self.main_window = main_window
        self.second_window = second_window
        self.webView = self.findChild(QWebEngineView, 'webView')
        self.webView.setUrl(QUrl("http://localhost:8000/map.html"))
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_location)
        self.timer.start(2000)  # Update every 2 seconds
        self.update_location()

        # Find the QPushButton widget for returning to the main window
        self.pushButton = self.findChild(QPushButton, 'pushButton')
        assert self.pushButton is not None, "QPushButton not found!"
        self.pushButton.clicked.connect(self.return_to_main_window)

        # Find the QPushButton widget for opening the diagnostics panel
        self.pushButton_2 = self.findChild(QPushButton, 'pushButton_2')
        assert self.pushButton_2 is not None, "QPushButton_2 not found!"
        self.pushButton_2.clicked.connect(self.open_diagnostics_panel)

    def update_location(self):
        try:
            script = f"updateMap({self.latitude}, {self.longitude});"
            self.webView.page().runJavaScript(script)
        except Exception as e:
            logging.error(f"Error updating location: {e}")

    def return_to_main_window(self):
        try:
            self.hide()
            self.main_window.show()
        except Exception as e:
            logging.error(f"Error returning to main window: {e}")

    def open_diagnostics_panel(self):
        try:
            self.hide()
            self.second_window.show()
        except Exception as e:
            logging.error(f"Error opening diagnostics panel: {e}")

class SecondWindow(QMainWindow):
    def __init__(self, main_window, battery_charge, battery_error, battery_status, motor_current, motor_voltage, temperature, auxilliary_voltage, solar_current, solar_voltage, solar_power, latitude, longitude, speed, acceleration, range_, remaining, motor_power, auxilliary_power, auxilliary_current, range_slow, range_fast, battery_time_plot_window):
        super().__init__()
        self.main_window = main_window
        self.battery_time_plot_window = battery_time_plot_window  # Store the passed instance
        try:
            uic.loadUi("Diagnostics Panel.ui", self)  # Load the second UI file
            logging.info("Second window initialized")
        except Exception as e:
            logging.error(f"Failed to load Diagnostics Panel.ui: {e}")

        # Find and set the QTextEdit widgets
        self.set_text_edit('textEdit', battery_charge)
        self.set_text_edit('textEdit_3', battery_error)
        self.set_text_edit('textEdit_4', motor_current)
        self.set_text_edit('textEdit_5', motor_voltage)
        self.set_text_edit('textEdit_6', temperature)
        self.set_text_edit('textEdit_7', auxilliary_voltage)
        self.set_text_edit('textEdit_8', solar_current)
        self.set_text_edit('textEdit_9', solar_voltage)
        self.set_text_edit('textEdit_10', solar_power)
        self.set_text_edit('textEdit_11', latitude)
        self.set_text_edit('textEdit_12', longitude)
        self.set_text_edit('textEdit_13', speed)
        self.set_text_edit('textEdit_14', acceleration)
        self.set_text_edit('textEdit_15', range_)
        self.set_text_edit('textEdit_16', remaining)
        self.set_text_edit('textEdit_17', motor_power)
        self.set_text_edit('textEdit_18', auxilliary_power)
        self.set_text_edit('textEdit_19', auxilliary_current)
        self.set_text_edit('textEdit_20', range_slow)
        self.set_text_edit('textEdit_21', range_fast)
        
        # Update button colors based on battery status
        self.update_button_colors(battery_status)

        # Find the QPushButton widget for returning to the main window
        self.pushButton_5 = self.findChild(QPushButton, 'pushButton_5')
        assert self.pushButton_5 is not None, "QPushButton_5 not found!"
        self.pushButton_5.clicked.connect(self.return_to_main_window)

        # Find the QPushButton widget for opening the map window
        self.pushButton_4 = self.findChild(QPushButton, 'pushButton_4')
        assert self.pushButton_4 is not None, "QPushButton_4 not found!"
        self.pushButton_4.clicked.connect(self.open_map_window)

        # Find the QPushButton widget for opening the battery time plot window
        self.pushButton_6 = self.findChild(QPushButton, 'pushButton_6')
        assert self.pushButton_6 is not None, "QPushButton_6 not found!"
        self.pushButton_6.clicked.connect(self.open_battery_time_plot)

    def open_battery_time_plot(self):
        try:
            self.battery_time_plot_window.show()
        except Exception as e:
            logging.error(f"Error opening battery time plot: {e}")

    def set_text_edit(self, object_name, value):
        try:
            text_edit = self.findChild(QTextEdit, object_name)
            assert text_edit is not None, f"{object_name} not found!"
            text_edit.setPlainText(f"{value}")
        except Exception as e:
            logging.error(f"Error setting text edit {object_name}: {e}")

    def update_button_colors(self, battery_status):
        try:
            logging.info(f"Updating button colors for battery status: {battery_status}")
            pushButton_1 = self.findChild(QPushButton, 'pushButton')
            pushButton_2 = self.findChild(QPushButton, 'pushButton_2')
            pushButton_3 = self.findChild(QPushButton, 'pushButton_3')

            assert pushButton_1 is not None and pushButton_2 is not None and pushButton_3 is not None, "One or more push buttons not found!"

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

            logging.info(f"Battery status: {battery_status}, button colors updated")
        except Exception as e:
            logging.error(f"Error updating button colors: {e}")

    def return_to_main_window(self):
        try:
            self.hide()
            self.main_window.show()
        except Exception as e:
            logging.error(f"Error returning to main window: {e}")

    def open_map_window(self):
        try:
            latitude = self.findChild(QTextEdit, 'textEdit_11').toPlainText()
            longitude = self.findChild(QTextEdit, 'textEdit_12').toPlainText()
            self.map_window = MapWindow(latitude, longitude, self.main_window, self)
            self.map_window.show()
            self.hide()  # Hide the second window
            logging.info("Opened map window")
        except Exception as e:
            logging.error(f"Failed to open map window: {e}")

class ShowMessageEvent(QEvent):
    def __init__(self, message):
        super().__init__(QEvent.Type(QEvent.registerEventType()))
        self.message = message

class MyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.lock = threading.Lock()
        try:
            uic.loadUi("TestGUI.ui", self)  # Load the UI file
        except Exception as e:
            logging.error(f"Failed to load TestGUI.ui: {e}")
            raise

        # Find the QDial widget
        self.dial = self.findChild(QDial, 'dial') 
        assert self.dial is not None, "QDial not found!"
        self.dial.setMaximum(20)  # Set the maximum value of the dial to 20

        # Initialize the Speed variable
        self.Speed = 0

        # Set the initial value of the dial to the Speed value
        self.dial.setValue(self.Speed)

        # Find the QLabel widget for Speed
        self.label = self.findChild(QLabel, 'label_20')  
        assert self.label is not None, "QLabel not found!"
        self.label.setText(f"{self.Speed} km/h")

        # Update the label to show the initial Speed value
        self.label.setText(f"{self.Speed} km/h")

        # Connect the dial's valueChanged signal to a slot
        self.dial.valueChanged.connect(self.update_speed)
        logging.info("Connected valueChanged signal to update_speed slot")

        # Find the QProgressBar widget
        self.progressBar = self.findChild(QProgressBar, 'progressBar')  
        assert self.progressBar is not None, "QProgressBar not found!"
        self.progressBar.setMaximum(100)  # Set the maximum value of the progress bar to 100

         # Find the QPushButton widget for opening the Remaining window
        self.pushButton_2 = self.findChild(QPushButton, 'pushButton_2')
        if self.pushButton_2 is None:
            print("QPushButton_2 not found!")
        else:
            print("QPushButton_2 found!")
            self.pushButton_2.clicked.connect(self.open_remaining_window)

        self.progressBar.setMaximum(100)  # Set the maximum value of the progress bar to 100

        # Initialize the BatteryCharge variable
        self.BatteryCharge = 0
        self.progressBar.setValue(self.BatteryCharge)

        # Initialize the Range variable
        self.Range = 0
        logging.info(f"Initial Range: {self.Range}")

        # Initialize the Remaining variable
        self.Remaining = 0
        logging.info(f"Initial Remaining: {self.Remaining}")

        # Find the QLabel widget for Range
        self.range_label = self.findChild(QLabel, 'label_2')  
        assert self.range_label is not None, "Range QLabel not found!"
        self.range_label.setText(f"{self.Range} km")

        # Find the QLabel widget for Remaining
        self.remaining_label = self.findChild(QLabel, 'label_19')  
        assert self.remaining_label is not None, "Remaining QLabel not found!"
        self.remaining_label.setText(f"{self.Remaining} km")

        self.battery_time_plot_window = BatteryTimePlotWindow()

        # Update the label to show the initial Remaining value
        self.remaining_label.setText(f"{self.Remaining} km")

        # Update the label to show the initial Remaining value
        self.range_label.setText(f"{self.Range} km")

        # Initialize the BatteryError variable
        self.BatteryError = "No Error"

        # Initialize the BatteryStatus variable
        self.BatteryStatus = "Discharging"  # Example status, you can change this as needed

        # Initialize the Current variable
        self.MotorCurrent = 0  # Example value, you can change this as needed

        # Initialize the Voltage variable
        self.MotorVoltage = 0  # Example value, you can change this as needed

        # Initialize the Temperature variable
        self.Temperature = 0  # Example value, you can change this as needed

        # Initialize the Throttle Position variable
        self.AuxilliaryVoltage = 0  # Example value, you can change this as needed

        # Initialize the SolarCurrent variable
        self.SolarCurrent = 0  # Example value, you can change this as needed

        # Initialize the SolarVoltage variable
        self.SolarVoltage = 0  # Example value, you can change this as needed

        # Initialize the SolarPower variable
        self.SolarPower = 0  # Example value, you can change this as needed

        # Initialize the Latitude variable
        self.Latitude = 0  # Example value, you can change this as needed

        # Initialize the Longitude variable
        self.Longitude = 0  # Example value, you can change this as needed

        # Initialize the Acceleration variable
        self.Acceleration = 0  # Example value, you can change this as needed

        # Initialize the Motor Power variable
        self.MotorPower = 0  # Example value, you can change this as needed

        # Initialize the Auxilliary Power variable
        self.AuxilliaryPower = 0  # Example value, you can change this as needed

        # Initialize the Auxilliary Current variable
        self.AuxilliaryCurrent = 0  # Example value, you can change this as needed

        # Initialize the Range Slow variable
        self.RangeSlow = 0  # Example value, you can change this as needed

        # Initialize the Range Fast variable
        self.RangeFast = 0  # Example value, you can change this as needed

        # Find the QLabel widget for label_21
        self.label_21 = self.findChild(QLabel, 'label_21')  
        if self.label_21 is None:
            print("QLabel label_21 not found!")
        else:
            print("QLabel label_21 found!")
            # Update the color of label_21 based on the comparison between range_ and remaining
            self.update_label_21_color()

        # Find the QPushButton widget
        self.pushButton = self.findChild(QPushButton, 'pushButton')  
        assert self.pushButton is not None, "QPushButton not found!"
        self.pushButton.clicked.connect(self.open_second_window)
        logging.info("Connected clicked signal to open_second_window slot")

        # Connect the button's clicked signal to a slot
        self.pushButton.clicked.connect(self.open_second_window)
        print("Connected clicked signal to open_second_window slot")

        # Set up a QTimer to send latitude and longitude to OpenCPN periodically
        self.timer = QTimer(self)
        self.timer.timeout.connect(lambda: self.send_to_opencpn(self.Latitude, self.Longitude, self.Speed))
        self.timer.start(5000)  # Send data every 5000 milliseconds (5 seconds)
        logging.info("QTimer started to send latitude and longitude every 5 seconds")

        # Set up a QTimer to send BatteryCharge to Adafruit every 5 seconds
        self.adafruit_timer = QTimer(self)
        self.adafruit_timer.timeout.connect(self.send_to_adafruit)
        self.adafruit_timer.start(20000)  # Send data every 20000 milliseconds (20 seconds)
        logging.info("QTimer started to send data to Adafruit every 20 seconds")

        # Start the UDP server in a separate thread
        self.server_thread = threading.Thread(target=self.start_udp_server)
        self.server_thread.daemon = True  # Makes sure the server stops when the program ends
        self.server_thread.start()
        logging.info("UDP server started")

        self.open_remaining_window()

    def customEvent(self, event):
        if isinstance(event, ShowMessageEvent):
            self.show_message_window(event.message)

    def update_speed(self, value):
        try:
            self.Speed = value
            logging.info(f"Updating label to: {self.Speed} km/h")
            self.label.setText(f"{self.Speed} km/h")
            logging.info(f"Speed is now: {self.Speed}")
        except Exception as e:
            logging.error(f"Error updating speed: {e}")

    def update_label_21_color(self):
        if self.label_21 is not None:
            logging.info(f"Updating label_21 color: Range = {self.Range}, Remaining = {self.Remaining}")
            if self.Range > self.Remaining:
                self.label_21.setStyleSheet("background-color: rgb(0, 255, 16); color: black;")
                logging.info("label_21 color set to green")
            else:
                self.label_21.setStyleSheet("background-color: rgb(255, 0, 0); color: black;")
                logging.info("label_21 color set to red")

    def open_remaining_window(self):
        self.remaining_window = RemainingWindow(self)
        self.remaining_window.show()
        self.hide()

    def open_second_window(self):
        battery_charge = self.BatteryCharge  # Pass the BatteryCharge value
        battery_error = self.BatteryError  # Pass the BatteryError value
        battery_status = self.BatteryStatus  # Pass the BatteryStatus value
        motor_current = self.MotorCurrent  # Pass the Current value
        motor_voltage = self.MotorVoltage  # Pass the Voltage value
        temperature = self.Temperature  # Pass the Temperature value
        auxilliary_voltage = self.AuxilliaryVoltage  # Pass the Throttle Position value
        solar_current = self.SolarCurrent  # Pass the SolarCurrent value
        solar_voltage = self.SolarVoltage  # Pass the SolarVoltage value
        solar_power = self.SolarPower  # Pass the SolarPower value
        latitude = self.Latitude  # Pass the Latitude value
        longitude = self.Longitude  # Pass the Longitude value
        speed = self.Speed  # Pass the Speed value
        acceleration = self.Acceleration  # Pass the Acceleration value
        range_ = self.Range  # Pass the Range value
        remaining = self.Remaining  # Pass the Remaining value
        motor_power = self.MotorPower  # Pass the Motor Power value
        auxilliary_power = self.AuxilliaryPower  # Pass the Motor Power value
        auxilliary_current = self.AuxilliaryCurrent # Pass the Auxilliary Current value
        range_slow = self.RangeSlow # Pass the Range Slow value
        range_fast = self.RangeFast # Pass the Range Fast value
        self.second_window = SecondWindow(self, battery_charge, battery_error, battery_status, motor_current, motor_voltage, temperature, auxilliary_voltage, solar_current, solar_voltage, solar_power, latitude, longitude, speed, acceleration, range_, remaining, motor_power, auxilliary_power, auxilliary_current, range_slow, range_fast, self.battery_time_plot_window)
        self.second_window.show()
        self.hide()
        self.update_label_21_color()  # Update the color when opening the second window
        logging.info("Opened second window")

    def send_to_opencpn(self, latitude, longitude, speed):
        logging.info(f"Sending latitude: {latitude}, longitude: {longitude}, speed: {speed} to OpenCPN")
        # Format latitude and longitude into NMEA sentences
        try:
            nmea_lat = self.format_nmea_latitude(latitude)
            nmea_lon = self.format_nmea_longitude(longitude)
            time_str = datetime.utcnow().strftime("%H%M%S.00")
            nmea_sentence = f"GPGLL,{nmea_lat},{nmea_lon},{time_str},A"
            checksum = self.calculate_checksum(nmea_sentence)
            nmea_sentence = f"${nmea_sentence}*{checksum}\r\n"
        except Exception as e:
            logging.error(f"Error formatting NMEA sentence: {e}")
            return

        # Send NMEA sentence to OpenCPN via UDP
        udp_ip = "100.69.35.41"  # OpenCPN IP address
        udp_port = 10110  # OpenCPN UDP port
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(nmea_sentence.encode(), (udp_ip, udp_port))
            logging.info(f"Sent NMEA sentence to OpenCPN: {nmea_sentence}")
        except Exception as e:
            logging.error(f"Failed to send NMEA sentence: {e}")

        # Format speed into NMEA sentence
        try:
            nmea_speed = f"GPVTG,,T,,M,{speed:.2f},N,,K"
            checksum = self.calculate_checksum(nmea_speed)
            nmea_speed_sentence = f"${nmea_speed}*{checksum}\r\n"
        except Exception as e:
            logging.error(f"Error formatting NMEA speed sentence: {e}")
            return

        try:
            sock.sendto(nmea_speed_sentence.encode(), (udp_ip, udp_port))
            logging.info(f"Sent NMEA speed sentence to OpenCPN: {nmea_speed_sentence}")
        except Exception as e:
            logging.error(f"Failed to send NMEA speed sentence: {e}")

    def send_to_adafruit(self):
        with self.lock:
            data_points = {
                "battery": self.BatteryCharge,
                "speed": self.Speed,
                "range": self.Range,
                "range_fast": self.RangeFast,
                "range_slow": self.RangeSlow,
                "map": f"{self.Latitude},{self.Longitude}"
            }
        
            # Send regular data points
            for key, value in data_points.items():
                url = f"https://io.adafruit.com/api/v2/{ADAFRUIT_AIO_USERNAME}/feeds/{ADAFRUIT_FEED_KEYS.get(key, key)}/data"
                headers = {
                    "X-AIO-Key": ADAFRUIT_AIO_KEY,
                    "Content-Type": "application/json"
                }
                data = {
                    "value": value
                }
                try:
                    response = requests.post(url, json=data, headers=headers)
                    if response.status_code == 200:
                        logging.info(f"Successfully sent {key} to Adafruit: {value}")
                    else:
                        logging.error(f"Failed to send {key} to Adafruit: {response.status_code}, {response.text}")
                except Exception as e:
                    logging.error(f"Error sending {key} to Adafruit: {e}")

            # Send location data
            location_data = {
                "value": self.Speed,
                "lat": self.Latitude,
                "lon": self.Longitude,
                "ele": 112
            }
            url = f"https://io.adafruit.com/api/v2/{ADAFRUIT_AIO_USERNAME}/feeds/{ADAFRUIT_FEED_KEYS['map']}/data"
            headers = {
                "X-AIO-Key": ADAFRUIT_AIO_KEY,
                "Content-Type": "application/json"
            }
            try:
                response = requests.post(url, json=location_data, headers=headers)
                if response.status_code == 200:
                    logging.info(f"Successfully sent location data to Adafruit: {location_data}")
                else:
                    logging.error(f"Failed to send location data to Adafruit: {response.status_code}, {response.text}")
            except Exception as e:
                logging.error(f"Error sending location data to Adafruit: {e}")

            # Update the battery time plot data
            try:
                logging.info(f"Appending data to plot: {self.BatteryCharge}, {datetime.now()}")
                self.battery_time_plot_window.data.append((self.BatteryCharge, datetime.now()))
                logging.info(f"Data appended to plot: {self.battery_time_plot_window.data}")
            except Exception as e:
                logging.error(f"Error updating battery time plot data: {e}")

    def format_nmea_latitude(self, latitude):
        try:
            degrees = int(latitude)
            minutes = (latitude - degrees) * 60
            direction = 'N' if latitude >= 0 else 'S'
            return f"{abs(degrees):02d}{abs(minutes):07.4f},{direction}"
        except Exception as e:
            logging.error(f"Error formatting NMEA latitude: {e}")
            return ""

    def format_nmea_longitude(self, longitude):
        try:
            degrees = int(longitude)
            minutes = (longitude - degrees) * 60
            direction = 'E' if longitude >= 0 else 'W'
            return f"{abs(degrees):03d}{abs(minutes):07.4f},{direction}"
        except Exception as e:
            logging.error(f"Error formatting NMEA longitude: {e}")
            return ""

    def calculate_checksum(self, sentence):
        try:
            checksum = 0
            for char in sentence:
                checksum ^= ord(char)
            return f"{checksum:02X}"
        except Exception as e:
            logging.error(f"Error calculating checksum: {e}")
            return "00"

    def start_udp_server(self):
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            udp_socket.bind(('0.0.0.0', 12345))  # Bind to all interfaces on port 12345
            logging.info("UDP server listening on port 12345")
        except Exception as e:
            logging.error(f"Error binding UDP socket: {e}")
            return

        while True:
            try:
                message, addr = udp_socket.recvfrom(1024)
                message = message.decode('utf-8')
                logging.info(f"Received message from {addr}: {message}")
                # Post a custom event to the main thread
                QApplication.postEvent(self, ShowMessageEvent(message))
            except Exception as e:
                logging.error(f"Error receiving message: {e}")

    def show_message_window(self, message):
        logging.info("Attempting to show MessageWindow")
        try:
            # Close any currently open UI
            self.hide()
            if hasattr(self, 'second_window') and self.second_window.isVisible():
                self.second_window.hide()
            if hasattr(self, 'map_window') and self.map_window.isVisible():
                self.map_window.hide()

            # Show the message window
            self.message_window = MessageWindow(message, self)
            self.message_window.show()
            logging.info("MessageWindow shown")
        except Exception as e:
            logging.error(f"Error showing MessageWindow: {e}")

def signal_handler(sig, frame):
    logging.info("Exiting...")
    sys.exit(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Start the local HTTP server in a separate thread to serve the HTML file
    def start_http_server():
        os.system('python -m http.server 8000')

    # Start the server in a separate thread
    server_thread = threading.Thread(target=start_http_server)
    server_thread.daemon = True  # Makes sure the server stops when the program ends
    server_thread.start()

    main_window = MyApp()
    main_window.show()
    sys.exit(app.exec())