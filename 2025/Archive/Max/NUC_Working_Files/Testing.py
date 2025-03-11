import os
import sqlite3
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import sessionmaker, declarative_base

# Database configuration
DB_PATH = "sensors.db"
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
        {"name": "temperature", "unit": "°C", "description": "Temperature sensor"},
        {"name": "motor_power", "unit": "W", "description": "Motor power"},
        {"name": "solar_power", "unit": "W", "description": "Solar power"},
        {"name": "auxiliary_power", "unit": "W", "description": "Auxiliary power"}
    ]
    
    for sensor in sensors:
        if not session.query(Sensor).filter_by(name=sensor["name"]).first():
            session.add(Sensor(**sensor))
    session.commit()

initialize_sensors()  # Ensure sensors exist

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

# Function to process and store CAN bus data






def process_and_store_data(hex_string, frame_id, dlc):

    data_bits = {f"part_{i}": s[i:i+n] for i in range(0, len(hex_string), dlc)}



    """Processes incoming CAN bus data and stores it in the database."""
    
    # Process Battery Data (Frame ID: 0x5FF)
    if frame_id == "0x5FF":
        part4 = int(hex_string[-2:], 16)
        part3 = int(hex_string[-4:-2], 16)
        part2 = int(hex_string[-6:-4], 16)
        part1 = int(hex_string[-8:-6], 16)

        # Alarm conditions
        alarm1 = []
        if part1 & 0x80: alarm1.append("Pack low-voltage alarm")
        if part1 & 0x20: alarm1.append("Over-temperature protection during discharge")
        if part1 & 0x10: alarm1.append("Overload protection")
        if part1 & 0x02: alarm1.append("Cell low voltage alarm")
        
        alarm2 = []
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

        # Store in the database
        insert_sensor_data("battery_soc", soc)  # ✅ Insert numeric data
        insert_sensor_log("battery_alarm1", alarm1_str)  # ✅ Insert text logs
        insert_sensor_log("battery_alarm2", alarm2_str)
        insert_sensor_log("battery_status", status_str)
    
    # Process GPS Data (Frame ID: 0x034)
    elif frame_id == "0x034":
        if len(hex_string) != 12:  # Ensure 6 bytes (12 hex characters)
            print("Invalid GPS data length")
            return

        # Extract latitude and longitude
        lat_raw = int(hex_string[:6], 16) / 1000000  # Convert to decimal degrees
        lon_raw = int(hex_string[6:], 16) / 1000000  # Convert to decimal degrees

        # Check if the values make sense (optional)
        if not (-90 <= lat_raw <= 90 and -180 <= lon_raw <= 180):
            print("Invalid GPS coordinates received")
            return

        # Store in the database
        insert_sensor_data("gps_latitude", lat_raw)
        insert_sensor_data("gps_longitude", lon_raw)

    # Process Temperature Sensor Data (Frame ID: 0x100)
    elif frame_id == "0x100":
        temperature = int(hex_string, 16) / 100  # Assuming 2-byte temperature data in centigrade
        
        # Store in the database
        insert_sensor_data("temperature", temperature)

    # Process Motor Power Data (Frame ID: 0x200)
    elif frame_id == "0x200":
        motor_power = int(hex_string, 16)  # Assuming the value is in watts
        
        # Store in the database
        insert_sensor_data("motor_power", motor_power)
    
    # Process Solar Power Data (Frame ID: 0x300)
    elif frame_id == "0x300":
        solar_power = int(hex_string, 16)  # Assuming the value is in watts
        
        # Store in the database
        insert_sensor_data("solar_power", solar_power)

    # Process Auxiliary Power Data (Frame ID: 0x400)
    elif frame_id == "0x400":
        auxiliary_power = int(hex_string, 16)  # Assuming the value is in watts
        
        # Store in the database
        insert_sensor_data("auxiliary_power", auxiliary_power)
    
    else:
        print(f"Unhandled frame ID: {frame_id}")

# Example usage
# process_and_store_data("FF10204030", "0x5FF")  # Example battery data
# process_and_store_data("012A03E8", "0x034")  # Example GPS data
# process_and_store_data("FA25", "0x100")  # Example temperature data
# process_and_store_data("0A2F", "0x200")  # Example motor power data
# process_and_store_data("0014", "0x300")  # Example solar power data
# process_and_store_data("0C50", "0x400")  # Example auxiliary power data
