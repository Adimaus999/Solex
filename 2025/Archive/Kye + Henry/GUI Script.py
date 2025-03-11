# Import necessary modules
import time
import sqlite3
import numpy as np
import pandas as pd
import xgboost as xgb
import os
from sklearn.model_selection import train_test_split
import multiprocessing
import psutil
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

        print('Initialised Variables')

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

# Set the working directory
#os.chdir("C:/Users/YourUsername/Documents/MyProject")

# A function to read the latest SQL database data based on a column named 'timestamp'.
def SQLread(sensor_id, db_path="sensors_log.db", table_name="sensor_data"):
    """
    Fucntion to extract most recent sensor data from an SQL database according to the timestamp column. The function 
    returns the sensor data sepcified according to the input 'sensor_id'. If there is any error, the function returns
    a nan.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = f"""
        SELECT value FROM {table_name} 
        WHERE sensor_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 1
        """
        
        cursor.execute(query, (sensor_id,))
        result = cursor.fetchone()

        conn.close()

        # Return nan if not found
        return result[0] if result and result[0] is not None else np.nan

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return np.nan  
    except Exception as e:
        print(f"Error: {e}")
        return np.nan

# A function to remove nosie from the sensor data inputs with a Kalman filter
def kalman_filter_update(dataField, dLabel: str, iteration, P, process_variance=5e-4,
                         measurement_variance=1): 
    """
    A function to filter/ remove noise from the input sensor data using a Kalman filter. 
    The dataframe is inputted containing all sensor data. dLabel allows the type of data to be 
    specified. P is regularly updated and represents the process variance. K, the Kalman gain is
    computed and the the difference between the 'prediction' and measured value is multiplied by the 
    gain to update the prediction.The new 'filtered' value is appended to the data frame and this is returned
    along with the updated process variance.
    """
    # if insufficient data is available, initialise predicted value and process variance such that the function works
    if (iteration == 0) or (iteration == 1):
         x_pred = 0
         P = 1
    else:
        x_pred = dataField[str(dLabel)].iat[-2] 
       
    # Follow Kalman filter steps to predict next sensor value    
    P_pred = P + process_variance
        
    K = P_pred / (P_pred + measurement_variance)
    x_est = x_pred + K * (dataField[str(dLabel)].iat[-1] - x_pred)  
    P = (1 - K) * P_pred 
        
    # Append filtered value to data frame
    dataField[str(dLabel)].iat[-1] = x_est
    
    return dataField, P  

# A fucntion to interpolate the next value, according to polynomial fitting
def interpolate_next_value(arDF, dLabel: str):
    
    """
    A fucntion to interpolate the next value of sensor data if the SQL query either 
    fails or returns an unexpected nan value. The function takes the data frame of sensor data and 
    a dLabel input which allows the user to specify the sensor value of interest. It converts this
    aray of data to a numpy array and extracts the 10 most recent values. A polynomial is fitted and
    the interpolated value is appended to the input data frame.
    """
    # Convert the dataframe column of interest to a numpy array
    arr = arDF[str(dLabel)].to_numpy()
    
    # Extract all valid values in most recent 10 data entries, if they exist
    valid_values = arr[~np.isnan(arr)][-10:]
    
    # If the first sensor reading is a nan, the function replaces this with a 0 reading
    if len(valid_values) < 1:
        next_value = 0 
    # If the second value is a nan, the function replaces this with the first value
    elif len(valid_values) < 2:
        next_value = valid_values[0]    
    # Otherwise the code performs interpolation
    else:
        x = np.arange(len(valid_values))
        y = valid_values
        coeffs = np.polyfit(x, y, 1)  
        next_x = len(valid_values) 
        next_value = np.polyval(coeffs, next_x)
    
    # Append the value to the input data frame
    arDF[str(dLabel)].iat[-1] = next_value
    
    return arDF

# Function to create a new, blank data frame to append new sensor readings to
# This can easily be converted to DMatrix format, which is required for machine learning applications
def newDataStruct():
    
    """
    Create a new, blank data frame ready to recieve data to train the ML models.
    """
    
    return pd.DataFrame({
        'speed': [],  
        'acceleration': [],  
        'motorCurrent': [],  
        'motorVoltage': [],  
        'batteryCurrent': [],
        'batteryVoltage': [],
        'batteryStateOfCharge': [],
        'batteryPowerConsumption': [],
        'motorPowerConsumption': [],
        'motorBasedPowerConsumption': [],
        'target': []
    })

# Function to insert a new row into the data frame. Each value is initialsed as a zero
def appendNewZeros(dataStructure):
    
    """
    Adds a new row of zeros to the data frame so that these zeros can be replaced with 
    sensor readings as the while loop code is executed.
    """
    
    newRow = {
        'speed': 0,  
        'acceleration': 0,  
        'motorCurrent': 0,  
        'motorVoltage': 0,  
        'batteryCurrent': 0,
        'batteryVoltage': 0,
        'batteryStateOfCharge': 0,
        'batteryPowerConsumption': 0,
        'motorPowerConsumption': 0,
        'motorBasedPowerConsumption': 0,
        'target': 0
    }
    dataStructure=dataStructure.append(newRow, ignore_index=True)
    return dataStructure
    
# Funciton to assign the number of cores to the retraining process to allow efficeint parallel computing
def assign_cores_to_retrain():
    """
    A Function to assign all but one core to the retraining procecss.
    """
    p = psutil.Process()
    # Retrive the number of cores in the CPU
    cores = psutil.cpu_count(logical=False)  
    # Assign all cores to retraining process but core '0'
    p.cpu_affinity(list(range(1, cores))) 

# Fucntion to either train a new machine learning model, or retrain an existing model
def train_or_retrain(dataStructure, model_path="xgboost_model.json", temp_model_path="xgboost_model_temp.json", test_size=0.2, random_state=42):
    """
    Recieves a data frame input of training data, and either trains a new XGBoost model (if one does not already exist) or retrais an existing model
    correctly identifying what data is new from the input data frame. The retrained model is temporarily saved under a differnt name to avoid issues of calling
    a model currently being retrained during lengthy processes. The input data frame must be a copy, so that its size does not change whilst retraining occurrs.
    The function uses a train/test spilt of 80/20 as a default. For optimal computation, the maximum depth of the decision trees is set to 4, and a histogram
    method is used. Early stopping rounds is initiated so that the perfromance of  a retraining process is evaluated after 50 rounds. If no further improvement
    is made through further training, the early stopping rounds initiates and prevents further operation, reducing computational load.
    """
    
    # Assign CPU cores for retraining by calling above function
    assign_cores_to_retrain()
    
    # Split features into X and y: x for the training input data, and y for the target data
    X = dataStructure.drop(columns=['target'])
    y = dataStructure['target']

    # Train-test split: separate trainig data into training set and testing set for the model to evaluate performance
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=test_size, random_state=random_state)

    # Convert data into XGBoost's DMatrix format
    dtrain = xgb.DMatrix(X_train, label=y_train)
    dval = xgb.DMatrix(X_val, label=y_val)
    
    #Set the number of cores available for the job in XGBoost's input parameters
    num_cores = multiprocessing.cpu_count()
    
    # Define XGBost input parameters
    params = {
        "objective": "reg:squarederror",  
        "learning_rate": 0.1,
        "max_depth": 4,  
        "eval_metric": "rmse",  
        "tree_method": "hist",  
        "n_jobs": max(1, num_cores - 1) 
    }

    # Initialise default number of training rounds
    num_rounds = 1000  
    # Set minimum number of rounds before early-stopping critera can apply
    early_stopping_rounds = 50  

    # If the model already exists, begin a retrianing process
    if os.path.exists(model_path):
        
        # Access existing model
        model = xgb.Booster()
        model.load_model(model_path) 

        # Save the model with a temporary path to avoid confusing th program when calling a model for predictions if it is currently being retrained
        model.save_model(temp_model_path)

        try:
            # Continue training with previous trees
            model = xgb.train(
                params,
                dtrain,
                num_boost_round=num_rounds,
                evals=[(dtrain, "train"), (dval, "val")],
                early_stopping_rounds=early_stopping_rounds,
                verbose_eval=0,
                xgb_model=model  # Load previous trees correctly
            )
            
            # After retraining, replace the original model with the newly trained model
            model.save_model(model_path)
    
        except:
            # If retraining fails, load the temporary model (no changes to the original)
            model.load_model(temp_model_path)
            
    else:
        # The model does not yet exist at the specified file path. Train a new model from scratch.
        model = xgb.train(
            params,
            dtrain,
            num_boost_round=num_rounds,
            evals=[(dtrain, "train"), (dval, "val")],
            early_stopping_rounds=early_stopping_rounds,
            verbose_eval=0
        )

        # Save the trained model
        model.save_model(model_path)
    
    # Delete the temporary file to remove clutter
    if os.path.exists(temp_model_path):
        os.remove(temp_model_path)

# A fucntion to call the training/ retraining process twice, once for the complex model for current speed predictions, and once for the simple ML model for alternative speed strategies
def multipleTrainingProcesses(dataStructure):
    """
    A funciton to be targetted in the multiprocessing part of the script. Calling this function intiates several train/ retrain processes.
    The input to this funciton is the data frame which the fucntion edits accordingly to create te DMatrix training data sets as required.
    """
    
    # Multi-parameter ML model, using all sensor data as input
    train_or_retrain(dataStructure, model_path="xgboost_model.json", temp_model_path="xgboost_model_temp.json")
    
    # Simple ML model for alternative speed strategies. Based on battery SOC and speed only, with power consumption as training target
    train_or_retrain(dataStructure[['speed', 'batteryStateOfCharge', 'target']], model_path="simple_xgboost_model.json", temp_model_path="simple_xgboost_model_temp.json")

# A function to use the XGBoost model to preidct power consumption of the boat at a set speed.
def predict_with_model(data, model_path="xgboost_model.json"):
   """
   A function to predict the power consumption of the boat at a given speed. Data can be the full data set of live sensor readings for the current speed
   range estimaate at a set time, or just the battery SOC and speed of interest if using the simple model for alternative speed strategies. The data input is in the form f a data frame. 
   Predicitons are made and returned as a single numerical value.
   """
   
   # If the model has not yet been trained as there is not yet enough data
   if not os.path.exists(model_path):
       # If the prediction of interest was the current speed range estimate
        if model_path == "xgboost_model.json":
            # Return the preduciton as the average of the motor-based and battery-based power consumptions
            predictions = (data['motorBasedPowerConsumption'].iat[-1] + data['batteryPowerConsumption'].iat[-1])/2
        else:
            # Else return predictions for power consumption as an unreasonably high number to make easily identifyable, very low, range estimates for slow and high speed strategies
            predictions = 9999999
   else:
    
        # Load the XGBoost model
        model = xgb.Booster()
        model.load_model(model_path)

        # Convert data into DMatrix format so that XGBoost can read it
        ddata = xgb.DMatrix(data)

        # Generate model predicitons
        predictions = model.predict(ddata)
        predictions = predictions.astype(int)

   return predictions

# A function to compute the average solar irradiaiton forecast for the next 6 hours of the race, given a latitude and longitude
def get_future_solar_irradiance_avg(lat, lon, hours=6):
    """
    Uses an API to access forecast solar irradiance (GHI) for the next 6 hours using OpenWeather's Solar Forecast and computes the average.
    """
    
    #Set API key for access to OpenWeather's system
    API_KEY = "ca82eee9df7c7c0474202f4863bbf88e"
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}"

    try:
        # Use the response module to send a URL respnse request
        response = requests.get(url)
        response.raise_for_status()  
        data = response.json()

        # Return 0 if there is an issue so that the range estimatio can still work ignoring solar charging
        if "list" not in data:
            print("Error: No forecast data available.")
            return 0

        ghi_values = []

        # Extract GHI forecasts for the next 6 hours
        for forecast in data["list"][:hours]:
            ghi = forecast.get("radiation", {}).get("ghi", 0)  # Get GHI, default to 0 if missing
            ghi_values.append(ghi)
            
        # Return 0 if there is an issue so that the range estimatio can still work ignoring solar charging
        if not ghi_values:
            print("Error: No GHI data found in forecast.")
            return 0
        
        # Compute average GHI forecast value
        avg_ghi = np.mean(ghi_values)
        return avg_ghi
    
    # Return 0 if there is an issue so that the range estimatio can still work ignoring solar charging
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return 0
    
# A function to compute a range estimate for the solar boat given a speed of interest and other power consumption data
def computeRange(speedOfInterest, consumptionRate, rangeEstArray):
    """
    A function to compute the range estimate for the solar boat. It computes the energy stored in the battery, and the expected solar charging rate
    over the remainder of the race. It looks at the speed of interest and the power consumption and calculates how long the charge is expected to 
    last, and at that speed, what range this equates to. An initial cmputation assuming no solarcharghing gives an initial estimate of time duration.
    Following this, solar charging is modelled with an iterative solver looking to reach an accepatable minimal difference between range estiamtes, 
    assuming cintinually longer charge durations, and hence longer time spent recieving solar charge.
    """
    
    # Import necessary varaibles from esewhere in the script to save on input arguments
    global dataStructure, batteryCapacity, avSolarIrr, solarEff, solarArea
    
    # Read battery state of charge from data frame of sensor data
    batteryStateOfCharge = dataStructure['batteryStateOfCharge'].iat[-1]
    
    # Convert speed of interest from kmh to m/s
    speedOfInterest = speedOfInterest*1000/3600 
    
    # Check for nan values in key parameters
    if any(np.isnan(val) for val in [speedOfInterest, consumptionRate, batteryStateOfCharge, avSolarIrr, solarEff, solarArea]):
        # If any values are nan, range cannot be computed. Hence, return existing range estimate array with no update. The code will use ;ast computed range estimate.
        return rangeEstArray  

    if consumptionRate == 0:  
        # Prevent division by zero and give an  unreaistically high number for the range, assuming the current speed is 0 (boat is stationary)
        return np.append(rangeEstArray, 9999)  

    # Initial estimate assumes no solar input
    # Soalr charge time is 0
    time = 0
    # Compute initial range estimate
    rangeEstInitial = (((batteryStateOfCharge * batteryCapacity) + (avSolarIrr * solarEff * solarArea * time)) * speedOfInterest) / consumptionRate

    # Recompute the time for solar charging
    time = rangeEstInitial / speedOfInterest
    # Compute an updated range estimate assuming solar charging
    newRangeEst = (((batteryStateOfCharge * batteryCapacity) + (avSolarIrr * solarEff * solarArea * time)) * speedOfInterest) / consumptionRate

    # Set up an iteration counter for the solver incacse of diverging range estimates
    iteration_count = 0
    # Prevent infinite looping
    max_iterations = 100  

    # Continue to re-evaluate the range estimate whilst the difference between outputs is greater than 400m and the iteration count is less than the maximum number of iterations
    while (abs(newRangeEst - rangeEstInitial)>0.4) and iteration_count < max_iterations:
        rangeEstInitial = newRangeEst
        time = rangeEstInitial / speedOfInterest
        newRangeEst = (((batteryStateOfCharge * batteryCapacity) + (avSolarIrr * solarEff * solarArea * time)) * speedOfInterest) / consumptionRate
        iteration_count += 1
    
    # Convert range estmate to km
    newRangeEst = newRangeEst/1000 
    # Append to array of range estimates
    rangeEstArray = np.append(rangeEstArray, newRangeEst)
  
    # Return the array of range estimates with the new update at the end
    return rangeEstArray

# Now the main scheduled script
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
    print('Reached')
    sys.exit(app.exec())  

    print('Moving on')
    
# Initialise variables    
    # Define target speed scenarios for range estimation
    # kmh
    slowSpeed = 5
    currentSpeed = 0
    highSpeed = 15
    # Define battery capacity and convert to Ws
    batteryCapacity = 1.4e3 * 3600
    # Define the area of solar pannels on the boat m2
    solarArea = 2 
    # Define an intial estimate for the solar efficiency
    initialSolarEfficiency = 0.2
    # Define the race length
    obj = MyApp()
    approxRaceLength = obj.Remaining #km
    # Define the refresh rate of the range estimation script
    interval = 5
    # Initialise the electrical system efficiency as 0, to be recomputed in the script
    electricalSystemEfficiency = 0
    # Initialie loop-based counts as 0
    count = 0
    iteration = 0
    # Initialise empty singal array
    newSignal = np.array([])
    # Initialie initial values as zero for Kalman filter process variance
    P1 = 0
    P2 = 0
    P3 = 0
    P4 = 0
    P5 = 0
    P6 = 0
    P7 = 0
    P8 = 0
    P9 = 0
    # Create the empty data frame for sensor data
    dataStructure = newDataStruct()
    # Crete a separate data frame for solar power data
    solarDataStructure = pd.DataFrame({
            'solarCurrent': [],  
            'solarVoltage': []
        })
    # Set a retraining rate for the ML of every 200 new data points
    retrainRate = 200
    # Set the intial training trigger to false, so retraining won't begin until 200 data points have been collected
    retraining_active = False
    retrain_process = None
    # initialse as false; incase retraining takes longer than 200 data points, this turns to TRUE and the code is set to retrain when ready
    retrainOnNextIteration = False
    # Get new solar foreacst updates every 15 minutes
    solarForecastTrigger = 15*60 // interval
    # Initialise the soalr pannel effiency estimate
    solarEff = initialSolarEfficiency
    
    # Set window for averaging of speed in verificaiton process (mins)
    verificationWindow = 3
    # Set intial range estiamtes to 0
    currentSpeedRange = np.array([0])
    slowSpeedRange = np.array([0])
    highSpeedRange= np.array([0])
        
    # For real-time checking of the ML outputs, set the range of discrete speeds to be checked against
    speedsRangeArray = np.arange(0.5,20.5,0.5)
    # Initialise the array to strore change in SOC per unit time at different speeds
    SOCrate = np.zeros(len(speedsRangeArray))
    # Initialise the array to store the number of instances of such speed in past boat operation
    SOCcount = np.zeros(len(speedsRangeArray))
    # Rangess array
    rangessArray = np.array([0])
    
    # Set the race start time (24-hour format: HH:MM)
    target_time = "13:17"

    # Convert target time to datetime format
    target_dt = datetime.strptime(target_time, "%H:%M").replace(
        year=datetime.now().year, 
        month=datetime.now().month, 
        day=datetime.now().day
        )

    # Wait until the target time is reached
    while datetime.now() < target_dt:
        # Check every second
        time.sleep(1) 
    
    # Begin infinite while loop when race starts (avoid logging pre-race data, not representative of boat's performance)
    while True:
        # Start the timer to ensure regular code execution
        startTime = time.time()
        
        # Check if retraining has finished and reset `retraining_active`
        if retraining_active and (retrain_process is None or not retrain_process.is_alive()):
            # If training/ retraining has finsihed, reset status to False
            retraining_active = False
        
        # Append a new row of zeros to the data frame
        dataStructure = appendNewZeros(dataStructure)
        
        # Append a new row of zeros to the solar power data frame
        newSolarZerosRow = {
            'solarCurrent': 0,  
            'solarVoltage': 0
        }
        solarDataStructure=solarDataStructure.append(newSolarZerosRow, ignore_index=True)
        
        # Extract GPS sensor data from SQL
        
        # Speed data from SQL
        dataStructure['speed'].iat[-1] = SQLread(10)
        if np.isnan(dataStructure['speed'].iat[-1]):
            # If value unavailable, use interpolation function
            dataStructure = interpolate_next_value(dataStructure, 'speed')
        # Kalamn filter to remove noise from sensor reading
        dataStructure, P1 = kalman_filter_update(dataStructure,'speed',iteration,P1,process_variance=0.01)
        
        # Set current speed value for this execution of the while loop
        currentSpeed = dataStructure['speed'].iat[-1]
        
        # Acceleration data from SQL
        dataStructure['acceleration'].iat[-1] = SQLread(13)
        if np.isnan(dataStructure['acceleration'].iat[-1]):
             # If value unavailable, use interpolation function
            dataStructure = interpolate_next_value(dataStructure,'acceleration')
        # Kalamn filter to remove noise from sensor reading
        dataStructure, P2 = kalman_filter_update(dataStructure,'acceleration',iteration,P2,process_variance=0.01)
        
        # Motor sensor data
        
        # Motor current data from SQL
        dataStructure['motorCurrent'].iat[-1] = SQLread(18)
        if np.isnan(dataStructure['motorCurrent'].iat[-1]):
            # If value unavailable, use interpolation function
            dataStructure = interpolate_next_value(dataStructure,'motorCurrent')
        # Kalamn filter to remove noise from sensor reading
        dataStructure, P3 = kalman_filter_update(dataStructure,'motorCurrent',iteration,P3)    
        
        # Motor voltage data from SQL
        dataStructure['motorVoltage'].iat[-1] = SQLread(19)
        if np.isnan(dataStructure['motorVoltage'].iat[-1]):
            # If value unavailable, use interpolation function
            dataStructure = interpolate_next_value(dataStructure,'motorVoltage')
        # Kalamn filter to remove noise from sensor reading
        dataStructure, P4 = kalman_filter_update(dataStructure,'motorVoltage',iteration,P4)
            
        # Battery sensor data
        
        # Battery current data from SQL
        dataStructure['batteryCurrent'].iat[-1] = SQLread(27)
        if np.isnan(dataStructure['batteryCurrent'].iat[-1]):
            # If value unavailable, use interpolation function
            dataStructure = interpolate_next_value(dataStructure,'batteryCurrent')
        # Kalamn filter to remove noise from sensor reading
        dataStructure, P5 = kalman_filter_update(dataStructure,'batteryCurrent',iteration,P5)
        
        # Battery voltage data from SQL
        dataStructure['batteryVoltage'].iat[-1] = SQLread(28)
        if np.isnan(dataStructure['batteryVoltage'].iat[-1]):
            # If value unavailable, use interpolation function
            dataStructure = interpolate_next_value(dataStructure,'batteryVoltage')
        # Kalamn filter to remove noise from sensor reading
        dataStructure, P6 = kalman_filter_update(dataStructure,'batteryVoltage',iteration,P6)
        
        # Battery state of charge from SQL
        dataStructure['batteryStateOfCharge'].iat[-1] = SQLread(1)
        if np.isnan(dataStructure['batteryStateOfCharge'].iat[-1]):
            # If value unavailable, use interpolation function
            dataStructure = interpolate_next_value(dataStructure,'batteryStateOfCharge')
        # Kalamn filter to remove noise from sensor reading
        dataStructure, P7 = kalman_filter_update(dataStructure,'batteryStateOfCharge',iteration,P7,process_variance=0.01)
        
        # Compute initial power consumption estimates for battery and motor usung P=IV
        dataStructure['batteryPowerConsumption'].iat[-1] = dataStructure['batteryCurrent'].iat[-1]*dataStructure['batteryVoltage'].iat[-1]
        dataStructure['motorPowerConsumption'].iat[-1] = dataStructure['motorCurrent'].iat[-1]*dataStructure['motorVoltage'].iat[-1]
        
        # Recompute estimate of efficiency using a weighted average
        if ~np.isnan(dataStructure['batteryPowerConsumption'].iat[-1]) & ~np.isnan(dataStructure['motorPowerConsumption'].iat[-1]) & (dataStructure['batteryPowerConsumption'].iat[-1] > 0):
            efficiencyRatio = (dataStructure['motorPowerConsumption'].iat[-1]/dataStructure['batteryPowerConsumption'].iat[-1])
            electricalSystemEfficiency = (efficiencyRatio + electricalSystemEfficiency*count)/(count+1)
            count+=1
            
        # Update motor-based power consumption estimate by dividing by efficiency
        dataStructure['motorBasedPowerConsumption'].iat[-1] = dataStructure['motorPowerConsumption'].iat[-1]/electricalSystemEfficiency
        dataStructure['target'].iat[-1] = (dataStructure['motorBasedPowerConsumption'].iat[-1] + dataStructure['batteryPowerConsumption'].iat[-1])/2   
        
        # Predict power consumption at current speed using ML models
        predictionInputDataCurrentSpeed = dataStructure.drop(columns=['target']).tail(1)
        currentSpeedPowerConsumption = predict_with_model(predictionInputDataCurrentSpeed)
        # Predict power consumption at slow speed strategy using ML models
        predictionInputDataSlowSpeed = pd.DataFrame({'speed': [slowSpeed], 'batteryStateOfCharge': [(dataStructure.iloc[-1]['batteryStateOfCharge'])]})
        slowSpeedPowerConsumption = predict_with_model(predictionInputDataSlowSpeed, model_path="simple_xgboost_model.json")
        # Predict power consumption at high-speed strategy using ML models
        predictionInputDataHighSpeed = pd.DataFrame({'speed': [highSpeed], 'batteryStateOfCharge': [(dataStructure.iloc[-1]['batteryStateOfCharge'])]})
        highSpeedPowerConsumption = predict_with_model(predictionInputDataHighSpeed, model_path="simple_xgboost_model.json")
        
        # If the models have not yet been trained, we can not provide an estimate for alterate speed strategies. So, this block ensures in this case both estimates are set to nan
        if slowSpeedPowerConsumption == highSpeedPowerConsumption:
            slowSpeedPowerConsumption = np.nan
            highSpeedPowerConsumption = np.nan
        
        # Check if ML models are ready for training/ retrianing processes
        if (iteration % retrainRate == 0 and iteration > 0) or (retrainOnNextIteration == True):
            if retraining_active == True:
                retrainOnNextIteration = True
            else:
                retrainOnNextIteration = False
                dataCopy = dataStructure.copy()
                retraining_active = True
                # Start retraining process using multiprocessing to ensure code execution can continue in parallel
                retrain_process = multiprocessing.Process(target=multipleTrainingProcesses, args=(dataCopy,))
                retrain_process.start()
        
        # Check if solar forecast is required according to soalr foreacst rate defined above
        if iteration % solarForecastTrigger == 0:
            # Get the lat and long values
            latitude = SQLread(5)
            longitude = SQLread(6)
            # Call the API to get the value for average 6 hour irradiance
            avSolarIrr = get_future_solar_irradiance_avg(latitude, longitude)
        
        # Extract solar data and append to solar data frame 
        
        # Solar current data from SQL database
        solarDataStructure['solarCurrent'].iat[-1] = SQLread(21)
        if np.isnan(solarDataStructure['solarCurrent'].iat[-1]):
            # If value is missing, interpolate
            solarDataStructure = interpolate_next_value(solarDataStructure, 'solarCurrent')
        # Use Kalman filter to remove noise
        solarDataStructure, P8 = kalman_filter_update(solarDataStructure,'solarCurrent',iteration,P8)
        
        # Solar voltage data from SQL
        solarDataStructure['solarVoltage'].iat[-1] = SQLread(22)
        if np.isnan(solarDataStructure['solarVoltage'].iat[-1]):
            # if value is missing, interpolate
            solarDataStructure = interpolate_next_value(solarDataStructure, 'solarVoltage')
        # Use Kalman filter to remove noise
        solarDataStructure, P9 = kalman_filter_update(solarDataStructure,'solarVoltage',iteration,P9)
        
        # Recompute the solar panel efficiency based on measured data and a comparison to forecast irradience
        
        # If there is an error in forecasting irradiance, pass
        if avSolarIrr == 0:
            pass
        else:
        # Else, recompute effiency, gibing a weighting of 1000 data points to the pre-defined value from the manufacturer
            if iteration == 0:
                solarEff = ((initialSolarEfficiency*1000)+(((solarDataStructure['solarVoltage'].iat[-1])*(solarDataStructure['solarCurrent'].iat[-1]))/(avSolarIrr*solarArea)))/(1000 + 1)
            else:
                solarEff = ((solarEff*(1000+iteration))+(((solarDataStructure['solarVoltage'].iat[-1])*(solarDataStructure['solarCurrent'].iat[-1]))/(avSolarIrr*solarArea)))/(1000 + iteration + 1)
            
        # Compute the range of the boat for the three different speed scenarios
        currentSpeedRange = computeRange(currentSpeed, currentSpeedPowerConsumption, currentSpeedRange)
        slowSpeedRange = computeRange(slowSpeed, slowSpeedPowerConsumption, slowSpeedRange)
        highSpeedRange= computeRange(highSpeed, highSpeedPowerConsumption, highSpeedRange)
        
        # The range estimates above are in the form of an array; now access the ltest value in the array
        csRange = currentSpeedRange[-1]
        ssRange = slowSpeedRange[-1]
        hsRange = highSpeedRange[-1]
        
        # Validation step to 'sanity check' the ML output automatically
        
        # Once more than three minutes (verificaiton window) worth of data has been gathered by the code, the process begins
        if len(dataStructure['speed'])>(verificationWindow * 60 // interval):
            # Compute the average speed for the past 3 min window in the data frame
            avSpd = dataStructure['speed'].iloc[-(verificationWindow * 60 // interval):].mean()
            # Compute the reduction in SOC over this period
            SOCrateVal = (dataStructure['batteryStateOfCharge'].iat[-(verificationWindow * 60 // interval)]-dataStructure['batteryStateOfCharge'].iat[-1])/(verificationWindow*60)
            # Match the speed averaged across the window to a discrete speed in the pre-defined array
            idxSpd = (np.abs(speedsRangeArray - avSpd)).argmin()
            # Use a weighted average to adjust the rate of SOC depletion at the given speed
            SOCrate[idxSpd] = (SOCrateVal + (SOCrate[idxSpd]*SOCcount[idxSpd]))/(SOCcount[idxSpd]+1)
            # Update the count of occurrence of that speed in the boat's operation
            SOCcount[idxSpd]+=1
        
        # Compute an alternative range estiamte with no ML, based only on observed rate of SOC depletion at set speeds
        
        # Search for the speed in the pre-defined array that matches the slow speed strategy
        slowSpdIdx = (np.abs(speedsRangeArray - slowSpeed)).argmin()
        # If no data exists, set the range to a high number for ID later
        if SOCrate[slowSpdIdx]==0:
            rangeEstSS = 999999 
        else: 
            # Else compute second range estimate using below formula
            rangeEstSS = dataStructure['batteryStateOfCharge'].iat[-1] * slowSpeed * (1/3600) / SOCrate[slowSpdIdx]
            
        # Search for the speed in the pre-defined array that matches the current speed strategy
        currentSpdIdx = (np.abs(speedsRangeArray - currentSpeed)).argmin()
        # If no data exists, set the range to a high number for ID later
        if SOCrate[currentSpdIdx]==0:
            rangeEstCS = 999999 
        else: 
            # Else compute second range estimate using below formula
            rangeEstCS = dataStructure['batteryStateOfCharge'].iat[-1] * currentSpeed * (1/3600) / SOCrate[currentSpdIdx]
            
        # Search for the speed in the pre-defined array that matches the high speed strategy
        highSpdIdx = (np.abs(speedsRangeArray - highSpeed)).argmin()
        # If no data exists, set the range to a high number for ID later
        if SOCrate[highSpdIdx]==0:
            rangeEstHS = 999999 
        else: 
            # Else compute second range estimate using below formula
            rangeEstHS = dataStructure['batteryStateOfCharge'].iat[-1] * highSpeed * (1/3600) / SOCrate[highSpdIdx]
    
        # If a realistic secondary range estimate exists, that is based on more than 15 data points recorded at that speed, appraise the ML based range estiamtes
        
        # Start with slow speed esitmate
        if (~(rangeEstSS == 999999)) and (SOCcount[slowSpdIdx] > 15):
            # If the absolute difference is less than 20%, take average of observed data based range, and ML based range
            if (abs(ssRange - rangeEstSS)/rangeEstSS)<0.2:
                ssRange = (ssRange + rangeEstSS)/2
                print('adjusted by', abs(ssRange-rangeEstSS)/2)
            else:
                # Else disregard the ML-based estimate as being inaccurate
                ssRange = rangeEstSS
                print('completely adjusted')
                
        # Next, look at the current speed estimate
        if (~(rangeEstCS == 999999)) and (SOCcount[currentSpdIdx] > 15):
             # If the absolute difference is less than 20%, take average of observed data based range, and ML based range
            if (abs(csRange - rangeEstCS)/rangeEstCS)<0.2:
                csRange = (csRange + rangeEstCS)/2
                print('adjusted by', abs(csRange-rangeEstCS)/2)
            else:
                # Else disregard the ML-based estimate as being inaccurate
                csRange = rangeEstCS
                print('completely adjusted')
            
        # And finally, the high speed estiate
        if (~(rangeEstHS == 999999)) and (SOCcount[highSpdIdx] > 15):
             # If the absolute difference is less than 20%, take average of observed data based range, and ML based range
            if (abs(hsRange - rangeEstHS)/rangeEstHS)<0.2:
                hsRange = (hsRange + rangeEstHS)/2
                print('adjusted by', abs(hsRange-rangeEstHS)/2)
            else:
                # Else disregard the ML-based estimate as being inaccurate
                hsRange = rangeEstHS
                print('completely adjusted')
        
        # Speed strategy optimisation: find the optimal speed to cross the finish line with very low SOC
        # Add a 7km contingency buffer to the calculation to leave approx. 10% charge level at the end of the race
        # Retrieve distance remaining from SQL
        distanceRemaining = approxRaceLength-SQLread(30)+7
        #Initialise an array of zeros corresponding to the discrete speeds array used above
        # This will represent the range of the boat at each speed
        rangess = np.zeros(len(speedsRangeArray))
        # Allow i to take each value of the speed array in turn
        for i in speedsRangeArray:
            # Create data frame for range estimation
            predictionForRangess = pd.DataFrame({'speed': [i], 'batteryStateOfCharge': [(dataStructure.iloc[-1]['batteryStateOfCharge'])]})
            # Use simple ML models to estimate power draw at speed i
            powerConsumptionRangess = predict_with_model(predictionForRangess, model_path="simple_xgboost_model.json")
            # Compute the range estimate for this power draw and append to the array in the relevant place
            rangessArray = computeRange(i, powerConsumptionRangess, rangessArray)
        
        # Find the minimum where the difference between range and race distance remaining is least
        rangessIdx = (np.abs(rangessArray - distanceRemaining)).argmin()  
        # Optimal speed is located at this index
        rangessOptimalSpeed = speedsRangeArray[rangessIdx]
        
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
                self.Speed = SQLread(10)

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
                self.BatteryCharge = SQLread(1)
                self.progressBar.setValue(self.BatteryCharge)

                # Initialize the Range variable
                self.Range = csRange
                logging.info(f"Initial Range: {self.Range}")

                # Initialize the Remaining variable
                self.Remaining = 50
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

                self.BatteryError = str(SQLreadmessage(2)) + str(' ') + str(SQLreadmessage(3))

                # Initialize the BatteryStatus variable
                self.BatteryStatus = SQLreadmessage(4)  # Example status, you can change this as needed

                # Initialize the Current variable
                self.MotorCurrent = SQLread(18)  # Example value, you can change this as needed

                # Initialize the Voltage variable
                self.MotorVoltage = SQLread(19)  # Example value, you can change this as needed

                # Initialize the Temperature variable
                self.Temperature = SQLread(16)  # Example value, you can change this as needed

                # Initialize the Throttle Position variable
                self.AuxilliaryVoltage = SQLread(25)  # Example value, you can change this as needed

                # Initialize the SolarCurrent variable
                self.SolarCurrent = SQLread(21)  # Example value, you can change this as needed

                # Initialize the SolarVoltage variable
                self.SolarVoltage = SQLread(22)  # Example value, you can change this as needed

                # Initialize the SolarPower variable
                self.SolarPower = SQLread(20)  # Example value, you can change this as needed

                # Initialize the Latitude variable
                self.Latitude = SQLread(5)  # Example value, you can change this as needed

                # Initialize the Longitude variable
                self.Longitude = SQLread(6)  # Example value, you can change this as needed

                # Initialize the Acceleration variable
                self.Acceleration = SQLread(14)  # Example value, you can change this as needed

                # Initialize the Motor Power variable
                self.MotorPower = SQLread(17)  # Example value, you can change this as needed

                # Initialize the Auxilliary Power variable
                self.AuxilliaryPower = SQLread(23)  # Example value, you can change this as needed

                # Initialize the Auxilliary Current variable
                self.AuxilliaryCurrent = SQLread(24)  # Example value, you can change this as needed

                # Initialize the Range Slow variable
                self.RangeSlow = ssRange  # Example value, you can change this as needed

                # Initialize the Range Fast variable
                self.RangeFast = hsRange  # Example value, you can change this as needed

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
                if ((iteration * interval) % 5) == 0:
                    self.send_to_opencpn()

                # Set up a QTimer to send BatteryCharge to Adafruit every 20 seconds
                if ((iteration * interval) % 20) == 0:
                    self.send_to_adafruit()

                # Start the UDP server in a separate thread
                self.server_thread = threading.Thread(target=self.start_udp_server)
                self.server_thread.daemon = True  # Makes sure the server stops when the program ends
                self.server_thread.start()
                logging.info("UDP server started")

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

            def SQLreadmessage(sensor_id, db_path="sensors_log.db", table_name="sensor_logs"):
                """
                Fucntion to extract most recent sensor data from an SQL database according to the timestamp column. The function 
                returns the sensor data sepcified according to the input 'sensor_id'. If there is any error, the function returns
                a nan.
                """
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()

                    query = f"""
                    SELECT message FROM {table_name} 
                    WHERE sensor_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                    """
                    
                    cursor.execute(query, (sensor_id,))
                    result = cursor.fetchone()

                    conn.close()

                    # Return nan if not found
                    return result[0] if result and result[0] is not None else 'No data'

                except sqlite3.Error as e:
                    print(f"Database error: {e}")
                    return 'No data' 
                except Exception as e:
                    print(f"Error: {e}")
                    return 'No data'

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

            # End of the loop, now the scheduling command evaluates the time to pause before beginning the next iteration
            print('reached the end')
            print(ssRange, csRange, hsRange)
            iteration+=1
            elapsed = time.time()-startTime
            time.sleep(max(0, interval - elapsed))
