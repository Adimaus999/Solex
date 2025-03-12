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
struct can_frame frame_tempvolt;
struct can_frame frame_solauxmot;

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
  uint8_t velocity_data[6] = {0x50, 0x00, 0x3C, 0x00, 0x50, 0x3C};
  uint8_t acceleration_data[6] = {0x60, 0xFF, 0x00, 0x01, 0x02, 0x03};
  uint8_t tempandvolt[6] = {0x80, 0x50, 0x00, 0xFF, 0x00, 0x00};
  uint8_t auxsolarmotor[7] = {0xA0, 0x05, 0x06, 0x07, 0x08, 0xFF, 0x00};
  
  initCANFrame(frame_battery, 0x5FF, battery_data, 8);
  initCANFrame(frame_location, 0x071, location_data, 8);
  initCANFrame(frame_velocity, 0x076, velocity_data, 6);
  initCANFrame(frame_acceleration, 0x035, acceleration_data, 6);
  initCANFrame(frame_tempvolt, 0x010, tempandvolt, 6);
  initCANFrame(frame_solauxmot, 0x020, auxsolarmotor, 7);
}

void loop() {
  sendCANMessage(frame_battery);
  delay(100);
  sendCANMessage(frame_location);
  delay(100);
  sendCANMessage(frame_velocity);
  delay(100);
  sendCANMessage(frame_acceleration);
  delay(100); 
  sendCANMessage(frame_motor_power);
  delay(100);
  sendCANMessage(frame_tempvolt);
  delay(100);
  sendCANMessage(frame_solauxmot);
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