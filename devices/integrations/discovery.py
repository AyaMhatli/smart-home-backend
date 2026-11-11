"""
Reconnaissance des appareils connus sur le réseau (sans bibliothèque externe).

  Samsung TV : http://IP:8001/api/v2/          (réponse contenant « samsung »)
  WLED       : http://IP/json/info             (brand = « WLED »)
  Shelly     : http://IP/shelly
  Tasmota    : http://IP/cm?cmnd=Status%200
  Roku       : http://IP:8060/query/device-info
  WiZ        : UDP IP:38899  (getPilot)

Pour ajouter une famille d'appareils : écrire une fonction « xxx_info(ip) »
ici, l'ajouter à PROBES, et créer son pilote (voir integrations/__init__.py).
"""
import json
import re

from .errors import IntegrationError
from .net import try_json, try_text, udp_json


def samsung_info(ip, timeout=1.0):
    data = try_json(f'http://{ip}:8001/api/v2/', timeout)
    if isinstance(data, dict) and 'samsung' in json.dumps(data).lower():
        return data
    return None


def wled_info(ip, timeout=1.0):
    data = try_json(f'http://{ip}/json/info', timeout)
    if isinstance(data, dict) and str(data.get('brand', '')).upper() == 'WLED':
        return data
    return None


def shelly_info(ip, timeout=0.8):
    data = try_json(f'http://{ip}/shelly', timeout)
    if isinstance(data, dict) and ('gen' in data or str(data.get('type', '')).upper().startswith('SH')):
        return data
    return None


def tasmota_info(ip, timeout=0.8):
    data = try_json(f'http://{ip}/cm?cmnd=Status%200', timeout)
    if not isinstance(data, dict):
        return None
    if 'StatusFWR' in data or 'StatusNET' in data:
        return data
    if 'Status' in data and isinstance(data['Status'], dict) and 'Topic' in data['Status']:
        return data
    if 'WARNING' in data and 'password' in json.dumps(data).lower():
        return {'protected': True}          # Tasmota avec mot de passe
    return None


def roku_info(ip, timeout=0.8):
    text = try_text(f'http://{ip}:8060/query/device-info', timeout)
    if text and '<device-info>' in text:
        return text
    return None


def wiz_info(ip, timeout=0.8):
    try:
        reply = udp_json(ip, 38899, {'method': 'getPilot', 'params': {}}, timeout)
    except IntegrationError:
        return None
    if isinstance(reply, dict) and reply.get('method') == 'getPilot' and isinstance(reply.get('result'), dict):
        return reply['result']
    return None


def is_samsung_tv(ip):
    return samsung_info(ip) is not None


def is_wled(ip):
    return wled_info(ip) is not None


def _xml_tag(text, tag):
    m = re.search(rf'<{tag}>([^<]*)</{tag}>', text)
    return m.group(1).strip() if m else ''


def _samsung(ip):
    info = samsung_info(ip)
    if not info:
        return None
    name = (info.get('device') or {}).get('name') or info.get('name') or 'Samsung TV'
    return {'kind': 'samsung_tv', 'name': name}


def _wled(ip):
    info = wled_info(ip)
    return {'kind': 'wled', 'name': info.get('name') or 'WLED'} if info else None


def _shelly(ip):
    info = shelly_info(ip)
    if not info:
        return None
    return {'kind': 'shelly', 'name': info.get('name') or info.get('id') or info.get('type') or 'Shelly'}


def _tasmota(ip):
    info = tasmota_info(ip)
    if not info:
        return None
    status = info.get('Status') or {}
    names = status.get('FriendlyName') or []
    name = status.get('DeviceName') or (names[0] if names else '') or 'Tasmota'
    return {'kind': 'tasmota', 'name': name}


def _roku(ip):
    text = roku_info(ip)
    if not text:
        return None
    name = _xml_tag(text, 'user-device-name') or _xml_tag(text, 'friendly-device-name') or 'Roku'
    return {'kind': 'roku', 'name': name}


def _wiz(ip):
    return {'kind': 'wiz', 'name': 'Ampoule WiZ'} if wiz_info(ip) else None


# Ordre d'essai : les plus fiables d'abord
PROBES = (_samsung, _wled, _shelly, _tasmota, _roku, _wiz)

# Nom lisible de chaque famille (affiché dans l'app)
KIND_LABELS = {
    'samsung_tv': 'Télé Samsung',
    'wled': 'Bande LED WLED',
    'shelly': 'Prise Shelly',
    'tasmota': 'Appareil Tasmota',
    'roku': 'Roku',
    'wiz': 'Ampoule WiZ',
}


def identify(ip):
    """Retourne {'kind': ..., 'name': ...} ou None si l'appareil n'est pas reconnu."""
    for probe in PROBES:
        found = probe(ip)
        if found:
            return found
    return None
