# devices/urls.py
from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('devices', views.DeviceViewSet, basename='device')
router.register('homes', views.HomeViewSet, basename='home')

urlpatterns = router.urls + [
    path('summary/', views.summary),
    path('sensors/history/', views.sensor_history),
    path('me/', views.me),
    path('auth/register/', views.register),
]
