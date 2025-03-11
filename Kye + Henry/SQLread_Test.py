import sqlite3
import numpy as np

def SQLread(sensor_id, db_path="sensors1.db", table_name="sensor_data"):
    """
    Function to extract most recent sensor data from an SQL database according to the timestamp column. The function 
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
    
print(SQLread(30))
print(int(SQLread(10)))


conn = sqlite3.connect('sensors1.db')
cursor = conn.cursor()
sqlquery = '''SELECT raceLength FROM race_length ORDER BY datetime(timestamp) DESC LIMIT 1'''
cursor.execute(sqlquery)
initial_race_length = cursor.fetchone()[0]
conn.close()

print(initial_race_length)