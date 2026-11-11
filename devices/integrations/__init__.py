"""
Appareils du commerce pilotés par le réseau local (sans MQTT).

Un appareil « intégré » a un champ `integration` (ex: 'samsung_tv', 'wled')
et un champ `host` (son adresse IP).
"""
from concurrent.futures import ThreadPoolExecutor

from .errors import IntegrationError
from .roku import RokuDriver
from .samsung_tv import SamsungTVDriver
from .shelly import ShellyDriver
from .tasmota import TasmotaDriver
from .wiz import WiZDriver
from .wled import WLEDDriver

__all__ = ['IntegrationError', 'get_driver', 'refresh_integration_status', 'INTEGRATIONS']

# famille -> classe du pilote (construite avec l'adresse IP)
SIMPLE_DRIVERS = {
    'wled': WLEDDriver,
    'shelly': ShellyDriver,
    'tasmota': TasmotaDriver,
    'wiz': WiZDriver,
    'roku': RokuDriver,
}
INTEGRATIONS = tuple(SIMPLE_DRIVERS) + ('samsung_tv',)


def get_driver(device):
    """Retourne le pilote de l'appareil, ou None si c'est un appareil MQTT."""
    kind = getattr(device, 'integration', '')
    if not kind:
        return None
    if not device.host:
        raise IntegrationError("Adresse de l'appareil inconnue")
    if kind in SIMPLE_DRIVERS:
        return SIMPLE_DRIVERS[kind](device.host)
    if kind == 'samsung_tv':
        from django.conf import settings
        token_file = str(settings.BASE_DIR / 'tokens' / f'tv_{device.id}_token.txt')
        return SamsungTVDriver(device.host, token_file)
    raise IntegrationError(f'Type d\'intégration inconnu : {kind}')


def refresh_integration_status(devices):
    """Met à jour « en ligne / hors ligne » des appareils intégrés (en parallèle)."""
    targets = [d for d in devices if getattr(d, 'integration', '') and d.host]
    if not targets:
        return

    def check(device):
        try:
            return device, bool(get_driver(device).is_online())
        except IntegrationError:
            return device, False

    with ThreadPoolExecutor(max_workers=8) as pool:
        for device, online in pool.map(check, targets):
            if device.is_online != online:
                device.is_online = online
                device.save(update_fields=['is_online'])
