import sys
import time
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6 import uic
from PyQt6.QtCore import QTimer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, TIMESTAMP, ForeignKey

# Set up database connection and session
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

# Function to get the most recent data for each sensor
def get_most_recent_data():
    # Fetch the most recent entries from the database
    latest_battery_soc = session.query(SensorData).filter_by(sensor_id=1).order_by(SensorData.timestamp.desc()).first()
    latest_battery_alarm1 = session.query(SensorLog).filter_by(sensor_id=2).order_by(SensorLog.timestamp.desc()).first()
    latest_battery_alarm2 = session.query(SensorLog).filter_by(sensor_id=3).order_by(SensorLog.timestamp.desc()).first()
    latest_battery_status = session.query(SensorLog).filter_by(sensor_id=4).order_by(SensorLog.timestamp.desc()).first()

    return {
        "battery_soc": latest_battery_soc,
        "battery_alarm1": latest_battery_alarm1,
        "battery_alarm2": latest_battery_alarm2,
        "battery_status": latest_battery_status
    }

# Main UI window class
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("Main_Window.ui", self)  # Load UI file

        self.start_time = datetime.now()  # Store the app start time
        self.last_update_time = self.start_time  # Track last progress bar update

        # Set font size and bold text for fields
        self.set_text_styles()

        # Start a timer to update fields every second
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_fields)
        self.timer.start(1000)  # Update every 1 second

        self.showFullScreen()  # Full-screen mode

        # Connect the Close button to the close function
        self.Close.clicked.connect(self.close_application)

    def close_application(self):
        """Method to close the application when the Close button is clicked."""
        print("Closing application...")
        self.close()  # Close the window and terminate the app

    def set_text_styles(self):
        """Set bold and font size for text fields."""
        style = "font-size: 32px; font-weight: bold;"
        self.LastTimeStampOutput.setStyleSheet(style)
        self.UpTimeOutput.setStyleSheet(style)
        self.TimeOutput.setStyleSheet(style)
        self.Error1Output.setStyleSheet(style)
        self.Error2Output.setStyleSheet(style)
        self.StatusOutput.setStyleSheet(style)
        self.UpTime.setStyleSheet(style)
        self.LastTimeStamp.setStyleSheet(style)
        self.Time.setStyleSheet(style)
        self.Error1.setStyleSheet(style)
        self.Error2.setStyleSheet(style)
        self.Status.setStyleSheet(style)

    def update_fields(self):
        """Update the text fields with the most recent data from the database."""
        current_time = datetime.now()
        uptime = current_time - self.start_time  # Calculate uptime

        # Fetch most recent data from the database
        data = get_most_recent_data()

        # Extract the most recent values
        latest_battery_soc = data["battery_soc"]
        latest_battery_alarm1 = data["battery_alarm1"]
        latest_battery_alarm2 = data["battery_alarm2"]
        latest_battery_status = data["battery_status"]

        # Update the UI fields with the latest values
        if latest_battery_soc:
            self.LastTimeStampOutput.setText(latest_battery_soc.timestamp.strftime("%H:%M:%S"))
            self.UpTimeOutput.setText(str(uptime).split(".")[0])  # Remove milliseconds
            self.TimeOutput.setText(current_time.strftime("%H:%M:%S"))

            # Check if there's a message for alarms
            self.Error1Output.setText(latest_battery_alarm1.message if latest_battery_alarm1 else "No Error")
            self.Error2Output.setText(latest_battery_alarm2.message if latest_battery_alarm2 else "No Error")
            
            # Show battery status and charge
            self.StatusOutput.setText(latest_battery_status.message if latest_battery_status else 'Unknown')
            # Update Progress Bar (SOC)
            self.SOC.setValue(int(latest_battery_soc.value))  # Update progress bar

            # Set progress bar color based on battery percentage
            if int(latest_battery_soc.value) > 90:
                color = 'rgb(0, 255, 0)'  # Bright Green for very high SOC
            elif int(latest_battery_soc.value) > 80:
                color = 'rgb(50, 255, 50)'  # Light Green for high SOC
            elif int(latest_battery_soc.value) > 70:
                color = 'rgb(100, 255, 0)'  # Yellow-Green for slightly high SOC
            elif int(latest_battery_soc.value) > 60:
                color = 'rgb(150, 255, 0)'  # Lime Green for moderate-high SOC
            elif int(latest_battery_soc.value) > 50:
                color = 'rgb(255, 255, 0)'  # Yellow for mid-high SOC
            elif int(latest_battery_soc.value) > 40:
                color = 'rgb(255, 200, 0)'  # Light Orange-Yellow for mid SOC
            elif int(latest_battery_soc.value) > 30:
                color = 'rgb(255, 140, 0)'  # Orange for lower mid SOC
            elif int(latest_battery_soc.value) > 20:
                color = 'rgb(255, 69, 0)'  # Red-Orange for low SOC
            elif int(latest_battery_soc.value) > 10:
                color = 'rgb(255, 0, 0)'  # Red for very low SOC
            else:
                color = 'rgb(139, 0, 0)'  # Dark Red for critically low SOC


            # Set the progress bar's color dynamically
            self.SOC.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; }}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
