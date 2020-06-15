# Message codes
# Common error codes not specific to a request
RESP_TIMEOUT = 0x01
RESP_INVALID_HEADER = 0x02
RESP_BYTE_DECODE_ERROR = 0x03
RESP_JSON_DECODE_ERROR = 0x04
RESP_INVALID_REQUEST = 0x05
RESP_JSON_ENCODE_ERROR = 0x06
RESP_INVALID_FUNCTIONCODE = 0x07 # used at the sensor module

# Request latest telemetry from module
REQ_TEL = 0x10
# Module response codes from telemetry request
RESP_TEL_SUCCESS = 0x11
RESP_TEL_ERROR = 0x12
RESP_TEL_NO_SENSORS = 0x13
RESP_TEL_NO_NEW_VALUES = 0x14

# Request attributes from module
REQ_ATT = 0x20
# Response codes to attribute request
RESP_ATT_SUCCESS = 0x21
RESP_ATT_ERROR = 0x22

# Request module time
REQ_TIMESTAMP = 0x30
# response codes to time request
RESP_GET_TIMESTAMP_SUCCESS = 0x31
RESP_GET_TIMESTAMP_ERROR = 0x32


# request debug information from slave
REQ_DEBUG = 0x30

# Set sample interval for sensor at module
SET_SAMPLEINTERVAL = 0x40
# Result codes
RESP_SAMPLEINTERVAL_SUCCESS = 0x41
RESP_SAMPLEINTERVAL_ERROR = 0x42
RESP_SAMPLEINTERVAL_NOSENSOR = 0x43
RESP_SAMPLEINTERVAL_JSONERROR = 0x44

MSG_START = 77
RESP_START = 82
MSG_END = 0