# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import datetime
import os
import sys
import asyncio
from azure.iot.device.aio import IoTHubModuleClient
from azure.iot.device import Message
import json
import config

"""
    This is an example of how the IoT Edge module twin should look like.
    {
        "Modules":{
            "SWT-Head-Module":{
                "Interface": "SerialInterface",
                "Address": 1
            }
            "SWT-Rotor-Module":{
                "Interface": "BluetoothInterface",
                "Address": {
                    "ID": BluetoothID,
                    "PIN": 1234
                }
            },
            "SWT-Inverter-Module":{
                "Interface": "NetworkInterface",
                "Address": "192.168.1.123"
            }
        }
    }
"""

# UTILITIES
# Find index of module
def FindModuleByTypeAndAddress(Modules: dict, Type, Address):
    # There can be only 1 bluetooth module be connected to the controller
    if(Type == 'BluetoothInterface'):
        for Key, Value in Modules.items():
            if(Value['InterfaceType'] == Type):
                return Key
        return None
    elif(Type == 'SerialInterface'):
        for Key, Value in Modules.items():
            if(
                Value['InterfaceType'] == Type and
                Value['Address'] == Address
                ):
                return Key
        return None

# Find index of sensor
def FindSensorByModuleAndName(Sensors: dict, SensorName, ModuleName):
    for Key, Value in Sensors.items():
            if(Key == SensorName):
                if(Value['ModuleName'] == ModuleName):
                    return Key
    return None

# Message scheduler callback
async def ScheduleMessage(delay: float, Queue: asyncio.Queue, Msg):
    await asyncio.sleep(delay)
    await Queue.put(Msg)

# Schedule a new telemetry request on the event loop, for when it needs to be sent to the module
def ScheduleTelemetryRequest(loop: asyncio.AbstractEventLoop, Queue: asyncio.Queue, Module, delay: float):
    print('Scheduling new telemtry request on event loop')
    Msg = {
        'InterfaceType': Module['InterfaceType'],
        'MessageType': 'ModuleCommand',
        'Address': Module['Address'],
        'FunctionCode': config.REQ_TEL
    }
    loop.create_task( ScheduleMessage( delay, Queue, Msg) )


async def ManageModules(InterfaceOut: asyncio.Queue):
    global Modules, Sensors
    while(True):
        for ModuleName, Properties in Modules.items():
            if(not Properties['Complete']):
                print('Manage modules: Incomplete module found. Sending Attribute request to address {}'.format(Properties['Address']))
                # Module information is not complete, request attribute update from module
                Msg = {
                    'InterfaceType': Properties['InterfaceType'],
                    'MessageType': 'ModuleCommand',
                    'Address': Properties['Address'],
                    'FunctionCode': config.REQ_ATT
                }
                await InterfaceOut.put(Msg)
        await asyncio.sleep(10)

# Update settings from received twin properties
def UpdateProperties(Twin: dict):
    global Modules, Sensors, Settings
    if('Modules' in Twin):
        for Key, Value in Twin['Modules'].items():
            if(Key not in Modules):
                print('Update properties: Registering new module')
                # new module
                ModuleTemplate = {
                    
                    Key:{
                        'InterfaceType': Value['InterfaceType'],
                        'Address': Value['Address'],
                        'Complete': False
                    }
                }
                print('Update properties: ', ModuleTemplate)
                Modules.update(ModuleTemplate)
            else:
                Modules[Key]['InterfaceType'] = Value['InterfaceType']
                Modules[Key]['Address'] = Value['Address']
                print('Update properties: Updating module', Modules[Key])
    return

# IOT EDGE MESSAGE PROCESSORS
# Listens to incoming messages from interface adapter, like the Serial interface and the Bluetooth interface
async def InterfaceReceiver(Client: IoTHubModuleClient, InterfaceIn: asyncio.Queue):
    try:
        while(True):
            try:
                input_message = await Client.receive_message_on_input('InterfaceIn')  # blocking call
                Msg = input_message.data
                try:
                    Msg = json.loads(Msg)
                    print('Interface receiver: Message available.', Msg)
                    if(Msg['MessageType'] == 'ModuleResponse'):
                        await InterfaceIn.put(Msg)
                        print('Interface receiver: Message queued.')
                except json.JSONDecodeError as ex:
                    print('Interface receiver: Error decoding JSON - {}'.format(ex))
            except Exception as ex:
                print('Message receiver: Error - {}'.format(ex))
            
    except asyncio.CancelledError:
        print('Interface receiver: Task cancelled.')

# Sends messages to modules
async def InterfaceSender(Client: IoTHubModuleClient, InterfaceOut: asyncio.Queue):
    try:
        while(True):
            data = await InterfaceOut.get()
            print('Interface sender: Message to send.', data)
            msg = json.dumps(data)
            msg = Message(msg)
            try:
                await Client.send_message_to_output(msg, 'InterfaceOut')
                InterfaceOut.task_done()
            except Exception as ex:
                print ('Interface sender: Unexpected error in sender: {}'.format(ex))
            print('Interface sender: Finished sending')
    except asyncio.CancelledError:
        print('Interface sender: Task cancelled')

# Send values upstream
async def DataPlatformSender(Client: IoTHubModuleClient, CloudOut: asyncio.Queue):
    try:
        while(True):
            data = await CloudOut.get()
            try:
                print('Data platform sender: Message to send.', data)
                msg = json.dumps(data)
                msg = Message(msg)
                await Client.send_message_to_output(msg, 'AdapterOut')
                CloudOut.task_done()
            except Exception as ex:
                print ('Data platform sender: Unexpected error in sender: {}'.format(ex))
            print('Data platform sender: Finished sending')
    except asyncio.CancelledError:
        print('Data platform sender: Task cancelled')


def ProcessTelemetry(ModuleKey: str, Msg: dict):
    # There is a module for that sensor
    try:
        Data = []
        for data in Msg['Message']:
            SensorName = data[0]
            if(SensorName in Sensors):
                # Sensor is also known
                UpdateInterval = float(data[1]) / 1000.0
                Timestamp = Modules[ModuleKey]['ModuleTime'] + float(data[2]) / 1000.0
                Values = data[3]
                # TS = Modules[ModuleKey]['Timestamp'] + Timestamp
                Sensor = {
                    SensorName: []
                }
                for value in Values:
                    Sensor[SensorName].append([Timestamp, value])
                    Timestamp += UpdateInterval
                Data.append(Sensor)
                Modules[ModuleKey]['LastUpdated'] = Timestamp
        return Data
    except Exception as ex:
        print ('Process telemetry: Error - {}'.format(ex)) 

# Task to process module responses, including but not limited to telemetry and attribute responses
async def ProcessMessages(
        loop: asyncio.AbstractEventLoop, 
        InterfaceIn: asyncio.Queue, 
        InterfaceOut: asyncio.Queue, 
        CloudOut: asyncio.Queue
    ):
    global Modules, Sensors
    try:
        while(True):
            # process incoming messages
            Msg = await InterfaceIn.get()
            InterfaceIn.task_done()
            print('Process messages: Received message -', Msg)
            if(Msg['MessageType'] == 'ModuleResponse'):
                Code = Msg['FunctionCode']
                # Process errors
                if(Code in range(0, 0x10)):
                    pass

                # Process telemetry message
                if(Code in range(config.RESP_TEL_SUCCESS, config.REQ_ATT)):
                    # Verify if module exists
                    print('Process messages: Received telemetry.')
                    ModuleKey = FindModuleByTypeAndAddress(Modules, Msg['InterfaceType'], Msg['Address'])
                    if(ModuleKey is not None):
                        ScheduleTelemetryRequest(loop, InterfaceOut, Modules[ModuleKey], 1)
                        if(Code == config.RESP_TEL_SUCCESS):
                            Data = ProcessTelemetry(ModuleKey, Msg)
                            await CloudOut.put(Data)
                    else:
                        print('Process messages: Corresponding module not found.')
                
                # Process module attributes
                elif(Code == config.RESP_ATT_SUCCESS):
                    body = Msg['Message']
                    ModuleName = FindModuleByTypeAndAddress(Modules, Msg['InterfaceType'], Msg['Address'])

                    if(ModuleName is not None):
                        # Module is declared in IoT Edge twin
                        if(Modules[ModuleName]['Complete'] == False):
                            # Finalize setup
                            TS = datetime.datetime.now().timestamp()
                            ModuleTemplate = {
                                'HardwareVersion': body['HWV'],
                                'SoftwareVersion': body['SWV'],
                                # Timestamp when module clock was 0
                                'ModuleTime': Msg['Timestamp'] - (float(body['Time']) / 1000.0),
                                'LastUpdated': TS
                            }
                            Modules[ModuleName].update(ModuleTemplate)
                            Modules[ModuleName]['Complete'] = True
                            
                            # Schedule first time telemetry request. Next requests will be made after each telemetry response
                            ScheduleTelemetryRequest(loop, InterfaceOut, Modules[ModuleName], 1)
                        else:
                            Modules[ModuleName]['HardwareVersion'] = body['HWV']
                            Modules[ModuleName]['SoftwareVersion'] = body['SWV']
                            Modules[ModuleName]['ModuleTime'] = Msg['Timestamp'] - (float(body['Time']) / 1000.0)
                            # Modules[ModuleName]['LastUpdated'] = datetime.datetime.now().timestamp()
                        
                        for Sensor in body['Sensors']:
                            if(Sensor['Name'] not in Sensors):
                                SensorTemplate = {
                                    Sensor['Name']:{
                                        'ModuleName': ModuleName,
                                        'Unit': Sensor['Unit'],
                                        'Data': list()
                                    }
                                }
                                Sensors.update(SensorTemplate)
                            else:
                                Sensors[Sensor['Name']]['ModuleName'] = ModuleName
                                Sensors[Sensor['Name']]['Unit'] = Sensor['Unit']
    except asyncio.CancelledError:
        print('Process messages: Task cancelled')
    except Exception as ex:
        print ('Process messages: Error - {}'.format(ex) )

# ReceiveTwinProperties is invoked when the module twin's desired properties are updated.
async def ReceiveTwinProperties(client: IoTHubModuleClient, InterfaceOut: asyncio.Queue):
    global Modules, Sensors
    try:
        # Get desired properties
        properties = await client.get_twin()
        print('Receive twin properties: Got twin', properties)
        UpdateProperties(properties['desired'])
        # await ManageModules(InterfaceOut)
        # Listen for updates
        while(True):
            try:
                data = await client.receive_twin_desired_properties_patch()  # blocking call
                print('Receive twin properties: Got update patch')
                UpdateProperties(data)
                # await ManageModules(InterfaceOut)
            except KeyError:
                # invalid message
                pass
            except Exception as ex:
                print ('Receive twin properties: {}'.format(ex) )
    except asyncio.CancelledError:
        print('Receive twin properties: Task cancelled')
    

async def Startup():
    print("Starting now")
    client = IoTHubModuleClient.create_from_edge_environment()
    print("Created client")
    await client.connect()
    print("Connected")
    return client
        
# GLOBALS
Modules = dict()
Sensors = dict()

# Everthing starts at the main
def Main():
    global Modules, Sensors, Settings
    # All settings required for the operation of the DMS
    
    Tasks = []
    
    # All settings required for the operation of this adapter are in place
    try:
        if(not sys.version >= '3.5.3'):
            raise Exception('The sample requires python 3.5.3+. Current version of Python: {}'.format(sys.version))
        loop = asyncio.get_event_loop()
        print('Controller: Starting')
        client = loop.run_until_complete(Startup())
        
        # message queue shared by all interfaces which send data to the controller
        InterfaceIn = asyncio.Queue()
        # Message queue for controller to serial interface
        InterfaceOut = asyncio.Queue()
        # Message queue for controller to cloud adapter
        CloudOut = asyncio.Queue()

        # Construct parallel processes
        # SerialAdapter = mp.Process(target=Thread_SerialAdapter, args=(MessageIn, SerialOut, Settings['SerialInterface']))
        # BluetoothAdapter = mp.Process(target=Thread_BluetoothAdapter, args=(MessageIn, BluetoothOut, Settings['BluetoothInterface']))
        print('Controller: Creating tasks')
        # asynchronous tasks
        Tasks.append( loop.create_task( ReceiveTwinProperties( client, InterfaceOut ) ) )
        Tasks.append( loop.create_task( DataPlatformSender( client, CloudOut ) ) )
        Tasks.append( loop.create_task( InterfaceReceiver( client, InterfaceIn ) ) )
        Tasks.append( loop.create_task( InterfaceSender( client, InterfaceOut ) ) )
        Tasks.append( loop.create_task( ProcessMessages( loop, InterfaceIn, InterfaceOut, CloudOut ) ) )
        Tasks.append( loop.create_task( ManageModules( InterfaceOut ) ) )
        
        # Infinite loop. The aforementioned tasks run during the asyncio.sleep function.
        while(True):
            loop.run_until_complete(asyncio.sleep(30))
        
    except KeyboardInterrupt:
        print('Controller: Quittin')
        for task in Tasks:
            task.cancel()
        loop.run_until_complete(client.disconnect())

if __name__ == "__main__":
    Main()
    print('Goodbye')

    # If using Python 3.7 or above, you can use following code instead:
    # asyncio.run(main())