from channels.generic.websocket import AsyncWebsocketConsumer
import json
import logging

logger = logging.getLogger(__name__)

class MatrizConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.matriz_id = self.scope['url_route']['kwargs']['matriz_id']
        self.room_group_name = f'matriz_{self.matriz_id}'
        
        logger.info(f"🔌 WebSocket conectando a grupo: {self.room_group_name}")
        logger.info(f"🔍 Scope URL: {self.scope.get('path')}")
        logger.info(f"🔍 Client: {self.scope.get('client')}")
        logger.info(f"🔍 Headers: {dict(self.scope.get('headers', []))}")
        
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        
        logger.info(f"✅ WebSocket conectado al grupo: {self.room_group_name}")
        logger.info(f"🔍 Channel name: {self.channel_name}")

    async def disconnect(self, close_code):
        logger.info(f"🔌 WebSocket desconectando del grupo: {self.room_group_name}")
        logger.info(f"🔍 Close code: {close_code}")
        logger.info(f"🔍 Close reason: {getattr(self, 'close_reason', 'No reason provided')}")
        
        # Verificar si group_name existe antes de remover
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            logger.info(f"✅ Removido del grupo: {self.room_group_name}")
        else:
            logger.warning("⚠️ No se pudo remover del grupo - room_group_name no existe")

    async def receive(self, text_data):
        """Nuevo: Log cuando se recibe algo del cliente"""
        logger.info(f"📥 Recibido del cliente: {text_data}")

    async def estado_actualizado(self, event):
        logger.info(f"📨 Recibido evento estado_actualizado: {event}")
        
        try:
            message = {
                "tipo": "estado",
                "caso_id": event["data"]["caso_id"],
                "valor": event["data"]["valor"],
            }
            await self.send(text_data=json.dumps(message))
            logger.info(f"📤 Mensaje enviado al WebSocket: {message}")
        except Exception as e:
            logger.error(f"❌ Error enviando mensaje: {e}")

    async def nota_actualizada(self, event):
        logger.info(f"📨 Recibido evento nota_actualizada: {event}")
        
        try:
            message = {
                "tipo": "nota",
                "caso_id": event["data"]["caso_id"],
                "valor": event["data"]["valor"],
            }
            await self.send(text_data=json.dumps(message))
            logger.info(f"📤 Mensaje nota enviado al WebSocket: {message}")
        except Exception as e:
            logger.error(f"❌ Error enviando nota: {e}")
        

class ValidateConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.super_matriz_id = self.scope['url_route']['kwargs']['super_matriz_id']
        self.group_name = f"validates_{self.super_matriz_id}"
        
        logger.info(f"🔌 ValidateConsumer conectando a grupo: {self.group_name}")
        logger.info(f"🔍 Validate Scope URL: {self.scope.get('path')}")
        logger.info(f"🔍 Validate Client: {self.scope.get('client')}")
        
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        
        logger.info(f"✅ ValidateConsumer conectado al grupo: {self.group_name}")
        logger.info(f"🔍 Validate Channel name: {self.channel_name}")

    async def disconnect(self, close_code):
        logger.info(f"🔌 ValidateConsumer desconectando del grupo: {self.group_name}")
        logger.info(f"🔍 Validate Close code: {close_code}")
        
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            logger.info(f"✅ ValidateConsumer removido del grupo: {self.group_name}")

    async def receive(self, text_data):
        """Log cuando se recibe algo del cliente"""
        logger.info(f"📥 ValidateConsumer recibido del cliente: {text_data}")

    async def estado_actualizado(self, event):
        logger.info(f"📨 ValidateConsumer recibido evento: {event}")
        
        try:
            message = {
                "type": "estado_actualizado",
                "validate_id": event["validate_id"],
                "nuevo_estado": event["nuevo_estado"],
            }
            await self.send(text_data=json.dumps(message))
            logger.info(f"📤 ValidateConsumer mensaje enviado: {message}")
        except Exception as e:
            logger.error(f"❌ ValidateConsumer error enviando: {e}")