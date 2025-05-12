# dashboard/consumers.py

import json
# Use AsyncWebsocketConsumer for asynchronous channel layer operations
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


class GreenhouseConsumer(AsyncWebsocketConsumer): # <-- Switched to AsyncWebsocketConsumer
    async def connect(self):
        # Get greenhouse_id from the URL route
        # url_route is in self.scope['url_route']['kwargs']
        self.greenhouse_id = self.scope['url_route']['kwargs']['greenhouse_id']
        # Define the channel group name based on the greenhouse ID
        self.greenhouse_group_name = f'greenhouse_{self.greenhouse_id}' # <-- Get greenhouse ID and define group name

        print(f"WebSocket Connected for Greenhouse ID: {self.greenhouse_id}")

        # Join the greenhouse group. Add the channel to the group.
        await self.channel_layer.group_add( # <-- Join the group
            self.greenhouse_group_name,
            self.channel_name
        )
        print(f"WebSocket joining group: {self.greenhouse_group_name}")


        # Accept the WebSocket connection
        await self.accept()
        print(f"WebSocket connection accepted.")


    async def disconnect(self, close_code):
        print(f"WebSocket Disconnected for Greenhouse ID: {self.greenhouse_id} with code: {close_code}")

        # Leave the greenhouse group. Remove the channel from the group.
        await self.channel_layer.group_discard( # <-- Leave the group
            self.greenhouse_group_name,
            self.channel_name
        )
        print(f"WebSocket left group: {self.greenhouse_group_name}")


    # Handler for receiving messages from the WebSocket (client to server)
    # We might not need this for just pushing data, but keep it for potential future use
    async def receive(self, text_data):
        # Example: Process messages sent from the frontend
        print(f"Received message from WebSocket on group {self.greenhouse_group_name}: {text_data}")
        # If the frontend sent data, you would process it here.
        # e.g., command = json.loads(text_data).get('command')
        # if command == 'request_initial_data':
        #     await self.send_initial_data() # Example: send initial data after connection

    # Handler for receiving messages from the channel layer (server to server/group)
    # This method name ('sensor_data_update') corresponds to the 'type' in group_send/group_receive
    async def sensor_data_update(self, event): # <-- THIS METHOD IS NOW UNCOMMENTED AND ASYNC
        """
        Receives sensor data updates from the channel layer and sends them to the WebSocket.
        """
        message = event['message']
        print(f"Consumer received 'sensor_data_update' message for group {self.greenhouse_group_name}: {message}") # <-- Debug print here

        # Send the message directly back to the WebSocket to the frontend
        await self.send(text_data=json.dumps(message))

    # Add other handler methods here if the signal sends messages with different 'type' values
    # Example: async def alert_created(self, event): ...