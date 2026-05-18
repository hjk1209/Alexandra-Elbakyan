from django.contrib import admin

from .models import Conversation, ConversationParticipant, Message, MessageReport


class ConversationParticipantInline(admin.TabularInline):
    model = ConversationParticipant
    extra = 0


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'is_group', 'updated_at')
    inlines = [ConversationParticipantInline, MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'author', 'created_at')


@admin.register(MessageReport)
class MessageReportAdmin(admin.ModelAdmin):
    list_display = ('message', 'reported_by', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('message__body', 'reported_by__handle', 'reported_by__username', 'message__author__handle', 'message__author__username')
