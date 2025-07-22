import json
import traceback
from channels.generic.websocket import AsyncWebsocketConsumer

class TestConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print("🟢 TEST: Aceptando...")
        await self.accept()
        print("🟢 TEST: Aceptado - SIN ENVIAR NADA")
        # NO enviar nada por ahora
    
    async def disconnect(self, close_code):
        print(f"🔴 TEST DISCONNECT: {close_code}")
    
    async def receive(self, text_data):
        print(f"📨 TEST RECIBIDO: {text_data}")
        if text_data['type'] == 'init':
            await self.send(json.dumps({'type': 'connected'}))
        elif text_data['type'] == 'estado_update':
            # Procesar actualización y difundir al grupo
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'estado_actualizado',
                    'validate_id': text_data['validate_id'],
                    'nuevo_estado': text_data['nuevo_estado']
                }
            )
        elif text_data['type'] == 'heartbeat':
            pass  # Solo mantener conexión activa

class MatrizConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.matriz_id = self.scope['url_route']['kwargs']['matriz_id']
            self.room_group_name = f'matriz_{self.matriz_id}'
            
            # Aceptar conexión primero
            await self.accept()
            
            # Verificar permisos/autenticación aquí si es necesario
            
            # Unirse al grupo
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            
            # Enviar mensaje de confirmación
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'Conexión WebSocket establecida',
                'matriz_id': self.matriz_id
            }))
            
        except Exception as e:
            print(f"Error en connect: {str(e)}")
            await self.close(code=4001)  # Código personalizado para errores

    async def disconnect(self, close_code):
        # Limpieza consistente
        try:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        except:
            pass

class ValidatesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            print(f"🔵 VALIDATES CONNECT INICIADO")
            self.super_matriz_id = self.scope['url_route']['kwargs']['super_matriz_id']
            self.room_group_name = f'validates_{self.super_matriz_id}'

            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            await self.accept()
            print(f"🟢 VALIDATES CONECTADO - NO ENVIANDO MENSAJE")
            
        except Exception as e:
            print(f"❌ ERROR EN VALIDATES CONNECT: {e}")
            traceback.print_exc()

    async def disconnect(self, close_code):
        print(f"🔴 VALIDATES DISCONNECT - código: {close_code}")
        try:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        except Exception as e:
            print(f"❌ ERROR EN DISCONNECT: {e}")

    async def receive(self, text_data):
        print(f"📨 TEST RECIBIDO: {text_data}")
        if text_data['type'] == 'init':
            await self.send(json.dumps({'type': 'connected'}))
        elif text_data['type'] == 'estado_update':
            # Procesar actualización y difundir al grupo
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'estado_actualizado',
                    'validate_id': text_data['validate_id'],
                    'nuevo_estado': text_data['nuevo_estado']
                }
            )
        elif text_data['type'] == 'heartbeat':
            pass  # Solo mantener conexión activa

    async def estado_actualizado(self, event):
        try:
            print(f"🎯🎯🎯 VALIDATES CONSUMER RECIBIÓ: {event}")
            
            mensaje = {
                'type': 'estado_actualizado',
                'validate_id': event['validate_id'],
                'nuevo_estado': event['nuevo_estado']
            }
            
            await self.send(text_data=json.dumps(mensaje, ensure_ascii=True))
        except Exception as e:
            print(f"❌ ERROR EN estado_actualizado: {e}")
            traceback.print_exc()