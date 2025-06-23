from channels.generic.websocket import AsyncWebsocketConsumer
import json

class MatrizConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.matriz_id = self.scope['url_route']['kwargs']['matriz_id']
        self.room_group_name = f'matriz_{self.matriz_id}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def estado_actualizado(self, event):
        await self.send(text_data=json.dumps(event["data"]))

    async def nota_actualizada(self, event):
        await self.send(text_data=json.dumps({
        "tipo": "nota",
        "caso_id": event['data']['caso_id'],
        "valor": event['data']['valor'],
    }))

class ValidateConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.super_matriz_id = self.scope['url_route']['kwargs']['super_matriz_id']
        self.group_name = f"validates_{self.super_matriz_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # Handler para eventos enviados desde views.py
    async def estado_actualizado(self, event):
        await self.send(text_data=json.dumps({
            "type": "estado_actualizado",
            "validate_id": event["validate_id"],
            "nuevo_estado": event["nuevo_estado"],
        }))