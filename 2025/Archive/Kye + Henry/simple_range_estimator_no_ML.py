# -*- coding: utf-8 -*-
"""
Created on Mon Mar 17 09:51:27 2025

@author: halla
"""

"""
A script to perform a simple range estimate for the soalr boat.
"""

"""
Import modules
"""

import sqlite3
import numpy as np
import datetime
from datetime import datetime
import time
import pandas as pd

"""
Functions
"""

def SQLread(sensor_id, db_path="SoleX_Database.db", table_name="sensor_data"):
    """
    Fucntion to extract most recent sensor data from an SQL database according to the timestamp column. The function 
    returns the sensor data sepcified according to the input 'sensor_id'. If there is any error, the function returns
    a nan.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = f"""
        SELECT value FROM {table_name} 
        WHERE sensor_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 1
        """
        
        cursor.execute(query, (sensor_id,))
        result = cursor.fetchone()

        conn.close()

        # Return nan if not found
        return result[0] if result and result[0] is not None else np.nan

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return np.nan  
    except Exception as e:
        print(f"Error: {e}")
        return np.nan
    
def newDataStruct():
    
    """
    Create a new, blank data frame ready to recieve data to train the ML models.
    """
    
    return pd.DataFrame({
        'speed': [],  
        'batteryCurrent': [],
        'batteryVoltage': [],
        'batteryStateOfCharge': [],
        'batteryPowerConsumption': [],
        'solarCurrent': [],
        'solarVoltage': []
    })

# Function to insert a new row into the data frame. Each value is initialsed as a zero
def appendNewZeros(dataStructure):
    
    """
    Adds a new row of zeros to the data frame so that these zeros can be replaced with 
    sensor readings as the while loop code is executed.
    """
    
    newRow = {
        'speed': 0,
        'batteryCurrent': 0,
        'batteryVoltage': 0,
        'batteryStateOfCharge': 0,
        'batteryPowerConsumption': 0,
        'solarCurrent': 0,
        'solarVoltage': 0
        }
    dataStructure = pd.concat([dataStructure, pd.DataFrame([newRow])], ignore_index=True)
    return dataStructure

"""
The main script
"""

if __name__=="__main__":
    
    # Connect to an existing database 
    conn = sqlite3.connect('SoleX_Database.db')
    cursor = conn.cursor()
    
    # Check if the table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='range_estimates'")
    table_exists = cursor.fetchone()
    
    # Create the table if it does not exist
    if not table_exists:
        create_table_query = '''
        CREATE TABLE IF NOT EXISTS range_estimates (
            timestamp TEXT,
            ssRange REAL,
            csRange REAL,
            hsRange REAL,
            optimalSpeed REAL
        )
        '''
        cursor.execute(create_table_query)
        print("Table created successfully.")
    else:
        pass
    
    # Commit the changes and close the connection
    conn.commit()
    conn.close()
    
    # Define target speed scenarios for range estimation
    # kmh
    currentSpeed = 0
    
    # Pandas data frame to store data
    dataStructure = newDataStruct()
    
    # Define battery capacity and convert to Ws
    batteryCapacity = 1357.8 * 3600
    
    # Define the race length
    conn = sqlite3.connect('SoleX_Database.db')
    cursor = conn.cursor()
    sqlquery = '''SELECT raceLength FROM race_length ORDER BY datetime(timestamp) DESC LIMIT 1'''
    cursor.execute(sqlquery)
    approxRaceLength = cursor.fetchone()[0]
    conn.close()
    
    # Define the refresh rate of the range estimation script
    interval = 5
    iteration = 0
    
    # Initialise empty arrays for range
    csRangeArray = np.arrray([])
    
    # Set a retraining rate for the ML of every 200 new data points
    retrainRate = 200
    
    # Set the race start time (24-hour format: HH:MM)
    target_time = "09:00"

    # Convert target time to datetime format
    target_dt = datetime.strptime(target_time, "%H:%M").replace(
        year=datetime.now().year, 
        month=datetime.now().month, 
        day=datetime.now().day
        )

    # Wait until the target time is reached
    while datetime.now() < target_dt:
        # Check every second
        time.sleep(1) 
    
    while True:
        # Start the timer to ensure regular code execution
        startTime = time.time()
        
        # Append a new row of zeros to the data frame
        dataStructure = appendNewZeros(dataStructure)
        
        # Gather most recent sensor data from SQL
        # Speed
        dataStructure['speed'].iat[-1] = SQLread(10)*3.6
        # BatteryCurrent
        dataStructure['batteryCurrent'].iat[-1] = SQLread(27)
        # BatteryVoltage
        dataStructure['batteryVoltage'].iat[-1] = SQLread(28)
        # BatteryStateOfCharge
        dataStructure['batteryStateOfCharge'].iat[-1] = SQLread(1)
        # BatteryPowerConsumption
        dataStructure['batteryPowerConsumption'].iat[-1] = dataStructure['batteryCurrent'].iat[-1] * dataStructure['batteryVoltage'].iat[-1]
        # SolarCurrent
        dataStructure['solarCurrent'].iat[-1] = SQLread(24)
        # SolarVoltage
        dataStructure['solarVoltage'].iat[-1] = SQLread(25)
        
        # Compute range estimates
        
        csRange = ((dataStructure['batteryStateOfCharge'].iat[-1] * batteryCapacity) * (currentSpeed*1000/3600)) / dataStructure['batteryPowerConsumption'].iat[-1]
        if (len(csRangeArray)==0) and np.isnan(csRange):
            csRange = 0
        elif np.isnan(csRange):
            csRange = csRangeArray[-1]
        else:
            csRangeArray = np.append(csRangeArray, csRange)
       
        # Set speed ptimiser to 9999 as an unrealistically high number, as it is not computed in this script
        rangessOptimalSpeed = 9999
        ssRange = 0
        hsRange = 0

        # Convert to float to avoid BLOB in SQL
        ssRange = float(ssRange)
        csRange = float(csRange)
        hsRange = float(hsRange)
        rangessOptimalSpeed = float(rangessOptimalSpeed)

        # Connect to the existing database
        conn = sqlite3.connect('SoleX_Database.db')
        cursor = conn.cursor()

        # SQL query to insert data into the table
        insert_query = '''
        INSERT INTO range_estimates (timestamp, ssRange, csRange, hsRange, optimalSpeed)
        VALUES (?, ?, ?, ?, ?)
        '''

        # Insert data into the table
        cursor.execute(insert_query, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ssRange, csRange, hsRange, rangessOptimalSpeed))

        # Commit the changes and close the connection
        conn.commit()
        conn.close()
        
        # Complete while loop with increase in iteration count and time sleep according to elapsed time
        iteration+=1
        elapsed = time.time()-startTime
        time.sleep(max(0, interval - elapsed))