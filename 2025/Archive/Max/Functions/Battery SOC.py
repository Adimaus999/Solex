import can
import struct

def parse_can_message(message):
    """Parses CAN message and extracts relevant fields."""
    if message.arbitration_id == 0x5FF:  # Broadcast ID for battery data
        data = message.data
        
        if data[0] == 0x20:  # Frame contains Alarm, Status, SOC
            alarms = (data[4], data[5])
            status = data[6]
            soc = data[7]  # SOC is in percentage
            print(f"Alarms: {alarms}, Status: {status}, SOC: {soc}%")

# Initialize CAN bus
try:
    bus = can.interface.Bus(bustype='socketcan', channel='can0', bitrate=250000)
    print("Listening for CAN messages...")
    
    while True:
        message = bus.recv()  # Receive message
        if message is not None:
            parse_can_message(message)

except Exception as e:
    print(f"Error: {e}")
