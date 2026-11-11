"""Pilotage d'une bande LED WLED par son API JSON locale."""
import json
import urllib.request

from .errors import IntegrationError


class WLEDDriver:
    def __init__(self, host, timeout=3):
        self.host = host
        self.timeout = timeout

    def _call(self, payload=None):
        url = f'http://{self.host}/json/state'
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(
            url, data=data, headers={'Content-Type': 'application/json'},
            method='POST' if payload is not None else 'GET')
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode('utf-8', 'ignore'))
        except Exception:
            raise IntegrationError('La bande LED ne répond pas')

    def _read_state(self):
        s = self._call()
        return {'on': bool(s.get('on')), 'value': round(s.get('bri', 0) * 100 / 255)}

    def is_online(self):
        try:
            self._call()
            return True
        except IntegrationError:
            return False

    def execute(self, action, value=None):
        if action == 'on':
            self._call({'on': True})
        elif action == 'off':
            self._call({'on': False})
        elif action == 'set_brightness':
            pct = max(0, min(100, int(value if value is not None else 50)))
            self._call({'on': True, 'bri': round(pct * 255 / 100)})
        elif action == 'set_color':
            h = str(value or '').lstrip('#')
            if len(h) != 6:
                raise IntegrationError('Couleur invalide (format attendu : #RRGGBB)')
            try:
                rgb = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
            except ValueError:
                raise IntegrationError('Couleur invalide (format attendu : #RRGGBB)')
            self._call({'on': True, 'seg': [{'col': [rgb]}]})
        else:
            raise IntegrationError('Action inconnue pour la bande LED')
        return self._read_state()
