#include <SPI.h>
#include <mcp2515.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// MCP2515 Initialization
MCP2515 mcp2515(10); // Chip Select pin 10

// Data wire is plugged into pin 3 on the Arduino
#define ONE_WIRE_BUS 3

OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// Define CAN frame structures
struct can_frame frame_battery;
struct can_frame frame_location;
struct can_frame frame_velocity;
struct can_frame frame_acceleration;
struct can_frame frame_temperature;
struct can_frame frame_motor_power;
struct can_frame frame_solar_power;
struct can_frame frame_aux_power;

void setup() {
  Serial.begin(115200);
  while (!Serial) {}
  
  Serial.println("Initializing MCP2515...");
  mcp2515.reset();
  mcp2515.setBitrate(CAN_250KBPS, MCP_8MHZ);
  mcp2515.setNormalMode();
  Serial.println("Setup Complete - Ready to send CAN messages.");

  sensors.begin();
  
  uint8_t battery_data[8] = {0x20, 0x81, 0x21, 0x01, 0x00, 0x00, 0x00, 0x64};
  uint8_t location_data[8] = {0x40, 0x12, 0x34, 0x56, 0x78, 0x90, 0xAB, 0xCD};
  uint8_t velocity_data[6] = {0x50, 0x00, 0x3C, 0x00, 0x00, 0x00};
  uint8_t acceleration_data[6] = {0x60, 0xFF, 0x00, 0x01, 0x02, 0x03};
  uint8_t motor_power_data[8] = {0x80, 0x50, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};
  uint8_t solar_power_data[8] = {0x90, 0x10, 0x20, 0x30, 0x00, 0x00, 0x00, 0x00};
  uint8_t aux_power_data[8] = {0xA0, 0x05, 0x06, 0x07, 0x08, 0x00, 0x00, 0x00};
  
  initCANFrame(frame_battery, 0x5FF, battery_data, 8);
  initCANFrame(frame_location, 0x071, location_data, 8);
  initCANFrame(frame_velocity, 0x076, velocity_data, 6);
  initCANFrame(frame_acceleration, 0x035, acceleration_data, 6);
  initCANFrame(frame_motor_power, 0x020, motor_power_data, 8);
  initCANFrame(frame_solar_power, 0x021, solar_power_data, 8);
  initCANFrame(frame_aux_power, 0x022, aux_power_data, 8);
}

void loop() {
  sendCANMessage(frame_battery);
  delay(1000);
  sendCANMessage(frame_location);
  delay(1000);
  sendCANMessage(frame_velocity);
  delay(1000);
  sendCANMessage(frame_acceleration);
  delay(1000);
  
  sensors.requestTemperatures();
  float temperature = sensors.getTempCByIndex(0);
  Serial.println(temperature); // Print the temperature in Celsius
  uint8_t temperature_data[3] = {0x00, 0x00, 0x00};
  int temp_milli = static_cast<int>(temperature * 1000);
  temperature_data[0] = (temp_milli >> 16) & 0xFF;
  temperature_data[1] = (temp_milli >> 8) & 0xFF;
  temperature_data[2] = temp_milli & 0xFF;
  initCANFrame(frame_temperature, 0x010, temperature_data, 3);
  sendCANMessage(frame_temperature);
  printCANFrame(frame_temperature); // Print the CAN frame temperature data
  delay(1000);
  
  sendCANMessage(frame_motor_power);
  delay(1000);
  sendCANMessage(frame_solar_power);
  delay(1000);
  sendCANMessage(frame_aux_power);
  delay(1000);
}

void initCANFrame(struct can_frame &frame, uint16_t id, uint8_t data[], uint8_t length) {
  frame.can_id = id;
  frame.can_dlc = length;
  for (int i = 0; i < length; i++) {
    frame.data[i] = data[i];
  }
}

void sendCANMessage(struct can_frame &frame) {
  Serial.print("Sending CAN message with ID: 0x");
  Serial.println(frame.can_id, HEX);
  
  if (mcp2515.sendMessage(&frame) == MCP2515::ERROR_OK) {
    Serial.println("Message sent successfully!");
  } else {
    Serial.println("Error: Message not sent.");
  }
  Serial.println();
}

void printCANFrame(struct can_frame &frame) {
  Serial.print("CAN Frame ID: 0x");
  Serial.println(frame.can_id, HEX);
  Serial.print("Data: ");
  for (int i = 0; i < frame.can_dlc; i++) {
    Serial.print(frame.data[i], HEX);
    Serial.print(" ");
  }
  Serial.println();
}
