#include <Adafruit_LSM303.h>
#include "Arduino.h"
#include "Interface.h"
#include <math.h>

#define READENABLE 2
#define WRITEENABLE 15
#define HALL_SENSOR 16

/* Construct an instance of an interface derived class for a serial connection, 
 * with the following parameters:
 * 65               - The address of this module
 * "Compass-sensor" - The name of this module.
 * "0.0.1"          - Hardware version of the module. Can be used by the controller or I-share
 *                    to provide different treatments for modules if they have changed to a newer version.
 * "0.0.1"          - Software version of the module. Same purpose as the hardware version.
 * READENABLE       - The pin which enables the RS485 chip to receive bytes
 * WRITEENABLE      - The pin which enables the RS485 chip to send bytes
 * Serial           - The Stream interface which is used to send and receive data from the controller
*/
SerialInterface GI(0x41, "Compass-sensor", "0.0.1", "0.0.1", READENABLE, WRITEENABLE, Serial, Serial);
Adafruit_LSM303_Mag_Unified Compass(1);
bool CompassConnected = false;

// The callback which is used by the interface to get sensor readings. 
// This function everytime the interface wants a new sensor value
uint16_t GetCompassValue(double* Value)
{
    if(CompassConnected)
    {
        sensors_event_t event;
        bool Success = Compass.getEvent(&event);
        if(Success)
        {
            *Value = atan2(event.magnetic.y, event.magnetic.x);
            // Reading success, return success indicator (0)
            return 0;
        }
        else
        {
            // all returned values above 0 indicate an error.
            return 1;
        }
    }
    else
    {
        // No sensor connected
        return 2;
    }
}

bool CurrentPinState;
bool PreviousPinState;
uint32_t PreviousTime = 0;
float LatestValue = 0.0;

uint16_t GetRotationSpeed(double* Value)
{
    *Value = LatestValue;
    return 0;
}


void CalcRotationSpeed()
{
    CurrentPinState = digitalRead(HALL_SENSOR);
    uint32_t CurrentTime = millis();
    uint32_t Duration = CurrentTime - PreviousTime;
    if(!CurrentPinState && PreviousPinState && Duration <= 5000)
    {
        // Falling edge detected
        Serial.println(F("Falling edge"));
        // duration in milliseconds
        // rotation frequency in Hz
        LatestValue = 1000.0 / double(Duration);
        PreviousTime = CurrentTime;
    }
    else if(Duration > 5000)
    {
        // < 0.2 Hz / 12 RPM
        // really slow, setting speed to 0.
        LatestValue = 0.0;
        PreviousTime = CurrentTime;
    }
    PreviousPinState = CurrentPinState;
}

void setup()
{
	// Set RS485 flow control pins as outputs
    pinMode(READENABLE, OUTPUT);
    pinMode(WRITEENABLE, OUTPUT);
    // Set RS485 to read mode
    digitalWrite(WRITEENABLE, false);
    digitalWrite(READENABLE, false);
    
    // Use a digital pin (faster) for hall effect input, or resort to ADC (slower)
    pinMode(HALL_SENSOR, INPUT_PULLUP);
    
    Serial.begin(BAUDRATE);
    // Serial1.begin(BAUDRATE);
    Compass.enableAutoRange(true);
    CompassConnected = Compass.begin();
    Serial.println(F("Welcome to the SWT-head sensor module."));

    /* Register a sensor at the interface.
     * 100              - The minimum sample interval the sensor can read data, in ms.
     * "Compass"        - The name of the sensor.
     * "Deg"            - The unit of the measured property.
     * 100              - The current samplerate of the sensor, in ms.
     * GetCompassValue  - The Callback function where the sensor values can be retrieved.
    */
    GI.AddSensor<1000>("Compass", "Deg", 10000, GetCompassValue);
    GI.AddSensor<1000>("Rotation Speed", "Hz", 1000, GetRotationSpeed);
    
    CurrentPinState = digitalRead(HALL_SENSOR);
    PreviousPinState = CurrentPinState;
    PreviousTime = millis();
    Serial.println(F("Setup finished."));
    
}

void loop()
{
	GI.Loop();
    // Other NON-BLOCKING logic
    CalcRotationSpeed();
}