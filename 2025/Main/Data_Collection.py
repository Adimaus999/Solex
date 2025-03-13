import time
import random
import serial
import signal
import sys
import traceback
from enum import Enum, auto
from typing import Dict, Union
from datetime import datetime
import sqlite3
import os
import numpy as np
from sqlalchemy import create_engine, Column, Integer, String, Float, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import sessionmaker, declarative_base
import math
import subprocess

# Database configuration
DB_PATH = "C:\SOLEX\Solex\2025\Archive\Max\NUC_Working_Files\new_sensors.db"
ENGINE = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Session = sessionmaker(bind=ENGINE) 
session = Session()
Base = declarative_base()

# Define Sensor Metadata Table
class Sensor(Base):
    __tablename__ = "sensors"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    unit = Column(String(20))
    description = Column(String(200))

# Define Numeric Sensor Data Table (e.g., SOC, GPS)
class SensorData(Base):
    __tablename__ = "sensor_data"
    id = Column(Integer, primary_key=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False)
    value = Column(Float, nullable=False)  # Only numeric values
    timestamp = Column(TIMESTAMP, default=datetime.utcnow)

# Define Log Table for Non-Numeric Data (Alarms, Status Messages)
class SensorLog(Base):
    __tablename__ = "sensor_logs"
    id = Column(Integer, primary_key=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False)
    message = Column(String(500), nullable=False)  # Text-based values
    timestamp = Column(TIMESTAMP, default=datetime.utcnow)

# Create tables if they don't exist
Base.metadata.create_all(ENGINE)

# Function to insert sensor metadata (only needed once)
def initialize_sensors():
    sensors = [
        {"name": "battery_soc", "unit": "%", "description": "State of Charge of the battery"},
        {"name": "battery_alarm1", "unit": "", "description": "Battery alarm 1"},
        {"name": "battery_alarm2", "unit": "", "description": "Battery alarm 2"},
        {"name": "battery_status", "unit": "", "description": "Battery status"},

        {"name": "gps_latitude", "unit": "degrees", "description": "GPS latitude"},
        {"name": "gps_longitude", "unit": "degrees", "description": "GPS longitude"},

        {"name": "velocity_x", "unit": "m/s", "description": "GPS velocity X (East-West)"},
        {"name": "velocity_y", "unit": "m/s", "description": "GPS velocity Y (North-South)"},
        {"name": "velocity_z", "unit": "m/s", "description": "GPS velocity Z (Up-Down)"},
        {"name": "velocity_t", "unit": "m/s", "description": "GPS velocity resultant (no Z)"},

        {"name": "acceleration_x", "unit": "m/s^2", "description": "GPS acceleration X (East-West)"},
        {"name": "acceleration_y", "unit": "m/s^2", "description": "GPS acceleration Y (North-South)"},
        {"name": "acceleration_z", "unit": "m/s^2", "description": "GPS acceleration Z (Up-Down)"},
        {"name": "acceleration_t", "unit": "m/s^2", "description": "GPS acceleration resultant (no z)"},

        {"name": "heading", "unit": "°", "description": "GPS velocity heading"},

        {"name": "distance", "unit": "m", "description": "Distance travelled since last calculation"},
        {"name": "total_distance", "unit": "m", "description": "Total distance travelled"},

        {"name": "temperature", "unit": "°C", "description": "Temperature sensor"},

        {"name": "motor_power", "unit": "W", "description": "Motor power"},
        {"name": "motor_current", "unit": "A", "description": "Motor current"},
        {"name": "motor_voltage", "unit": "V", "description": "Motor voltage"},

        {"name": "solar_power", "unit": "W", "description": "Solar power"},
        {"name": "solar_current", "unit": "A", "description": "Solar current"},
        {"name": "solar_voltage", "unit": "V", "description": "Solar voltage"},

        {"name": "auxiliary_power", "unit": "W", "description": "Auxiliary power"},
        {"name": "auxiliary_current", "unit": "A", "description": "Auxiliary current"},
        {"name": "auxiliary_voltage", "unit": "V", "description": "Auxiliary voltage"},

        {"name": "battery_power", "unit": "W", "description": "Battery power"},
        {"name": "battery_current", "unit": "A", "description": "Battery current"},
        {"name": "battery_voltage", "unit": "V", "description": "Battery voltage"},     
    ]
    
    for sensor in sensors:
        if not session.query(Sensor).filter_by(name=sensor["name"]).first():
            session.add(Sensor(**sensor))
    session.commit()

initialize_sensors()

# Enum for CAN Bus speed (only 250000 is defined here)
class CANUSB_SPEED(Enum):
    SPEED_250000 = 0x05

# Enum for CAN Bus modes (Normal mode here)
class CANUSB_MODE(Enum):
    NORMAL = 0x00

# Enum for CAN frame types (Standard frame here)
class CANUSB_FRAME(Enum):
    STANDARD = 0x01

# Enum for payload injection modes (fixed injection mode here)
class CANUSB_PAYLOAD_MODE(Enum):
    INJECT_PAYLOAD_MODE_RANDOM = 0
    INJECT_PAYLOAD_MODE_INCREMENTAL = 1
    INJECT_PAYLOAD_MODE_FIXED = 2

# Custom error for serial port issues
class SerialPortError(Exception):
    pass

# Main class to interact with the USB-CAN adapter
class UsbCanAdapter:
    """A class to interact with a USB CAN adapter."""

    # Default values for CAN USB adapter settings
    CANUSB_INJECT_SLEEP_GAP_DEFAULT = 200  # Default sleep gap in milliseconds between frames
    CANUSB_TTY_BAUD_RATE_DEFAULT = 2000000  # Baud rate for serial communication
    DATA_START_INDEX = 6  # The starting index for data in the frame

    # Initializer method that sets up default values for the adapter
    def __init__(self):
        self.device_port = "COM5"  # Hardcoded to COM3 for the serial device
        self.speed = CANUSB_SPEED.SPEED_250000  # Default CAN Bus speed
        self.baudrate = self.CANUSB_TTY_BAUD_RATE_DEFAULT  # Default baud rate for serial communication
        self.terminate_after = 0  # No automatic termination by default
        self.program_running = True  # Flag to control the program loop
        self.inject_payload_mode = CANUSB_PAYLOAD_MODE.INJECT_PAYLOAD_MODE_FIXED  # Fixed payload injection
        self.inject_sleep_gap = self.CANUSB_INJECT_SLEEP_GAP_DEFAULT  # Sleep gap for payload injection
        self.print_traffic = False  # Traffic printing is off by default
        self.frame = bytearray()  # Holds the current frame being processed
        self.serial_device = None  # Placeholder for the serial device object
        self.data_dict = {}  # Holds extracted data from received frames
        self.previous_lat = None
        self.previous_lon = None
        self.cumulative_distance = 0

    @staticmethod
    def canusb_int_to_speed(speed: int) -> CANUSB_SPEED:
        """
        Converts an integer speed value to a CANUSB_SPEED enum.
        Currently supports only 250000.
        """
        speed_dict = {
            250000: CANUSB_SPEED.SPEED_250000,
        }
        return speed_dict.get(speed, 0)

    @staticmethod
    def generate_checksum(data: bytearray) -> int:
        """
        Generates a checksum for the provided data (sum of bytes).
        Returns the least significant byte of the sum.
        """
        checksum = sum(data)
        return checksum & 0xff  # Ensure the checksum fits in one byte

    def frame_send(self, frame: bytearray, print_flag: bool) -> int:
        """
        Sends a frame to the USB-CAN adapter device through serial communication.
        Throws SerialPortError if the serial port is not open or write fails.
        """
        if not self.serial_device.is_open:
            raise SerialPortError("Serial port is not open.")
        frame_len = len(frame)
        try:
            result = self.serial_device.write(bytes(frame))  # Write the frame as bytes
            # Print the extracted data if the flag is set
        
        except serial.SerialException as e:
            raise SerialPortError(f"write() failed: {e}")
        
        return frame_len

    def frame_receive(self, frame_len_max: int = 20) -> int:
        """
        Receives a CAN frame from the USB-CAN adapter device over serial communication.
        Continues reading until the maximum length is reached or until a frame end (0x55) is encountered.
        """
        if not self.serial_device.is_open:
            print("Error: Serial port is not open.")
            return -1

        self.frame = bytearray()  # Reset the frame buffer
        frame_len = 0  # Keep track of the number of bytes received
        started = False  # Flag to indicate if frame reading has started

        if self.print_traffic:
            print("<<< ", end="")

        while self.program_running and frame_len < frame_len_max:
            try:
                byte = self.serial_device.read(1)  # Read one byte at a time
            except serial.SerialException as e:
                print(f"Error reading from serial port: {e}")
                return -1

            if self.print_traffic:
                print(f"{byte[0]:02x} ", end="")

            # If we reach byte 0x55, end of frame, break the loop
            if byte[0] == 0x55 and started:
                self.frame.append(byte[0])
                frame_len += 1
                break

            # If the byte is 0xAA, it indicates the start of a frame
            if byte[0] == 0xaa:
                started = True

            if started:
                self.frame.append(byte[0])  # Add byte to the frame buffer
                frame_len += 1

            if frame_len >= 32:  # Prevent reading too many bytes
                break

        if self.print_traffic:
            print('')  # End the traffic printing line
        return frame_len

    def command_settings(self) -> int:
        """
        Sends a frame to set the CAN to serial adapter settings.
        Configures speed, frame type, filter ID, etc., and generates a checksum.
        """
        cmd_frame = bytearray()

        # Append CAN speed, frame type, filter settings, and checksum to the command frame
        cmd_frame.append(self.speed.value)
        cmd_frame.append(CANUSB_FRAME.STANDARD.value)
        cmd_frame.extend([0] * 8)  # Fill with zeros for Filter ID and Mask ID (not handled here)
        cmd_frame.append(CANUSB_MODE.NORMAL.value)
        cmd_frame.extend([0x01, 0, 0, 0, 0])  # Additional settings
        cmd_frame.append(self.generate_checksum(cmd_frame[2:19]))  # Generate checksum from specific bytes

        # Send the command frame and handle any errors
        if self.frame_send(cmd_frame,True) < 0:
            return -1

        return 0

    def extract_data(self, frame: bytearray) -> Dict[str, Union[bytearray, str]]:
        try:
            frame_hex = frame.hex()
            frame_hex = frame_hex[3:] 
            dlc = frame_hex[0]  
            frame_id = frame_hex[3:5]+frame_hex[1:3]  
            data = frame_hex[5:-2]  
        except IndexError as e:
            # Catch IndexError in case the frame does not have the expected length
            error_message = f"Error in CAN data frame\nException: {e}\nTraceback:\n{traceback.format_exc()}"
            print(error_message)
        return data, dlc, frame_id
    


    def dump_data_frames(self) -> int:
        """
        Receives and processes data frames from the CAN adapter.
        Prints the extracted frame data if the print_flag is True.
        """
        
        frame_len = self.frame_receive(20)  # Receive up to 20 bytes in a frame

        if not self.program_running:
            return 0

        if frame_len == -1:
            print("Frame receive error!")
        else:
            # Extract data from the received frame
            data, dlc, frame_id = self.extract_data(self.frame)
            self.process_and_store_data(data, frame_id, dlc)

    def adapter_init(self) -> serial.Serial:
        """
        Initializes the serial connection with the USB-CAN adapter.
        Sets the correct baud rate, byte size, and parity settings for the connection.
        """
        try:
            # Open the serial connection with specified parameters
            self.serial_device = serial.Serial(self.device_port, baudrate=self.baudrate, bytesize=serial.EIGHTBITS,
                                               parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_TWO, timeout=None)
            return self.serial_device
        except serial.SerialException as e:
            print(f"Error opening serial port {self.device_port}: {e}")
            return None

    def adapter_close(self) -> None:
        """
        Closes the serial connection gracefully when done with the adapter.
        """
        try:
            if self.serial_device is not None and hasattr(self.serial_device, 'close'):
                self.serial_device.close()
        except serial.SerialException as e:
            print("Error closing serial port", e)

    def sigterm(self, signo, frame) -> None:
        """
        Handles termination signals (SIGTERM or SIGINT) to cleanly shut down the program.
        Sets the `program_running` flag to False.
        """
        self.program_running = False

    



    def great_circle_distance(lat1, lon1, lat2, lon2):
        """
        Calculate the great-circle distance between two points on the Earth's surface.
        The input coordinates are in decimal degrees.
        """
        R = 6371000  # Radius of the Earth in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance = R * c
        return distance
    
    # Function to insert NUMERIC sensor data (SOC, GPS, etc.)
    def insert_sensor_data(self, sensor_name, value):
        sensor = session.query(Sensor).filter_by(name=sensor_name).first()
        if sensor:
            session.add(SensorData(sensor_id=sensor.id, value=value))
            session.commit()
            print(f"Inserted Numeric Data: {sensor_name} = {value}")
        else:
            print(f"Sensor {sensor_name} not found!")

    # Function to insert TEXT-BASED sensor logs (Alarms, Status)
    def insert_sensor_log(self,sensor_name, message):
        sensor = session.query(Sensor).filter_by(name=sensor_name).first()
        if sensor:
            session.add(SensorLog(sensor_id=sensor.id, message=message))
            session.commit()
            print(f"Inserted Log: {sensor_name} = {message}")
        else:
            print(f"Sensor {sensor_name} not found!")

    # Function to handle battery data and insert into the database
    def battery_data(self,data_bits):
        try:    
            # Initialize alarm lists
            alarm1 = []
            alarm2 = []

            # Extract parts from data_bits
            part1 = int(data_bits.get("Bit_4", "0"), 16)
            part2 = int(data_bits.get("Bit_5", "0"), 16)
            part3 = int(data_bits.get("Bit_6", "0"), 16)
            part4 = int(data_bits.get("Bit_7", "0"), 16)

            # Check for alarms in part1
            if part1 & 0x80: alarm1.append("Pack low-voltage alarm")
            if part1 & 0x20: alarm1.append("Over-temperature protection during discharge")
            if part1 & 0x10: alarm1.append("Overload protection")
            if part1 & 0x02: alarm1.append("Cell low voltage alarm")

            # Check for alarms in part2
            if part2 & 0x40: alarm2.append("Over-current alarm during discharge")
            if part2 & 0x20: alarm2.append("Pack under-voltage protection")
            if part2 & 0x10: alarm2.append("Cell under-voltage protection")
            if part2 & 0x02: alarm2.append("Over-temperature alarm")

            # Status conditions
            status = []
            if part3 & 0x40: status.append("Fully charged (SOC 100%)")
            if part3 & 0x20: status.append("Heating-element ON")
            if part3 & 0x04: status.append("Discharge current detected")
            if part3 & 0x02: status.append("Charging current detected")

            # Convert lists to string
            alarm1_str = ", ".join(alarm1) if alarm1 else "No alarms"
            alarm2_str = ", ".join(alarm2) if alarm2 else "No alarms"
            status_str = ", ".join(status) if status else "No status"

            # SOC
            soc = part4/100

            # Insert data into the database
            try:
                # Insert SOC
                self.insert_sensor_data("battery_soc", soc)

                # Insert alarms
                self.insert_sensor_log("battery_alarm1", alarm1_str)
                self.insert_sensor_log("battery_alarm2", alarm2_str)

                # Insert status
                self.insert_sensor_log("battery_status", status_str)

                print("Battery Data & Status Inserted into Database")
            except Exception as e:
                print(f"Error inserting battery data: {e}")
        except Exception as e:
            print(f"Error inserting battery data: {e}")


    

   

    # Function to handle temperature data
    def temperature_voltage(self,data_bits):
        try:
            print(data_bits)
            temperature = [] 
            battery_voltage = []
            # Extract and combine parts from data_bits for temperature
            temp_to_convert = data_bits.get("Bit_0", "0") + data_bits.get("Bit_1", "0") + data_bits.get("Bit_2", "0")
            temperature = int(temp_to_convert, 16)/1000

            # Extract and combine parts from data_bits for voltage
            voltage_to_convert =  data_bits.get("Bit_4", "0") + data_bits.get("Bit_5", "0")
            battery_voltage = int(voltage_to_convert, 16)/1000


            self.battery_voltage = battery_voltage

            try:
                self.insert_sensor_data("temperature", temperature)
                self.insert_sensor_data("battery_voltage", battery_voltage)
                print("Temperature Inserted into Database")
            except Exception as e:
                print(f"Error inserting GPS velocity data: {e}")

        except Exception as e:
            print(f"Error inserting battery power data: {e}")
    
    def motor_aux_solar(self,data_bits):

        try:
            motor_current = []
            aux_current = []
            solar_current = []

            # Extract and combine parts from data_bits for motor current
            mc_to_convert = data_bits.get("Bit_0", "0") + data_bits.get("Bit_1", "0") + data_bits.get("Bit_2", "0")
            motor_current = int(mc_to_convert, 16) / 1000

            # Extract and combine parts from data_bits for auxiliary current
            ac_to_convert = data_bits.get("Bit_3", "0") + data_bits.get("Bit_4", "0") 
            aux_current = int(ac_to_convert, 16) / 1000
    
            # Extract and combine parts from data_bits for solar current
            sc_to_convert = data_bits.get("Bit_5", "0") + data_bits.get("Bit_6", "0")
            solar_current = int(sc_to_convert, 16) / 1000

            motor_voltage = self.battery_voltage
            aux_voltage = self.battery_voltage
            solar_voltage = self.battery_voltage

            motor_power = motor_current * motor_voltage
            aux_power = aux_current * aux_voltage
            solar_power = solar_current * solar_voltage

            battery_current = motor_current + aux_current - solar_current
            battery_power = motor_power + aux_power - solar_power


            # Insert the battery power, current, and voltage values into the database
            self.insert_sensor_data("battery_power", battery_power)
            self.insert_sensor_data("battery_current", battery_current)
            
            self.insert_sensor_data("motor_current", motor_current)
            self.insert_sensor_data("motor_power", motor_power)
            self.insert_sensor_data("motor_voltage", motor_voltage)

            self.insert_sensor_data("solar_current", solar_current)
            self.insert_sensor_data("solar_power", solar_power)
            self.insert_sensor_data("solar_voltage", solar_voltage)

            self.insert_sensor_data("auxiliary_current", aux_current)
            self.insert_sensor_data("auxiliary_power", aux_power)
            self.insert_sensor_data("auxiliary_voltage", aux_voltage)

            print("Current Sensor Data Inserted into Database")
        except Exception as e:
            print(f"Error inserting battery power data: {e}")



    # Function to handle location data
    def location(self,data_bits):
        # Extract parts from data_bits
        lat1 = data_bits.get("Bit_0", "0")
        lat2 = data_bits.get("Bit_1", "0")
        lat3 = data_bits.get("Bit_2", "0")
        lat4 = data_bits.get("Bit_3", "0")

        lat_to_convert = lat1 + lat2 + lat3 + lat4
        unsigned_lat = int(lat_to_convert, 16)

        if unsigned_lat >= 2**31:
            signed_lat = (unsigned_lat - 2**32) * 2**-24
        else:
            signed_lat = unsigned_lat * 2**-24

        lon1 = data_bits.get("Bit_4", "0")
        lon2 = data_bits.get("Bit_5", "0")
        lon3 = data_bits.get("Bit_6", "0")
        lon4 = data_bits.get("Bit_7", "0")

        lon_to_convert = lon1 + lon2 + lon3 + lon4
        unsigned_lon = int(lon_to_convert, 16)

        if unsigned_lon >= 2**31:
            signed_lon = (unsigned_lon - 2**32) * 2**-23
        else:
            signed_lon = unsigned_lon * 2**-23

        # Update previous coordinates
        self.previous_lat = signed_lat
        self.previous_lon = signed_lon

        # Calculate distance if previous coordinates exist
        if self.previous_lat is not None and self.previous_lon is not None:
            distance = self.great_circle_distance(self.previous_lat, self.previous_lon, signed_lat, signed_lon)
            self.cumulative_distance += distance

            # Insert distance and cumulative distance into the database
            self.insert_sensor_data("distance", distance)
            self.insert_sensor_data("total_distance", self.cumulative_distance)

        # Insert data into the database
        try:
            # Insert latitude
            self.insert_sensor_data("gps_latitude", signed_lat)

            # Insert longitude
            self.insert_sensor_data("gps_longitude", signed_lon)

            print("GPS Location Inserted into Database")
        except Exception as e:
            print(f"Error inserting GPS location data: {e}")

    def acceleration(self,data_bits):
        # Extract parts from data_bits
        acc_x1 = data_bits.get("Bit_0", "0")
        acc_x2 = data_bits.get("Bit_1", "0")

        acc_x_to_convert = acc_x1+acc_x2
        unsigned_acc_x = int(acc_x_to_convert,16)

        if unsigned_acc_x >= 2**15:
            signed_acc_x = (unsigned_acc_x - 2**16)*2**-8
        else:
            signed_acc_x = unsigned_acc_x*2**-8

        # Extract parts from data_bits
        acc_y1 = data_bits.get("Bit_2", "0")
        acc_y2 = data_bits.get("Bit_3", "0")

        acc_y_to_convert = acc_y1+acc_y2
        unsigned_acc_y = int(acc_y_to_convert,16)

        if unsigned_acc_y >= 2**15:
            signed_acc_y = (unsigned_acc_y - 2**16)*2**-8
        else:
            signed_acc_y = unsigned_acc_y*2**-8


        # Extract parts from data_bits
        acc_z1 = data_bits.get("Bit_4", "0")
        acc_z2 = data_bits.get("Bit_5", "0")

        acc_z_to_convert = acc_z1+acc_z2
        unsigned_acc_z = int(acc_z_to_convert,16)

        if unsigned_acc_z >= 2**15:
            signed_acc_z = (unsigned_acc_z - 2**16)*2**-8
        else:
            signed_acc_z = unsigned_acc_z*2**-8


        acc_t = np.sqrt(signed_acc_x**2 + signed_acc_y**2)

        try:
            # Insert x velocity
            self.insert_sensor_data("acceleration_x", signed_acc_x)

            # Insert y velocity
            self.insert_sensor_data("acceleration_y", signed_acc_y)

            self.insert_sensor_data("acceleration_z", signed_acc_z)

            self.insert_sensor_data("acceleration_t", acc_t)

            print("GPS Acceleration Inserted into Database")
        except Exception as e:
            print(f"Error inserting GPS velocity data: {e}")
    # Function to handle velocity data
    def velocity(self,data_bits):
        # Extract parts from data_bits
        vel_x1 = data_bits.get("Bit_0", "0")
        vel_x2 = data_bits.get("Bit_1", "0")

        vel_x_to_convert = vel_x1+vel_x2
        unsigned_vel_x = int(vel_x_to_convert,16)

        if unsigned_vel_x >= 2**15:
            signed_vel_x = (unsigned_vel_x - 2**16)*2**-6
        else:
            signed_vel_x = unsigned_vel_x*2**-6

        # Extract parts from data_bits
        vel_y1 = data_bits.get("Bit_2", "0")
        vel_y2 = data_bits.get("Bit_3", "0")

        vel_y_to_convert = vel_y1+vel_y2
        unsigned_vel_y = int(vel_y_to_convert,16)

        if unsigned_vel_y >= 2**15:
            signed_vel_y = (unsigned_vel_y - 2**16)*2**-6
        else:
            signed_vel_y = unsigned_vel_y*2**-6


        # Extract parts from data_bits
        vel_z1 = data_bits.get("Bit_4", "0")
        vel_z2 = data_bits.get("Bit_5", "0")

        vel_z_to_convert = vel_z1+vel_z2
        unsigned_vel_z = int(vel_z_to_convert,16)

        if unsigned_vel_z >= 2**15:
            signed_vel_z = (unsigned_vel_z - 2**16)*2**-6
        else:
            signed_vel_z = unsigned_vel_z*2**-6


        vel_t = np.sqrt(signed_vel_x**2 + signed_vel_y**2)
        heading = 90-(np.degrees(np.arctan2(signed_vel_y, signed_vel_x)))

        try:
            # Insert x velocity
            self.insert_sensor_data("velocity_x", signed_vel_x)

            # Insert y velocity
            self.insert_sensor_data("velocity_y", signed_vel_y)

            self.insert_sensor_data("velocity_z", signed_vel_z)

            self.insert_sensor_data("velocity_t", vel_t)

            self.insert_sensor_data("heading", heading)

            print("GPS Velocity Inserted into Database")
        except Exception as e:
            print(f"Error inserting GPS velocity data: {e}")

    # Function to process and store data based on frame ID
    def process_and_store_data(self, hex_string, frame_id, dlc):
        # Calculate chunk size and remainder for data distribution
        chunk_size = len(hex_string) // int(dlc)
        remainder = len(hex_string) % int(dlc)

        # Dictionary to store data bits
        data_bits = {}
        start = 0

        # Distribute hex string into chunks
        for i in range(int(dlc)):
            extra = 1 if i < remainder else 0
            end = start + chunk_size + extra
            data_bits[f"Bit_{i}"] = hex_string[start:end]
            start = end

        # Dictionary to map frame IDs to their respective functions
        frame_id_to_function = {
            "05ff": self.battery_data,
            "0071": self.location,
            "0076": self.velocity,
            "0035": self.acceleration,
            "0010": self.temperature_voltage,
            "0020": self.motor_aux_solar,
        }
        
        # Call the appropriate function based on frame ID
        if frame_id in frame_id_to_function:
            frame_id_to_function[frame_id](data_bits)
        else:
            print("Frame ID not found")

        print("Frame Handled")


    
    def main(self) -> None:
        """
        Main function that runs the program.
        Initializes the adapter, sets the CAN settings, and enters the data frame receiving loop.
        Sends the number 99 to the CAN bus every 5 seconds and injects a frame.
        """
        try:
            signal.signal(signal.SIGTERM, self.sigterm)
            signal.signal(signal.SIGINT, self.sigterm)
            self.adapter_init()  # Initialize the adapter
            if self.serial_device is None:
                sys.exit(1)
            
            self.command_settings()  # Configure the CAN settings
            
            # Start dumping data frames (default behavior)
        except Exception as e:
            print(f"Error in main loop: {e}")
        try:
            while True:
                self.dump_data_frames()
        except Exception as e:
            print(f"Error in main loop: {e}")
            





# Main entry point for the scriptca
if __name__ == "__main__":
    uca = UsbCanAdapter()  # Create an instance of the UsbCanAdapter class
    uca.main()  # Start the main function
