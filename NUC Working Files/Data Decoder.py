import os
import sqlite3
import numpy as np
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import sessionmaker, declarative_base

# Database configuration
DB_PATH = "sensors1.db"
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
        {"name": "acceleration_t", "unit": "m/s^2", "description": "GPS acceleration resultant"},

        {"name": "heading", "unit": "°", "description": "GPS velocity heading"},

        {"name": "temperature", "unit": "°C", "description": "Temperature sensor"},

        {"name": "motor_power", "unit": "W", "description": "Motor power"},
        {"name": "motor_current", "unit": "A", "description": "Motor current"},
        {"name": "motor_voltage", "unit": "V", "description": "Motor voltage"},

        {"name": "solar_power", "unit": "W", "description": "Solar power"},
        {"name": "solar_current", "unit": "A", "description": "Solar current"},
        {"name": "solar_voltage", "unit": "V", "description": "Solar voltage"},

        {"name": "auxiliary_power", "unit": "W", "description": "Auxiliary power"},
        {"name": "auxiliary_current", "unit": "A", "description": "Motor current"},
        {"name": "auxiliary_voltage", "unit": "V", "description": "Motor voltage"},
    ]
    
    for sensor in sensors:
        if not session.query(Sensor).filter_by(name=sensor["name"]).first():
            session.add(Sensor(**sensor))
    session.commit()

initialize_sensors()

# Function to insert NUMERIC sensor data (SOC, GPS, etc.)
def insert_sensor_data(sensor_name, value):
    sensor = session.query(Sensor).filter_by(name=sensor_name).first()
    if sensor:
        session.add(SensorData(sensor_id=sensor.id, value=value))
        session.commit()
        print(f"Inserted Numeric Data: {sensor_name} = {value}")
    else:
        print(f"Sensor {sensor_name} not found!")

# Function to insert TEXT-BASED sensor logs (Alarms, Status)
def insert_sensor_log(sensor_name, message):
    sensor = session.query(Sensor).filter_by(name=sensor_name).first()
    if sensor:
        session.add(SensorLog(sensor_id=sensor.id, message=message))
        session.commit()
        print(f"Inserted Log: {sensor_name} = {message}")
    else:
        print(f"Sensor {sensor_name} not found!")

# Function to handle battery data and insert into the database
def battery_data(data_bits):
    print(data_bits)
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
    soc = part4

    # Insert data into the database
    try:
        # Insert SOC
        insert_sensor_data("battery_soc", soc)

        # Insert alarms
        insert_sensor_log("battery_alarm1", alarm1_str)
        insert_sensor_log("battery_alarm2", alarm2_str)

        # Insert status
        insert_sensor_log("battery_status", status_str)

        print("Battery Data & Status Inserted into Database")
    except Exception as e:
        print(f"Error inserting battery data: {e}")

# Function to handle motor power data and insert into the database
def motor_power(data_bits):
    try:
        # Extract and combine parts from data_bits for motor power
        mp_to_convert = data_bits.get("Bit_0", "0") + data_bits.get("Bit_1", "0") + data_bits.get("Bit_2", "0")
        motor_power_value = int(mp_to_convert, 16) / 1000

        # Extract and combine parts from data_bits for motor current
        mc_to_convert = data_bits.get("Bit_3", "0") + data_bits.get("Bit_4", "0") + data_bits.get("Bit_5", "0")
        motor_current_value = int(mc_to_convert, 16) / 1000

        # Extract and combine parts from data_bits for motor voltage
        mv_to_convert = data_bits.get("Bit_6", "0") + data_bits.get("Bit_7", "0")
        motor_voltage_value = int(mv_to_convert, 16) / 1000

        # Insert the motor power, current, and voltage values into the database
        insert_sensor_data("motor_power", motor_power_value)
        insert_sensor_data("motor_current", motor_current_value)
        insert_sensor_data("motor_voltage", motor_voltage_value)

        print("Motor Power, Current, and Voltage Inserted into Database")
    except Exception as e:
        print(f"Error inserting motor power data: {e}")

# Function to handle solar power data and insert into the database
def solar_power(data_bits):
    try:
        # Extract and combine parts from data_bits for solar power
        sp_to_convert = data_bits.get("Bit_0", "0") + data_bits.get("Bit_1", "0") + data_bits.get("Bit_2", "0")
        solar_power_value = int(sp_to_convert, 16) / 1000

        # Extract and combine parts from data_bits for solar current
        sc_to_convert = data_bits.get("Bit_3", "0") + data_bits.get("Bit_4", "0") + data_bits.get("Bit_5", "0")
        solar_current_value = int(sc_to_convert, 16) / 1000

        # Extract and combine parts from data_bits for solar voltage
        sv_to_convert = data_bits.get("Bit_6", "0") + data_bits.get("Bit_7", "0")
        solar_voltage_value = int(sv_to_convert, 16) / 1000

        # Insert the solar power, current, and voltage values into the database
        insert_sensor_data("solar_power", solar_power_value)
        insert_sensor_data("solar_current", solar_current_value)
        insert_sensor_data("solar_voltage", solar_voltage_value)

        print("Solar Power, Current, and Voltage Inserted into Database")
    except Exception as e:
        print(f"Error inserting solar power data: {e}")

# Function to handle auxiliary power data and insert into the database
def auxiliary_power(data_bits):
    try:
        # Extract and combine parts from data_bits for auxiliary power
        ap_to_convert = data_bits.get("Bit_0", "0") + data_bits.get("Bit_1", "0") + data_bits.get("Bit_2", "0")
        auxiliary_power_value = int(ap_to_convert, 16) / 1000

        # Extract and combine parts from data_bits for auxiliary current
        ac_to_convert = data_bits.get("Bit_3", "0") + data_bits.get("Bit_4", "0") + data_bits.get("Bit_5", "0")
        auxiliary_current_value = int(ac_to_convert, 16) / 1000

        # Extract and combine parts from data_bits for auxiliary voltage
        av_to_convert = data_bits.get("Bit_6", "0") + data_bits.get("Bit_7", "0")
        auxiliary_voltage_value = int(av_to_convert, 16) / 1000

        # Insert the auxiliary power, current, and voltage values into the database
        insert_sensor_data("auxiliary_power", auxiliary_power_value)
        insert_sensor_data("auxiliary_current", auxiliary_current_value)
        insert_sensor_data("auxiliary_voltage", auxiliary_voltage_value)

        print("Auxiliary Power, Current, and Voltage Inserted into Database")
    except Exception as e:
        print(f"Error inserting auxiliary power data: {e}")

# Function to handle temperature data
def temperature(data_bits):
    temperature = [] 
    temperature = int(data_bits.get("Bit_0", "0"), 16)-56

    try:
        # Insert x velocity
        insert_sensor_data("temperature", temperature)

        print("Temperature Inserted into Database")
    except Exception as e:
        print(f"Error inserting GPS velocity data: {e}")

# Function to handle location data
def location(data_bits):

    # Initialize alarm lists
    lat = []
    lon = []

    # Extract parts from data_bits
    lat1 = data_bits.get("Bit_0", "0")
    lat2 = data_bits.get("Bit_1", "0")
    lat3 = data_bits.get("Bit_2", "0")
    lat4 = data_bits.get("Bit_3", "0")

    lat_to_convert = lat1+lat2+lat3+lat4

    unsigned_lat = int(lat_to_convert,16)

    if unsigned_lat >= 2**31:
        signed_lat = (unsigned_lat - 2**32)*2**-24
    else:
        signed_lat = unsigned_lat*2**-24




    lon1 = data_bits.get("Bit_4", "0")
    lon2 = data_bits.get("Bit_5", "0")
    lon3 = data_bits.get("Bit_6", "0")
    lon4 = data_bits.get("Bit_7", "0")

    lon_to_convert = lon1+lon2+lon3+lon4

    unsigned_lon = int(lon_to_convert,16)

    print(unsigned_lon)

    if unsigned_lon >= 2**31:
        signed_lon = (unsigned_lon - 2**32)*2**-23
    else:
        signed_lon = unsigned_lon*2**-23
    

     # Insert data into the database
    try:
        # Insert latitude
        insert_sensor_data("gps_latitude", signed_lat)

        # Insert longitude
        insert_sensor_data("gps_longitude", signed_lon)

        print("GPS Location Inserted into Database")
    except Exception as e:
        print(f"Error inserting GPS location data: {e}")

def acceleration(data_bits):
        # Initialize alarm lists
    acc_x = []
    acc_y = []
    acc_z = []
    acc_t = []

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
        insert_sensor_data("acceleration_x", signed_acc_x)

        # Insert y velocity
        insert_sensor_data("acceleration_y", signed_acc_y)

        insert_sensor_data("acceleration_z", signed_acc_z)

        insert_sensor_data("acceleration_t", acc_t)

        print("GPS Velocity Inserted into Database")
    except Exception as e:
        print(f"Error inserting GPS velocity data: {e}")
# Function to handle velocity data
def velocity(data_bits):
    # Initialize alarm lists
    vel_x = []
    vel_y = []
    vel_z = []
    vel_t = []
    heading = []


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
        insert_sensor_data("velocity_x", signed_vel_x)

        # Insert y velocity
        insert_sensor_data("velocity_y", signed_vel_y)

        insert_sensor_data("velocity_z", signed_vel_z)

        insert_sensor_data("velocity_t", vel_t)

        insert_sensor_data("heading", heading)

        print("GPS Velocity Inserted into Database")
    except Exception as e:
        print(f"Error inserting GPS velocity data: {e}")

# Function to process and store data based on frame ID
def process_and_store_data(hex_string, frame_id, dlc):
    # Calculate chunk size and remainder for data distribution
    chunk_size = len(hex_string) // dlc
    remainder = len(hex_string) % dlc

    # Dictionary to store data bits
    data_bits = {}
    start = 0

    # Distribute hex string into chunks
    for i in range(dlc):
        extra = 1 if i < remainder else 0
        end = start + chunk_size + extra
        data_bits[f"Bit_{i}"] = hex_string[start:end]
        start = end

    # Dictionary to map frame IDs to their respective functions
    frame_id_to_function = {
        "0x5FF": battery_data,
        "0x071": location,
        "0x076": velocity,
        "0x035": acceleration,
        "0x010": temperature,
        "0x020": motor_power,
        "0x021": solar_power,
        "0x022": auxiliary_power
    }

    # Call the appropriate function based on frame ID
    if frame_id in frame_id_to_function:
        frame_id_to_function[frame_id](data_bits)
    else:
        print("Frame ID not found")

    print("Frame Handled")

# Example usage
process_and_store_data("00c8000000FFFFFF", "0x021", 8)
#process_and_store_data("0000000000004055", "0x5FF", 8)