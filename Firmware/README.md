# Firmware

ESP32 code for the bin. Reads the fill level with a JSN-SR04T ultrasonic sensor
and sends it to the backend over MQTT (TLS). Right now it only blinks the LED.

## Pins

| Signal | ESP32 pin | Note |
| --- | --- | --- |
| TRIG | GPIO 5 | |
| ECHO | GPIO 18 | Through a 1k/2k voltage divider (sensor outputs 5V, ESP32 takes 3.3V) |
| LED | GPIO 4 | Status LED |

## Run

Needs [PlatformIO](https://platformio.org/) (VS Code extension or CLI).

```bash
cd Firmware
pio run                 # build
pio run -t upload       # flash the board
pio device monitor      # serial output at 115200
```
