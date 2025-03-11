import sqlite3
import os
from datetime import datetime
import time

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
        timestamp TEXT NOT NULL,
        error_1 INTEGER NOT NULL,
        error_2 INTEGER NOT NULL,
        status TEXT NOT NULL,
        soc REAL NOT NULL
    );
    """

    try:
        cursor.execute(create_table_query)
        print("Table created successfully (if it didn't exist).")
    except sqlite3.Error as e:
        print(f"Error creating table: {e}")
        return False

    conn.close()
    return True


def insert_data(db_name, soc, error_1, error_2, status):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Get the current date and time
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Insert data into the table
    insert_data_query = """
    INSERT INTO data_table (timestamp, error_1, error_2, status, soc)
    VALUES (?, ?, ?, ?, ?);
    """

    data = (current_time, error_1, error_2, status, soc)

    try:
        cursor.execute(insert_data_query, data)
        conn.commit()  # Commit the changes to the database
        print(f"Data inserted: SOC = {soc}, Status = {status}")
    except sqlite3.Error as e:
        print(f"Error inserting data: {e}")

    # Close the database connection
    conn.close()


def run_charging_cycle(db_name):
    # Iterate for 100 seconds, simulating a charging cycle
    for soc in range(101):  # SOC from 0 to 100
        # Insert data into the database each second
        insert_data(db_name, soc, 0, 0, 'charging')
        time.sleep(1)  # Wait for 1 second


if __name__ == "__main__":
    db_name = "db_test.db"  # Updated database file name

    # Check and create the database and table
    if check_and_create_database(db_name):
        print("Database setup completed successfully.")
    
    # Run the charging cycle for 100 seconds
    print("Starting charging cycle...")
    run_charging_cycle(db_name)
    print("Charging cycle completed.")
