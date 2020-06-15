#ifndef INTERFACE_ERRORS_H
#define INTERFACE_ERRORS_H

// NOT USED

// Define potential errors in this enumeration
// ERR_END should always be the last entry, so users can define their own error codes
// without creating duplicates by creating their own enumeration:
// 
// enum DerivedInterfaceError
// {
//     ERR_NEW = InterfaceError::ERR_END
// }

enum InterfaceError
{
    ERR_NO_ERROR,
    ERR_SENSOR_BUFFER_OVERFLOW,
    ERR_SENSOR_NOT_COMPLIANT,
    ERR_SENSOR_MODULE_0,
    ERR_SENSOR_MODULE_1,
    ERR_SENSOR_MODULE_2,
    ERR_SENSOR_MODULE_3,
    ERR_SENSOR_MODULE_4,
    ERR_SENSOR_MODULE_5,
    ERR_SENSOR_MODULE_6,
    ERR_SENSOR_MODULE_7,
    ERR_SENSOR_MODULE_8,
    ERR_SENSOR_MODULE_9,
    ERR_END // Always the last 
};

#endif