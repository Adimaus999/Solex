import serial
import traceback
from typing import Dict, Union

class CANUSB_MODE:
    NORMAL = 1000000
    LOOPBACK = 1
    SILENT = 2
    LOOPBACK_SILENT = 3

class CANUSB_FRAME:
    STANDARD = 0
    EXTENDED = 1

class USB_CAN_Adapter:
    FRAME_ID_SLICE = slice(0, 4)
    PGN_SLICE = slice(4, 6)
    DATA_START_INDEX = 6

    def __init__(self, port: str, baudrate: int = 9600):
        self.serial_device = serial.Serial(port, baudrate)
        self.program_running = True
        self.print_traffic = True
        self.frame = bytearray()
        self.speed = CANUSB_MODE.NORMAL

    def frame_receive(self, frame_len_max: int) -> int:
        frame_len = 0
        started = False

        if self.print_traffic:
            print("<<< ", end="")

        while self.program_running and frame_len < frame_len_max:
            try:
                byte = self.serial_device.read(1)
            except serial.SerialException as e:
                print(f"Error reading from serial port: {e}")
                return -1

            if self.print_traffic:
                print(f"{byte[0]:02x} ", end="")

            if byte[0] == 0x55 and started:
                self.frame.append(byte[0])
                frame_len += 1
                break

            if byte[0] == 0xaa:
                started = True

            if started:
                self.frame.append(byte[0])
                frame_len += 1

            if frame_len >= 32:
                break

        if self.print_traffic:
            print('')
            print("Received bytes: ", ' '.join(f"{b:02x}" for b in self.frame))

        return frame_len

    def extract_data(self, frame: bytearray) -> Dict[str, Union[bytearray, str]]:
        """
        Extracts the frame ID, PGN, node, and data bytes from a CAN frame.

        Args:
            frame (bytearray): A bytearray containing the CAN frame data.

        Returns:
            dict: A dictionary containing the following keys:
                * frame_id: The frame ID (4 bytes) as a string.
                * pgn: The parameter group number (2 bytes) as a string.
                * node: The node ID (1 byte) as a string.
                * data: A bytearray containing the data bytes.
        """
        try:
            # Extract frame ID, PGN, and node bytes
            frame_id_bytes = frame[self.FRAME_ID_SLICE][::-1]
            pgn_bytes = frame[self.PGN_SLICE][::-1]
            node_byte = frame[2]

            # Convert to string representations
            frame_id = frame_id_bytes.hex()
            pgn = pgn_bytes.hex()
            node = f"{node_byte:02x}"

            # Extract raw data bytes directly and strip the last two items
            data_bytes = frame[self.DATA_START_INDEX:-2]

            # Debug information
            print(f"Raw frame: {frame.hex()}")
            print(f"Frame ID bytes: {frame[self.FRAME_ID_SLICE].hex()}")
            print(f"PGN bytes: {frame[self.PGN_SLICE].hex()}")
            print(f"Data bytes: {data_bytes.hex()}")

        except IndexError as e:
            error_message = (f"Error in CAN data frame\nException: {e}\nTraceback:\n{traceback.format_exc()}")
            print(error_message)

        return {"frame_id": frame_id, "pgn": pgn, "node": node, "data": data_bytes.hex()}

    def run(self):
        while self.program_running:
            frame_len = self.frame_receive(20)

            if not self.program_running:
                break

            if frame_len == -1:
                print("Frame receive error!")
            else:
                self.data_dict = self.extract_data(self.frame)

def main():
    adapter = USB_CAN_Adapter(port='COM5')  # Change 'COM3' to your serial port
    adapter.run()

if __name__ == "__main__":
    main()