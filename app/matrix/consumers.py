# app/matrix/consumers.py
import json
import traceback
from channels.generic.websocket import AsyncWebsocketConsumer

class MatrizConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            print(f"🔵 MATRIZ CONNECT INICIADO")
            self.matriz_id = self.scope['url_route']['kwargs']['matriz_id']
            self.room_group_name = f'matriz_{self.matriz_id}'
            print(f"🔵 matriz_id: {self.matriz_id}, grupo: {self.room_group_name}")

            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            print(f"🔵 Agregado al grupo exitosamente")

            await self.accept()
            print(f"🟢 WebSocket ACEPTADO")
            
            # Enviar confirmación de conexión
            await self.send(text_data=json.dumps({
                'type': 'connected',
                'matriz_id': self.matriz_id
            }))
            print(f"🟢 Mensaje de confirmación enviado")
            
        except Exception as e:
            print(f"❌ ERROR EN MATRIZ CONNECT: {e}")
            traceback.print_exc()
            await self.close()

    async def disconnect(self, close_code):
        print(f"🔴 MATRIZ DISCONNECT - código: {close_code}")
        try:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        except Exception as e:
            print(f"❌ ERROR EN DISCONNECT: {e}")

    async def receive(self, text_data):
        print(f"📨 MATRIZ RECIBIÓ: {text_data}")

    async def estado_actualizado(self, event):
        try:
            print(f"🚀🚀🚀 CONSUMER RECIBIÓ: {event}")
            data = event['data']
            
            mensaje = {
                'tipo': 'estado',
                'caso_id': data['caso_id'],
                'valor': data['valor']
            }
            print(f"🚀🚀🚀 ENVIANDO A BROWSER: {mensaje}")
            
            await self.send(text_data=json.dumps(mensaje))
        except Exception as e:
            print(f"❌ ERROR EN estado_actualizado: {e}")
            traceback.print_exc()

    async def nota_actualizada(self, event):
        try:
            data = event['data']
            
            await self.send(text_data=json.dumps({
                'tipo': 'nota',
                'caso_id': data['caso_id'],
                'valor': data['valor']
            }))
        except Exception as e:
            print(f"❌ ERROR EN nota_actualizada: {e}")
            traceback.print_exc()


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
            
            await self.send(text_data=json.dumps({
                'type': 'connected',
                'super_matriz_id': self.super_matriz_id
            }))
            print(f"🟢 VALIDATES CONECTADO - grupo: {self.room_group_name}")
            
        except Exception as e:
            print(f"❌ ERROR EN VALIDATES CONNECT: {e}")
            traceback.print_exc()
            await self.close()

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
        print(f"📨 VALIDATES RECIBIÓ: {text_data}")

    async def estado_actualizado(self, event):
        try:
            print(f"🎯🎯🎯 VALIDATES CONSUMER RECIBIÓ: {event}")
            
            mensaje = {
                'type': 'estado_actualizado',
                'validate_id': event['validate_id'],
                'nuevo_estado': event['nuevo_estado']
            }
            print(f"🎯🎯🎯 ENVIANDO VALIDATE A BROWSER: {mensaje}")
            
            await self.send(text_data=json.dumps(mensaje))
        except Exception as e:
            print(f"❌ ERROR EN estado_actualizado: {e}")
            traceback.print_exc()


# Cambié TestConsumer a async para consistencia
class TestConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            print("🟢 TEST WEBSOCKET CONECTANDO...")
            await self.accept()
            print("🟢 TEST WEBSOCKET ACEPTADO")
            
            await self.send(text_data=json.dumps({
                'message': 'Test WebSocket conectado exitosamente!'
            }))
            print("🟢 TEST MENSAJE ENVIADO")
            
        except Exception as e:
            print(f"❌ ERROR EN TEST CONNECT: {e}")
            traceback.print_exc()
    
    async def disconnect(self, close_code):
        print(f"🔴 TEST WEBSOCKET DESCONECTADO: {close_code}")
    
    async def receive(self, text_data):
        print(f"📨 TEST RECIBIDO: {text_data}")
        await self.send(text_data=json.dumps({
            'echo': text_data
        }))