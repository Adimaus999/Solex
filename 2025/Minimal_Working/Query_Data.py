import time
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, TIMESTAMP, ForeignKey

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

# Function to print the most recent sensor data by timestamp every second
def print_most_recent_sensor_data():
    while True:
        # Query the most recent sensor data from the database based on timestamp
        latest_battery_soc = session.query(SensorData).filter_by(sensor_id=1).order_by(SensorData.timestamp.desc()).first()
        latest_battery_alarm1 = session.query(SensorLog).filter_by(sensor_id=2).order_by(SensorLog.timestamp.desc()).first()
        latest_battery_alarm2 = session.query(SensorLog).filter_by(sensor_id=3).order_by(SensorLog.timestamp.desc()).first()
        latest_battery_status = session.query(SensorLog).filter_by(sensor_id=4).order_by(SensorLog.timestamp.desc()).first()

        # Print the latest values for each sensor
        if latest_battery_soc:
            print(f"Battery SOC: {latest_battery_soc.value}%, Timestamp: {latest_battery_soc.timestamp}")

        if latest_battery_alarm1:
            print(f"Battery Alarm 1: {latest_battery_alarm1.message}, Timestamp: {latest_battery_alarm1.timestamp}")

        if latest_battery_alarm2:
            print(f"Battery Alarm 2: {latest_battery_alarm2.message}, Timestamp: {latest_battery_alarm2.timestamp}")

        if latest_battery_status:
            print(f"Battery Status: {latest_battery_status.message}, Timestamp: {latest_battery_status.timestamp}")

        print("-" * 50)  # Separator for readability

        # Wait for 1 second before printing the next set of data
        time.sleep(1)

if __name__ == "__main__":
    print_most_recent_sensor_data()
