import can
import os
import time

def setup_can_interface():
    os.system("sudo ip link set can0 down")
    os.system("sudo ip link set can0 type can bitrate 250000 txqueuelen 1000")
    os.system("sudo ip link set can0 up")
    print("CAN interface can0 set up successfully!")

def send_can_message():
    bus = can.interface.Bus(channel='can0', bustype='socketcan')
    msg = can.Message(arbitration_id=0x5FF, data=[20, 81, 21, 0, 0, 0, 0, 100], is_extended_id=False)
    
    while True:
        try:
            bus.send(msg)
            print("Message sent: ID=0x5FF, Data=[20, 81, 21, 0, 0, 0, 0, 100]")
            time.sleep(1)
        except can.CanError:
            print("Failed to send message!")
            break

if __name__ == "__main__":
    setup_can_interface()
    send_can_message()
