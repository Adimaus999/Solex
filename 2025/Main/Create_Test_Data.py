import numpy as np

import pandas as pd

from matplotlib import pyplot as plt

# max current 8.5a at 12v 3. 3.5

 

sensorDataInputs = pd.DataFrame({

        'speed': [], 

        'acceleration': [], 

        'motorCurrent': [], 

        'motorVoltage': [], # 56.8 to 42 (nom 51.2)

        'batteryCurrent': [], # 100A max, 50 nom, (discharge 1.5C)

        'batteryVoltage': [],

        'batteryStateOfCharge': [],

        'solarCurrent': [], # 2kw 95%

        'solarVoltage': [], # 56.8

        'timestamp':[]

    })

 

time = np.arange(0,21600,3)

 

speed = 9+3*np.cos(2*np.pi*time/600)

speed_noise = np.random.normal(0, 0.2, len(speed))  # Small noise for realism

speed_noisy = speed + speed_noise

 

dt = time[1]-time[0]

# acceleration = np.gradient(speed, dt)

 

period = 3600

half_period = period // 2  # 1800 seconds

growth = np.linspace(0, 1, half_period // dt)  # Linearly growing

decay = np.linspace(1, 0, half_period // dt)   # Linearly decaying

one_period_amplitude = np.concatenate((growth, decay))

 

# Tile the pattern to cover the full 6-hour duration

total_time = time[-1]+dt

num_repeats = total_time // period

amplitude = np.tile(one_period_amplitude, num_repeats)

 

# Generate noise, scaled by amplitude

noise = np.random.normal(loc=0, scale=1, size=len(time))  # Zero-mean Gaussian noise

acceleration = amplitude * noise  # Scale noise with changing sea-state amplitude

 

# Base voltage around 51.2V

mean_voltage = 51.2

std_dev_data = 0.8  # Noise level for voltage data

std_dev_signal = 1.0  # Slightly different noise for signal

 

# Generate noise for both datasets

noise_data = np.random.normal(0, std_dev_data, len(time))  # Noise for voltage data

noise_signal = np.random.normal(0, std_dev_signal, len(time))  # Different noise for signal

 

# Add occasional larger transients

transient_prob = 0.005  # ~0.5% chance per point

transients_data = (np.random.rand(len(time)) < transient_prob) * np.random.uniform(-2, 2, len(time))

transients_signal = (np.random.rand(len(time)) < transient_prob) * np.random.uniform(-2, 2, len(time))

 

# Compute final voltage signals

voltage_data = mean_voltage + noise_data + transients_data

voltage_signal = mean_voltage + noise_signal + transients_signal  # Different noise, same base trend

 

# Clip to stay within [42, 56.8]V

batteryVoltage = np.clip(voltage_data, 42, 56.8)

motorVoltage = np.clip(voltage_signal, 42, 56.8)

 

# Generate speed array with noise

speed = 9 + 3 * np.cos(2 * np.pi * time / 600)

speed_noise = np.random.normal(0, 0.2, len(speed))  # Small noise for speed

speed_noisy = speed + speed_noise

 

# Define battery current based on speed^3 relation

speed_min, speed_max = 6, 12  # Given speed range

current_min, current_max = 10, 50  # Assumed min/max battery current

 

# Normalize speed to range 0-1, then scale to battery current range

battery_current = current_min + (current_max - current_min) * ((speed_noisy - speed_min) / (speed_max - speed_min))**3

 

# Add battery current noise

battery_noise = np.random.normal(0, 2, len(battery_current))  # Small noise

battery_current_noisy = np.clip(battery_current + battery_noise, current_min, current_max)  # Ensure within valid range

 

# Compute motor current with 85% electrical efficiency

motor_current = battery_current_noisy * 0.85 

 

# Add a different noise profile for motor current (higher variance)

motor_noise = np.random.normal(0, 3, len(motor_current))  # Slightly larger noise

motor_current_noisy = np.clip(motor_current + motor_noise, 0, current_max)  # Ensure valid range

 

 

# Battery capacity (in kWh) and initial SOC (100%)

battery_capacity_kWh =  (26.52*51.2)/1000

initial_soc = 1.0  # 100% charge

 

# Assume a nominal voltage of the battery (in volts)

battery_voltage = batteryVoltage

 

 

 

# Compute energy consumed in each time step (in kWh)

# Energy (in kWh) = Current (in A) * Voltage (in V) * Time (in hours)

energy_consumed = (motor_current_noisy * battery_voltage * dt) / 3600 / 1000  # Convert to kWh

 

# Solar power generation (in kW) with 95% efficiency

solar_power_max = 2.0  # Maximum power in kW

solar_efficiency = 0.95  # 95% efficiency

availablePower = 0.7

solar_power = solar_power_max * solar_efficiency * availablePower  # Peak solar power in kW

 

# Solar current based on power and battery voltage

solar_current = (solar_power * 1000) / battery_voltage  # Convert to Amps (1 kW = 1000 W)

 

# Add noise to simulate solar sensor error (e.g., 2-3% noise)

solar_current_noise = np.random.normal(0, 0.03, len(solar_current))  # 3% noise

solar_current_noisy = np.clip(solar_current + solar_current_noise, 0, None)  # Ensure current is non-negative

 

# Calculate SOC over time by subtracting the energy consumed and adding the solar energy

soc = np.zeros(len(time))

soc[0] = initial_soc  # Start at 100% SOC

 

# Add solar energy to SOC and subtract battery energy consumption

for i in range(1, len(time)):

    # Compute energy consumed by motor and energy provided by solar

    energy_consumed_step = (motor_current_noisy[i] * battery_voltage[i] * dt) / 3600 / 1000  # kWh

    solar_energy_step = (solar_current_noisy[i] * battery_voltage[i] * dt) / 3600 / 1000  # kWh

   

    # Update SOC considering both energy consumed by motor and energy gained from solar

    soc[i] = soc[i-1] - (energy_consumed_step / battery_capacity_kWh) + (solar_energy_step / battery_capacity_kWh)

   

    # Ensure SOC stays within 0 and 1

    soc[i] = np.clip(soc[i], 0, 1)

 

# # Plot results

# plt.figure(figsize=(10, 6))

 

# # Plot motor current

# plt.subplot(4, 1, 1)

# plt.plot(time / 3600, motor_current_noisy, label="Motor Current (A)", color='g')

# plt.xlabel("Time (hours)")

# plt.ylabel("Motor Current (A)")

# plt.legend()

# plt.grid()

 

# # Plot solar current

# plt.subplot(4, 1, 2)

# plt.plot(time / 3600, solar_current_noisy, label="Solar Current (A)", color='orange')

# plt.xlabel("Time (hours)")

# plt.ylabel("Solar Current (A)")

# plt.legend()

# plt.grid()

 

# # Plot state of charge (SOC)

# plt.subplot(4, 1, 3)

# plt.plot(time / 3600, soc, label="State of Charge (SOC)", color='b')

# plt.xlabel("Time (hours)")

# plt.ylabel("SOC")

# plt.legend()

# plt.grid()

 

# # Plot state of charge (SOC)

# plt.subplot(4, 1, 4)

# plt.plot(time / 3600, speed, label="Speed", color='r')

# plt.xlabel("Time (hours)")

# plt.ylabel("Speed (km/h)")

# plt.legend()

# plt.grid()

 

# plt.tight_layout()

# plt.show()

 

# plt.plot(time, speed)

 

sensorDataInputs['speed']=speed

sensorDataInputs['acceleration'] = acceleration

sensorDataInputs['motorCurrent'] = motor_current_noisy

sensorDataInputs['motorVoltage'] = motorVoltage

sensorDataInputs['batteryCurrent'] = battery_current_noisy

sensorDataInputs['batteryVoltage'] = battery_voltage

sensorDataInputs['batteryStateOfCharge'] = soc

sensorDataInputs['solarCurrent'] = solar_current_noisy 

sensorDataInputs['solarVoltage'] = battery_voltage

sensorDataInputs['timestamp'] = time

 

motorCurrent = motor_current_noisy

batteryCurrent = battery_current_noisy

batteryVoltage = battery_voltage

solarCurrent = solar_current_noisy

solarVoltage = battery_voltage

 

import sqlite3

 

db_path = 'SoleX_Database.db'

 

from datetime import datetime

import time as ttt

 

id = 100000

 

for i in range(len(time)):
    conn = sqlite3.connect(db_path)

 

    cursor = conn.cursor()
# 1          battery_soc

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 1, soc[i], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 2          battery_alarm1

    timestamp2 = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute("INSERT INTO sensor_logs (id, sensor_id, message, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 2, 'No error 2', timestamp2))

    #conn.commit()

    id+=1

# 3          battery_alarm2

    timestamp2 = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute("INSERT INTO sensor_logs (id, sensor_id, message, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 3, 'No error 3', timestamp2))

    #conn.commit()

    id+=1

# 4          battery_status

    timestamp2 = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute("INSERT INTO sensor_logs (id, sensor_id, message, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 4, 'Charging', timestamp2))

    #conn.commit()

    id+=1

# 5          gps_latitude

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 5, 50.1710, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 6          gps_longitude

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 6, -5.1246, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 7          velocity_x

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 7, 66, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 8          velocity_y

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 8, 67, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 9          velocity_z

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 9, 68, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 10       velocity_t

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 10, speed[i]/3.6, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 11       acceleration_x

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 11, 12, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 12       acceleration_y

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 12, 13, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 13       acceleration_z

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 13, acceleration[i], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 14       acceleration_t

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 14, 14, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 15       heading

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 15, 90.01, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 16       temperature

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 16, 25.4, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 17       motor_power

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 17, motorVoltage[i]*motorCurrent[i], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 18       motor_current

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 18, motorCurrent[i], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 19       motor_voltage

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 19, motorVoltage[i], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 20       solar_power

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 20, solarCurrent[i]*solarVoltage[i], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 21       auxiliary_power

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 21, 20.5, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 22       auxiliary_current

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 22, 22.2, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 23       auxiliary_voltage

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 23, 33.3, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 24       solar_current

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 24, solarCurrent[i], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 25       solar_voltage

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 25, solarVoltage[i], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 26       battery_power

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 26, batteryVoltage[i]*batteryCurrent[i], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 27       battery_current

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 27, batteryCurrent[i], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 28       battery_voltage

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 28, batteryVoltage[i], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 29       distance

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 29, 0.05, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

# 30       total_distance

    cursor.execute("INSERT INTO sensor_data (id, sensor_id, value, timestamp) VALUES (?, ?, ?, ?)",

                   (id, 30, 30, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #conn.commit()

    id+=1

   

    conn.commit()
    conn.close()
    print('Uploaded')

    ttt.sleep(0.6)