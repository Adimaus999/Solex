import can
import struct

# Set up the CAN bus interface using python-can
bus = can.interface.Bus(channel='can0', bustype='socketcan')  # Adjust for your setup

# Victron-specific CAN identifiers
MANUFACTURER_CODE = 0x66  # First byte in Victron proprietary messages
DEVICE_CODE = 0x99        # Second byte in Victron proprietary messages
CHARGER_POWER_REGISTER = 0xEDD6  # Register for charger power (in 0.01W)

# Function to request charger power
def request_charger_power():
    # Request message format: Victron proprietary + register ID + mask (0xFFFF to specify a single register)
    request_data = struct.pack('<BBHH', MANUFACTURER_CODE, DEVICE_CODE, CHARGER_POWER_REGISTER, 0xFFFF)
    request_msg = can.Message(arbitration_id=0x1EF00, data=request_data, is_extended_id=True)

    try:
        # Send the request to the bus
        bus.send(request_msg)
        print("Request sent for charger power register.")

    except can.CanError:
        print("Failed to send CAN request.")
        return None

# Function to listen for the response and decode charger power
def read_charger_power():
    print("Listening for charger power data...")
    while True:
        message = bus.recv(timeout=10)
        
        if message is None:
            print("No response received.")
            continue

        # Decode message based on Victron's format
        if message.arbitration_id == 0x1EFF:  # Broadcasted proprietary message ID for Victron
            data = message.data
            
            # Check manufacturer code
            if data[0] == MANUFACTURER_CODE and data[1] == DEVICE_CODE:
                # Verify if this is the charger power register
                reg_id = struct.unpack('<H', data[2:4])[0]
                
                if reg_id == CHARGER_POWER_REGISTER:
                    # Charger power is a 2-byte value in 0.01W, convert to W
                    charger_power_raw = struct.unpack('<H', data[4:6])[0]
                    charger_power = charger_power_raw * 0.01  # Convert to watts

                    print(f"Charger Power: {charger_power:.2f} W")
                    return charger_power

# Call functions to request and read solar power
request_charger_power()
read_charger_power()
