import datetime
import os
import sys
import asyncio
from azure.iot.device.aio import IoTHubModuleClient
from azure.iot.device import Message
import json
import requests

# Verify if all settings are set
def SettingsFilled():
    global Settings
    # Serial interface settings
    if(Settings['URL'] == None): return False
    if(Settings['API-KEY'] == None): return False
    
    return True

# ReceiveTwinProperties is invoked when the module twin's desired properties are updated.
async def ReceiveTwinProperties(client: IoTHubModuleClient):
    global SettingsComplete, Settings
    try:
        # Get desired properties
        properties = await client.get_twin()
        print('Receive twin properties: Got twin')
        SettingsComplete = UpdateProperties(properties['desired'])
        
        # Listen for updates
        while(True):
            try:
                data = await client.receive_twin_desired_properties_patch()  # blocking call
                print('Receive twin properties: Got update patch')
                SettingsComplete = UpdateProperties(data)
            except Exception as ex:
                print ( 'Unexpected error in twin_patch_listener: {}'.format(ex) )
    except asyncio.CancelledError:
        print('Receive twin properties: Task cancelled')

# receive messages from the controller
async def DataPlatformReceiver(Client: IoTHubModuleClient, DataPlatformIn: asyncio.Queue):
    try:
        while(True):
            try:
                input_message = await Client.receive_message_on_input('AdapterIn')  # blocking call
                print('Data platform receiver: Received message from controller')
                Msg = input_message.data
                try:
                    Msg = json.loads(Msg)
                    print('Data platform receiver: ', Msg)
                    await DataPlatformIn.put(Msg)
                except json.JSONDecodeError as ex:
                    print('Interface receiver: Error decoding JSON - {}'.format(ex))
            except Exception as ex:
                print('Message receiver: Error - {}'.format(ex))
            
    except asyncio.CancelledError:
        print('Dataplatform receiver: Task cancelled.')

def FormatMessageToIshare(Msg: dict):
    global Settings
    Message = {
        'api-key': Settings['API-KEY'],
        'data': []
    }
    for Sensor in Msg:
        for Key, Values in Sensor.items():
            for value in Values:
                Template = {
                    'id': Key,
                    'value': value[0],
                    'timestamp': value[1]
                }
                Message['data'].append(Template)
    return Message

# Send message to I-share
async def SendToIshare(MessageQueue: asyncio.Queue):
    global Settings
    headers = {
        'Content-Type': 'application/json'
    }
    try:
        while(not Settings):
            await asyncio.sleep(5)
        while(True):
            Msg = await MessageQueue.get()
            if(Settings):
                try:
                    Message = FormatMessageToIshare(Msg)
                    print('Send to I-share: Sending message -', Message)
                    result = requests.post(url=Settings['URL'], headers=headers , json=Message)
                except Exception as ex:
                    print('Error: {}'.format(ex))
    except asyncio.CancelledError:
        print('Send to I-share: Task cancelled.')  

# Update settings from received twin properties
def UpdateProperties(Twin: dict):
    global Settings
    if('URL' in Twin):
        Settings['URL'] = Twin['URL']
    if('API-KEY' in Twin):
        Settings['API-KEY'] = Twin['API-KEY']
    return SettingsFilled()

Settings = {
    'URL': None,
    'API-KEY': None,
}
SettingsComplete = False

async def Startup():
    print("Starting now")
    client = IoTHubModuleClient.create_from_edge_environment()
    print("Created client")
    await client.connect()
    print("Connected")
    return client

def Main():
    # All settings required for the operation of the DMS
    
    Tasks = []
    
    # All settings required for the operation of this adapter are in place
    try:
        if(not sys.version >= '3.7.0'):
            raise Exception('The sample requires python 3.7.0+. Current version of Python: {}'.format(sys.version))
        loop = asyncio.get_event_loop()
        client = loop.run_until_complete(Startup())
        
        # message queue shared by all interfaces which send data to the controller
        DataPlatformIn = asyncio.Queue()
        
        # Construct tasks
        Tasks.append( loop.create_task( ReceiveTwinProperties( client ) ) )
        Tasks.append( loop.create_task( DataPlatformReceiver( client, DataPlatformIn ) ) )
        Tasks.append( loop.create_task( SendToIshare( DataPlatformIn ) ) )
        
        
        while(True):
            loop.run_until_complete(asyncio.sleep(30))
        
    except KeyboardInterrupt:
        print('Quittin')
    except Exception as ex:
        print('IshareAdapter: {}'.format(ex))
    finally:
        print('Quittin')
        for task in Tasks:
            task.cancel()
        

if __name__ == "__main__":
    Main()

    # If using Python 3.7 or above, you can use following code instead:
    # asyncio.run(main())