from channels.generic.websocket import AsyncWebsocketConsumer
import json
import logging

logger = logging.getLogger(__name__)

import asyncio

class MatrizConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # ... lo actual
        await self.accept()
        self.keepalive = asyncio.create_task(self.keep_alive())

    async def disconnect(self, close_code):
        if hasattr(self, "keepalive"):
            self.keepalive.cancel()
        # ... lo actual

    async def keep_alive(self):
        while True:
            await asyncio.sleep(30)
            try:
                await self.send(text_data=json.dumps({"type": "ping"}))
            except Exception as e:
                logger.warning(f"Keep-alive failed: {e}")
                break

class ValidateConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.super_matriz_id = self.scope['url_route']['kwargs']['super_matriz_id']
        self.group_name = f"validates_{self.super_matriz_id}"
        
        logger.info(f"🔌 ValidateConsumer conectando a grupo: {self.group_name}")
        logger.info(f"🔍 Scope URL: {self.scope.get('path')}")
        logger.info(f"🔍 Cliente: {self.scope.get('client')}")
        
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        
        logger.info(f"✅ Conectado al grupo: {self.group_name}")
        logger.info(f"🔍 Channel name: {self.channel_name}")

    async def disconnect(self, close_code):
        logger.info(f"🔌 Desconectando del grupo: {self.group_name}")
        logger.info(f"🔍 Close code: {close_code}")
        
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            logger.info(f"✅ Removido del grupo: {self.group_name}")

    async def receive(self, text_data):
        logger.info(f"📥 Mensaje recibido del cliente: {text_data}")
        # Puedes manejar comandos entrantes aquí si lo deseas
        try:
            data = json.loads(text_data)
            # Procesar data si es necesario
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ JSON inválido recibido: {text_data} - {e}")

    async def estado_actualizado(self, event):
        logger.info(f"📨 Evento recibido: {event}")
        
        try:
            message = {
                "type": "estado_actualizado",
                "validate_id": event["validate_id"],
                "nuevo_estado": event["nuevo_estado"],
            }
            await self.send(text_data=json.dumps(message))
            logger.info(f"📤 Mensaje enviado al cliente: {message}")
        except Exception as e:
            logger.error(f"❌ Error al enviar mensaje: {e}")