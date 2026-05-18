from django.contrib import admin

from .models import LoginAttempt, SecurityEvent


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ('username', 'ip_address', 'was_successful', 'attempted_at')
    list_filter = ('was_successful', 'attempted_at')
    search_fields = ('username', 'ip_address')


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'severity', 'user', 'ip_address', 'request_path', 'created_at')
    list_filter = ('event_type', 'severity', 'created_at')
    search_fields = ('user__username', 'user__handle', 'user__display_name', 'ip_address', 'request_path')
