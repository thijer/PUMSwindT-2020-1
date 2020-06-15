#ifndef SENSORS_HPP
#define SENSORS_HPP

#include "Arduino.h"
#include "InterfaceConfig.h"
#include "InterfaceErrors.h"

// This file contains some helper object which are used by the Interface class. the Sensor classes store all the real data and metadata of a sensor.

#if defined(ESP8266) || defined(ESP32)
    #include <functional>
    #define FLOAT_CALLBACK_SIGNATURE std::function<uint16_t(double*)> Callback
    #define INT_CALLBACK_SIGNATURE std::function<uint16_t(int32_t*)> Callback
    #define BOOL_CALLBACK_SIGNATURE std::function<uint16_t(bool*)> Callback
#else
    #define FLOAT_CALLBACK_SIGNATURE uint16_t (*Callback)(double*)
    #define INT_CALLBACK_SIGNATURE uint16_t (*Callback)(int32_t*)
    #define BOOL_CALLBACK_SIGNATURE uint16_t (*Callback)(bool*)
#endif

#define FRIEND_CLASS Interface
class Interface;

class Sensor
{
    protected:
        const char* const mSensorName;
        const char* const mUnit;
        const uint32_t mMaxUpdateInterval;
        // Current sensor update interval (ms)
        uint32_t mUpdateInterval;
        // Next sensor update interval (ms)
        uint32_t mNextUpdateInterval;
        // Timestamp from when sensor was last updated (ms)
        uint32_t mUpdateTimestamp;
        // Timestamp from when sensor was first updated (ms)
        uint32_t mTimestamp = 0;

        uint8_t mWritePointer = 0;
        Sensor(const char* const SensorName, const char* const Unit, const uint32_t UpdateInterval, const uint32_t MaxUpdateInterval):
            mSensorName(SensorName),
            mUnit(Unit),
            mUpdateInterval(UpdateInterval),
            mNextUpdateInterval(UpdateInterval),
            mMaxUpdateInterval(MaxUpdateInterval)
        {}
        // Sensor()
        // {}
        virtual InterfaceError Update(uint32_t TimeStamp) = 0;
        virtual void Get(JsonArray& Values) = 0;
    public:
        void SetUpdateInterval(uint32_t UpdateInterval)
        {
            // if(UpdateInterval > mUpdateInterval) return false;
            mNextUpdateInterval = UpdateInterval;
        }
        friend class FRIEND_CLASS;
};

template<unsigned int MaxSampleInterval>
class FloatSensor: public Sensor
{
    private:
        static const uint32_t SIZE = SENSORMEMORY_SIZE * (1000 / MaxSampleInterval);
        double mValueStore[SIZE];
        // bool mStoreOverflowed = false;
    protected:
        FloatSensor(const char* const SensorName, const char* const Unit, const uint32_t SampleInterval, FLOAT_CALLBACK_SIGNATURE):
            Sensor(SensorName, Unit, SampleInterval, MaxSampleInterval),
            Callback(Callback)
        {}
        
        InterfaceError Update(uint32_t Timestamp)
        {
            mUpdateTimestamp = Timestamp;
            if(mWritePointer >= SIZE)
            {
                return ERR_SENSOR_BUFFER_OVERFLOW;
            }
            double Value;
            uint16_t Error = Callback(&Value);
            if(Error > 0) 
            {
                if(Error > 9) return ERR_SENSOR_NOT_COMPLIANT;
                else return InterfaceError(Error + ERR_SENSOR_MODULE_0);
            }
            mValueStore[mWritePointer] = Value;
            if(mWritePointer == 0) mTimestamp = Timestamp;
            mWritePointer++;
            /* 
                if(mWritePointer == SIZE) mStoreOverflowed = true;
                mWritePointer = (mWritePointer + 1) % SIZE; 
            */
        }

        void Get(JsonArray& Values)
        {
            for(uint8_t i = 0; i < mWritePointer; i++)
            {
                Values.add(mValueStore[i]);
            }
            mWritePointer = 0;
            mUpdateInterval = mNextUpdateInterval;
        }

        FLOAT_CALLBACK_SIGNATURE;
    public:
        friend class FRIEND_CLASS;
};

template<unsigned int MaxSampleInterval>
class IntSensor: public Sensor
{
    private:
        static const uint32_t SIZE = SENSORMEMORY_SIZE * (1000 / MaxSampleInterval);
        int32_t mValueStore[SIZE];
    protected:
        IntSensor(const char* const SensorName, const char* const Unit, const uint32_t SampleInterval, INT_CALLBACK_SIGNATURE):
            Sensor(SensorName, Unit, SampleInterval, MaxSampleInterval),
            Callback(Callback)
        {}
        
        InterfaceError Update(uint32_t Timestamp)
        {
            if(mWritePointer >= SIZE) return ERR_SENSOR_BUFFER_OVERFLOW;
            int32_t Value;
            uint16_t Error = Callback(&Value);
            if(Error > 0) 
            {
                if(Error > 9) return ERR_SENSOR_NOT_COMPLIANT;
                else return InterfaceError(Error + ERR_SENSOR_MODULE_0);
            }
            mValueStore[mWritePointer] = Value;
            if(mWritePointer == 0) mTimestamp = Timestamp;
            mWritePointer++;
            mUpdateTimestamp = Timestamp;
            /* 
                if(mWritePointer == SIZE) mStoreOverflowed = true;
                mWritePointer = (mWritePointer + 1) % SIZE; 
            */
        }

        void Get(JsonArray& Values)
        {
            for(uint8_t i = 0; i < mWritePointer; i++)
            {
                Values.add(mValueStore[i]);
            }
            mWritePointer = 0;
            mUpdateInterval = mNextUpdateInterval;
        }

        INT_CALLBACK_SIGNATURE;
    public:
        friend class FRIEND_CLASS;
};

template<unsigned int MaxSampleInterval>
class BoolSensor: public Sensor
{
    private:
        static const uint32_t SIZE = SENSORMEMORY_SIZE * (1000 / MaxSampleInterval);
        bool mValueStore[SIZE];
    protected:
        BoolSensor(const char* const SensorName, const char* const Unit, const uint32_t SampleInterval, BOOL_CALLBACK_SIGNATURE):
            Sensor(SensorName, Unit, SampleInterval, MaxSampleInterval),
            Callback(Callback)
        {}
        InterfaceError Update(uint32_t Timestamp)
        {
            if(mWritePointer >= SIZE) return ERR_SENSOR_BUFFER_OVERFLOW;
            bool Value;
            uint16_t Error = Callback(&Value);
            if(Error > 0) 
            {
                if(Error > 9) return ERR_SENSOR_NOT_COMPLIANT;
                else return InterfaceError(Error + ERR_SENSOR_MODULE_0);
            }
            mValueStore[mWritePointer] = Value;
            if(mWritePointer == 0) mTimestamp = Timestamp;
            mWritePointer++;
            mUpdateTimestamp = Timestamp;
            /* 
                if(mWritePointer == SIZE) mStoreOverflowed = true;
                mWritePointer = (mWritePointer + 1) % SIZE; 
            */
        }

        void Get(JsonArray& Values)
        {
            for(uint8_t i = 0; i < mWritePointer; i++)
            {
                Values.add(mValueStore[i]);
            }
            mWritePointer = 0;
            mUpdateInterval = mNextUpdateInterval;
        }

        BOOL_CALLBACK_SIGNATURE;
    public:
        friend class FRIEND_CLASS;
};

#endif