"""Pilotage d'une télé Samsung (Tizen, 2016 ou plus) par le réseau."""
import os

from .discovery import is_samsung_tv
from .errors import IntegrationError

KEYS = {
    'power': 'KEY_POWER',          # allume ou éteint (bascule)
    'volume_up': 'KEY_VOLUP',
    'volume_down': 'KEY_VOLDOWN',
    'mute': 'KEY_MUTE',
    'channel_up': 'KEY_CHUP',
    'channel_down': 'KEY_CHDOWN',
    'home': 'KEY_HOME',
    'menu': 'KEY_MENU',
    'source': 'KEY_SOURCE',
}


class SamsungTVDriver:
    def __init__(self, host, token_file, port=8002):
        self.host = host
        self.token_file = token_file
        self.port = port

    def is_online(self):
        return is_samsung_tv(self.host)

    def execute(self, action, value=None):
        key = KEYS.get(action)
        if key is None:
            raise IntegrationError('Action inconnue pour la télé')
        try:
            from samsungtvws import SamsungTVWS  # import tardif : paquet optionnel
        except ImportError:
            raise IntegrationError("Le paquet samsungtvws n'est pas installé sur le serveur")
        try:
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
            tv = SamsungTVWS(host=self.host, port=self.port, timeout=5,
                             token_file=self.token_file, name='SmartHomePFE')
            tv.send_key(key)
        except Exception:
            raise IntegrationError(
                "La télé ne répond pas. Est-elle allumée ? "
                "Acceptez la demande d'autorisation affichée sur l'écran.")
        return {'last_action': action}
