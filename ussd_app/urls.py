# ussd_app/urls.py
from django.urls import path
from .views import ussd

urlpatterns = [
    path('', ussd, name='ussd'),
]