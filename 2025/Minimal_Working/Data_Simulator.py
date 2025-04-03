import random
import time
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, TIMESTAMP, ForeignKey
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Setup database connection and session
DB_PATH = "Minimal_Database.db"
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

# Define Numeric Sensor Data Table
class SensorData(Base):
    __tablename__ = "sensor_data"
    id = Column(Integer, primary_key=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False)
    value = Column(Float, nullable=False)
    timestamp = Column(TIMESTAMP, default=datetime.utcnow)

# Define Log Table
class SensorLog(Base):
    __tablename__ = "sensor_logs"
    id = Column(Integer, primary_key=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False)
    message = Column(String(500), nullable=False)
    timestamp = Column(TIMESTAMP, default=datetime.utcnow)

# Create tables if they do not exist
Base.metadata.create_all(ENGINE)

# Function to insert data into sensor_data and sensor_logs every 5 seconds
def insert_data_every_5_seconds():
    while True:
        # Get the current timestamp
        current_time = datetime.utcnow()

        # Insert a new data point for battery_soc (simulate random value between 0 and 100)
        battery_soc_value = random.uniform(0, 100)
        battery_alarm1_message = "Low Voltage"
        battery_alarm2_message = "Overheat"
        battery_status_message = "Battery OK"

        # Insert battery_soc data point into sensor_data table (assuming sensor_id = 1 for battery_soc)
        sensor_data = SensorData(sensor_id=1, value=battery_soc_value, timestamp=current_time)
        session.add(sensor_data)

        # Insert battery_alarm1 data point into sensor_logs table (assuming sensor_id = 2 for battery_alarm1)
        sensor_log1 = SensorLog(sensor_id=2, message=battery_alarm1_message, timestamp=current_time)
        session.add(sensor_log1)

        # Insert battery_alarm2 data point into sensor_logs table (assuming sensor_id = 3 for battery_alarm2)
        sensor_log2 = SensorLog(sensor_id=3, message=battery_alarm2_message, timestamp=current_time)
        session.add(sensor_log2)

        # Insert battery_status data point into sensor_logs table (assuming sensor_id = 4 for battery_status)
        sensor_log3 = SensorLog(sensor_id=4, message=battery_status_message, timestamp=current_time)
        session.add(sensor_log3)

        # Commit the session to insert the data into the database
        session.commit()

        print(f"Inserted data at {current_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Wait for 5 seconds before inserting the next data point
        time.sleep(5)

if __name__ == "__main__":
    insert_data_every_5_seconds()
