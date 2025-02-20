import serial

# Configure serial connection (update port if needed)
ser = serial.Serial(
    port="COM3",  # Update this to your actual COM port
    baudrate=115200,
    bytesize=serial.EIGHTBITS,
    stopbits=serial.STOPBITS_ONE,
    parity=serial.PARITY_NONE,
    timeout=1  # Adjust as needed
)

print(f"Connected to {ser.port}")

def calculate_crc(data_bytes):
    """Calculate checksum as the sum of all bytes (mod 256)"""
    return sum(data_bytes) % 256

# Construct message
message = bytearray(b"!0x03S")  # '!3S' (Start, Length, Command)
crc = calculate_crc(message)
message.append(crc)

# Send command
ser.write(message)
print("Sent:", message)

# Read response
response = ser.read(32)  # Adjust buffer size as needed
print("Received:", response)


if response and response[0] == ord("?"):  # Check for '?' sync byte
    print("Valid response received!")

    temp = response[3]  # TP (Temperature Byte)
    temperature = -15.5 + (249 * ((854598 - temp) ** 0.5 - 1))
    print(f"Temperature: {temperature:.2f} °C")

    voltage = ((response[4] | (response[5] << 8)) * 27.78) / 1023
    print(f"Voltage: {voltage:.2f} V")
