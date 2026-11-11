# devices/admin.py
from django.contrib import admin
from .models import Device, Home, SensorReading

admin.site.register(Device)
admin.site.register(SensorReading)
admin.site.register(Home)
