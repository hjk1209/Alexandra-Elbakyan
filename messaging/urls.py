from django.urls import path

from .views import InboxView, MessageCreateView, MessageReportCreateView, StartConversationView

urlpatterns = [
    path('', InboxView.as_view(), name='inbox'),
    path('nova/', StartConversationView.as_view(), name='conversation-start'),
    path('<int:conversation_id>/', InboxView.as_view(), name='conversation-detail'),
    path('<int:conversation_id>/enviar/', MessageCreateView.as_view(), name='message-send'),
    path('<int:conversation_id>/mensagem/<int:message_id>/reportar/', MessageReportCreateView.as_view(), name='message-report'),
]
