"""
Règles de l'ajout d'un appareil (automatique ou manuel).

  - appareil MQTT (ESP32) : l'identifiant (uid) et l'adresse MQTT sont créés
    automatiquement si l'app ne les envoie pas ;
  - appareil du commerce (Samsung TV, WLED) : l'adresse IP est obligatoire
    et doit être une adresse du réseau local ;
  - un même identifiant ne peut pas être ajouté deux fois par le même utilisateur.
"""
import ipaddress
import re
import secrets

from django.utils.text import slugify
from rest_framework import serializers

UID_RE = re.compile(r'^[A-Za-z0-9_-]{1,64}$')   # sûr pour un topic MQTT
from .integrations import INTEGRATIONS


def valid_lan_host(host):
    """Vrai pour une adresse IPv4 privée (réseau local), faux sinon."""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return (ip.version == 4 and ip.is_private
            and not ip.is_loopback and not ip.is_link_local)


class DeviceValidationMixin:
    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance is not None:      # modification : on ne touche à rien
            return attrs

        request = self.context.get('request')
        user = getattr(request, 'user', None)
        integration = (attrs.get('integration') or '').strip()
        uid = (attrs.get('uid') or '').strip()

        if integration:
            if integration not in INTEGRATIONS:
                raise serializers.ValidationError({'integration': 'Type d\'appareil inconnu.'})
            host = (attrs.get('host') or '').strip()
            if not host:
                raise serializers.ValidationError({'host': "L'adresse IP est obligatoire."})
            if not valid_lan_host(host):
                raise serializers.ValidationError(
                    {'host': "Adresse invalide : une adresse du réseau local est attendue (ex: 192.168.1.20)."})
            attrs['host'] = host
            if not uid:
                uid = f"{integration}-{host.replace('.', '-')}"
        else:
            if not uid:
                base = slugify(attrs.get('name', '')) or 'appareil'
                uid = f"{base[:50]}-{secrets.token_hex(2)}"
            attrs['host'] = ''
            if not attrs.get('mqtt_topic'):
                attrs['mqtt_topic'] = f'home/{uid}/cmd'

        if not UID_RE.match(uid):
            raise serializers.ValidationError(
                {'uid': 'Identifiant invalide : lettres, chiffres, - et _ seulement.'})
        attrs['uid'] = uid

        if user is not None and user.is_authenticated:
            from .models import Device
            if Device.objects.filter(owner=user, uid=uid).exists():
                raise serializers.ValidationError(
                    {'uid': 'Un appareil avec cet identifiant existe déjà.'})
        return attrs
