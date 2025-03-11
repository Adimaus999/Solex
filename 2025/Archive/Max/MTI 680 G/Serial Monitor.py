import serial
import sys

def main():
    # Replace with your USB port and baud rate
    usb_port = input("Enter the USB port (e.g., COM3 or /dev/ttyUSB0): ").strip()
    baud_rate = 46080  # Adjust to match the device settings

    try:
        # Open the serial connection
        with serial.Serial(usb_port, baud_rate, timeout=1) as ser:
            print(f"Listening to {usb_port} at {baud_rate} baud.")
            print("Press Ctrl+C to stop.")

            while True:
                # Read data from the USB port
                data = ser.readline().decode('utf-8', errors='ignore').strip()
                if data:
                    print(f"Received: {data}")

    except serial.SerialException as e:
        print(f"Error: Could not open port {usb_port}. Details: {e}")
    except KeyboardInterrupt:
        print("\nStopped by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
