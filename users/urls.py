

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView,
    RegisterManagerView,
    LoginView,
    ProfileView,
    ChangePasswordView,
    ForgotPasswordView,
    ResetPasswordView,
    AllUsersView,
    PlatformAdminSetupView,
    GoogleAuthView,
)
urlpatterns = [
    # Public — customers only
    path('register/', RegisterView.as_view(), name='register'),

    # Admin only — register a restaurant manager
    path('register-manager/', RegisterManagerView.as_view(), name='register_manager'),
    path('admin-setup/', PlatformAdminSetupView.as_view(), name='platform_admin'),

    path('login/', LoginView.as_view(), name='login'),
    path('google/', GoogleAuthView.as_view(), name='google_auth'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('users/', AllUsersView.as_view(), name='all_users'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
]
