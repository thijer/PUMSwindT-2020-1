#ifndef INTERFACE_HPP
#define INTERFACE_HPP
#include "Arduino.h"
#include "ArduinoJson.h"
#include "Sensors.hpp"
#include "InterfaceConfig.h"

// This file contains the Interface class, the class containg the most relevant logic for the Interface

class Interface
{
	protected:
		Interface(
			const char* const ModuleName, 
            const char* const HardwareVersion, 
            const char* const SoftwareVersion, 
            Stream& Debug
            );
		Interface(
			const char* const ModuleName, 
            const char* const HardwareVersion, 
            const char* const SoftwareVersion
            );
		~Interface();
        // Pointer to object where debug information can be sent to. Use some type of Serial
        Stream* mDebug = nullptr;
        
        // Arrays containing references (pointers) to sensor objects.
        Sensor* mSensorStore[SENSORBUFFER_SIZE];
        uint16_t mSensorsRegistered = 0;

        // Buffer for incoming messages from DMS controller
        char mMessageBuffer[INBUFFER_SIZE] = {0};
        uint16_t mWritePointer = 0;
        
        // Information about this module
        // Module name. Should, but not must, be unique. Can be used in the i-share invironment to identify a module
        const char* const mModuleName;
        // Hardware version. This information is not used by the Interface, but can be used in the i-share environment to 
        // differentiate between module versions which might output their data different. 
        const char* const mHardwareVersion;
        // Software version. This information is not used by the Interface, but can be used in the i-share environment to 
        // differentiate between module versions which might output their data different. 
        const char* const mSoftwareVersion;
		
        // Class methods
        void GetModuleTime();
        void SetUpdateInterval(const char* Msg);
        Sensor* FindSensorByName(const char* Name);
		void ProcessMessage(const char* Msg);
        void SendTelemetry();
		void SendAttributes();
		void GatherValues();
        void ClearBuffer();
		virtual void Send(char ResponseCode, const char* MsgPtr);
        virtual void Send(char ResponseCode);
        virtual void Send(char ResponseCode, JsonDocument& Doc);
	public:
        template<unsigned int MaxSampleInterval>
        uint16_t AddSensor(const char* const Name, const char* const Unit, const uint32_t SampleInterval, FLOAT_CALLBACK_SIGNATURE);

        template<unsigned int MaxSampleInterval>
        uint16_t AddSensor(const char* const Name, const char* const Unit, const uint32_t SampleInterval, INT_CALLBACK_SIGNATURE);

        template<unsigned int MaxSampleInterval>
        uint16_t AddSensor(const char* const Name, const char* const Unit, const uint32_t SampleInterval, BOOL_CALLBACK_SIGNATURE);
		virtual void Listen();
        void Loop();
	
	private:
		
	
};

// CONSTRUCTION
    Interface::Interface
    (
        const char* const ModuleName, 
        const char* const HardwareVersion, 
        const char* const SoftwareVersion, 
        Stream& Debug
        ):
        mModuleName(ModuleName),
        mHardwareVersion(HardwareVersion),
        mSoftwareVersion(SoftwareVersion),
        mDebug(&Debug)
    {}

    Interface::Interface
    (
        const char* const ModuleName, 
        const char* const HardwareVersion, 
        const char* const SoftwareVersion 
        ):
        mModuleName(ModuleName),
        mHardwareVersion(HardwareVersion),
        mSoftwareVersion(SoftwareVersion),
        mDebug(nullptr)
    {}

    Interface::~Interface()
    {}
// 

// TIMEKEEPING
    // Set the sample interval of a sensor
    void Interface::SetUpdateInterval(const char* Msg)
    {
        /** Example data:
            [
                [
                    Sensor name,
                    interval between samples (ms)
                ],
                [
                    "Compass",
                    1000
                ]
            ]
        */
        // char* Msg = mMessageBuffer + 3;
        // uint32_t Length = strlen(Msg);
        StaticJsonDocument<150> Doc;
        DeserializationError err = deserializeJson(Doc, Msg);
        if(err)
        {
            if(mDebug)
            {
                mDebug->print(F("SetUpdateInterval - Error deserializing data: "));
                mDebug->print(err.c_str());
            }
            Send(RESP_SAMPLEINTERVAL_JSONERROR);
            return;
        }
        JsonArray array = Doc.as<JsonArray>();
        if(array.isNull())
        {
            Send(RESP_SAMPLEINTERVAL_JSONERROR);
            return;
        }
        for(JsonArray Entry : array)
        {
            if(!Entry[0].is<char*>())
            {
                Send(RESP_SAMPLEINTERVAL_JSONERROR);
                return;
            }
            Sensor* Sens = FindSensorByName(Entry[0].as<char*>());
            if(Sens == nullptr)
            {
                Send(RESP_SAMPLEINTERVAL_NOSENSOR);
                return;
            }
            if(!Entry[1].is<uint32_t>())
            {
                Send(RESP_SAMPLEINTERVAL_JSONERROR);
                return;
            }
            Sens->SetUpdateInterval(Entry[1].as<uint32_t>());
            Send(RESP_SAMPLEINTERVAL_SUCCESS);
        }
    }

    // Get the value of the internal clock
    void Interface::GetModuleTime()
    {
        StaticJsonDocument<100> Timestamp;
        Timestamp["ts"] = millis();
        uint32_t Length = measureJson(Timestamp);
        if(Length > 100)
        {
            Send(RESP_GET_TIMESTAMP_ERROR);
            if(mDebug)
            {
                mDebug->print(F("\tError - JSON too long for buffer: "));
                mDebug->print(Length);
            }
            return;
        }
        Send(RESP_GET_TIMESTAMP_SUCCESS, Timestamp);
    }
//

// MESSAGING
    void Interface::ProcessMessage(const char* Ptr)
    {
        if(mDebug)
        {
            mDebug->println(F("Message received:"));
            mDebug->println(Ptr);
        }
        // invalid message received. Quittin'.
        switch(Ptr[0])
        {
            case REQ_TEL:
                SendTelemetry();
                break;
            case REQ_ATT:
                SendAttributes();
                break;
            case REQ_TIMESTAMP:
                // return the current time (value of the internal clock)
                GetModuleTime();
                break;
            case SET_SAMPLEINTERVAL:
                // Set interval for sensor
                SetUpdateInterval(&Ptr[1]);
                break;
            default:
                // Send invalid functioncode message
                Send(RESP_INVALID_FUNCTIONCODE);
                break;
        }
    }

    void Interface::SendAttributes()
    {
        StaticJsonDocument<OUTBUFFER_SIZE> Doc;
        Doc["HWV"] = mHardwareVersion;
        Doc["SWV"] = mSoftwareVersion;
        Doc["Time"] = millis();
        JsonArray DocSensors = Doc.createNestedArray("Sensors");
        
        for(int i = 0; i < mSensorsRegistered; i++)
        {
            JsonObject SensorObj = DocSensors.createNestedObject();
            SensorObj["Name"] = mSensorStore[i]->mSensorName;
            SensorObj["Unit"] = mSensorStore[i]->mUnit;
            SensorObj["SR"] = mSensorStore[i]->mMaxUpdateInterval;
        }
        uint32_t Length = measureJson(Doc);
        if(Length > OUTBUFFER_SIZE)
        {
            Send(RESP_ATT_ERROR);
            if(mDebug)
            {
                mDebug->print(F("\tError - JSON too long for buffer: "));
                mDebug->print(Length);
            }
            return;
        }
        Send(RESP_ATT_SUCCESS, Doc);
    }

    void Interface::SendTelemetry()
    {
        /** Example data:
        [
            [
                Sensor name,
                Sample interval (ms),
                timestamp of value_0 (ms since module start),
                [
                    value_0,
                    value_1,
                    value_2,
                    ...
                    value_n
                ]
            ],
            [
                "Compass",
                1000,
                10020,
                [
                    0,
                    10,
                    12,
                    ...
                    8
                ]
            ]
        ]
        */
        // TODO - Put some logic here to dynamically calculate JSON size.
        if(mDebug)
        {
            mDebug->print(F("SendTelemetry\n"));
        }
        if(mSensorsRegistered == 0)
        {
            Send(RESP_TEL_NO_SENSORS);
            if(mDebug)
            {
                mDebug->print(F("\tNo sensors available.\n"));
            }
            return;
        }
        // Are there any sensors with new values?
        bool Updated = false;
        for(uint8_t i = 0; i < mSensorsRegistered; i++)
        {
            // Sensor* Ptr = mSensorStore[i];
            if(mSensorStore[i]->mWritePointer > 0)
            {
                Updated = true;
                break;
            }
        }
        if(!Updated)
        {
            // there are no new values.
            Send(RESP_TEL_NO_NEW_VALUES);
            if(mDebug)
            {
                mDebug->print(F("\tNo new values.\n"));
            }
            return;
        }
        // There are new values
        StaticJsonDocument<OUTBUFFER_SIZE> Telemetry;
        // JsonArray Telemetry = Doc.as<JsonArray>();
        for(uint8_t i = 0; i < mSensorsRegistered; i++)
        {
            Sensor* Ptr = mSensorStore[i];
            if(Ptr->mWritePointer > 0)
            {
                StaticJsonDocument<200> Sensor;
                // JsonArray Sensor = Sens.as<JsonArray>();
                Sensor.add(Ptr->mSensorName);
                Sensor.add(Ptr->mUpdateInterval);
                Sensor.add(Ptr->mTimestamp);
                JsonArray Values = Sensor.createNestedArray();
                Ptr->Get(Values);
                bool success = Telemetry.add(Sensor);
                if(mDebug)
                {
                    mDebug->print(F("\tAdding data: "));
                    mDebug->println(success);
                }
            }
        }
        uint32_t Length = measureJson(Telemetry);
        if(Length > OUTBUFFER_SIZE)
        {
            Send(RESP_TEL_ERROR);
            if(mDebug)
            {
                mDebug->print(F("\tError - JSON too long for buffer: "));
                mDebug->println(Length);
            }
            return;
        }
        Send(RESP_TEL_SUCCESS, Telemetry);
    }

    void Interface::Send(char ResponseCode, const char* MsgPtr)
    {
        // Nuthin'
        // This funcion is implemented at the derived classes.
    }

    void Interface::Send(char ResponseCode)
    {
        Send(ResponseCode, "\n");
    }

    void Interface::Send(char ResponseCode, JsonDocument& Doc)
    {
        // Nuthin'
        // This funcion is implemented at the derived classes.
    }
// 

// SENSOR REGISTRATION
    template<unsigned int MaxSampleInterval>
    uint16_t Interface::AddSensor(const char* const Name, const char* const Unit, const uint32_t SampleInterval, FLOAT_CALLBACK_SIGNATURE)
    {
        if(mSensorsRegistered >= SENSORBUFFER_SIZE) return 65535;
        // if(mDebug)
        // {
        //     mDebug->println(F("Reached this place."));
        //     delay(1000);
        // }
        FloatSensor<MaxSampleInterval>* temp = new FloatSensor<MaxSampleInterval>(Name, Unit, SampleInterval, Callback);
        // if(mDebug)
        // {
        //     delay(1000);
        //     mDebug->println(F("Here too."));
        // }
        mSensorStore[mSensorsRegistered] = (Sensor*)temp;
        // if(mDebug)
        // {
        //     delay(1000);
        //     mDebug->println(F("Here again."));
        // }
        return mSensorsRegistered++;
    }

    template<unsigned int MaxSampleInterval>
    uint16_t Interface::AddSensor(const char* const Name, const char* const Unit, const uint32_t SampleInterval, INT_CALLBACK_SIGNATURE)
    {
        if(mSensorsRegistered >= SENSORBUFFER_SIZE) return 65535;
        mSensorStore[mSensorsRegistered] = new IntSensor<MaxSampleInterval>(Name, Unit, SampleInterval, Callback);
        return mSensorsRegistered++;
    }

    template<unsigned int MaxSampleInterval>
    uint16_t Interface::AddSensor(const char* const Name, const char* const Unit, const uint32_t SampleInterval, BOOL_CALLBACK_SIGNATURE)
    {
        if(mSensorsRegistered >= SENSORBUFFER_SIZE) return 65535;
        mSensorStore[mSensorsRegistered] = new BoolSensor<MaxSampleInterval>(Name, Unit, SampleInterval, Callback);
        return mSensorsRegistered++;
    }

    Sensor* Interface::FindSensorByName(const char* Name)
    {
        for (uint8_t i = 0; i < mSensorsRegistered; i++) {
            if (!strcmp(mSensorStore[i]->mSensorName, Name)) {
                return mSensorStore[i];
            }
        }
        return nullptr;
    }
// 

// SYSTEM UTILITIES
    // Get values from provided callback functions
    // This function should run as often and fast as possible, 
    // to minimize the delays between the update timestamp and the actual measurement
    void Interface::GatherValues()
    {
        uint32_t TimeStamp = millis();
        for(int i = 0; i < mSensorsRegistered; i++)
        {
            Sensor* Ptr = mSensorStore[i];
            if(TimeStamp - Ptr->mUpdateTimestamp > Ptr->mUpdateInterval - SENSOR_UPDATE_DELAYMARGIN)
            {
                // if(mDebug)
                // {
                //     mDebug->println(F("Gathering."));
                // }
                InterfaceError Error = mSensorStore[i]->Update(TimeStamp);
            }
        }
    }

    void Interface::ClearBuffer()
    {
        memset(mMessageBuffer, 0, sizeof(mMessageBuffer[0]) * INBUFFER_SIZE);
        mWritePointer = 0;
    }

    void Interface::Loop()
    {
        // Listen for incoming messages.
        Listen();
        // Check if a measurement needs to be done.
        GatherValues();
    }

    void Interface::Listen()
    {
        // Nuthin'
        // This funcion is implemented at the derived classes.
    }
// 

#endif