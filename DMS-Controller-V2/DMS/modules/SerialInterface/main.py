# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import datetime
import os
import sys
import asyncio
from azure.iot.device.aio import IoTHubModuleClient
from azure.iot.device import Message
import serial
import json
import config

# Verify if all settings are set
def SettingsFilled():
    global Settings
    # Serial interface settings
    if(Settings['BAUDRATE'] == None): return False
    if(Settings['SERIALPORT'] == None): return False
    if(Settings['PARITY'] == None): return False
    if(Settings['STOPBITS'] == None): return False
    if(Settings['DATABITS'] == None): return False
    if(Settings['TIMEOUT'] == None): return False
    return True

# Update settings from received twin properties
def UpdateProperties(Twin: dict):
    global Settings, SettingsUpdated
    if('BAUDRATE' in Twin):
        Settings['BAUDRATE'] = int(Twin['BAUDRATE'])
        SettingsUpdated = True
    if('TIMEOUT' in Twin):
        Settings['TIMEOUT'] = float(Twin['TIMEOUT'])
        SettingsUpdated = True
    if('SERIALPORT' in Twin):
        Settings['SERIALPORT'] = str(Twin['SERIALPORT'])
        SettingsUpdated = True
    if('PARITY' in Twin):
        if(Twin['PARITY'] == 'ODD'): Settings['PARITY'] = serial.PARITY_ODD
        elif(Twin['PARITY'] == 'EVEN'): Settings['PARITY'] = serial.PARITY_EVEN
        elif(Twin['PARITY'] == 'NONE'): Settings['PARITY'] = serial.PARITY_NONE
        elif(Twin['PARITY'] == 'MARK'): Settings['PARITY'] = serial.PARITY_MARK
        elif(Twin['PARITY'] == 'SPACE'): Settings['PARITY'] = serial.PARITY_SPACE
        SettingsUpdated = True
    if('STOPBITS' in Twin):
        if(Twin['STOPBITS'] == 'ONE'): Settings['STOPBITS'] = serial.STOPBITS_ONE
        elif(Twin['STOPBITS'] == 'ONE_POINT_FIVE'): Settings['STOPBITS'] = serial.STOPBITS_ONE_POINT_FIVE
        elif(Twin['STOPBITS'] == 'TWO'): Settings['STOPBITS'] = serial.STOPBITS_TWO
        SettingsUpdated = True
    if('DATABITS' in Twin):
        if(Twin['DATABITS'] == 7): Settings['DATABITS'] = serial.SEVENBITS
        elif(Twin['DATABITS'] == 8): Settings['DATABITS'] = serial.EIGHTBITS
        SettingsUpdated = True
    return SettingsFilled()

# Listen for messages from the controller
async def MessageReceiver(Client: IoTHubModuleClient, InQueue: asyncio.Queue):
    try:
        while(True):
            try:
                input_message = await Client.receive_message_on_input('InterfaceIn')  # blocking call
                Msg = input_message.data
                try:
                    Msg = json.loads(Msg)
                    print('Message receiver: Got Data: ', Msg)
                    if(Msg['MessageType'] == 'ModuleCommand' and Msg['InterfaceType'] == 'SerialInterface'):
                        print('Message receiver: Queueing')
                        await InQueue.put(Msg)
                except json.JSONDecodeError as ex:
                    print('Message receiver: Error decoding JSON - {}'.format(ex))
            except Exception as ex:
                print('Message receiver: Error - {}'.format(ex))
            
    except asyncio.CancelledError:
        print('Message receiver: Task cancelled.')

# Send message to the controller
async def MessageSender(Client: IoTHubModuleClient, OutQueue: asyncio.Queue):
    try:
        while(True):
            data = await OutQueue.get()
            print('Message sender: ', data)
            msg = json.dumps(data)
            msg = Message(msg)
            try:
                await Client.send_message_to_output(msg, 'InterfaceOut')
                OutQueue.task_done()
            except Exception as ex:
                print ('Unexpected error in sender: {}'.format(ex))
            print('Finished sending')
    except asyncio.CancelledError:
        print('Message sender: Task cancelled')
            
# Process message form controller
def ProcessMessage(Msg: dict, OutQueue: asyncio.Queue):
    if(Msg['MessageType'] == 'ModuleCommand'):
        OutQueue.put(Msg)
    # More logic can be added to switch between message types

# Convert bytearray message to dictionary
def SerialBytesToDict(Response: bytes,  Request: dict):
    # Decode a serial interface message to a python dictionary
    try: 
        print(Response)
        length = len(Response)
        if(length < 4 or Response[-1] != config.MSG_END or int(Response[0]) != config.RESP_START):
            print('Invalid Message: ')
            Msg = {
                'MessageType': 'ModuleResponse',
                'InterfaceType': 'SerialInterface',
                'Address': Request['Address'],
            }
            return False, dict()
        PH = ''
        if(length > 4):
            try:
                PH = json.loads(Response[3:-1].decode('ascii'))
            except json.JSONDecodeError as ex:
                print('Decoding failed: {}'.format(ex))
                return False, dict()

            print('Message contents:')
            print(PH)
        Message = {
            'MessageType': 'ModuleResponse',
            'InterfaceType': 'SerialInterface',
            'Address': int(Response[1]),
            'Timestamp': datetime.datetime.now().timestamp(),
            'FunctionCode': int(Response[2]),
            'Message': PH
        }
        return True, Message
    except Exception as ex:
        print('Serial: Error converting bytes to dict - {}'.format(ex))
        False, dict()

# Convert dictionary message to bytearray
def DictToSerialBytes(Msg: dict):
    try:
        # text = bytearray()
        # text += bytes([config.MSG_START,  int(Msg['Address']), int(Msg['FunctionCode'])])
        if('Message' in Msg): 
            text = bytes([
                config.MSG_START, 
                int(Msg['Address']), 
                int(Msg['FunctionCode']),
                json.dumps(Msg['Message']).encode('ascii'),
                0
            ])
            return True, text
        else:
            text = bytes([
                config.MSG_START, 
                int(Msg['Address']), 
                int(Msg['FunctionCode']),
                0
            ])
            return True, text
        # text += bytes([0])
        
    except Exception as ex:
        print ('Serial: Error converting dict to bytes - {}'.format(ex))
        return False, bytearray()

# Replacement for SerialBytesToDict
def ConstructResponse(Request: dict, Input: bytes):
    # This function constructs a response message for the controller, based on the received bytes from the serial connection.
    # It uses the responsecodes defined in config. Ensure that those response codes are equal to the codes in the controller config and the InterfaceConfig.h file
    Message = {
        'MessageType': 'ModuleResponse',
        'InterfaceType': 'SerialInterface',
        'Address': int(Request[1]),
        'Timestamp': datetime.datetime.now().timestamp(),
        'FunctionCode': int(Request[2])
    }
    # No response at all
    if(len(Input) == 0): 
        Message.update({'ResponseCode': config.RESP_TIMEOUT})
    
    # At least 4 bytes are expected in a response
    elif(len(Input) < 4):
        Message.update({'ResponseCode': config.RESP_INVALID_HEADER})
    
    # Last byte should be MSG_END and first byte should be RESP_START
    elif(Input[-1] != config.MSG_END or int(Input[0]) != config.RESP_START):
        Message.update({'ResponseCode': config.RESP_INVALID_HEADER})
    
    # Normal response without JSON payload
    elif(len(Input) == 4):
        Message.update({'ResponseCode': int(Input[2])})
    
    # Normal response with JSON payload
    else:
        try:
            String = Input[3:-1].decode('ascii')
            PH = json.loads(String)
            Message.update({'ResponseCode': int(Input[2]), 'Message': PH})
        except UnicodeDecodeError as ex:
            # Byte array cna't be converted to string
            print('Decoding failed: {}'.format(ex))
            Message.update({'ResponseCode': config.RESP_BYTE_DECODE_ERROR})
        except json.JSONDecodeError as ex:
            # Wrong JSON syntax
            print('Decoding failed: {}'.format(ex))
            Message.update({'ResponseCode': config.RESP_JSON_DECODE_ERROR})
    return Message
            
# Serial manager
async def SerialAdapter(InQueue: asyncio.Queue, OutQueue: asyncio.Queue):
    global Settings, SettingsComplete, SettingsUpdated
    # RequestInProcess = False
    # StartingTime = datetime.time()
    # print('Serial: Starting')
    while(not SettingsComplete):
        await asyncio.sleep(3)
    print('Serial adapter: Starting serial port.')
    
    try:
        ser = serial.Serial(
            port = Settings['SERIALPORT'], 
            baudrate = Settings['BAUDRATE'], 
            bytesize = Settings['DATABITS'], 
            parity = Settings['PARITY'], 
            stopbits = Settings['STOPBITS'],
            timeout = Settings['TIMEOUT']
            )
        SettingsUpdated = False
        print('Serial adapter: Serial port started.')
        while(True):
            if(SettingsUpdated):
                ser.close()
                ser.baudrate = Settings['BAUDRATE']
                ser.bytesize = Settings['DATABITS']
                ser.parity = Settings['PARITY']
                ser.stopbits = Settings['STOPBITS']
                ser.timeout = Settings['TIMEOUT']
                ser.port = Settings['SERIALPORT']
                ser.open()
                SettingsUpdated = False
            # A queued message can be sent
            Request = await OutQueue.get() # this function blocks until a message is available from the queue
            if( Request['Address'] in range(0, 256) and Request['FunctionCode'] in range(0, 256) ):
                print('Serial adapter: Message from controller:', Request)
                Success, data = DictToSerialBytes(Request)
                # OutQueue.task_done()
                if(Success):
                    print('Serial adapter: Sending message -', data)
                    try:
                        # Discard any previous responses that failed the timeout deadline but still arrived
                        ser.flushInput()
                        BytesSent = ser.write(data)
                    except Exception as ex:
                        print ('Serial adapter: Error sending message - {}'.format(ex))
                    # StartingTime = datetime.time()
                    try:
                        text = bytearray()
                        # Blocks until timeout or byte received
                        text += ser.read()
                        if(len(text) > 0):
                            # We wantz more bytez, until the zero byte haz arrived
                            while(text[-1] != 0):
                                byte = ser.read()
                                # Timeout
                                if(len(byte) == 0): break
                                else: text += byte
                        Message = ConstructResponse(Request, text)
                        await InQueue.put(Message)
                    
                    except Exception as ex:
                        print ('Serial adapter: Error receiving response - {}'.format(ex))
                else:
                    await InQueue.put(
                        {
                            'MessageType': 'ModuleResponse',
                            'InterfaceType': 'SerialInterface',
                            'Address': int(Request[1]),
                            'Timestamp': datetime.datetime.now().timestamp(),
                            'FunctionCode': int(Request[2]), 
                            'ResponseCode': config.RESP_JSON_ENCODE_ERROR
                        }
                    )
            else:
                await InQueue.put(
                {
                    'MessageType': 'ModuleResponse',
                    'InterfaceType': 'SerialInterface',
                    'Address': int(Request[1]),
                    'Timestamp': datetime.datetime.now().timestamp(),
                    'FunctionCode': int(Request[2]), 
                    'ResponseCode': config.RESP_INVALID_REQUEST
                }
            )
    # except Exception as ex:
    #     print ('Serial adapter: Error - {}'.format(ex))
    except (KeyboardInterrupt, asyncio.CancelledError):
        print('Serial adapter: exit.')
        ser.close()# Send to and receive commands from modules connected to the serial interface

# ReceiveTwinProperties is invoked when the module twin's desired properties are updated.
async def ReceiveTwinProperties(client: IoTHubModuleClient):
    global SettingsComplete, Settings
    print('Receive twin properties: Starting')
    try:
        # Get desired properties
        properties = await client.get_twin()
        SettingsComplete = UpdateProperties(properties['desired'])
        print('Receive twin properties: Got twin:', properties['desired'])
        print('Receive twin properties: Current settings:', Settings)
        # Listen for updates
        while(True):
            try:
                data = await client.receive_twin_desired_properties_patch()  # blocking call
                SettingsComplete = UpdateProperties(data)
                print('Receive twin properties: Got update patch', Settings)
            except Exception as ex:
                print('Receive twin properties: Error - {}'.format(ex))
    except asyncio.CancelledError:
        print('Receive twin properties: Task cancelled')
    except Exception as ex:
        print('Receive twin properties: Error - {}'.format(ex))

# async setup function, because create_from_edge_environment needs a background event loop
async def Startup():
    print('Starting now')
    try:
        client = IoTHubModuleClient.create_from_edge_environment()
        print('Created client')
        await client.connect()
        print('Connected')
        return client
    except Exception as ex:
        print('Startup: Error - {}'.format(ex))

# GLOBALS
Settings = {
    'BAUDRATE': None,
    'SERIALPORT': None,
    'PARITY': None,
    'STOPBITS': None,
    'DATABITS': None,
    'TIMEOUT': None
}

SettingsComplete = False
SettingsUpdated = False

# Everthing starts at the main
def Main():
    OutQueue = asyncio.Queue()
    InQueue = asyncio.Queue()
    Tasks = []

    # All settings required for the operation of this adapter are in place
    try:
        if(not sys.version >= '3.7.0'):
            raise Exception('The sample requires python 3.7.0+. Current version of Python: {}'.format(sys.version))
        loop = asyncio.get_event_loop()
        client = loop.run_until_complete(Startup())
        
        # Create running tasks
        Tasks.append(loop.create_task(
            ReceiveTwinProperties(client)
            ))
        Tasks.append(loop.create_task(
            MessageReceiver(client, OutQueue)
            ))
        Tasks.append(loop.create_task(
            MessageSender(client, InQueue)
            ))
        Tasks.append(loop.create_task(
            SerialAdapter(InQueue, OutQueue)
            ))
        
        while(True):
            loop.run_until_complete(asyncio.sleep(30))
    except Exception as ex:
        print('Main: {}'.format(ex))
    except KeyboardInterrupt:
        pass
    finally:
        print('Quittin\'')
        for task in Tasks:
            task.cancel()
        loop.run_until_complete(client.disconnect())

# Program starts here
if __name__ == '__main__':
    Main()