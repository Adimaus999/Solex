#include <SoftwareSerial.h>

#define BAUD_RATE 115200

SoftwareSerial rs232Serial(6, 7); // RX on D6, TX on D7 (to MAX232)

void setup() {
    Serial.begin(115200);  // Debugging via USB Serial Monitor
    rs232Serial.begin(BAUD_RATE); // RS-232 communication on D6/D7
    
    Serial.println("SLS Motor Controller Communication Started");
}

void loop() {
    // 1. Send the status request command
    byte command[] = {'!', 0x3, 'S', 0x00}; // 0x00 is a placeholder for CRC
    command[3] = calculateCRC(command, 3);  // Compute the CRC

    Serial.print("Sending Command: ");
    for (int i = 0; i < sizeof(command); i++) {
        Serial.print(command[i], HEX);
        Serial.print(" ");
    }
    Serial.println();

    rs232Serial.write(command, sizeof(command)); // Send the command over RS-232
    Serial.println("Sent Status Request");

    // 2. Wait and read the response
    delay(1000); // Allow time for the response

    if (rs232Serial.available() > 0) {
        Serial.println("Received Response:");
        while (rs232Serial.available()) {
            byte receivedByte = rs232Serial.read();
            Serial.print(receivedByte, HEX);
            Serial.print(" ");
        }
        Serial.println(); // New line after reading response
    } else {
        Serial.println("No response received.");
    }

    delay(2000); // Wait 2 seconds before sending the next request
}

// Function to calculate CRC checksum (Simple Checksum)
byte calculateCRC(byte *data, int length) {
    byte crc = 0;
    for (int i = 0; i < length; i++) {
        crc += data[i];
    }
    return crc;
}
