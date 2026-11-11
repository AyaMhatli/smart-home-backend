# devices/serializers.py
from django.contrib.auth.models import User
from rest_framework import serializers
from .validation import DeviceValidationMixin
from .models import Device, Home, SensorReading


class DeviceSerializer(DeviceValidationMixin, serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ['id', 'uid', 'name', 'device_type', 'mqtt_topic', 'integration', 'host', 'home',
                  'is_online', 'state', 'last_updated']
        read_only_fields = ['id', 'is_online', 'state', 'last_updated']


class SensorReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorReading
        fields = ['device', 'temperature', 'humidity', 'motion_detected', 'timestamp']


class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=60)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=6, write_only=True)

    def validate_email(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('Cet email est déjà utilisé.')
        return value.lower()

    def create(self, data):
        # L'email sert d'identifiant de connexion
        return User.objects.create_user(
            username=data['email'], email=data['email'],
            password=data['password'], first_name=data['name'],
        )


class HomeSerializer(serializers.ModelSerializer):
    devices_count = serializers.IntegerField(source='devices.count', read_only=True)

    class Meta:
        model = Home
        fields = ['id', 'name', 'devices_count', 'created_at']
        read_only_fields = ['id', 'created_at']
