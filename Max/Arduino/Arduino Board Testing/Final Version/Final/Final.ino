#include <SPI.h>
#include <mcp2515.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// MCP2515 Initialization
MCP2515 mcp2515(10); // Chip Select pin 10

// Data wire is plugged into port 2 on the Arduino for temperature sensor
#define ONE_WIRE_BUS 2

OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// Define the reference voltage constant
const float VREF = 4.615;

// Define resistor values for the voltage divider
const float R1 = 226500; // 220k ohms
const float R2 = 12080;  // 12k ohms

// Define the delay between cycles in milliseconds
const int cycleDelay = 2500; // 10 times per second

const int numReadings = 10; // Number of readings for averaging
float temperatureReadings[numReadings];
float currentSensorVREFReadings[numReadings];
float batteryVoltageReadings[numReadings];
float currentSensor1Readings[numReadings];
float currentSensor2Readings[numReadings];
float currentSensor3Readings[numReadings];

int readIndex = 0; // Index for circular buffer
float totalTemperature = 0;
float totalCurrentSensorVREF = 0;
float totalBatteryVoltage = 0;
float totalCurrentSensor1 = 0;
float totalCurrentSensor2 = 0;
float totalCurrentSensor3 = 0;

unsigned long lastTempReadTime = 0; // Time of last temperature reading
unsigned long lastCANSendTime = 0; // Time of last CAN message send

// Define CAN frame structures
struct can_frame frame_temperature;
struct can_frame frame_currentSensorVREF;
struct can_frame frame_batteryVoltage;
struct can_frame frame_current1;
struct can_frame frame_current2;
struct can_frame frame_current3;
struct can_frame frame_batteryPower;

void setup() {
  // Initialize serial communication
  Serial.begin(115200);
  while (!Serial) {}

  // Initialize MCP2515 CAN controller
  Serial.println("Initializing MCP2515...");
  mcp2515.reset();
  mcp2515.setBitrate(CAN_250KBPS, MCP_8MHZ);
  mcp2515.setNormalMode();
  Serial.println("Setup Complete - Ready to send CAN messages.");

  // Initialize temperature sensor
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

void loop() {
  unsigned long currentMillis = millis();
  
  // Read temperature every 1 second
  if (currentMillis - lastTempReadTime >= 1000) {
    sensors.requestTemperatures(); 
    float temperature = sensors.getTempCByIndex(0);
    totalTemperature -= temperatureReadings[readIndex];
    temperatureReadings[readIndex] = temperature;
    totalTemperature += temperature;
    lastTempReadTime = currentMillis;
  }

  // Read other sensors based on cycle delay
  if (currentMillis % cycleDelay == 0) {
    // Read sensor values from analog pins
    int sensorValueA7 = analogRead(A7);
    int sensorValueA0 = analogRead(A0);
    int sensorValueA1 = analogRead(A1);
    int sensorValueA2 = analogRead(A2);
    int sensorValueA4 = analogRead(A4);

    // Convert analog readings to voltages
    float Current_Sensor_VREF = sensorValueA7 * (VREF / 1023.0);
    float Battery_Voltage_Sensor = sensorValueA0 * (VREF / 1023.0);
    float Current_Sensor_1_Voltage_Sensor = sensorValueA1 * (VREF / 1023.0);
    float Current_Sensor_2_Voltage_Sensor = sensorValueA2 * (VREF / 1023.0);
    float Current_Sensor_3_Voltage_Sensor = sensorValueA4 * (VREF / 1023.0);

    // Calculate battery voltage and currents
    float Battery_Voltage = Battery_Voltage_Sensor * (R1 + R2) / R2;
    float Current_1 = ((Current_Sensor_1_Voltage_Sensor - Current_Sensor_VREF) * 200) / 1.25;
    float Current_2 = ((Current_Sensor_2_Voltage_Sensor - Current_Sensor_VREF) * 200) / 1.25;
    float Current_3 = ((Current_Sensor_3_Voltage_Sensor - Current_Sensor_VREF) * 200) / 1.25;

    // Update total values by subtracting the oldest reading and adding the new reading
    totalCurrentSensorVREF -= currentSensorVREFReadings[readIndex];
    totalBatteryVoltage -= batteryVoltageReadings[readIndex];
    totalCurrentSensor1 -= currentSensor1Readings[readIndex];
    totalCurrentSensor2 -= currentSensor2Readings[readIndex];
    totalCurrentSensor3 -= currentSensor3Readings[readIndex];

    currentSensorVREFReadings[readIndex] = Current_Sensor_VREF;
    batteryVoltageReadings[readIndex] = Battery_Voltage;
    currentSensor1Readings[readIndex] = Current_1;
    currentSensor2Readings[readIndex] = Current_2;
    currentSensor3Readings[readIndex] = Current_3;

    totalCurrentSensorVREF += Current_Sensor_VREF;
    totalBatteryVoltage += Battery_Voltage;
    totalCurrentSensor1 += Current_1;
    totalCurrentSensor2 += Current_2;
    totalCurrentSensor3 += Current_3;

    // Advance to the next position in the circular buffer
    readIndex = (readIndex + 1) % numReadings;

    // Calculate the average values
    float averageTemperature = totalTemperature / numReadings;
    float averageCurrentSensorVREF = totalCurrentSensorVREF / numReadings;
    float averageBatteryVoltage = totalBatteryVoltage / numReadings;
    float averageCurrent1 = totalCurrentSensor1 / numReadings;
    float averageCurrent2 = totalCurrentSensor2 / numReadings;
    float averageCurrent3 = totalCurrentSensor3 / numReadings;

    // Calculate power values
    float powerCurrent1 = averageCurrent1 * averageBatteryVoltage;
    float powerCurrent2 = averageCurrent2 * averageBatteryVoltage;
    float powerCurrent3 = averageCurrent3 * averageBatteryVoltage;
    float batteryPower = powerCurrent1 + powerCurrent2 + powerCurrent3;

    // Print the averages and power values to serial monitor
    Serial.print("Average Temperature: ");
    Serial.println(averageTemperature);
    Serial.print("Average Current Sensor VREF: ");
    Serial.println(averageCurrentSensorVREF);
    Serial.print("Average Battery Voltage: ");
    Serial.println(averageBatteryVoltage);
    Serial.print("Average Current 1: ");
    Serial.println(averageCurrent1);
    Serial.print("Power Current 1: ");
    Serial.println(powerCurrent1);
    Serial.print("Average Current 2: ");
    Serial.println(averageCurrent2);
    Serial.print("Power Current 2: ");
    Serial.println(powerCurrent2);
    Serial.print("Average Current 3: ");
    Serial.println(averageCurrent3);
    Serial.print("Power Current 3: ");
    Serial.println(powerCurrent3);
    Serial.print("Battery Power: ");
    Serial.println(batteryPower);

    // Send CAN messages with the averages and power values at 1Hz frequency
    if (currentMillis - lastCANSendTime >= 1000) {
      sendCANFrame(averageTemperature, 0x010, frame_temperature);
      sendPowerCANFrame(averageCurrent1, powerCurrent1, averageBatteryVoltage, 0x020, frame_current1);
      sendPowerCANFrame(averageCurrent2, powerCurrent2, averageBatteryVoltage, 0x021, frame_current2);
      sendPowerCANFrame(averageCurrent3, powerCurrent3, averageBatteryVoltage, 0x022, frame_current3);
      sendPowerCANFrame(averageCurrent1 + averageCurrent2 + averageCurrent3, batteryPower, averageBatteryVoltage, 0x023, frame_batteryPower);
      lastCANSendTime = currentMillis;
    }
  }
}

// Function to send a CAN frame with a single float value
void sendCANFrame(float data, uint16_t id, struct can_frame &frame) {
  uint8_t data_array[4];
  int data_milli = static_cast<int>(data * 1000);
  data_array[0] = (data_milli >> 24) & 0xFF;
  data_array[1] = (data_milli >> 16) & 0xFF;
  data_array[2] = (data_milli >> 8) & 0xFF;
  data_array[3] = data_milli & 0xFF;

  initCANFrame(frame, id, data_array, 4);
  sendCANMessage(frame);
}

// Function to send a CAN frame with power, current, and voltage data
void sendPowerCANFrame(float current, float power, float voltage, uint16_t id, struct can_frame &frame) {
  uint8_t data_array[8];
  int power_milli = static_cast<int>(power * 1000);
  int current_milli = static_cast<int>(current * 1000);
  int voltage_milli = static_cast<int>(voltage * 1000);

  data_array[0] = (power_milli >> 16) & 0xFF;
  data_array[1] = (power_milli >> 8) & 0xFF;
  data_array[2] = power_milli & 0xFF;

  data_array[3] = (current_milli >> 16) & 0xFF;
  data_array[4] = (current_milli >> 8) & 0xFF;
  data_array[5] = current_milli & 0xFF;

  data_array[6] = (voltage_milli >> 8) & 0xFF;
  data_array[7] = voltage_milli & 0xFF;

  initCANFrame(frame, id, data_array, 8);
  sendCANMessage(frame);
}

// Function to initialize a CAN frame
void initCANFrame(struct can_frame &frame, uint16_t id, uint8_t data[], uint8_t length) {
  frame.can_id = id;
  frame.can_dlc = length;
  for (int i = 0; i < length; i++) {
    frame.data[i] = data[i];
  }
}

// Function to send a CAN message
void sendCANMessage(struct can_frame &frame) {
  // Print CAN message details
  Serial.print("Sending CAN message with ID: 0x");
  Serial.print(frame.can_id, HEX);
  Serial.print(", DLC: ");
  Serial.print(frame.can_dlc);
  Serial.print(", Data: ");
  for (int i = 0; i < frame.can_dlc; i++) {
    Serial.print(frame.data[i], HEX);
    Serial.print(" ");
  }
  Serial.println();
  
  // Send the CAN message
  if (mcp2515.sendMessage(&frame) == MCP2515::ERROR_OK) {
    Serial.println("Message sent successfully!");
  } else {
    Serial.println("Error: Message not sent.");
  }
  Serial.println();
}