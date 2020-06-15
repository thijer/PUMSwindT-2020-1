#ifndef INTERFACECONFIG_H
#define INTERFACECONFIG_H

/* This header contains all the functioncodes and corresponding error codes for the Interface library at the Sensor module. 
Ensure that the functioncodes in this header are the same as the functioncodes in the config.py files in the DMS-controller edge modules 
*/

// Sensor data types
#define DMS_INT int32_T
#define DMS_FLOAT float
#define DMS_BOOL bool

// Serial settings
#define BAUDRATE 115200

// Addresses
// Broadcast address. All modules will process information sent to this address
#define ADDRESS_BROADCAST 0xfe

// Message codes
// Request type neutral response codes
#define RESP_INVALID_FUNCTIONCODE 0x07

// Request latest telemetry from module
#define REQ_TEL 0x10
// Module response codes to telemetry request
#define RESP_TEL_SUCCESS 0x11
#define RESP_TEL_ERROR 0x12
#define RESP_TEL_NO_SENSORS 0x13
#define RESP_TEL_NO_NEW_VALUES 0x14

// Request attributes from module
#define REQ_ATT 0x20
// Response codes to attribute request
#define RESP_ATT_SUCCESS 0x21
#define RESP_ATT_ERROR 0x22

// Request module time
#define REQ_TIMESTAMP 0x30
// response codes to time request
#define RESP_GET_TIMESTAMP_SUCCESS 0x31
#define RESP_GET_TIMESTAMP_ERROR 0x32

// Set sample interval for sensor at module
#define SET_SAMPLEINTERVAL 0x40
// Result codes
#define RESP_SAMPLEINTERVAL_SUCCESS 0x41
#define RESP_SAMPLEINTERVAL_ERROR 0x42
#define RESP_SAMPLEINTERVAL_NOSENSOR 0x43
#define RESP_SAMPLEINTERVAL_JSONERROR 0x44

#define MSG_START 77 // 'M'
#define RESP_START 82 // 'R'
#define MESSAGE_END 0

// Sensor module specific settings
#define OUTBUFFER_SIZE 400
#define INBUFFER_SIZE 100

// Max number of sensors of a datatype the module interface accepts.
#define SENSORBUFFER_SIZE 10
// store values in module from until n seconds ago
#define SENSORMEMORY_SIZE 2 

// The expected delay between reaching the update interval and reaching the function which updates the sensor values
// This value will be subtracted from the UpdateInterval value to compensate for delays.
#define SENSOR_UPDATE_DELAYMARGIN 5

#endif