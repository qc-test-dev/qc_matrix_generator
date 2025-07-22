import json
import traceback
from channels.generic.websocket import AsyncWebsocketConsumer

class MatrizConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.matriz_id = self.scope['url_route']['kwargs']['matriz_id']
            self.room_group_name = f'matriz_{self.matriz_id}'

            await self.accept()

            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            await self.send(json.dumps({
                'type': 'connected',
                'message': f'Conectado a matriz {self.matriz_id}'
            }))
        except Exception as e:
            print(f"⚠️ Error en MatrizConsumer.connect: {e}")
            traceback.print_exc()
            await self.close(code=4001)

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        except Exception as e:
            print(f"⚠️ Error en MatrizConsumer.disconnect: {e}")
            traceback.print_exc()

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            if data.get('type') == 'heartbeat':
                pass
            elif data.get('type') == 'init':
                await self.send(json.dumps({'type': 'connected'}))
            elif data.get('type') == 'estado_update':
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'estado_actualizado',
                        'validate_id': data['validate_id'],  # usar validate_id
                        'nuevo_estado': data['nuevo_estado']
                    }
                )
            elif data.get('type') == 'nota_update':
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'nota_actualizada',
                        'validate_id': data['validate_id'],  # usar validate_id
                        'nueva_nota': data['nueva_nota']
                    }
                )
        except Exception as e:
            print(f"❌ ERROR en MatrizConsumer.receive: {e}")
            traceback.print_exc()

    async def estado_actualizado(self, event):
        try:
            mensaje = {
                'type': 'estado',
                'caso_id': event.get('validate_id'),  # aquí pongo caso_id para el frontend, pero lo tomo de validate_id
                'valor': event.get('nuevo_estado'),
            }
            await self.send(text_data=json.dumps(mensaje))
        except Exception as e:
            print(f"❌ ERROR en MatrizConsumer.estado_actualizado: {e}")
            traceback.print_exc()

    async def nota_actualizada(self, event):
        try:
            mensaje = {
                'type': 'nota',
                'caso_id': event.get('validate_id'),  # mismo caso aquí
                'valor': event.get('nueva_nota'),
            }
            await self.send(text_data=json.dumps(mensaje))
        except Exception as e:
            print(f"❌ ERROR en MatrizConsumer.nota_actualizada: {e}")
            traceback.print_exc()
            
class ValidatesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.super_matriz_id = self.scope['url_route']['kwargs']['super_matriz_id']
        self.group_name = f"validate_{self.super_matriz_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        await self.send(text_data=json.dumps({'message': 'Mensaje recibido', 'data': data}))

    async def send_validation(self, event):
        await self.send(text_data=json.dumps(event['data']))