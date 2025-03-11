import can

# Configure the bus for Waveshare USB-to-CAN
bus = can.interface.Bus(
    bustype='serial',
    channel='COM3',  # Replace with your COM port (e.g., COM3, COM4, etc.)
    bitrate=250000   # Match the CAN network bitrate
)

# Test receiving messages
print("Listening for CAN messages...")
try:
    while True:
        message = bus.recv(timeout=10)  # Wait up to 10 seconds for a message
        if message:
            print(f"Received: {message}")
        else:
            print("No message received.")
except KeyboardInterrupt:
    print("Exiting...")
