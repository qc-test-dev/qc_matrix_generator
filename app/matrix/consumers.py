import json
from channels.generic.websocket import AsyncWebsocketConsumer

class MatrizConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.matriz_id = self.scope['url_route']['kwargs']['matriz_id']
        self.room_group_name = f'matriz_{self.matriz_id}'

        # Unir grupo
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # Enviar confirmación de conexión
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'message': f'Conectado a matriz {self.matriz_id}'
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        tipo = data.get('type')

        if tipo == 'estado_update':
            # Broadcast al grupo con el nuevo estado
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'estado_actualizado',
                    'validate_id': data['validate_id'],
                    'nuevo_estado': data['nuevo_estado'],
                    'from_instance': data.get('from_instance')
                }
            )
        elif tipo == 'nota_update':
            # Broadcast al grupo con la nueva nota
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'nota_actualizada',
                    'validate_id': data['validate_id'],
                    'nueva_nota': data['nueva_nota'],
                    'from_instance': data.get('from_instance')
                }
            )
        elif tipo == 'heartbeat':
            # Puedes manejar heartbeat si quieres
            pass

    async def estado_actualizado(self, event):
        mensaje = {
            'type': 'estado',
            'caso_id': event.get('validate_id'),
            'valor': event.get('nuevo_estado'),
            'from_instance': event.get('from_instance')
        }
        await self.send(text_data=json.dumps(mensaje))

    async def nota_actualizada(self, event):
        mensaje = {
            'type': 'nota',
            'caso_id': event.get('validate_id'),
            'valor': event.get('nueva_nota'),
            'from_instance': event.get('from_instance')
        }
        await self.send(text_data=json.dumps(mensaje))


class ValidatesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.super_matriz_id = self.scope['url_route']['kwargs']['super_matriz_id']
        self.room_group_name = f'validates_{self.super_matriz_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        await self.send(text_data=json.dumps({
            'type': 'connected',
            'message': f'Conectado a validates {self.super_matriz_id}'
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        tipo = data.get('type')

        # Aquí puedes manejar mensajes específicos para validates
        # Por ejemplo, si también quieres que valide estados o notas, 
        # replica la lógica igual que en MatrizConsumer o adáptala.

        # Ejemplo simple de echo
        if tipo == 'heartbeat':
            pass
        else:
            # Simple echo o log
            await self.send(text_data=json.dumps({
                'type': 'info',
                'message': f'Recibido mensaje: {data}'
            }))
