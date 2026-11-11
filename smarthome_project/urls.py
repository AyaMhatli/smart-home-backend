# smarthome_project/urls.py  (remplace tout le contenu)
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/', TokenObtainPairView.as_view()),         # connexion
    path('api/token/refresh/', TokenRefreshView.as_view()),    # renouvellement
    path('api/', include('devices.urls')),
#     path('api/', include('mqtt_handler.urls')),                # assistant vocal
]
