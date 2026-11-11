"""Shelly (prises, relais) : API web locale, générations 1 et 2+."""
from .errors import IntegrationError
from .net import http_json


class ShellyDriver:
    def __init__(self, host, timeout=3):
        self.host = host
        self.timeout = timeout

    def _url(self, path):
        return f'http://{self.host}{path}'

    def _gen(self):
        info = http_json(self._url('/shelly'), self.timeout)
        try:
            return 2 if int(info.get('gen', 1)) >= 2 else 1
        except (TypeError, ValueError):
            return 1

    def _read(self, gen):
        if gen == 1:
            return {'on': bool(http_json(self._url('/relay/0'), self.timeout).get('ison'))}
        return {'on': bool(http_json(self._url('/rpc/Switch.GetStatus?id=0'), self.timeout).get('output'))}

    def is_online(self):
        try:
            self._gen()
            return True
        except IntegrationError:
            return False

    def execute(self, action, value=None):
        if action not in ('on', 'off'):
            raise IntegrationError('Action inconnue pour cette prise')
        gen = self._gen()
        if gen == 1:
            http_json(self._url(f'/relay/0?turn={action}'), self.timeout)
        else:
            flag = 'true' if action == 'on' else 'false'
            http_json(self._url(f'/rpc/Switch.Set?id=0&on={flag}'), self.timeout)
        return self._read(gen)
