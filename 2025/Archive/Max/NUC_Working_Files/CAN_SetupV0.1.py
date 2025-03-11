import time
import random
import serial
import signal
import sys
import traceback
from enum import Enum, auto
from typing import Dict, Union
from datetime import datetime
import sqlite3
import os

# Enum for CAN Bus speed (only 250000 is defined here)
class CANUSB_SPEED(Enum):
    SPEED_250000 = 0x05

# Enum for CAN Bus modes (Normal mode here)
class CANUSB_MODE(Enum):
    NORMAL = 0x00

# Enum for CAN frame types (Standard frame here)
class CANUSB_FRAME(Enum):
    STANDARD = 0x01

# Enum for payload injection modes (fixed injection mode here)
class CANUSB_PAYLOAD_MODE(Enum):
    INJECT_PAYLOAD_MODE_RANDOM = 0
    INJECT_PAYLOAD_MODE_INCREMENTAL = 1
    INJECT_PAYLOAD_MODE_FIXED = 2

# Custom error for serial port issues
class SerialPortError(Exception):
    pass

# Main class to interact with the USB-CAN adapter
class UsbCanAdapter:
    """A class to interact with a USB CAN adapter."""

    # Default values for CAN USB adapter settings
    CANUSB_INJECT_SLEEP_GAP_DEFAULT = 200  # Default sleep gap in milliseconds between frames
    CANUSB_TTY_BAUD_RATE_DEFAULT = 2000000  # Baud rate for serial communication
    DATA_START_INDEX = 6  # The starting index for data in the frame

    # Initializer method that sets up default values for the adapter
    def __init__(self):
        self.device_port = "COM5"  # Hardcoded to COM3 for the serial device
        self.speed = CANUSB_SPEED.SPEED_250000  # Default CAN Bus speed
        self.baudrate = self.CANUSB_TTY_BAUD_RATE_DEFAULT  # Default baud rate for serial communication
        self.terminate_after = 0  # No automatic termination by default
        self.program_running = True  # Flag to control the program loop
        self.inject_payload_mode = CANUSB_PAYLOAD_MODE.INJECT_PAYLOAD_MODE_FIXED  # Fixed payload injection
        self.inject_sleep_gap = self.CANUSB_INJECT_SLEEP_GAP_DEFAULT  # Sleep gap for payload injection
        self.print_traffic = False  # Traffic printing is off by default
        self.frame = bytearray()  # Holds the current frame being processed
        self.serial_device = None  # Placeholder for the serial device object
        self.data_dict = {}  # Holds extracted data from received frames

    @staticmethod
    def canusb_int_to_speed(speed: int) -> CANUSB_SPEED:
        """
        Converts an integer speed value to a CANUSB_SPEED enum.
        Currently supports only 250000.
        """
        speed_dict = {
            250000: CANUSB_SPEED.SPEED_250000,
        }
        return speed_dict.get(speed, 0)

    @staticmethod
    def generate_checksum(data: bytearray) -> int:
        """
        Generates a checksum for the provided data (sum of bytes).
        Returns the least significant byte of the sum.
        """
        checksum = sum(data)
        return checksum & 0xff  # Ensure the checksum fits in one byte

    def frame_send(self, frame: bytearray, print_flag: bool) -> int:
        """
        Sends a frame to the USB-CAN adapter device through serial communication.
        Throws SerialPortError if the serial port is not open or write fails.
        """
        if not self.serial_device.is_open:
            raise SerialPortError("Serial port is not open.")
        frame_len = len(frame)
        try:
            result = self.serial_device.write(bytes(frame))  # Write the frame as bytes
            # Print the extracted data if the flag is set
        
        except serial.SerialException as e:
            raise SerialPortError(f"write() failed: {e}")
        
        return frame_len

    def frame_receive(self, frame_len_max: int = 20) -> int:
        """
        Receives a CAN frame from the USB-CAN adapter device over serial communication.
        Continues reading until the maximum length is reached or until a frame end (0x55) is encountered.
        """
        if not self.serial_device.is_open:
            print("Error: Serial port is not open.")
            return -1

        self.frame = bytearray()  # Reset the frame buffer
        frame_len = 0  # Keep track of the number of bytes received
        started = False  # Flag to indicate if frame reading has started

        if self.print_traffic:
            print("<<< ", end="")

        while self.program_running and frame_len < frame_len_max:
            try:
                byte = self.serial_device.read(1)  # Read one byte at a time
            except serial.SerialException as e:
                print(f"Error reading from serial port: {e}")
                return -1

            if self.print_traffic:
                print(f"{byte[0]:02x} ", end="")

            # If we reach byte 0x55, end of frame, break the loop
            if byte[0] == 0x55 and started:
                self.frame.append(byte[0])
                frame_len += 1
                break

            # If the byte is 0xAA, it indicates the start of a frame
            if byte[0] == 0xaa:
                started = True

            if started:
                self.frame.append(byte[0])  # Add byte to the frame buffer
                frame_len += 1

            if frame_len >= 32:  # Prevent reading too many bytes
                break

        if self.print_traffic:
            print('')  # End the traffic printing line
        return frame_len

    def command_settings(self) -> int:
        """
        Sends a frame to set the CAN to serial adapter settings.
        Configures speed, frame type, filter ID, etc., and generates a checksum.
        """
        cmd_frame = bytearray()

        # Append CAN speed, frame type, filter settings, and checksum to the command frame
        cmd_frame.append(self.speed.value)
        cmd_frame.append(CANUSB_FRAME.STANDARD.value)
        cmd_frame.extend([0] * 8)  # Fill with zeros for Filter ID and Mask ID (not handled here)
        cmd_frame.append(CANUSB_MODE.NORMAL.value)
        cmd_frame.extend([0x01, 0, 0, 0, 0])  # Additional settings
        cmd_frame.append(self.generate_checksum(cmd_frame[2:19]))  # Generate checksum from specific bytes

        # Send the command frame and handle any errors
        if self.frame_send(cmd_frame,True) < 0:
            return -1

        return 0

    def extract_data(self, frame: bytearray) -> Dict[str, Union[bytearray, str]]:
        try:
            # Convert the frame to a hex string for easier reading (useful for debugging).
            frame_hex = frame.hex()
            
            
            # Step 1: Remove the first three bytes (the 'acc' part, typically the header of the frame)
            frame_hex = frame_hex[3:]  # Remove the first 3 bytes

            # Step 2: Set the DLC (Data Length Code) to the first byte after 'acc'.
            # The DLC is stored in the first byte after 'acc' (i.e., after byte 3 in the original frame)
            dlc = frame_hex[0]  # DLC is the first byte after 'acc'
           

            # Step 3: Set the ID to be the next two bytes (following the DLC byte).
            # The ID will be in bytes 1 and 2 (after the DLC).
            frame_id = frame_hex[3:5]+frame_hex[1:3]  # Frame ID is the next two bytes
            

            # Step 4: Extract the data bytes.
            # The remaining data starts from byte 3 and continues until the second-to-last byte (before 0x55).
            # Remove the last byte (0x55) from the frame.
            data = frame_hex[5:-2]  # All bytes from byte 3 until the second last byte (before 0x55)


        except IndexError as e:
            # Catch IndexError in case the frame does not have the expected length
            error_message = f"Error in CAN data frame\nException: {e}\nTraceback:\n{traceback.format_exc()}"
            print(error_message)
        return data, dlc, frame_id
    


    def dump_data_frames(self, print_flag: bool) -> int:
        """
        Receives and processes data frames from the CAN adapter.
        Prints the extracted frame data if the print_flag is True.
        """
        
        frame_len = self.frame_receive(20)  # Receive up to 20 bytes in a frame

        if not self.program_running:
            return 0

        if frame_len == -1:
            print("Frame receive error!")
        else:
            # Extract data from the received frame
            self.data_dict = self.extract_data(self.frame)

        # Print the extracted data if the flag is set
        if print_flag:
            try:
                print(f"{self.data_dict}")
            except KeyError:
                pass
        return 0

    def adapter_init(self) -> serial.Serial:
        """
        Initializes the serial connection with the USB-CAN adapter.
        Sets the correct baud rate, byte size, and parity settings for the connection.
        """
        try:
            # Open the serial connection with specified parameters
            self.serial_device = serial.Serial(self.device_port, baudrate=self.baudrate, bytesize=serial.EIGHTBITS,
                                               parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_TWO, timeout=None)
            return self.serial_device
        except serial.SerialException as e:
            print(f"Error opening serial port {self.device_port}: {e}")
            return None

    def adapter_close(self) -> None:
        """
        Closes the serial connection gracefully when done with the adapter.
        """
        try:
            if self.serial_device is not None and hasattr(self.serial_device, 'close'):
                self.serial_device.close()
        except serial.SerialException as e:
            print("Error closing serial port", e)

    def sigterm(self, signo, frame) -> None:
        """
        Handles termination signals (SIGTERM or SIGINT) to cleanly shut down the program.
        Sets the `program_running` flag to False.
        """
        self.program_running = False

    def check_and_create_database(db_name):
        # Check if database file exists
        if not os.path.exists(db_name):
            print(f"Database {db_name} does not exist. Creating new database.")
        else:
            print(f"Database {db_name} exists.")

        # Connect to the SQLite database (this will create the database if it doesn't exist)
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        # Create a table if it doesn't exist
        create_table_query = """
        CREATE TABLE IF NOT EXISTS data_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            value INTEGER NOT NULL
        );
        """

        try:
            cursor.execute(create_table_query)
            print("Table created successfully (if it didn't exist).")
        except sqlite3.Error as e:
            print(f"Error creating table: {e}")
            return False
        
        # Insert sample data into the table
        insert_data_query = """
        INSERT INTO data_table (name, value)
        VALUES ('Sample Name', 123);
        """

        try:
            cursor.execute(insert_data_query)
            conn.commit()  # Commit the changes to the database
            print("Data inserted successfully!")
        except sqlite3.Error as e:
            print(f"Error inserting data: {e}")
            return False

        # Close the database connection
        conn.close()
        return True


    # Example usage
    db_name = "example.db"  # Database file name
    if check_and_create_database(db_name):
        print("Database setup completed successfully.")
    else:
        print("Database setup failed.")



    def main(self) -> None:
        """
        Main function that runs the program.
        Initializes the adapter, sets the CAN settings, and enters the data frame receiving loop.
        Sends the number 99 to the CAN bus every 5 seconds and injects a frame.
        """
        signal.signal(signal.SIGTERM, self.sigterm)
        signal.signal(signal.SIGINT, self.sigterm)
        self.adapter_init()  # Initialize the adapter
        if self.serial_device is None:
            sys.exit(1)
        
        self.command_settings()  # Configure the CAN settings
        
        # Start dumping data frames (default behavior)
        while True:
            self.dump_data_frames(print_flag=True)
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Get the current time
            print(f"Current Time: {current_time}")  # Print the current time
            time.sleep(1)  # Sleep for 1 second

        # Now, send the number 99 to the CAN bus and inject a data frame every 5 seconds





# Main entry point for the scriptca
if __name__ == "__main__":
    uca = UsbCanAdapter()  # Create an instance of the UsbCanAdapter class
    uca.main()  # Start the main function
