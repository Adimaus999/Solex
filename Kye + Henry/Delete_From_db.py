import sqlite3
conn = sqlite3.connect('sensors1.db')
cursor = conn.cursor()

cursor.execute("DELETE FROM sensor_data")
cursor.execute("DELETE FROM sensor_logs")
cursor.execute("DELETE FROM range_estimates")
cursor.execute("DELETE FROM race_length")
conn.commit()
conn.close()

print("Data deleted")