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
const float VREF = 4.54;

// Define resistor values for the voltage divider
const float R1 = 226500; // 220k ohms
const float R2 = 12080;  // 12k ohms

const float Aux_Coils = 10;
const float Solar_Coils = 2;

// Define the delay between cycles in milliseconds
const int cycleDelay = 1000; // 10 times per second

const int numReadings = 10; // Number of readings for averaging
float temperatureReadings[numReadings];
float currentSensorVREFReadings[numReadings];
float batteryVoltageReadings[numReadings];
float currentSensorMotorReadings[numReadings];
float currentSensorAuxiliaryReadings[numReadings];
float currentSensorSolarReadings[numReadings];

int readIndex = 0; // Index for circular buffer
float totalTemperature = 0;
float totalCurrentSensorVREF = 0;
float totalBatteryVoltage = 0;
float totalCurrentSensorMotor = 0;
float totalCurrentSensorAuxiliary = 0;
float totalCurrentSensorSolar = 0;

unsigned long lastTempReadTime = 0; // Time of last temperature reading
unsigned long lastCANSendTime = 0; // Time of last CAN message send

// Define CAN frame structures
struct can_frame frame_temperaturevoltage;
struct can_frame frame_motorauxsolar;

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
    currentSensorMotorReadings[thisReading] = 0;
    currentSensorAuxiliaryReadings[thisReading] = 0;
    currentSensorSolarReadings[thisReading] = 0;
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
    int sensorValueA7 = analogRead(A7);    // VREF
    int sensorValueA0 = analogRead(A0);    // Battery
    int sensorValueA1 = analogRead(A1);    // Motor
    int sensorValueA2 = analogRead(A2);    // Auxiliary
    int sensorValueA4 = analogRead(A4);    // Solar

    Serial.println(sensorValueA4);
    // Convert analog readings to voltages
    float Current_Sensor_VREF = sensorValueA7 * (VREF / 1023.0);
    float Battery_Voltage_Sensor = sensorValueA0 * (VREF / 1023.0);
    float Current_Sensor_Motor_Voltage = sensorValueA1 * (VREF / 1023.0);
    float Current_Sensor_Auxiliary_Voltage = sensorValueA2 * (VREF / 1023.0);
    float Current_Sensor_Solar_Voltage = sensorValueA4 * (VREF / 1023.0);

    // Calculate battery voltage and currents
    float Battery_Voltage_Temp = Battery_Voltage_Sensor * (R1 + R2) / R2;
    float Battery_Voltage = Battery_Voltage_Temp + ((Battery_Voltage_Temp * 0.0141) + 0.058);

    float Current_Motor_Temp = ((Current_Sensor_Motor_Voltage - Current_Sensor_VREF) * 200) / 1.25;
    float Current_Motor = Current_Motor_Temp + ((Current_Motor_Temp * 0.0283) -  0.2982);

    float Current_Auxiliary_Temp = ((Current_Sensor_Auxiliary_Voltage - Current_Sensor_VREF) * 200) / 1.25;
    float Current_Auxiliary = Current_Auxiliary_Temp + ((Current_Auxiliary_Temp * 0.0102) -  0.266);
    
    float Current_Solar_Temp = ((Current_Sensor_Solar_Voltage - Current_Sensor_VREF) * 200) / 1.25;
    float Current_Solar = Current_Solar_Temp + ((Current_Solar_Temp * 0.0351) - 0.2808);

    // Update total values by subtracting the oldest reading and adding the new reading
    totalCurrentSensorVREF -= currentSensorVREFReadings[readIndex];
    totalBatteryVoltage -= batteryVoltageReadings[readIndex];
    totalCurrentSensorMotor -= currentSensorMotorReadings[readIndex];
    totalCurrentSensorAuxiliary -= currentSensorAuxiliaryReadings[readIndex];
    totalCurrentSensorSolar -= currentSensorSolarReadings[readIndex];

    currentSensorVREFReadings[readIndex] = Current_Sensor_VREF;
    batteryVoltageReadings[readIndex] = Battery_Voltage;
    currentSensorMotorReadings[readIndex] = Current_Motor;
    currentSensorAuxiliaryReadings[readIndex] = Current_Auxiliary;
    currentSensorSolarReadings[readIndex] = Current_Solar;

    totalCurrentSensorVREF += Current_Sensor_VREF;
    totalBatteryVoltage += Battery_Voltage;
    totalCurrentSensorMotor += Current_Motor;
    totalCurrentSensorAuxiliary += Current_Auxiliary;
    totalCurrentSensorSolar += Current_Solar;

    // Advance to the next position in the circular buffer
    readIndex = (readIndex + 1) % numReadings;

    float averageTemperature = totalTemperature / numReadings;
    float averageCurrentSensorVREF = totalCurrentSensorVREF / numReadings;
    if (averageCurrentSensorVREF < 0) {
        averageCurrentSensorVREF = 0;
    }

    float averageBatteryVoltage = (totalBatteryVoltage / numReadings);
    if (averageBatteryVoltage < 0.5) {
        averageBatteryVoltage = 0;
    }

    float averageCurrentMotor = totalCurrentSensorMotor / numReadings;
    if (averageCurrentMotor < 1) {
        averageCurrentMotor = 0;
    }

    float averageCurrentAuxiliary = (totalCurrentSensorAuxiliary / numReadings)/Aux_Coils;
    if (averageCurrentAuxiliary < 0.1) {
        averageCurrentAuxiliary = 0;
    }
    Serial.println(averageCurrentAuxiliary);

    float averageCurrentSolar = (totalCurrentSensorSolar / numReadings)/Solar_Coils;
    if (averageCurrentSolar < 0.5) {
        averageCurrentSolar = 0;
    }

    // Print the averages and power values to serial monitor
    Serial.print("Average Temperature: ");
    Serial.println(averageTemperature);
    Serial.print("Average Current Sensor VREF: ");
    Serial.println(averageCurrentSensorVREF);
    Serial.print("Average Battery Voltage: ");
    Serial.println(averageBatteryVoltage);
    Serial.print("Average Current Motor: ");
    Serial.println(averageCurrentMotor);
    Serial.print("Average Current Auxiliary: ");
    Serial.println(averageCurrentAuxiliary);
    Serial.print("Average Current Solar: ");
    Serial.println(averageCurrentSolar);

    // Send CAN messages with the averages and power values at 1Hz frequency
    if (currentMillis - lastCANSendTime >= 1000) {
      sendTemperatureVoltage(averageTemperature, averageBatteryVoltage, 0x010, frame_temperaturevoltage);
      sendMotorAuxSolar(averageCurrentMotor, averageCurrentAuxiliary, averageCurrentSolar, 0x020, frame_motorauxsolar);
      lastCANSendTime = currentMillis;
    }
  }
}

// Function to send a CAN frame with a single float value
void sendTemperatureVoltage(float temp, float voltage, uint16_t id, struct can_frame &frame) {
  uint8_t data_array[6];
  int temp_milli = static_cast<int>(temp * 1000);
  data_array[0] = (temp_milli >> 16) & 0xFF;
  data_array[1] = (temp_milli >> 8) & 0xFF;
  data_array[2] = temp_milli & 0xFF;

  int volt_milli = static_cast<int>(voltage * 1000);
  data_array[3] = (volt_milli >> 16) & 0xFF;
  data_array[4] = (volt_milli >> 8) & 0xFF;
  data_array[5] = volt_milli & 0xFF;

  initCANFrame(frame, id, data_array, 6);
  sendCANMessage(frame);
}

void sendMotorAuxSolar(float motor, float aux, float solar, uint16_t id, struct can_frame &frame) {
  uint8_t data_array[7];
  int motor_milli = static_cast<int>(motor * 1000);
  data_array[0] = (motor_milli >> 16) & 0xFF;
  data_array[1] = (motor_milli >> 8) & 0xFF;
  data_array[2] = motor_milli & 0xFF;

  int aux_milli = static_cast<int>(aux * 1000);
  data_array[3] = (aux_milli >> 8) & 0xFF;
  data_array[4] = aux_milli & 0xFF;

  int solar_milli = static_cast<int>(solar * 1000);
  data_array[5] = (solar_milli >> 8) & 0xFF;
  data_array[6] = solar_milli & 0xFF;

  initCANFrame(frame, id, data_array, 7);
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
  
  // Add the additional text line here
  Serial.println("CAN message sent successfully!");

  // Send the CAN message
  if (mcp2515.sendMessage(&frame) == MCP2515::ERROR_OK) {
    Serial.println("Message sent successfully!");
  } else {
    Serial.println("Error: Message not sent.");
  }
  Serial.println();
}