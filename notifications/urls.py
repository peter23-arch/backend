# notifications/urls.py

from django.urls import path
from .views import SaveFCMTokenView

urlpatterns = [
    path('save-token/', SaveFCMTokenView.as_view(), name='save_fcm_token'),
]