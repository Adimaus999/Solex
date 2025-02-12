import sqlite3
import os
from datetime import datetime

def process_and_store_data(hex_string):
    db_name = 'device_data2.db'  # Hardcoded database name

    # Split the hex string into 4 parts (reverse order)
    part4 = int(hex_string[-2:], 16)  # Last byte (last two hex characters)
    part3 = int(hex_string[-4:-2], 16)  # Second last byte
    part2 = int(hex_string[-6:-4], 16)  # Third last byte
    part1 = int(hex_string[-8:-6], 16)  # First byte (beginning two hex characters)
    
    # Initialize variables for alarms and status
    alarm1 = ""
    alarm2 = ""
    status = ""

    # Alarm 1 conditions (analyzing part1)
    if part1 & 0x80:  # Pack low-voltage alarm
        alarm1 += "Pack low-voltage alarm, "
    if part1 & 0x20:  # Over-temperature protection during discharge
        alarm1 += "Over-temperature protection during discharge, "
    if part1 & 0x10:  # Overload protection
        alarm1 += "Overload protection, "
    if part1 & 0x02:  # Cell low voltage alarm
        alarm1 += "Cell low voltage alarm, "

    # Alarm 2 conditions (analyzing part2)
    if part2 & 0x40:  # Over-current alarm during discharge
        alarm2 += "Over-current alarm during discharge, "
    if part2 & 0x20:  # Pack under-voltage protection
        alarm2 += "Pack under-voltage protection, "
    if part2 & 0x10:  # Cell under-voltage protection
        alarm2 += "Cell under-voltage protection, "
    if part2 & 0x02:  # Over-temperature alarm
        alarm2 += "Over-temperature alarm, "

    # Status conditions (analyzing part3)
    if part3 & 0x40:  # Fully charged status (SOC = 100%)
        status += "Fully charged status (SOC = 100%), "
    if part3 & 0x20:  # Heating-element ON
        status += "Heating-element ON, "
    if part3 & 0x04:  # Discharge current detected
        status += "Discharge current detected, "
    if part3 & 0x02:  # Charging current detected
        status += "Charging current detected, "

    # Remove trailing commas and spaces
    alarm1 = alarm1.strip(', ') if alarm1 else "No alarms"
    alarm2 = alarm2.strip(', ') if alarm2 else "No alarms"
    status = status.strip(', ') if status else "No status"

    # SOC (raw value from part4)
    soc = part4  # Directly take the last byte as the raw SOC

    # Check if the database exists, if not, create it and the table
    if not os.path.exists(db_name):
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS device_data (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TEXT,
                            alarm1 TEXT,
                            alarm2 TEXT,
                            status TEXT,
                            soc INTEGER
                          )''')
        conn.commit()
        conn.close()
        print(f"Database '{db_name}' and table 'device_data' created.")
    else:
        print(f"Database '{db_name}' already exists.")

    # Connect to the SQLite database
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Get current timestamp
    current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Insert the data into the table
    cursor.execute('''INSERT INTO device_data (timestamp, alarm1, alarm2, status, soc)
                      VALUES (?, ?, ?, ?, ?)''', 
                      (current_timestamp, alarm1, alarm2, status, soc))

    # Commit the transaction and close the connection
    conn.commit()
    conn.close()

    # Confirmation message
    print("Data has been written to the database with the current timestamp.")


# Example usage with hex string
hex_string = "2081210100000064"  # Example hex string

# Process the data and store it in the database
process_and_store_data(hex_string)
