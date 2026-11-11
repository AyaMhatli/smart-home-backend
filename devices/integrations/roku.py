"""Roku (box et télés) : commande locale ECP sur le port 8060, sans mot de passe."""
from .errors import IntegrationError
from .net import http_text

PORT = 8060

KEYS = {
    'power': 'Power',            # bascule
    'volume_up': 'VolumeUp',
    'volume_down': 'VolumeDown',
    'mute': 'VolumeMute',
    'channel_up': 'ChannelUp',
    'channel_down': 'ChannelDown',
    'home': 'Home',
    'menu': 'Info',
}


class RokuDriver:
    def __init__(self, host, timeout=3):
        self.host = host
        self.timeout = timeout

    def is_online(self):
        try:
            http_text(f'http://{self.host}:{PORT}/query/device-info', self.timeout)
            return True
        except IntegrationError:
            return False

    def execute(self, action, value=None):
        key = KEYS.get(action)
        if key is None:
            raise IntegrationError("Cette touche n'existe pas sur Roku")
        http_text(f'http://{self.host}:{PORT}/keypress/{key}', self.timeout, method='POST', data=b'')
        return {'last_action': action}
