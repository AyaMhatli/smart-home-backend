# """Ampoules WiZ : messages JSON en UDP sur le port 38899."""
# from .errors import IntegrationError
# from .net import udp_json

# PORT = 38899


# class WiZDriver:
#     def __init__(self, host, timeout=2):
#         self.host = host
#         self.timeout = timeout

#     def _call(self, method, params=None):
#         reply = udp_json(self.host, PORT, {'id': 1, 'method': method, 'params': params or {}}, self.timeout)
#         if not isinstance(reply, dict) or 'error' in reply:
#             raise IntegrationError("L'ampoule a refusé la commande")
#         return reply.get('result') or {}

#     def _read(self):
#         r = self._call('getPilot')
#         return {'on': bool(r.get('state')), 'value': int(r.get('dimming', 100))}

#     def is_online(self):
#         try:
#             self._call('getPilot')
#             return True
#         except IntegrationError:
#             return False

#     def execute(self, action, value=None):
#         if action == 'on':
#             self._call('setPilot', {'state': True})
#         elif action == 'off':
#             self._call('setPilot', {'state': False})
#         elif action == 'set_brightness':
#             pct = max(10, min(100, int(value if value is not None else 50)))  # WiZ : minimum 10 %
#             self._call('setPilot', {'state': True, 'dimming': pct})
#         elif action == 'set_color':
#             h = str(value or '').lstrip('#')
#             try:
#                 if len(h) != 6:
#                     raise ValueError
#                 r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
#             except ValueError:
#                 raise IntegrationError('Couleur invalide (format attendu : #RRGGBB)')
#             self._call('setPilot', {'state': True, 'r': r, 'g': g, 'b': b})
#         else:
#             raise IntegrationError("Action inconnue pour l'ampoule")
#         return self._read()


"""Ampoules WiZ : messages JSON en UDP sur le port 38899."""
from .errors import IntegrationError
from .net import udp_json

PORT = 38899


class WiZDriver:
    def __init__(self, host, timeout=2):
        self.host = host
        self.timeout = timeout

    def _call(self, method, params=None):
        reply = udp_json(self.host, PORT, {'id': 1, 'method': method, 'params': params or {}}, self.timeout)
        if not isinstance(reply, dict) or 'error' in reply:
            raise IntegrationError("L'ampoule a refusé la commande")
        return reply.get('result') or {}

    def _read(self):
        r = self._call('getPilot')
        color = None
        if all(k in r for k in ('r', 'g', 'b')):
            color = '#%02X%02X%02X' % (r['r'], r['g'], r['b'])
        return {'on': bool(r.get('state')), 'value': int(r.get('dimming', 100)), 'color': color}

    def is_online(self):
        try:
            self._call('getPilot')
            return True
        except IntegrationError:
            return False

    def execute(self, action, value=None):
        if action == 'on':
            self._call('setPilot', {'state': True})
        elif action == 'off':
            self._call('setPilot', {'state': False})
        elif action == 'set_brightness':
            pct = max(10, min(100, int(value if value is not None else 50)))  # WiZ : minimum 10 %
            self._call('setPilot', {'state': True, 'dimming': pct})
        elif action == 'set_color':
            h = str(value or '').lstrip('#')
            try:
                if len(h) != 6:
                    raise ValueError
                r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
            except ValueError:
                raise IntegrationError('Couleur invalide (format attendu : #RRGGBB)')
            self._call('setPilot', {'state': True, 'r': r, 'g': g, 'b': b})
        else:
            raise IntegrationError("Action inconnue pour l'ampoule")
        return self._read()