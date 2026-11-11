#!/usr/bin/env python3
"""
check_backend.py : vérifie l'ajout manuel sur ton serveur en marche.

Usage :
    python check_backend.py http://localhost:8000
    python check_backend.py http://localhost:8000 --tv 192.168.1.20     (teste ta télé)

Crée un compte « verif@exemple.com », ajoute puis supprime des appareils de test.
"""
import json
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else 'http://localhost:8000').rstrip('/')
TV = sys.argv[sys.argv.index('--tv') + 1] if '--tv' in sys.argv else None
EMAIL, PWD = 'verif@exemple.com', 'verif12345'
token = None
failures = 0


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={'Content-Type': 'application/json'})
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw


def check(label, ok, detail=''):
    global failures
    print(('  OK  ' if ok else '  ÉCHEC  ') + label + (f'   {detail}' if detail and not ok else ''))
    if not ok:
        failures += 1


print(f'Serveur : {BASE}\n')
call('POST', '/api/auth/register/', {'name': 'Verif', 'email': EMAIL, 'password': PWD})
st, js = call('POST', '/api/token/', {'username': EMAIL, 'password': PWD})
check('connexion', st == 200 and isinstance(js, dict) and 'access' in js, f'{st} {js}')
if failures:
    sys.exit(1)
token = js['access']
created = []

st, js = call('POST', '/api/devices/probe/', {'host': '8.8.8.8'})
check('adresse publique refusée (probe)', st == 400, f'{st} {js}')
st, js = call('POST', '/api/devices/', {'name': 'Lampe de test', 'device_type': 'light'})
check('ajout manuel MQTT (nom + type seulement)', st == 201, f'{st} {js}')
if st == 201:
    created.append(js['id'])
    check('identifiant créé automatiquement', js['uid'].startswith('lampe-de-test-'), js['uid'])
    check('adresse MQTT créée automatiquement', js['mqtt_topic'] == f"home/{js['uid']}/cmd", js['mqtt_topic'])
    st2, js2 = call('POST', '/api/devices/', {'name': 'Autre', 'device_type': 'light', 'uid': js['uid']})
    check('doublon refusé', st2 == 400, f'{st2} {js2}')
st, js = call('POST', '/api/devices/', {'name': 'Piège', 'device_type': 'light', 'uid': 'x/#'})
check('identifiant dangereux refusé', st == 400, f'{st} {js}')
st, js = call('POST', '/api/devices/', {'name': 'Télé', 'device_type': 'tv', 'integration': 'samsung_tv'})
check('télé sans adresse refusée', st == 400, f'{st} {js}')
st, js = call('POST', '/api/devices/', {'name': 'Télé', 'device_type': 'tv', 'integration': 'samsung_tv', 'host': '8.8.8.8'})
check('télé avec adresse publique refusée', st == 400, f'{st} {js}')
st, js = call('POST', '/api/devices/', {'name': 'Télé test', 'device_type': 'tv', 'integration': 'samsung_tv', 'host': '192.168.1.250'})
check('ajout manuel télé (adresse locale)', st == 201, f'{st} {js}')
if st == 201:
    created.append(js['id'])
    check('identifiant de la télé créé', js['uid'] == 'samsung_tv-192-168-1-250', js['uid'])

if TV:
    st, js = call('POST', '/api/devices/probe/', {'host': TV})
    check(f'reconnaissance de {TV}', st == 200 and js.get('found'), f'{st} {js}')
    print('     ->', js)

st, js = call('GET', '/api/devices/')
check('liste des appareils', st == 200 and len(js) >= len(created), f'{st}')
for i in created:
    call('DELETE', f'/api/devices/{i}/')
print('\n' + ('TOUT EST BON' if not failures else f'{failures} vérification(s) en échec'))
sys.exit(1 if failures else 0)
