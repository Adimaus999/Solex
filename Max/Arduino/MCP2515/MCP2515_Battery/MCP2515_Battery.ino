#include <SPI.h>
#include <mcp2515.h>

// MCP2515 Initialization
MCP2515 mcp2515(10); // Chip Select pin 10

// CAN ID definition
#define CAN_ID 0x001

// Define the CAN frames data as arrays
const uint8_t frame_soc_data[5] = {0x0D, 0x81, 0x01, 0x00, 0x00};
const uint8_t frame_voltage_data[5] = {0x09, 0x81, 0x01, 0x00, 0x00};
const uint8_t frame_current_data[5] = {0x2A, 0x81, 0x02, 0x00, 0x00};

// Create a struct to hold a CAN frame
struct can_frame frame_soc;
struct can_frame frame_voltage;
struct can_frame frame_current;

void setup() {
  Serial.begin(115200);
  while (!Serial) {} // Wait for Serial Monitor (optional)
  
  Serial.println("Initializing MCP2515...");
  
  mcp2515.reset(); // Reset MCP2515 before configuring
  Serial.println("MCP2515 reset complete.");
  
  mcp2515.setBitrate(CAN_250KBPS, MCP_8MHZ); // Set CAN speed to 250Kbps (8MHz oscillator)
  Serial.println("Bitrate set to 250Kbps (8MHz).");
  
  mcp2515.setNormalMode(); // Set to normal mode for operation
  Serial.println("MCP2515 set to normal mode.");
  
  Serial.println("Setup Complete - Ready to send and receive CAN messages.");
  
  // Initialize the CAN frames with the predefined data
  initCANFrame(frame_soc, frame_soc_data);
  initCANFrame(frame_voltage, frame_voltage_data);
  initCANFrame(frame_current, frame_current_data);
}

void loop() {
 sendCANMessage(frame_soc);     // Send the 'soc' CAN message
  delay(10000);                   // Wait 1 second before sending the next message
  
  //sendCANMessage(frame_voltage); // Send the 'voltage' CAN message
  //delay(10000);                   // Wait 1 second before sending the next message
  
  //sendCANMessage(frame_current); // Send the 'current' CAN message
  //delay(10000);                   // Wait 1 second before sending the next message
}


void initCANFrame(struct can_frame &frame, const uint8_t data[5]) {
  frame.can_id = CAN_ID;      // Use defined CAN ID
  frame.can_dlc = 5;          // Data Length Code (5 bytes)
  for (int i = 0; i < 5; i++) {
    frame.data[i] = data[i];  // Initialize frame data
  }
}

void sendCANMessage(struct can_frame &frame) {
  Serial.println("Sending CAN message...");
  
  if (mcp2515.sendMessage(&frame) == MCP2515::ERROR_OK) {
    Serial.println("Message sent successfully!");
  } else {
    Serial.println("Error: Message not sent.");
  }
  
  Serial.println(); // Move to the next line for readability
}
