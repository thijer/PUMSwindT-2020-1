#ifndef NETWORKINTERFACE_H
#define NETWORKINTERFACE_H
#include "Interface.hpp"
#include <Server.h>
#include <Client.h>

/* WORK IN PROGRESS - NOT USABLE
This code is an attempt to use basic server and client interface from Arduino to implement an Interface class for network communication.
 */

class NetworkInterface
{
	public:
		NetworkInterface(
			const char* const ModuleName, 
			const char* const HardwareVersion, 
			const char* const SoftwareVersion, 
			Server& Server, 
			Stream& Debug
			):
			Interface(ModuleName, HardwareVersion, SoftwareVersion, Debug),
			mDatalink(&Server),
			mConnected(false)
		{}
		NetworkInterface(
			const char* const ModuleName, 
			const char* const HardwareVersion, 
			const char* const SoftwareVersion, 
			Server& Server, 
			):
			Interface(ModuleName, HardwareVersion, SoftwareVersion),
			mServer(&Server),
			mConnected(false)
		{}
		~NetworkInterface(){}
		void Listen();
		
	protected:
	
	private:
		Client mDatalink;
		Server* mServer;
		void Send(char ResponseCode, const char* MsgPtr);
		bool mConnected;
};

void NetworkInterface::Send(char ResponseCode, const char* MsgPtr = "\n")
{
	if(mDebug)
	{
		mDebug->print(F("Sending message: "));
		mDebug->print(MsgPtr);
	}
	
	mDatalink.write(RESP_START);
	mDatalink.write(ResponseCode);
	mDatalink.write(MsgPtr);
	delay(1);
}

void NetworkInterface::Listen()
{
	// Listen for requests from master
	mDatalink = mServer.available();
	if(mDatalink)
	{
		mConnected = mDatalink.connected();
		// Controller made connection
		while(mConnected && mDatalink.available() > 0)
		{
			// Le message est arrivé
			char c = mDatalink.read();
			mMessageBuffer[mWritePointer] = c;
			mWritePointer++;
			if(c == MESSAGE_END)
			{
				// Message end received. Message can be processed
				if(mDebug)
				{
					mDebug->println(F("Message received"));
				}
				ProcessMessage();
				// Clear buffer
				ClearBuffer();
			}
		}
		if(!mConnected)
		{
			mDatalink.stop();
		}

	}
	
	
}

#endif