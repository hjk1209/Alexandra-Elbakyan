from django.urls import path

from .views import (
    ApiTokenLoginView,
    ApiTokenRefreshView,
    ApiTokenRevokeView,
    PasswordRequestView,
    ProfileConnectionsView,
    ProfileDetailView,
    ProfileEditView,
    SecureLoginView,
    SignUpView,
    TwoFactorVerifyView,
    UserBlockToggleView,
    logout_view,
)

urlpatterns = [
    path('entrar/', SecureLoginView.as_view(), name='login'),
    path('entrar/2fa/', TwoFactorVerifyView.as_view(), name='two-factor-verify'),
    path('api/token/', ApiTokenLoginView.as_view(), name='api-token-login'),
    path('api/token/refresh/', ApiTokenRefreshView.as_view(), name='api-token-refresh'),
    path('api/token/revoke/', ApiTokenRevokeView.as_view(), name='api-token-revoke'),
    path('solicitar-senha/', PasswordRequestView.as_view(), name='password-request'),
    path('sair/', logout_view, name='logout'),
    path('cadastro/', SignUpView.as_view(), name='signup'),
    path('perfil/editar/', ProfileEditView.as_view(), name='profile-edit'),
    path('perfil/<slug:handle>/bloquear/', UserBlockToggleView.as_view(), name='user-block-toggle'),
    path('perfil/<slug:handle>/<slug:relation_type>/', ProfileConnectionsView.as_view(), name='profile-connections'),
    path('perfil/<slug:handle>/', ProfileDetailView.as_view(), name='profile'),
]
