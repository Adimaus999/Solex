const int sensorPin0_Vout = A1;
const int sensorPin1_Vref = A7;
const int Vcc = 4.615;
#define NUM_READINGS 25  // Number of readings to average

float readings[NUM_READINGS];  // Array to store past readings
int readIndex = 0;             // Index to track position in the buffer
float total = 0;               // Sum of all stored readings
bool bufferFilled = false;     // Flag to indicate buffer is full

void setup() {
    Serial.begin(115200);  // Start serial communication
    analogReference(DEFAULT);  // Use 5V as reference for analog readings

    // Initialize readings array with zeros
    for (int i = 0; i < NUM_READINGS; i++) {
        readings[i] = 0;
    }
}

void loop() {
    int adcVout = analogRead(sensorPin0_Vout); 
    int adcVref = analogRead(sensorPin1_Vref);

    // Convert ADC values to voltages
    float Vout = (adcVout / 1023.0) * Vcc; 
    float Vref = (adcVref / 1023.0) * Vcc;

    // Calculate current
    float current_temp = ((Vout - Vref) * 200) / 1.25;
    float current = current_temp + ((current_temp*0.1358) -0.5552);
    
   
    // Remove the oldest reading from the total sum
    total -= readings[readIndex];

    // Store the new reading in the array
    readings[readIndex] = current;

    // Add the new reading to the total sum
    total += current;

    // Move to the next position in the buffer
    readIndex++;

    // If we reach the end of the array, loop back to the beginning
    if (readIndex >= NUM_READINGS) {
        readIndex = 0;
        bufferFilled = true;  // Mark buffer as full
    }

    // Calculate the average over available readings
    float averageCurrent;
    if (bufferFilled) {
        averageCurrent = total / NUM_READINGS;  // Use full buffer
    } else {
        averageCurrent = total / readIndex;  // Use only filled portion
    }

    // Get time since startup in HH:MM:SS format
    unsigned long ms = millis();
    unsigned long seconds = ms / 1000;
    unsigned long minutes = seconds / 60;
    unsigned long hours = minutes / 60;

    // Print timestamp
    Serial.print("[");
    Serial.print(hours);
    Serial.print(":");
    Serial.print(minutes % 60);
    Serial.print(":");
    Serial.print(seconds % 60);
    Serial.print("] ");

    // Print averaged current
    Serial.print("Avg Current: ");
    Serial.println(averageCurrent, 2); // Print with 2 decimal places

    delay(100);  // Wait 250ms before next reading
}
