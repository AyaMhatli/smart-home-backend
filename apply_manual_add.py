#!/usr/bin/env python3
"""
apply_manual_add.py : ajout manuel d'appareils (2e correctif).

Prérequis : apply_integrations.py déjà lancé.
Usage (depuis le dossier qui contient manage.py) :
    python apply_manual_add.py
Aucune migration à faire. Peut être relancé sans danger.
"""
import re
import sys
from pathlib import Path

DEV = Path.cwd() / 'devices'


def fail(msg):
    print(f'\n[ERREUR] {msg}\nRien n\'a été modifié dans ce fichier.')
    sys.exit(1)


def load(name):
    p = DEV / name
    if not p.exists():
        fail(f'{p} introuvable. Lance le script depuis le dossier qui contient manage.py.')
    return p, p.read_text(encoding='utf-8')


def once(text, anchor, label):
    n = text.count(anchor)
    if n != 1:
        fail(f'Point d\'ancrage « {label} » trouvé {n} fois (attendu : 1) :\n  {anchor!r}')


def class_span(text, name):
    """(début, fin) du corps d'une classe de premier niveau."""
    m = re.search(rf'^class {name}\b.*$', text, re.M)
    if not m:
        fail(f'La classe {name} est introuvable.')
    nxt = re.search(r'^\S', text[m.end() + 1:], re.M)
    end = m.end() + 1 + nxt.start() if nxt else len(text)
    return m.start(), end


if not (DEV / 'validation.py').exists():
    fail('devices/validation.py est absent : extrais d\'abord l\'archive.')

# Toutes les vérifications avant la moindre modification
_, _views = load('views.py')
if 'get_driver' not in _views:
    fail('Lance d\'abord apply_integrations.py (views.py ne contient pas encore get_driver).')
_, _ser = load('serializers.py')
if 'DeviceValidationMixin' not in _ser:
    once(_ser, 'class DeviceSerializer(serializers.ModelSerializer):', 'classe DeviceSerializer')
    once(_ser, 'from rest_framework import serializers', 'import serializers')
if 'def probe(' not in _views:
    once(_views, "from .integrations import get_driver, refresh_integration_status, IntegrationError", 'import integrations')
    _a, _b = class_span(_views, 'DeviceViewSet')
    if _views[_a:_b].count("    def list(self, request, *args, **kwargs):") != 1:
        fail('La méthode list de DeviceViewSet est introuvable (apply_integrations.py a-t-il été lancé ?).')

# ── serializers.py ───────────────────────────────────────────────────────
p, s = load('serializers.py')
if 'DeviceValidationMixin' in s:
    print('serializers.py : déjà fait')
else:
    once(s, 'class DeviceSerializer(serializers.ModelSerializer):', 'classe DeviceSerializer')
    once(s, 'from rest_framework import serializers', 'import serializers')
    s = s.replace('class DeviceSerializer(serializers.ModelSerializer):',
                  'class DeviceSerializer(DeviceValidationMixin, serializers.ModelSerializer):')
    s = s.replace('from rest_framework import serializers',
                  'from rest_framework import serializers\nfrom .validation import DeviceValidationMixin')
    p.write_text(s, encoding='utf-8')
    print('serializers.py : modifié')

# ── views.py ─────────────────────────────────────────────────────────────
p, s = load('views.py')
if 'get_driver' not in s:
    fail('Lance d\'abord apply_integrations.py (views.py ne contient pas encore get_driver).')
if 'def probe(' in s:
    print('views.py : déjà fait')
else:
    imp = "from .integrations import get_driver, refresh_integration_status, IntegrationError"
    probe_code = (
        "    @action(detail=False, methods=['post'])\n"
        "    def probe(self, request):\n"
        "        \"\"\"POST /api/devices/probe/ {\"host\": \"192.168.1.20\"} : reconnaît une télé Samsung ou une bande WLED.\"\"\"\n"
        "        host = (request.data.get('host') or '').strip()\n"
        "        if not valid_lan_host(host):\n"
        "            return Response({'error': 'Adresse invalide : une adresse du réseau local est attendue.'},\n"
        "                            status=status.HTTP_400_BAD_REQUEST)\n"
        "        found = identify(host)\n"
        "        if not found:\n"
        "            return Response({'found': False})\n"
        "        return Response({'found': True, **found})\n\n")
    anchor = "    def list(self, request, *args, **kwargs):"
    a, b = class_span(s, 'DeviceViewSet')
    s = s[:a] + s[a:b].replace(anchor, probe_code + anchor, 1) + s[b:]
    s = s.replace(imp, imp + "\nfrom .integrations.discovery import identify\nfrom .validation import valid_lan_host", 1)
    p.write_text(s, encoding='utf-8')
    print('views.py : modifié')

print('\nTerminé. Relance le serveur, puis lance check_backend.py pour vérifier.')
