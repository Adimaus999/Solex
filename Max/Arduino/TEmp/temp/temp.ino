// Include the libraries we need
#include <OneWire.h>
#include <DallasTemperature.h>

// Data wire is plugged into port 2 on the Arduino
#define ONE_WIRE_BUS 2

// Setup a oneWire instance to communicate with any OneWire devices (not just Maxim/Dallas temperature ICs)
OneWire oneWire(ONE_WIRE_BUS);

// Pass our oneWire reference to Dallas Temperature.
DallasTemperature sensors(&oneWire);

// Define the reference voltage constant
const float VREF = 4.615;

// Define resistor values for the voltage divider
const float R1 = 226500; // 220k ohms
const float R2 = 12080;  // 12k ohms

const int numReadings = 10;
float temperatureReadings[numReadings];
float currentSensorVREFReadings[numReadings];
float batteryVoltageReadings[numReadings];
float currentSensor1Readings[numReadings];
float currentSensor2Readings[numReadings];
float currentSensor3Readings[numReadings];

int readIndex = 0;
float totalTemperature = 0;
float totalCurrentSensorVREF = 0;
float totalBatteryVoltage = 0;
float totalCurrentSensor1Motor = 0;
float totalCurrentSensor2Auxiliarry = 0;
float totalCurrentSensor3Solar = 0;

/*
 * The setup function. We only start the sensors here
 */
void setup(void)
{
  // start serial port
  Serial.begin(9600);

  // Start up the library
  sensors.begin();

  // Initialize all the readings to 0
  for (int thisReading = 0; thisReading < numReadings; thisReading++) {
    temperatureReadings[thisReading] = 0;
    currentSensorVREFReadings[thisReading] = 0;
    batteryVoltageReadings[thisReading] = 0;
    currentSensor1Readings[thisReading] = 0;
    currentSensor2Readings[thisReading] = 0;
    currentSensor3Readings[thisReading] = 0;
  }
}

/*
 * Main function, get and show the temperature and pin A7, A0 readings
 */
void loop(void)
{
  // request to all devices on the bus
  sensors.requestTemperatures(); 
  float temperature = sensors.getTempCByIndex(0);

  int sensorValueA7 = analogRead(A7);
  int sensorValueA0 = analogRead(A0);
  int sensorValueA1 = analogRead(A1);
  int sensorValueA2 = analogRead(A2);
  int sensorValueA4 = analogRead(A4);

  float Current_Sensor_VREF = sensorValueA7 * (VREF / 1023.0);
  float Battery_Voltage_Sensor = sensorValueA0 * (VREF / 1023.0);
  float Current_Sensor_1_Voltage_Sensor = sensorValueA1 * (VREF / 1023.0);
  float Current_Sensor_2_Voltage_Sensor = sensorValueA2 * (VREF / 1023.0);
  float Current_Sensor_3_Voltage_Sensor = sensorValueA4 * (VREF / 1023.0);

  float Battery_Voltage = Battery_Voltage_Sensor * (R1 + R2) / R2;
  float Current_1 = ((Current_Sensor_1_Voltage_Sensor - Current_Sensor_VREF) * 200) / 1.25;
  float Current_2 = ((Current_Sensor_2_Voltage_Sensor - Current_Sensor_VREF) * 200) / 1.25;
  float Current_3 = ((Current_Sensor_3_Voltage_Sensor - Current_Sensor_VREF) * 200) / 1.25;

  // Subtract the last reading
  totalTemperature -= temperatureReadings[readIndex];
  totalCurrentSensorVREF -= currentSensorVREFReadings[readIndex];
  totalBatteryVoltage -= batteryVoltageReadings[readIndex];
  totalCurrentSensor1 -= currentSensor1Readings[readIndex];
  totalCurrentSensor2 -= currentSensor2Readings[readIndex];
  totalCurrentSensor3 -= currentSensor3Readings[readIndex];

  // Add the new reading
  temperatureReadings[readIndex] = temperature;
  currentSensorVREFReadings[readIndex] = Current_Sensor_VREF;
  batteryVoltageReadings[readIndex] = Battery_Voltage;
  currentSensor1Readings[readIndex] = Current_1;
  currentSensor2Readings[readIndex] = Current_2;
  currentSensor3Readings[readIndex] = Current_3;

  totalTemperature += temperature;
  totalCurrentSensorVREF += Current_Sensor_VREF;
  totalBatteryVoltage += Battery_Voltage;
  totalCurrentSensor1 += Current_1;
  totalCurrentSensor2 += Current_2;
  totalCurrentSensor3 += Current_3;

  // Advance to the next position in the array
  readIndex = (readIndex + 1) % numReadings;

  // Calculate the average
  float averageTemperature = totalTemperature / numReadings;
  float averageCurrentSensorVREF = totalCurrentSensorVREF / numReadings;
  float averageBatteryVoltage = totalBatteryVoltage / numReadings;
  float averageCurrent1 = totalCurrentSensor1 / numReadings;
  float averageCurrent2 = totalCurrentSensor2 / numReadings;
  float averageCurrent3 = totalCurrentSensor3 / numReadings;

  // Print the averages
  Serial.print("Average Temperature: ");
  Serial.println(averageTemperature);
  Serial.print("Average Current Sensor VREF: ");
  Serial.println(averageCurrentSensorVREF);
  Serial.print("Average Battery Voltage: ");
  Serial.println(averageBatteryVoltage);
  Serial.print("Average Current 1: ");
  Serial.println(averageCurrent1);
  Serial.print("Average Current 2: ");
  Serial.println(averageCurrent2);
  Serial.print("Average Current 3: ");
  Serial.println(averageCurrent3);

  delay(100); // 10 times per second
}