# app/matrix/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class MatrizConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.matriz_id = self.scope['url_route']['kwargs']['matriz_id']
        self.room_group_name = f'matriz_{self.matriz_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        
        # Enviar confirmación de conexión
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'matriz_id': self.matriz_id
        }))

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        pass  # No necesitamos recibir mensajes del cliente

    # Receive message from room group
    # En consumers.py, método estado_actualizado:
    async def estado_actualizado(self, event):
        print(f"🚀🚀🚀 CONSUMER RECIBIÓ: {event}")
        data = event['data']
        
        mensaje = {
            'tipo': 'estado',
            'caso_id': data['caso_id'],
            'valor': data['valor']
        }
        print(f"🚀🚀🚀 ENVIANDO A BROWSER: {mensaje}")
        
        await self.send(text_data=json.dumps(mensaje))
    

    async def nota_actualizada(self, event):
        data = event['data']
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'tipo': 'nota',
            'caso_id': data['caso_id'],
            'valor': data['valor']
        }))
    


class ValidatesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.super_matriz_id = self.scope['url_route']['kwargs']['super_matriz_id']
        self.room_group_name = f'validates_{self.super_matriz_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        
        # Enviar confirmación de conexión
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'super_matriz_id': self.super_matriz_id
        }))

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        pass  # No necesitamos recibir mensajes del cliente

    # Receive message from room group
# En consumers.py, clase ValidatesConsumer:
    async def estado_actualizado(self, event):
        print(f"🎯🎯🎯 VALIDATES CONSUMER RECIBIÓ: {event}")
        
        mensaje = {
            'type': 'estado_actualizado',
            'validate_id': event['validate_id'],
            'nuevo_estado': event['nuevo_estado']
        }
        print(f"🎯🎯🎯 ENVIANDO VALIDATE A BROWSER: {mensaje}")
        
        await self.send(text_data=json.dumps(mensaje))