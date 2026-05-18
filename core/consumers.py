import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.serializers.json import DjangoJSONEncoder

logger = logging.getLogger('raiz.websocket')


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer para notificações em tempo real."""

    async def connect(self):
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        self.user_group = f'notifications_{self.user.id}'

        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.accept()

        logger.info(f'User {self.user.id} connected to notifications')

    async def disconnect(self, close_code):
        if self.user.is_authenticated:
            await self.channel_layer.group_discard(self.user_group, self.channel_name)
            logger.info(f'User {self.user.id} disconnected from notifications')

    async def receive(self, text_data):
        """Recebe mensagens do cliente (heartbeat, etc)."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
        except json.JSONDecodeError:
            logger.warning(f'Invalid JSON from user {self.user.id}')

    async def send_notification(self, event):
        """Envia notificação para o cliente."""
        await self.send(text_data=json.dumps(event['message']))


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer para chat em tempo real."""

    async def connect(self):
        self.user = self.scope['user']
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group = f'chat_{self.conversation_id}'

        if not self.user.is_authenticated:
            await self.close()
            return

        # Verificar se usuário tem permissão
        has_access = await self.user_has_conversation_access()
        if not has_access:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

        # Notificar que usuário entrou
        await self.channel_layer.group_send(
            self.room_group,
            {
                'type': 'user_status',
                'user_id': self.user.id,
                'username': self.user.username,
                'status': 'online'
            }
        )

        logger.info(f'User {self.user.id} joined chat {self.conversation_id}')

    async def disconnect(self, close_code):
        await self.channel_layer.group_send(
            self.room_group,
            {
                'type': 'user_status',
                'user_id': self.user.id,
                'username': self.user.username,
                'status': 'offline'
            }
        )

        await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = data.get('message', '').strip()

            if not message or len(message) > 500:
                return

            # Salvar mensagem no banco
            message_obj = await self.save_message(message)

            # Broadcast para grupo
            await self.channel_layer.group_send(
                self.room_group,
                {
                    'type': 'chat_message',
                    'message': {
                        'id': message_obj['id'],
                        'author': message_obj['author'],
                        'body': message_obj['body'],
                        'created_at': message_obj['created_at'],
                    }
                }
            )
        except json.JSONDecodeError:
            logger.warning(f'Invalid JSON from user {self.user.id}')

    async def chat_message(self, event):
        """Envia mensagem de chat para cliente."""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'data': event['message']
        }, cls=DjangoJSONEncoder))

    async def user_status(self, event):
        """Envia status de usuário (online/offline)."""
        await self.send(text_data=json.dumps({
            'type': 'status',
            'user_id': event['user_id'],
            'username': event['username'],
            'status': event['status']
        }))

    @database_sync_to_async
    def user_has_conversation_access(self):
        from messaging.models import Conversation
        return Conversation.objects.filter(
            id=self.conversation_id,
            participants=self.user
        ).exists()

    @database_sync_to_async
    def save_message(self, message_text):
        from messaging.models import Message
        from django.utils import timezone

        message = Message.objects.create(
            conversation_id=self.conversation_id,
            author=self.user,
            body=message_text
        )

        return {
            'id': message.id,
            'author': message.author.username,
            'body': message.body,
            'created_at': message.created_at.isoformat()
        }
