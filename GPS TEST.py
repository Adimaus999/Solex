import geopy.distance
import random
from datetime import datetime
import time


cumulative_distance = 0
prev_velocity = 0

while True:
    # Add small random amount to coordinates
    
    coords_1 = (random.uniform(50, 50.0001), random.uniform(-4.9999, -5))
    time_1 = datetime.now()
    time.sleep(random.uniform(1, 2))
    coords_2 = (random.uniform(50, 50.0001), random.uniform(-4.9999, -5))
    time_2 = datetime.now()
    
    time_difference = time_2 - time_1

    # Extract the difference in seconds
    seconds = time_difference.total_seconds()
    
    distance_m = geopy.distance.geodesic(coords_1, coords_2).m
    cumulative_distance += distance_m
    velocity = distance_m / seconds  
    
    acceleration = (velocity - prev_velocity)/seconds
    prev_velocity = velocity
    
    print("Velocity:", velocity, "m/s")
    print("Cumulative distance:", cumulative_distance, "m")
    print("Acceleration:", acceleration, "m/s^2")
    
    
