import json

import paho.mqtt.client as mqtt
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q

from devices.models import Device, SensorReading


class Command(BaseCommand):
    help = "Ecoute les messages MQTT des appareils et met a jour la base."

    def handle(self, *args, **options):
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except AttributeError:  # paho-mqtt 1.x
            client = mqtt.Client()
        client.username_pw_set(settings.MQTT_USER, settings.MQTT_PASSWORD)
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.connect(settings.MQTT_HOST, settings.MQTT_PORT, 60)
        self.stdout.write("Ecoute MQTT demarree (Ctrl+C pour arreter)")
        client.loop_forever()

    def on_connect(self, client, userdata, flags, rc, *extra):
        self.stdout.write(f"Connecte au broker (code {rc})")
        client.subscribe("home/#")

    def on_message(self, client, userdata, msg):
        try:
            self.handle_message(msg.topic, msg.payload.decode(errors="ignore"))
        except Exception as e:
            self.stderr.write(f"Erreur sur {msg.topic} : {e}")

    def handle_message(self, topic, payload):
        parts = topic.split("/")
        if parts == ["home", "discovery"]:
            self.stdout.write(f"Annonce d'appareil : {payload}")
            return
        if len(parts) != 3 or parts[0] != "home":
            return
        uid, kind = parts[1], parts[2]
        devices = Device.objects.filter(
            Q(uid=uid) | Q(mqtt_topic=f"home/{uid}/cmd")
        )
        if kind == "status":
            devices.update(is_online=(payload == "online"))
            self.stdout.write(f"{uid} : {payload}")
        elif kind == "sensors":
            data = json.loads(payload)
            for d in devices:
                SensorReading.objects.create(
                    device=d,
                    temperature=data.get("temperature"),
                    humidity=data.get("humidity"),
                    motion_detected=data.get("motion"),
                )
            self.stdout.write(f"{uid} : mesure enregistree")
        elif kind == "state":
            data = json.loads(payload)
            for d in devices:
                d.state = data
                d.save()
            self.stdout.write(f"{uid} : etat mis a jour")
