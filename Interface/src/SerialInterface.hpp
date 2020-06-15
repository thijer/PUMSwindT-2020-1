#ifndef SERIALINTERFACE_HPP
#define SERIALINTERFACE_HPP
#include "Interface.hpp"


class SerialInterface: public Interface
{
	public:
		SerialInterface
		(
			char ThisAddress, 
			const char* const ModuleName, 
			const char* const HardwareVersion, 
			const char* const SoftwareVersion, 
			uint8_t ReadEnablePin, 
			uint8_t WriteEnablePin, 
			Stream& Datalink, 
			Stream& Debug
			):
			Interface(ModuleName, HardwareVersion, SoftwareVersion, Debug),
			mDatalink(&Datalink),
			mReadEnablePin(ReadEnablePin),
			mWriteEnablePin(WriteEnablePin),
			mThisAddress(ThisAddress)
		{}
		SerialInterface
		(
			char ThisAddress, 
			const char* const ModuleName, 
			const char* const HardwareVersion, 
			const char* const SoftwareVersion, 
			uint8_t ReadEnablePin, 
			uint8_t WriteEnablePin, 
			Stream& Datalink
			):
			Interface(ModuleName, HardwareVersion, SoftwareVersion),
			mDatalink(&Datalink),
			mReadEnablePin(ReadEnablePin),
			mWriteEnablePin(WriteEnablePin),
			mThisAddress(ThisAddress)
		{}
		~SerialInterface(){}
		void Listen();
	protected:
	
	private:
		// Pointer to object which can act as a serial connection. 
		// To use the default arduino serial port, pass Serial as an argument to the constructor.
		// Must inherit from the Stream class.
		Stream* mDatalink = nullptr;
		const char mThisAddress;
        const uint8_t mReadEnablePin;
		const uint8_t mWriteEnablePin;
		void Send(char ResponseCode, const char* MsgPtr);
		void Send(char ResponseCode, JsonDocument& Doc);
		// void Send(char ResponseCode);
		
};

// void SerialInterface::Send(char ResponseCode)
// {
// 	Send(ResponseCode, "\n");
// }

void SerialInterface::Send(char ResponseCode, const char* MsgPtr)
{
	if(mDebug)
	{
		mDebug->println(F("Sending message: "));
		// mDebug->print(MsgPtr);
	}
	mDatalink->flush();
	digitalWrite(mReadEnablePin, true);
	digitalWrite(mWriteEnablePin, true);
	mDatalink->write(RESP_START);
	mDatalink->write(mThisAddress);
	mDatalink->write(ResponseCode);
	mDatalink->write(MsgPtr);
	mDatalink->write((uint8_t)0x00);
	mDatalink->flush();
	digitalWrite(mWriteEnablePin, false);
	digitalWrite(mReadEnablePin, false);
	// if(mDebug)
	// {
	// 	mDebug->write(RESP_START);
	// 	mDebug->write(mThisAddress);
	// 	mDebug->write(ResponseCode);
	// 	mDebug->print(MsgPtr);
	// 	mDebug->write((uint8_t)0x00);
	// }
	
}

void SerialInterface::Send(char ResponseCode, JsonDocument& Doc)
{
	if(mDebug)
	{
		mDebug->println(F("Sending message: "));
		// mDebug->print(MsgPtr);
		
	}
	// if the serial port for debugging is the same as for the interface, wait for all debug 
	// information to be transmitted before switching the RS485 module to write mode
	// otherwise, the controller would receive debug strings as module responses
	// This is not necessary if debug is disabled
	mDatalink->flush();
	digitalWrite(mReadEnablePin, true);
	digitalWrite(mWriteEnablePin, true);
	mDatalink->write(RESP_START);
	mDatalink->write(mThisAddress);
	mDatalink->write(ResponseCode);
	serializeJson(Doc, *mDatalink);
	mDatalink->write((uint8_t)0x00);
	// wait for transmission of all bytes before resetting the rs485 flow control pins
	mDatalink->flush();
	// delay(5);
	digitalWrite(mWriteEnablePin, false);
	digitalWrite(mReadEnablePin, false);
}

void SerialInterface::Listen()
{
	// Listen for requests from master
	if(mDatalink->available() > 0)
	{
		uint32_t StartTime = millis();
		char c = mDatalink->read();
		mMessageBuffer[mWritePointer] = c;
		mWritePointer++;
		while(c != MESSAGE_END || millis() - StartTime < 500)
		{
			while(mDatalink->available() > 0)
			{
				// Le message est arrivé
				c = mDatalink->read();
				mMessageBuffer[mWritePointer] = c;
				mWritePointer++;
			}	
		}
		if(c == MESSAGE_END)
		{
			// Message end received. Message can be processed
			if(mDebug)
			{
				mDebug->println(F("Serial message received."));
				mDebug->println(mMessageBuffer);
			}
			if(mMessageBuffer[0] == RESP_START)
			{
				if(mDebug) mDebug->println(F("Response message: Ignoring."));
				ClearBuffer();
				return;
			}
			// Message is not specifically for this module, or is a broadcasted message. Quittin'.
			if(mMessageBuffer[1] != mThisAddress && mMessageBuffer[1] != ADDRESS_BROADCAST)
			{
				if(mDebug) mDebug->println(F("Message is not for this module"));
				ClearBuffer();
				return;
			}
			ProcessMessage(&mMessageBuffer[2]);
		}
		else
		{
			// Timeout
			if(mDebug)
			{
				mDebug->println(F("Serial message timeout."));
				mDebug->write(mMessageBuffer, mWritePointer);
			}
		}
		ClearBuffer();
	}
}

#endif