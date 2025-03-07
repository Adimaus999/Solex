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
const int cycleDelay = 50; // 50 milliseconds

const int numReadings = 50; // Number of readings for averaging
float batteryVoltageReadings[numReadings];

int readIndex = 0; // Index for circular buffer
float totalBatteryVoltage = 0;

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

  // Initialize all the readings to 0
  for (int thisReading = 0; thisReading < numReadings; thisReading++) {
    batteryVoltageReadings[thisReading] = 0;
  }
}

void loop() {
  unsigned long currentMillis = millis();

  // Read sensor values from analog pins every cycleDelay milliseconds
  if (currentMillis % cycleDelay == 0) {
    // Read sensor value from analog pin A0 (Battery)
    int sensorValueA0 = analogRead(A0); // Battery

    // Convert analog reading to voltage
    float Battery_Voltage_Sensor = sensorValueA0 * (VREF / 1023.0);

    // Calculate battery voltage
    float Battery_Voltage_Temp = Battery_Voltage_Sensor * (R1 + R2) / R2;
    float Battery_Voltage = Battery_Voltage_Temp - 0.0055* Battery_Voltage_Temp +0.0496;
    if (Battery_Voltage == 0.0496) {
      Battery_Voltage = 0.0;
    }
    // Update total values by subtracting the oldest reading and adding the new reading
    totalBatteryVoltage -= batteryVoltageReadings[readIndex];
    batteryVoltageReadings[readIndex] = Battery_Voltage;
    totalBatteryVoltage += Battery_Voltage;

    // Advance to the next position in the circular buffer
    readIndex = (readIndex + 1) % numReadings;

    // Calculate the average battery voltage
    float averageBatteryVoltage = totalBatteryVoltage / numReadings;

    // Print the average battery voltage to serial monitor
    Serial.print("Average Battery Voltage: ");
    Serial.println(averageBatteryVoltage);
  }
}