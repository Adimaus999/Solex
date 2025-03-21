# -*- coding: utf-8 -*-
"""
Created on Mon Mar 17 08:27:37 2025

@author: halla
"""

"""
A script to perform a simple range estimate for the solar boat.
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
import xgboost as xgb
import os
from sklearn.model_selection import train_test_split
import multiprocessing

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

# Fucntion to either train a new machine learning model, or retrain an existing model
def train_or_retrain(dataStructure, model_path="xgboost_model_V2_code.json", temp_model_path="xgboost_model_temp_V2_code.json", test_size=0.2, random_state=42):
    """
    Recieves a data frame input of training data, and either trains a new XGBoost model (if one does not already exist) or retrais an existing model
    correctly identifying what data is new from the input data frame. The retrained model is temporarily saved under a differnt name to avoid issues of calling
    a model currently being retrained during lengthy processes. The input data frame must be a copy, so that its size does not change whilst retraining occurrs.
    The function uses a train/test spilt of 80/20 as a default. For optimal computation, the maximum depth of the decision trees is set to 4, and a histogram
    method is used. Early stopping rounds is initiated so that the perfromance of  a retraining process is evaluated after 50 rounds. If no further improvement
    is made through further training, the early stopping rounds initiates and prevents further operation, reducing computational load.
    """
    
    # Split features into X and y: x for the training input data, and y for the target data
    X = dataStructure.drop(columns=['batteryCurrent', 'batteryVoltage', 'batteryPowerConsumption', 'solarCurrent', 'solarVoltage'])
    y = dataStructure['batteryPowerConsumption']

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
        
# A function to use the XGBoost model to preidct power consumption of the boat at a set speed.
def predict_with_model(data, model_path="xgboost_model_V2_code.json"):
   """
   A function to predict the power consumption of the boat at a given speed. Data can be the full data set of live sensor readings for the current speed
   range estimaate at a set time, or just the battery SOC and speed of interest if using the simple model for alternative speed strategies. The data input is in the form f a data frame. 
   Predicitons are made and returned as a single numerical value.
   """
   global currentSpeed, dataStructure
   # If the model has not yet been trained as there is not yet enough data
   if not os.path.exists(model_path):
       # If the prediction of interest was the current speed range estimate
        if data['speed'].iat[-1] == currentSpeed:
            # Return the prediction as the SQL-based battery power consumption
            predictions = dataStructure['batteryPowerConsumption'].iat[-1]
        else:
            # Else return predictions for power consumption as an unreasonably high number to make easily identifyable, very low, range estimates for slow and high speed strategies
            predictions = np.nan
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
    slowSpeed = 5
    currentSpeed = 0
    highSpeed = 15
    
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
    interval = 1
    iteration = 0
    
    # Initialise empty arrays for range
    ssRangeArray = np.array([])
    csRangeArray = np.array([])
    hsRangeArray = np.array([])
    
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
        currentSpeed = max(0.001, dataStructure['speed'].iat[-1])
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
        
        # If 200 data points have been reached, train model
        if (iteration % retrainRate == 0 and iteration > 0):
            train_or_retrain(dataStructure)
        
        # Use ML model to predict power consumption
        # Predict power consumption at current speed using ML models
        predictionInputDataCurrentSpeed = pd.DataFrame({'speed': [currentSpeed], 'batteryStateOfCharge': [(dataStructure.iloc[-1]['batteryStateOfCharge'])]})
        currentSpeedPowerConsumption = predict_with_model(predictionInputDataCurrentSpeed)
        # Predict power consumption at slow speed strategy using ML models
        predictionInputDataSlowSpeed = pd.DataFrame({'speed': [slowSpeed], 'batteryStateOfCharge': [(dataStructure.iloc[-1]['batteryStateOfCharge'])]})
        slowSpeedPowerConsumption = predict_with_model(predictionInputDataSlowSpeed)
        # Predict power consumption at high-speed strategy using ML models
        predictionInputDataHighSpeed = pd.DataFrame({'speed': [highSpeed], 'batteryStateOfCharge': [(dataStructure.iloc[-1]['batteryStateOfCharge'])]})
        highSpeedPowerConsumption = predict_with_model(predictionInputDataHighSpeed)
        
        # Compute range estimates
        # Fist, compute distance remaining
        # distanceRemaining = max(0, (approxRaceLength - (SQLread(30)/1000)))
        # slowSpeedTime = (distanceRemaining / slowSpeed) * 3600
        # currentSpeedTime = (distanceRemaining / currentSpeed) * 3600 
        # highSpeedTime = (distanceRemaining / highSpeed) * 3600
        max_iter = 10000
        
        ssRange = (((dataStructure['batteryStateOfCharge'].iat[-1] * batteryCapacity)  * (slowSpeed*1000/3600)) / slowSpeedPowerConsumption) * (1/1000)
        slowSpeedTime = (ssRange / slowSpeed) * 3600
        ssRangeNew = ((((dataStructure['batteryStateOfCharge'].iat[-1] * batteryCapacity) + (dataStructure['solarCurrent'].iat[-1] * dataStructure['solarVoltage'].iat[-1] * slowSpeedTime)) * (slowSpeed*1000/3600)) / slowSpeedPowerConsumption) * (1/1000)
        iter_count = 0
        while (ssRangeNew-ssRange>0.01) and (iter_count < max_iter):
            iter_count+=1
            slowSpeedTime = (ssRangeNew / slowSpeed) * 3600
            ssRange = ssRangeNew
            ssRangeNew = ((((dataStructure['batteryStateOfCharge'].iat[-1] * batteryCapacity) + (dataStructure['solarCurrent'].iat[-1] * dataStructure['solarVoltage'].iat[-1] * slowSpeedTime)) * (slowSpeed*1000/3600)) / slowSpeedPowerConsumption) * (1/1000)
        ssRange = ssRangeNew
        if (len(ssRangeArray)==0) and np.isnan(ssRange):
            ssRange = 0
        elif np.isnan(ssRange):
            ssRange = ssRangeArray[-1]
        else:
            ssRangeArray = np.append(ssRangeArray, ssRange)
        
        csRange = (((dataStructure['batteryStateOfCharge'].iat[-1] * batteryCapacity)  * (currentSpeed*1000/3600)) / currentSpeedPowerConsumption) * (1/1000)
        currentSpeedTime = (csRange / currentSpeed) * 3600
        csRangeNew = ((((dataStructure['batteryStateOfCharge'].iat[-1] * batteryCapacity) + (dataStructure['solarCurrent'].iat[-1] * dataStructure['solarVoltage'].iat[-1] * currentSpeedTime)) * (currentSpeed*1000/3600)) / currentSpeedPowerConsumption) * (1/1000)
        iter_count = 0
        while (csRangeNew-csRange>0.01) and (iter_count < max_iter):
            iter_count+=1
            currentSpeedTime = (csRangeNew / currentSpeed) * 3600
            csRange = csRangeNew
            csRangeNew = ((((dataStructure['batteryStateOfCharge'].iat[-1] * batteryCapacity) + (dataStructure['solarCurrent'].iat[-1] * dataStructure['solarVoltage'].iat[-1] * currentSpeedTime)) * (currentSpeed*1000/3600)) / currentSpeedPowerConsumption) * (1/1000)
        csRange = csRangeNew
        if (len(csRangeArray)==0) and np.isnan(csRange):
            csRange = 0
        elif np.isnan(csRange):
            csRange = csRangeArray[-1]
        else:
            csRangeArray = np.append(csRangeArray, csRange)
        
        hsRange = (((dataStructure['batteryStateOfCharge'].iat[-1] * batteryCapacity)  * (highSpeed*1000/3600)) / highSpeedPowerConsumption) * (1/1000)
        highSpeedTime = (hsRange / highSpeed) * 3600
        hsRangeNew = ((((dataStructure['batteryStateOfCharge'].iat[-1] * batteryCapacity) + (dataStructure['solarCurrent'].iat[-1] * dataStructure['solarVoltage'].iat[-1] * highSpeedTime)) * (highSpeed*1000/3600)) / highSpeedPowerConsumption) * (1/1000)
        iter_count = 0
        while (hsRangeNew-hsRange>0.4) and (iter_count < max_iter):
            iter_count+=1
            highSpeedTime = (hsRangeNew / highSpeed) * 3600
            hsRange = hsRangeNew
            hsRangeNew = ((((dataStructure['batteryStateOfCharge'].iat[-1] * batteryCapacity) + (dataStructure['solarCurrent'].iat[-1] * dataStructure['solarVoltage'].iat[-1] * highSpeedTime)) * (highSpeed*1000/3600)) / highSpeedPowerConsumption) * (1/1000)
        hsRange = hsRangeNew
        if (len(hsRangeArray)==0) and np.isnan(hsRange):
            hsRange = 0
        elif np.isnan(hsRange):
            hsRange = hsRangeArray[-1]
        else:
            hsRangeArray = np.append(hsRangeArray, hsRange)
          
        # Set speed optimiser to 9999 as an unrealistically high number, as it is not computed in this script
        
        rangessOptimalSpeed = 9999
        
        ssRange = 9999 if np.isinf(ssRange) else (0 if np.isnan(ssRange) else ssRange)
        csRange = 9999 if np.isinf(csRange) else (0 if np.isnan(csRange) else csRange)
        hsRange = 9999 if np.isinf(hsRange) else (0 if np.isnan(hsRange) else hsRange)
        
        # Convert to float to avoid BLOB in SQL
        ssRange = np.array(ssRange)
        ssRange = float(ssRange.flatten()[0])
        csRange = np.array(csRange)
        csRange = float(csRange.flatten()[0])
        hsRange = np.array(hsRange)
        hsRange = float(hsRange.flatten()[0])
        rangessOptimalSpeed = np.array(rangessOptimalSpeed)
        rangessOptimalSpeed = float(rangessOptimalSpeed.flatten()[0])

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
        
        print(ssRange, csRange, hsRange)
        # Commit the changes and close the connection
        conn.commit()
        conn.close()
        
        # Complete while loop with increase in iteration count and time sleep according to elapsed time
        iteration+=1
        elapsed = time.time()-startTime
        time.sleep(max(0, interval - elapsed))
