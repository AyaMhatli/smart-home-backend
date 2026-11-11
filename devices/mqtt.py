# devices/mqtt.py
import json
from django.conf import settings
import paho.mqtt.publish as publish


def publish_command(topic, payload):
    """Publie une commande JSON sur le broker Mosquitto."""
    publish.single(
        topic,
        payload=json.dumps(payload),
        hostname=settings.MQTT_HOST,
        port=settings.MQTT_PORT,
        auth={'username': settings.MQTT_USER, 'password': settings.MQTT_PASSWORD},
    )
