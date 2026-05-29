from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import ApiRefreshToken, PasswordRequest, TwoFactorChallenge, User, UserBlock


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        'login_id',
        'username',
        'display_name',
        'email',
        'role',
        'is_health_operator',
        'is_rapporteur',
        'is_warehouse_operator',
        'is_staff',
        'is_active',
    )
    list_filter = (
        'role',
        'is_health_operator',
        'is_rapporteur',
        'is_warehouse_operator',
        'is_staff',
        'is_active',
        'is_profile_private',
        'two_factor_enabled',
    )
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            'Perfil social',
            {
                'fields': (
                    'login_id',
                    'handle',
                    'display_name',
                    'birth_date',
                    'phone_number',
                    'bio',
                    'location',
                    'avatar',
                    'avatar_url',
                    'role',
                    'is_health_operator',
                    'is_rapporteur',
                    'is_warehouse_operator',
                    'is_profile_private',
                    'requires_moderation_review',
                    'onboarding_completed',
                    'background_theme',
                    'two_factor_enabled',
                    'two_factor_channel',
                    'last_two_factor_verified_at',
                )
            },
        ),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        (
            'Perfil social',
            {
                'fields': (
                    'email',
                    'handle',
                    'display_name',
                    'birth_date',
                    'phone_number',
                    'bio',
                    'location',
                    'avatar',
                    'avatar_url',
                    'role',
                    'is_health_operator',
                    'is_rapporteur',
                    'is_warehouse_operator',
                    'is_profile_private',
                    'background_theme',
                    'two_factor_enabled',
                    'two_factor_channel',
                )
            },
        ),
    )
    readonly_fields = ('login_id', 'last_two_factor_verified_at')
    search_fields = ('login_id', 'username', 'display_name', 'email', 'handle')


@admin.register(PasswordRequest)
class PasswordRequestAdmin(admin.ModelAdmin):
    list_display = ('requested_username', 'requested_email', 'status', 'created_at', 'processed_by')
    list_filter = ('status', 'created_at')
    search_fields = ('requested_username', 'requested_email', 'target_user__display_name')


@admin.register(UserBlock)
class UserBlockAdmin(admin.ModelAdmin):
    list_display = ('blocker', 'blocked', 'created_at')
    search_fields = ('blocker__display_name', 'blocked__display_name', 'blocker__handle', 'blocked__handle')


@admin.register(TwoFactorChallenge)
class TwoFactorChallengeAdmin(admin.ModelAdmin):
    list_display = ('user', 'purpose', 'channel', 'sent_to', 'created_at', 'expires_at', 'consumed_at')
    list_filter = ('purpose', 'channel', 'created_at', 'consumed_at')
    search_fields = ('user__display_name', 'user__handle', 'sent_to')


@admin.register(ApiRefreshToken)
class ApiRefreshTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'jti', 'ip_address', 'created_at', 'expires_at', 'revoked_at')
    list_filter = ('created_at', 'revoked_at')
    search_fields = ('user__display_name', 'user__handle', 'jti', 'ip_address')
