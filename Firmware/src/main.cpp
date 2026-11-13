#include <Arduino.h>

// Pin map (see Firmware/README.md)
const int LED_PIN = 4;
const int TRIG_PIN = 5;   // not used yet
const int ECHO_PIN = 18;  // not used yet, goes through a 1k/2k divider

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  Serial.println("SmartBin firmware started");
}

void loop() {
  digitalWrite(LED_PIN, HIGH);
  delay(500);
  digitalWrite(LED_PIN, LOW);
  delay(500);
}
