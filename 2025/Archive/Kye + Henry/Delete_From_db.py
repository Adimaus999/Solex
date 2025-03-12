import sqlite3
conn = sqlite3.connect('C:/Users/kyeba/OneDrive/Documents/Group Project/Coding/Solex/Kye/Solex/2025/Working_Files/Database/SoleX_Database.db')
cursor = conn.cursor()

cursor.execute("DELETE FROM sensor_data")
cursor.execute("DELETE FROM sensor_logs")
cursor.execute("DELETE FROM range_estimates")
cursor.execute("DELETE FROM race_length")
conn.commit()
conn.close()

print("Data deleted")