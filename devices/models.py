# devices/models.py
from django.conf import settings
from django.db import models


class Device(models.Model):
    DEVICE_TYPES = [
        ('light', 'Lumière'),
        ('fan', 'Ventilateur'),
        ('door', 'Porte'),
        ('servo', 'Servo'),
        ('sensor', 'Capteur'),
        ('tv', 'Télévision'),
    ]

    # Chaque appareil appartient à un utilisateur (une maison par client)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name='devices')
    home = models.ForeignKey('Home', on_delete=models.CASCADE, related_name='devices', null=True, blank=True)
    uid = models.CharField(max_length=64, blank=True)  # identifiant annoncé par l'appareil
    name = models.CharField(max_length=100)
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES)
    mqtt_topic = models.CharField(max_length=200, blank=True, default='')  # ex: home/esp32-a1b2/cmd
    # Appareils du commerce pilotés par le réseau (Samsung TV, WLED...)
    integration = models.CharField(max_length=30, blank=True, default='')
    host = models.CharField(max_length=100, blank=True, default='')
    is_online = models.BooleanField(default=False)
    state = models.JSONField(default=dict, blank=True)  # {"on": true, "value": 40}
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class SensorReading(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='readings')
    temperature = models.FloatField(null=True, blank=True)
    humidity = models.FloatField(null=True, blank=True)
    motion_detected = models.BooleanField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']


class Home(models.Model):
    """Un foyer appartient a un seul utilisateur, qui peut en avoir plusieurs."""
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='homes')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
