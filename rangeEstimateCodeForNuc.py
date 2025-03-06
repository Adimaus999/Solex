# -*- coding: utf-8 -*-
"""
Created on Thu Mar  6 09:02:16 2025

@author: halla
"""

# Import necessary modules
import time
import sqlite3
import numpy as np
import pandas as pd
import xgboost as xgb
import os
from sklearn.model_selection import train_test_split
import multiprocessing
import psutil
import requests
import datetime

# Set the working directory
#os.chdir("C:/Users/YourUsername/Documents/MyProject")

# Functions are defined below

# A function to read the latest SQL database data based on a column named 'timestamp'.
def SQLread(sensor_id, db_path="sensors1.db", table_name="sensor_data"):
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

# A function to remove nosie from the sensor data inputs with a Kalman filter
def kalman_filter_update(dataField, dLabel: str, iteration, P, process_variance=5e-4,
                         measurement_variance=1): 
    """
    A function to filter/ remove noise from the input sensor data using a Kalman filter. 
    The dataframe is inputted containing all sensor data. dLabel allows the type of data to be 
    specified. P is regularly updated and represents the process variance. K, the Kalman gain is
    computed and the the difference between the 'prediction' and measured value is multiplied by the 
    gain to update the prediction.The new 'filtered' value is appended to the data frame and this is returned
    along with the updated process variance.
    """
    # if insufficient data is available, initialise predicted value and process variance such that the function works
    if (iteration == 0) or (iteration == 1):
         x_pred = 0
         P = 1
    else:
        x_pred = dataField[str(dLabel)].iat[-2] 
       
    # Follow Kalman filter steps to predict next sensor value    
    P_pred = P + process_variance
        
    K = P_pred / (P_pred + measurement_variance)
    x_est = x_pred + K * (dataField[str(dLabel)].iat[-1] - x_pred)  
    P = (1 - K) * P_pred 
        
    # Append filtered value to data frame
    dataField[str(dLabel)].iat[-1] = x_est
    
    return dataField, P  

# A fucntion to interpolate the next value, according to polynomial fitting
def interpolate_next_value(arDF, dLabel: str):
    
    """
    A fucntion to interpolate the next value of sensor data if the SQL query either 
    fails or returns an unexpected nan value. The function takes the data frame of sensor data and 
    a dLabel input which allows the user to specify the sensor value of interest. It converts this
    aray of data to a numpy array and extracts the 10 most recent values. A polynomial is fitted and
    the interpolated value is appended to the input data frame.
    """
    # Convert the dataframe column of interest to a numpy array
    arr = arDF[str(dLabel)].to_numpy()
    
    # Extract all valid values in most recent 10 data entries, if they exist
    valid_values = arr[~np.isnan(arr)][-10:]
    
    # If the first sensor reading is a nan, the function replaces this with a 0 reading
    if len(valid_values) < 1:
        next_value = 0 
    # If the second value is a nan, the function replaces this with the first value
    elif len(valid_values) < 2:
        next_value = valid_values[0]    
    # Otherwise the code performs interpolation
    else:
        x = np.arange(len(valid_values))
        y = valid_values
        coeffs = np.polyfit(x, y, 1)  
        next_x = len(valid_values) 
        next_value = np.polyval(coeffs, next_x)
    
    # Append the value to the input data frame
    arDF[str(dLabel)].iat[-1] = next_value
    
    return arDF

# Function to create a new, blank data frame to append new sensor readings to
# This can easily be converted to DMatrix format, which is required for machine learning applications
def newDataStruct():
    
    """
    Create a new, blank data frame ready to recieve data to train the ML models.
    """
    
    return pd.DataFrame({
        'speed': [],  
        'acceleration': [],  
        'motorCurrent': [],  
        'motorVoltage': [],  
        'batteryCurrent': [],
        'batteryVoltage': [],
        'batteryStateOfCharge': [],
        'batteryPowerConsumption': [],
        'motorPowerConsumption': [],
        'motorBasedPowerConsumption': [],
        'target': []
    })

# Function to insert a new row into the data frame. Each value is initialsed as a zero
def appendNewZeros(dataStructure):
    
    """
    Adds a new row of zeros to the data frame so that these zeros can be replaced with 
    sensor readings as the while loop code is executed.
    """
    
    newRow = {
        'speed': 0,  
        'acceleration': 0,  
        'motorCurrent': 0,  
        'motorVoltage': 0,  
        'batteryCurrent': 0,
        'batteryVoltage': 0,
        'batteryStateOfCharge': 0,
        'batteryPowerConsumption': 0,
        'motorPowerConsumption': 0,
        'motorBasedPowerConsumption': 0,
        'target': 0
    }
    dataStructure=dataStructure.append(newRow, ignore_index=True)
    return dataStructure
    
# Funciton to assign the number of cores to the retraining process to allow efficeint parallel computing
def assign_cores_to_retrain():
    """
    A Function to assign all but one core to the retraining procecss.
    """
    p = psutil.Process()
    # Retrive the number of cores in the CPU
    cores = psutil.cpu_count(logical=False)  
    # Assign all cores to retraining process but core '0'
    p.cpu_affinity(list(range(1, cores))) 

# Fucntion to either train a new machine learning model, or retrain an existing model
def train_or_retrain(dataStructure, model_path="xgboost_model.json", temp_model_path="xgboost_model_temp.json", test_size=0.2, random_state=42):
    """
    Recieves a data frame input of training data, and either trains a new XGBoost model (if one does not already exist) or retrais an existing model
    correctly identifying what data is new from the input data frame. The retrained model is temporarily saved under a differnt name to avoid issues of calling
    a model currently being retrained during lengthy processes. The input data frame must be a copy, so that its size does not change whilst retraining occurrs.
    The function uses a train/test spilt of 80/20 as a default. For optimal computation, the maximum depth of the decision trees is set to 4, and a histogram
    method is used. Early stopping rounds is initiated so that the perfromance of  a retraining process is evaluated after 50 rounds. If no further improvement
    is made through further training, the early stopping rounds initiates and prevents further operation, reducing computational load.
    """
    
    # Assign CPU cores for retraining by calling above function
    assign_cores_to_retrain()
    
    # Split features into X and y: x for the training input data, and y for the target data
    X = dataStructure.drop(columns=['target'])
    y = dataStructure['target']

    # Train-test split: separate trainig data into training set and testing set for the model to evaluate performance
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=test_size, random_state=random_state)

    # Convert data into XGBoost's DMatrix format
    dtrain = xgb.DMatrix(X_train, label=y_train)
    dval = xgb.DMatrix(X_val, label=y_val)
    
    #Set the number of cores available for the job in XGBoost's input parameters
    num_cores = multiprocessing.cpu_count()
    
    # Define XGBost input parameters
    params = {
        "objective": "reg:squarederror",  
        "learning_rate": 0.1,
        "max_depth": 4,  
        "eval_metric": "rmse",  
        "tree_method": "hist",  
        "n_jobs": max(1, num_cores - 1) 
    }

    # Initialise default number of training rounds
    num_rounds = 1000  
    # Set minimum number of rounds before early-stopping critera can apply
    early_stopping_rounds = 50  

    # If the model already exists, begin a retrianing process
    if os.path.exists(model_path):
        
        # Access existing model
        model = xgb.Booster()
        model.load_model(model_path) 

        # Save the model with a temporary path to avoid confusing th program when calling a model for predictions if it is currently being retrained
        model.save_model(temp_model_path)

        try:
            # Continue training with previous trees
            model = xgb.train(
                params,
                dtrain,
                num_boost_round=num_rounds,
                evals=[(dtrain, "train"), (dval, "val")],
                early_stopping_rounds=early_stopping_rounds,
                verbose_eval=0,
                xgb_model=model  # Load previous trees correctly
            )
            
            # After retraining, replace the original model with the newly trained model
            model.save_model(model_path)
    
        except:
            # If retraining fails, load the temporary model (no changes to the original)
            model.load_model(temp_model_path)
            
    else:
        # The model does not yet exist at the specified file path. Train a new model from scratch.
        model = xgb.train(
            params,
            dtrain,
            num_boost_round=num_rounds,
            evals=[(dtrain, "train"), (dval, "val")],
            early_stopping_rounds=early_stopping_rounds,
            verbose_eval=0
        )

        # Save the trained model
        model.save_model(model_path)
    
    # Delete the temporary file to remove clutter
    if os.path.exists(temp_model_path):
        os.remove(temp_model_path)

# A fucntion to call the training/ retraining process twice, once for the complex model for current speed predictions, and once for the simple ML model for alternative speed strategies
def multipleTrainingProcesses(dataStructure):
    """
    A funciton to be targetted in the multiprocessing part of the script. Calling this function intiates several train/ retrain processes.
    The input to this funciton is the data frame which the fucntion edits accordingly to create te DMatrix training data sets as required.
    """
    
    # Multi-parameter ML model, using all sensor data as input
    train_or_retrain(dataStructure, model_path="xgboost_model.json", temp_model_path="xgboost_model_temp.json")
    
    # Simple ML model for alternative speed strategies. Based on battery SOC and speed only, with power consumption as training target
    train_or_retrain(dataStructure[['speed', 'batteryStateOfCharge', 'target']], model_path="simple_xgboost_model.json", temp_model_path="simple_xgboost_model_temp.json")

# A function to use the XGBoost model to preidct power consumption of the boat at a set speed.
def predict_with_model(data, model_path="xgboost_model.json"):
   """
   A function to predict the power consumption of the boat at a given speed. Data can be the full data set of live sensor readings for the current speed
   range estimaate at a set time, or just the battery SOC and speed of interest if using the simple model for alternative speed strategies. The data input is in the form f a data frame. 
   Predicitons are made and returned as a single numerical value.
   """
   
   # If the model has not yet been trained as there is not yet enough data
   if not os.path.exists(model_path):
       # If the prediction of interest was the current speed range estimate
        if model_path == "xgboost_model.json":
            # Return the preduciton as the average of the motor-based and battery-based power consumptions
            predictions = (data['motorBasedPowerConsumption'].iat[-1] + data['batteryPowerConsumption'].iat[-1])/2
        else:
            # Else return predictions for power consumption as an unreasonably high number to make easily identifyable, very low, range estimates for slow and high speed strategies
            predictions = 9999999
   else:
    
        # Load the XGBoost model
        model = xgb.Booster()
        model.load_model(model_path)

        # Convert data into DMatrix format so that XGBoost can read it
        ddata = xgb.DMatrix(data)

        # Generate model predicitons
        predictions = model.predict(ddata)
        predictions = predictions.astype(int)

   return predictions

# A function to compute the average solar irradiaiton forecast for the next 6 hours of the race, given a latitude and longitude
def get_future_solar_irradiance_avg(lat, lon, hours=6):
    """
    Uses an API to access forecast solar irradiance (GHI) for the next 6 hours using OpenWeather's Solar Forecast and computes the average.
    """
    
    #Set API key for access to OpenWeather's system
    API_KEY = "ca82eee9df7c7c0474202f4863bbf88e"
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}"

    try:
        # Use the response module to send a URL respnse request
        response = requests.get(url)
        response.raise_for_status()  
        data = response.json()

        # Return 0 if there is an issue so that the range estimatio can still work ignoring solar charging
        if "list" not in data:
            print("Error: No forecast data available.")
            return 0

        ghi_values = []

        # Extract GHI forecasts for the next 6 hours
        for forecast in data["list"][:hours]:
            ghi = forecast.get("radiation", {}).get("ghi", 0)  # Get GHI, default to 0 if missing
            ghi_values.append(ghi)
            
        # Return 0 if there is an issue so that the range estimatio can still work ignoring solar charging
        if not ghi_values:
            print("Error: No GHI data found in forecast.")
            return 0
        
        # Compute average GHI forecast value
        avg_ghi = np.mean(ghi_values)
        return avg_ghi
    
    # Return 0 if there is an issue so that the range estimatio can still work ignoring solar charging
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return 0
    
# A function to compute a range estimate for the solar boat given a speed of interest and other power consumption data
def computeRange(speedOfInterest, consumptionRate, rangeEstArray):
    """
    A function to compute the range estimate for the solar boat. It computes the energy stored in the battery, and the expected solar charging rate
    over the remainder of the race. It looks at the speed of interest and the power consumption and calculates how long the charge is expected to 
    last, and at that speed, what range this equates to. An initial cmputation assuming no solarcharghing gives an initial estimate of time duration.
    Following this, solar charging is modelled with an iterative solver looking to reach an accepatable minimal difference between range estiamtes, 
    assuming cintinually longer charge durations, and hence longer time spent recieving solar charge.
    """
    
    # Import necessary varaibles from esewhere in the script to save on input arguments
    global dataStructure, batteryCapacity, avSolarIrr, solarEff, solarArea
    
    # Read battery state of charge from data frame of sensor data
    batteryStateOfCharge = dataStructure['batteryStateOfCharge'].iat[-1]
    
    # Convert speed of interest from kmh to m/s
    speedOfInterest = speedOfInterest*1000/3600 
    
    # Check for nan values in key parameters
    if any(np.isnan(val) for val in [speedOfInterest, consumptionRate, batteryStateOfCharge, avSolarIrr, solarEff, solarArea]):
        # If any values are nan, range cannot be computed. Hence, return existing range estimate array with no update. The code will use ;ast computed range estimate.
        return rangeEstArray  

    if consumptionRate == 0:  
        # Prevent division by zero and give an  unreaistically high number for the range, assuming the current speed is 0 (boat is stationary)
        return np.append(rangeEstArray, 9999)  

    # Initial estimate assumes no solar input
    # Soalr charge time is 0
    time = 0
    # Compute initial range estimate
    rangeEstInitial = (((batteryStateOfCharge * batteryCapacity) + (avSolarIrr * solarEff * solarArea * time)) * speedOfInterest) / consumptionRate

    # Recompute the time for solar charging
    time = rangeEstInitial / speedOfInterest
    # Compute an updated range estimate assuming solar charging
    newRangeEst = (((batteryStateOfCharge * batteryCapacity) + (avSolarIrr * solarEff * solarArea * time)) * speedOfInterest) / consumptionRate

    # Set up an iteration counter for the solver incacse of diverging range estimates
    iteration_count = 0
    # Prevent infinite looping
    max_iterations = 100  

    # Continue to re-evaluate the range estimate whilst the difference between outputs is greater than 400m and the iteration count is less than the maximum number of iterations
    while (abs(newRangeEst - rangeEstInitial)>0.4) and iteration_count < max_iterations:
        rangeEstInitial = newRangeEst
        time = rangeEstInitial / speedOfInterest
        newRangeEst = (((batteryStateOfCharge * batteryCapacity) + (avSolarIrr * solarEff * solarArea * time)) * speedOfInterest) / consumptionRate
        iteration_count += 1
    
    # Convert range estmate to km
    newRangeEst = newRangeEst/1000 
    # Append to array of range estimates
    rangeEstArray = np.append(rangeEstArray, newRangeEst)
  
    # Return the array of range estimates with the new update at the end
    return rangeEstArray
        

# Now the main scheduled script
if __name__ == "__main__":    

# Initialise variables    
    # Define target speed scenarios for range estimation
    # kmh
    slowSpeed = 5
    currentSpeed = 0
    highSpeed = 15
    # Define battery capacity and convert to Ws
    batteryCapacity = 1.4e3 * 3600
    # Define the area of solar pannels on the boat m2
    solarArea = 2 
    # Define an intial estimate for the solar efficiency
    initialSolarEfficiency = 0.2
    # Define the race length
    approxRaceLength = 70 #km
    # Define the refresh rate of the range estimation script
    interval = 1
    # Initialise the electrical system efficiency as 0, to be recomputed in the script
    electricalSystemEfficiency = 0
    # Initialie loop-based counts as 0
    count = 0
    iteration = 0
    # Initialise empty singal array
    newSignal = np.array([])
    # Initialie initial values as zero for Kalman filter process variance
    P1 = 0
    P2 = 0
    P3 = 0
    P4 = 0
    P5 = 0
    P6 = 0
    P7 = 0
    P8 = 0
    P9 = 0
    # Create the empty data frame for sensor data
    dataStructure = newDataStruct()
    # Crete a separate data frame for solar power data
    solarDataStructure = pd.DataFrame({
            'solarCurrent': [],  
            'solarVoltage': []
        })
    # Set a retraining rate for the ML of every 200 new data points
    retrainRate = 200
    # Set the intial training trigger to false, so retraining won't begin until 200 data points have been collected
    retraining_active = False
    retrain_process = None
    # initialse as false; incase retraining takes longer than 200 data points, this turns to TRUE and the code is set to retrain when ready
    retrainOnNextIteration = False
    # Get new solar foreacst updates every 15 minutes
    solarForecastTrigger = 15*60 // interval
    # Initialise the soalr pannel effiency estimate
    solarEff = initialSolarEfficiency
    
    # Set window for averaging of speed in verificaiton process (mins)
    verificationWindow = 3
    # Set intial range estiamtes to 0
    currentSpeedRange = np.array([0])
    slowSpeedRange = np.array([0])
    highSpeedRange= np.array([0])
        
    # For real-time checking of the ML outputs, set the range of discrete speeds to be checked against
    speedsRangeArray = np.arange(0.5,20.5,0.5)
    # Initialise the array to strore change in SOC per unit time at different speeds
    SOCrate = np.zeros(len(speedsRangeArray))
    # Initialise the array to store the number of instances of such speed in past boat operation
    SOCcount = np.zeros(len(speedsRangeArray))
    # Rangess array
    rangessArray = np.array([0])
    
    # Set the race start time (24-hour format: HH:MM)
    target_time = "10:00"

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
    
    # Begin infinite while loop when race starts (avoid logging pre-race data, not representative of boat's performance)
    while True:
        # Start the timer to ensure regular code execution
        startTime = time.time()
        
        # Check if retraining has finished and reset `retraining_active`
        if retraining_active and (retrain_process is None or not retrain_process.is_alive()):
            # If training/ retraining has finsihed, reset status to False
            retraining_active = False
        
        # Append a new row of zeros to the data frame
        dataStructure = appendNewZeros(dataStructure)
        
        # Append a new row of zeros to the solar power data frame
        newSolarZerosRow = {
            'solarCurrent': 0,  
            'solarVoltage': 0
        }
        solarDataStructure=solarDataStructure.append(newSolarZerosRow, ignore_index=True)
        
        # Extract GPS sensor data from SQL
        
        # Speed data from SQL
        dataStructure['speed'].iat[-1] = SQLread(10)
        if np.isnan(dataStructure['speed'].iat[-1]):
            # If value unavailable, use interpolation function
            dataStructure = interpolate_next_value(dataStructure, 'speed')
        # Kalamn filter to remove noise from sensor reading
        dataStructure, P1 = kalman_filter_update(dataStructure,'speed',iteration,P1,process_variance=0.01)
        
        # Set current speed value for this execution of the while loop
        currentSpeed = dataStructure['speed'].iat[-1]
        
        # Acceleration data from SQL
        dataStructure['acceleration'].iat[-1] = SQLread(13)
        if np.isnan(dataStructure['acceleration'].iat[-1]):
             # If value unavailable, use interpolation function
            dataStructure = interpolate_next_value(dataStructure,'acceleration')
        # Kalamn filter to remove noise from sensor reading
        dataStructure, P2 = kalman_filter_update(dataStructure,'acceleration',iteration,P2,process_variance=0.01)
        
        # Motor sensor data
        
        # Motor current data from SQL
        dataStructure['motorCurrent'].iat[-1] = SQLread(18)
        if np.isnan(dataStructure['motorCurrent'].iat[-1]):
            # If value unavailable, use interpolation function
            dataStructure = interpolate_next_value(dataStructure,'motorCurrent')
        # Kalamn filter to remove noise from sensor reading
        dataStructure, P3 = kalman_filter_update(dataStructure,'motorCurrent',iteration,P3)    
        
        # Motor voltage data from SQL
        dataStructure['motorVoltage'].iat[-1] = SQLread(19)
        if np.isnan(dataStructure['motorVoltage'].iat[-1]):
            # If value unavailable, use interpolation function
            dataStructure = interpolate_next_value(dataStructure,'motorVoltage')
        # Kalamn filter to remove noise from sensor reading
        dataStructure, P4 = kalman_filter_update(dataStructure,'motorVoltage',iteration,P4)
            
        # Battery sensor data
        
        # Battery current data from SQL
        dataStructure['batteryCurrent'].iat[-1] = SQLread(27)
        if np.isnan(dataStructure['batteryCurrent'].iat[-1]):
            # If value unavailable, use interpolation function
            dataStructure = interpolate_next_value(dataStructure,'batteryCurrent')
        # Kalamn filter to remove noise from sensor reading
        dataStructure, P5 = kalman_filter_update(dataStructure,'batteryCurrent',iteration,P5)
        
        # Battery voltage data from SQL
        dataStructure['batteryVoltage'].iat[-1] = SQLread(28)
        if np.isnan(dataStructure['batteryVoltage'].iat[-1]):
            # If value unavailable, use interpolation function
            dataStructure = interpolate_next_value(dataStructure,'batteryVoltage')
        # Kalamn filter to remove noise from sensor reading
        dataStructure, P6 = kalman_filter_update(dataStructure,'batteryVoltage',iteration,P6)
        
        # Battery state of charge from SQL
        dataStructure['batteryStateOfCharge'].iat[-1] = SQLread(1)
        if np.isnan(dataStructure['batteryStateOfCharge'].iat[-1]):
            # If value unavailable, use interpolation function
            dataStructure = interpolate_next_value(dataStructure,'batteryStateOfCharge')
        # Kalamn filter to remove noise from sensor reading
        dataStructure, P7 = kalman_filter_update(dataStructure,'batteryStateOfCharge',iteration,P7,process_variance=0.01)
        
        # Compute initial power consumption estimates for battery and motor usung P=IV
        dataStructure['batteryPowerConsumption'].iat[-1] = dataStructure['batteryCurrent'].iat[-1]*dataStructure['batteryVoltage'].iat[-1]
        dataStructure['motorPowerConsumption'].iat[-1] = dataStructure['motorCurrent'].iat[-1]*dataStructure['motorVoltage'].iat[-1]
        
        # Recompute estimate of efficiency using a weighted average
        if ~np.isnan(dataStructure['batteryPowerConsumption'].iat[-1]) & ~np.isnan(dataStructure['motorPowerConsumption'].iat[-1]) & (dataStructure['batteryPowerConsumption'].iat[-1] > 0):
            efficiencyRatio = (dataStructure['motorPowerConsumption'].iat[-1]/dataStructure['batteryPowerConsumption'].iat[-1])
            electricalSystemEfficiency = (efficiencyRatio + electricalSystemEfficiency*count)/(count+1)
            count+=1
            
        # Update motor-based power consumption estimate by dividing by efficiency
        dataStructure['motorBasedPowerConsumption'].iat[-1] = dataStructure['motorPowerConsumption'].iat[-1]/electricalSystemEfficiency
        dataStructure['target'].iat[-1] = (dataStructure['motorBasedPowerConsumption'].iat[-1] + dataStructure['batteryPowerConsumption'].iat[-1])/2   
        
        # Predict power consumption at current speed using ML models
        predictionInputDataCurrentSpeed = dataStructure.drop(columns=['target']).tail(1)
        currentSpeedPowerConsumption = predict_with_model(predictionInputDataCurrentSpeed)
        # Predict power consumption at slow speed strategy using ML models
        predictionInputDataSlowSpeed = pd.DataFrame({'speed': [slowSpeed], 'batteryStateOfCharge': [(dataStructure.iloc[-1]['batteryStateOfCharge'])]})
        slowSpeedPowerConsumption = predict_with_model(predictionInputDataSlowSpeed, model_path="simple_xgboost_model.json")
        # Predict power consumption at high-speed strategy using ML models
        predictionInputDataHighSpeed = pd.DataFrame({'speed': [highSpeed], 'batteryStateOfCharge': [(dataStructure.iloc[-1]['batteryStateOfCharge'])]})
        highSpeedPowerConsumption = predict_with_model(predictionInputDataHighSpeed, model_path="simple_xgboost_model.json")
        
        # If the models have not yet been trained, we can not provide an estimate for alterate speed strategies. So, this block ensures in this case both estimates are set to nan
        if slowSpeedPowerConsumption == highSpeedPowerConsumption:
            slowSpeedPowerConsumption = np.nan
            highSpeedPowerConsumption = np.nan
        
        # Check if ML models are ready for training/ retrianing processes
        if (iteration % retrainRate == 0 and iteration > 0) or (retrainOnNextIteration == True):
            if retraining_active == True:
                retrainOnNextIteration = True
            else:
                retrainOnNextIteration = False
                dataCopy = dataStructure.copy()
                retraining_active = True
                # Start retraining process using multiprocessing to ensure code execution can continue in parallel
                retrain_process = multiprocessing.Process(target=multipleTrainingProcesses, args=(dataCopy,))
                retrain_process.start()
        
        # Check if solar forecast is required according to soalr foreacst rate defined above
        if iteration % solarForecastTrigger == 0:
            # Get the lat and long values
            latitude = SQLread(5)
            longitude = SQLread(6)
            # Call the API to get the value for average 6 hour irradiance
            avSolarIrr = get_future_solar_irradiance_avg(latitude, longitude)
        
        # Extract solar data and append to solar data frame 
        
        # Solar current data from SQL database
        solarDataStructure['solarCurrent'].iat[-1] = SQLread(24)
        if np.isnan(solarDataStructure['solarCurrent'].iat[-1]):
            # If value is missing, interpolate
            solarDataStructure = interpolate_next_value(solarDataStructure, 'solarCurrent')
        # Use Kalman filter to remove noise
        solarDataStructure, P8 = kalman_filter_update(solarDataStructure,'solarCurrent',iteration,P8)
        
        # Solar voltage data from SQL
        solarDataStructure['solarVoltage'].iat[-1] = SQLread(25)
        if np.isnan(solarDataStructure['solarVoltage'].iat[-1]):
            # if value is missing, interpolate
            solarDataStructure = interpolate_next_value(solarDataStructure, 'solarVoltage')
        # Use Kalman filter to remove noise
        solarDataStructure, P9 = kalman_filter_update(solarDataStructure,'solarVoltage',iteration,P9)
        
        # Recompute the solar panel efficiency based on measured data and a comparison to forecast irradience
        
        # If there is an error in forecasting irradiance, pass
        if avSolarIrr == 0:
            pass
        else:
        # Else, recompute effiency, gibing a weighting of 1000 data points to the pre-defined value from the manufacturer
            if iteration == 0:
                solarEff = ((initialSolarEfficiency*1000)+(((solarDataStructure['solarVoltage'].iat[-1])*(solarDataStructure['solarCurrent'].iat[-1]))/(avSolarIrr*solarArea)))/(1000 + 1)
            else:
                solarEff = ((solarEff*(1000+iteration))+(((solarDataStructure['solarVoltage'].iat[-1])*(solarDataStructure['solarCurrent'].iat[-1]))/(avSolarIrr*solarArea)))/(1000 + iteration + 1)
            
        # Compute the range of the boat for the three different speed scenarios
        currentSpeedRange = computeRange(currentSpeed, currentSpeedPowerConsumption, currentSpeedRange)
        slowSpeedRange = computeRange(slowSpeed, slowSpeedPowerConsumption, slowSpeedRange)
        highSpeedRange= computeRange(highSpeed, highSpeedPowerConsumption, highSpeedRange)
        
        # The range estimates above are in the form of an array; now access the ltest value in the array
        csRange = currentSpeedRange[-1]
        ssRange = slowSpeedRange[-1]
        hsRange = highSpeedRange[-1]
        
        # Validation step to 'sanity check' the ML output automatically
        
        # Once more than three minutes (verificaiton window) worth of data has been gathered by the code, the process begins
        if len(dataStructure['speed'])>(verificationWindow * 60 // interval):
            # Compute the average speed for the past 3 min window in the data frame
            avSpd = dataStructure['speed'].iloc[-(verificationWindow * 60 // interval):].mean()
            # Compute the reduction in SOC over this period
            SOCrateVal = (dataStructure['batteryStateOfCharge'].iat[-(verificationWindow * 60 // interval)]-dataStructure['batteryStateOfCharge'].iat[-1])/(verificationWindow*60)
            # Match the speed averaged across the window to a discrete speed in the pre-defined array
            idxSpd = (np.abs(speedsRangeArray - avSpd)).argmin()
            # Use a weighted average to adjust the rate of SOC depletion at the given speed
            SOCrate[idxSpd] = (SOCrateVal + (SOCrate[idxSpd]*SOCcount[idxSpd]))/(SOCcount[idxSpd]+1)
            # Update the count of occurrence of that speed in the boat's operation
            SOCcount[idxSpd]+=1
        
        # Compute an alternative range estiamte with no ML, based only on observed rate of SOC depletion at set speeds
        
        # Search for the speed in the pre-defined array that matches the slow speed strategy
        slowSpdIdx = (np.abs(speedsRangeArray - slowSpeed)).argmin()
        # If no data exists, set the range to a high number for ID later
        if SOCrate[slowSpdIdx]==0:
            rangeEstSS = 999999 
        else: 
            # Else compute second range estimate using below formula
            rangeEstSS = dataStructure['batteryStateOfCharge'].iat[-1] * slowSpeed * (1/3600) / SOCrate[slowSpdIdx]
            
        # Search for the speed in the pre-defined array that matches the current speed strategy
        currentSpdIdx = (np.abs(speedsRangeArray - currentSpeed)).argmin()
        # If no data exists, set the range to a high number for ID later
        if SOCrate[currentSpdIdx]==0:
            rangeEstCS = 999999 
        else: 
            # Else compute second range estimate using below formula
            rangeEstCS = dataStructure['batteryStateOfCharge'].iat[-1] * currentSpeed * (1/3600) / SOCrate[currentSpdIdx]
            
        # Search for the speed in the pre-defined array that matches the high speed strategy
        highSpdIdx = (np.abs(speedsRangeArray - highSpeed)).argmin()
        # If no data exists, set the range to a high number for ID later
        if SOCrate[highSpdIdx]==0:
            rangeEstHS = 999999 
        else: 
            # Else compute second range estimate using below formula
            rangeEstHS = dataStructure['batteryStateOfCharge'].iat[-1] * highSpeed * (1/3600) / SOCrate[highSpdIdx]
    
        # If a realistic secondary range estimate exists, that is based on more than 15 data points recorded at that speed, appraise the ML based range estiamtes
        
        # Start with slow speed esitmate
        if (~(rangeEstSS == 999999)) and (SOCcount[slowSpdIdx] > 15):
            # If the absolute difference is less than 20%, take average of observed data based range, and ML based range
            if (abs(ssRange - rangeEstSS)/rangeEstSS)<0.2:
                ssRange = (ssRange + rangeEstSS)/2
                print('adjusted by', abs(ssRange-rangeEstSS)/2)
            else:
                # Else disregard the ML-based estimate as being inaccurate
                ssRange = rangeEstSS
                print('completely adjusted')
                
        # Next, look at the current speed estimate
        if (~(rangeEstCS == 999999)) and (SOCcount[currentSpdIdx] > 15):
             # If the absolute difference is less than 20%, take average of observed data based range, and ML based range
            if (abs(csRange - rangeEstCS)/rangeEstCS)<0.2:
                csRange = (csRange + rangeEstCS)/2
                print('adjusted by', abs(csRange-rangeEstCS)/2)
            else:
                # Else disregard the ML-based estimate as being inaccurate
                csRange = rangeEstCS
                print('completely adjusted')
            
        # And finally, the high speed estiate
        if (~(rangeEstHS == 999999)) and (SOCcount[highSpdIdx] > 15):
             # If the absolute difference is less than 20%, take average of observed data based range, and ML based range
            if (abs(hsRange - rangeEstHS)/rangeEstHS)<0.2:
                hsRange = (hsRange + rangeEstHS)/2
                print('adjusted by', abs(hsRange-rangeEstHS)/2)
            else:
                # Else disregard the ML-based estimate as being inaccurate
                hsRange = rangeEstHS
                print('completely adjusted')
        
        # Speed strategy optimisation: find the optimal speed to cross the finish line with very low SOC
        # Add a 7km contingency buffer to the calculation to leave approx. 10% charge level at the end of the race
        # Retrieve distance remaining from SQL
        distanceRemaining = SQLread(29)+7
        #Initialise an array of zeros corresponding to the discrete speeds array used above
        # This will represent the range of the boat at each speed
        rangess = np.zeros(len(speedsRangeArray))
        # Allow i to take each value of the speed array in turn
        for i in speedsRangeArray:
            # Create data frame for range estimation
            predictionForRangess = pd.DataFrame({'speed': [i], 'batteryStateOfCharge': [(dataStructure.iloc[-1]['batteryStateOfCharge'])]})
            # Use simple ML models to estimate power draw at speed i
            powerConsumptionRangess = predict_with_model(predictionForRangess, model_path="simple_xgboost_model.json")
            # Compute the range estimate for this power draw and append to the array in the relevant place
            rangessArray = computeRange(i, powerConsumptionRangess, rangessArray)
        
        # Find the minimum where the difference between range and race distance remaining is least
        rangessIdx = (np.abs(rangessArray - distanceRemaining)).argmin()  
        # Optimal speed is located at this index
        rangessOptimalSpeed = speedsRangeArray[rangessIdx]
        
        # End of the loop, now the scheduling command evaluates the time to pause before beginning the next iteration
        print('reached the end')
        print(ssRange, csRange, hsRange)
        iteration+=1
        elapsed = time.time()-startTime
        time.sleep(max(0, interval - elapsed))

