from channels.generic.websocket import AsyncWebsocketConsumer
import json
import logging

logger = logging.getLogger(__name__)

class MatrizConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.matriz_id = self.scope['url_route']['kwargs']['matriz_id']
        self.room_group_name = f'matriz_{self.matriz_id}'
        logger.info(f"🔌 WebSocket conectando a grupo: {self.room_group_name}")
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        logger.info(f"✅ WebSocket conectado al grupo: {self.room_group_name}")

    async def disconnect(self, close_code):
        logger.info(f"🔌 WebSocket desconectando del grupo: {self.room_group_name}")
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def estado_actualizado(self, event):
        logger.info(f"📨 Recibido evento estado_actualizado: {event}")
        await self.send(text_data=json.dumps({
            "tipo": "estado",
            "caso_id": event["data"]["caso_id"],
            "valor": event["data"]["valor"],
        }))
        logger.info(f"📤 Mensaje enviado al WebSocket")

    async def nota_actualizada(self, event):
        logger.info(f"📨 Recibido evento nota_actualizada: {event}")
        await self.send(text_data=json.dumps({
            "tipo": "nota",
            "caso_id": event["data"]["caso_id"],
            "valor": event["data"]["valor"],
        }))
        logger.info(f"📤 Mensaje nota enviado al WebSocket")

class ValidateConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.super_matriz_id = self.scope['url_route']['kwargs']['super_matriz_id']
        self.group_name = f"validates_{self.super_matriz_id}"
        logger.info(f"🔌 ValidateConsumer conectando a grupo: {self.group_name}")
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(f"✅ ValidateConsumer conectado al grupo: {self.group_name}")

    async def disconnect(self, close_code):
        logger.info(f"🔌 ValidateConsumer desconectando del grupo: {self.group_name}")
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def estado_actualizado(self, event):
        logger.info(f"📨 ValidateConsumer recibido evento: {event}")
        await self.send(text_data=json.dumps({
            "type": "estado_actualizado",
            "validate_id": event["validate_id"],
            "nuevo_estado": event["nuevo_estado"],
        }))
        logger.info(f"📤 ValidateConsumer mensaje enviado")