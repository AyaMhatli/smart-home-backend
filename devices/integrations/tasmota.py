"""Tasmota (prises, ampoules reflashées) : API web locale."""
from .errors import IntegrationError
from .net import http_json


class TasmotaDriver:
    def __init__(self, host, timeout=3):
        self.host = host
        self.timeout = timeout

    def _cmd(self, command):
        data = http_json(f'http://{self.host}/cm?cmnd={command.replace(" ", "%20")}', self.timeout)
        if isinstance(data, dict) and 'WARNING' in data:
            raise IntegrationError("L'appareil est protégé par un mot de passe. "
                                   "Désactivez-le dans les réglages de l'appareil.")
        return data

    @staticmethod
    def _power(data):
        for key, val in data.items():
            if str(key).upper().startswith('POWER'):
                return str(val).upper() == 'ON'
        raise IntegrationError("Réponse inattendue de l'appareil")

    def is_online(self):
        try:
            self._cmd('Power')
            return True
        except IntegrationError:
            return False

    def execute(self, action, value=None):
        if action == 'on':
            data = self._cmd('Power On')
        elif action == 'off':
            data = self._cmd('Power Off')
        else:
            raise IntegrationError('Action inconnue pour cet appareil')
        return {'on': self._power(data)}
