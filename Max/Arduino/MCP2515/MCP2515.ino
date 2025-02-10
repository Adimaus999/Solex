#include <SPI.h>
#include <mcp2515.h>

MCP2515 mcp2515(10); // Initialize MCP2515 with Chip Select pin 10

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
}

void loop() {
  sendCANMessage();  // Send a CAN message
  readCANMessage();  // Read any incoming CAN messages
  delay(1000);       // Wait 1 second before sending again
}

void sendCANMessage() {
  struct can_frame frame; // Create a CAN frame structure

  frame.can_id = 0x000;  // Standard CAN ID (0x00)
  frame.can_dlc = 4;     // Data Length Code (4 bytes)
  frame.data[0] = 0xFF;
  frame.data[1] = 0xFF;
  frame.data[2] = 0xFF;
  frame.data[3] = 0xFF;

  Serial.println("Sending CAN message...");

  if (mcp2515.sendMessage(&frame) == MCP2515::ERROR_OK) {
    Serial.println("Message sent successfully!");
  } else {
    Serial.println("Error: Message not sent.");
  }
}

void readCANMessage() {
  struct can_frame receivedMsg; // Structure to store received CAN message

  if (mcp2515.readMessage(&receivedMsg) == MCP2515::ERROR_OK) {
    Serial.println("Received CAN message:");
    Serial.print("ID: 0x");
    Serial.print(receivedMsg.can_id, HEX); // Print message ID
    Serial.print(" | DLC: ");
    Serial.print(receivedMsg.can_dlc, HEX); // Print Data Length Code
    Serial.print(" | Data: ");

    // Print each byte of the received data
    for (int i = 0; i < receivedMsg.can_dlc; i++) {
      Serial.print("0x");
      Serial.print(receivedMsg.data[i], HEX);
      Serial.print(" ");
    }
    Serial.println(); // Move to the next line for readability
  }
}
