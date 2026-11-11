#!/usr/bin/env python3
"""
apply_integrations.py : branche les appareils Samsung TV / WLED sur ton backend.

Usage (depuis le dossier qui contient manage.py) :
    python apply_integrations.py

Modifie devices/models.py, devices/serializers.py et devices/views.py.
Toutes les vérifications sont faites AVANT d'écrire : si un point d'ancrage
est introuvable, le script s'arrête sans rien modifier.
Peut être relancé sans danger (il saute ce qui est déjà fait).
"""
import re
import sys
from pathlib import Path

ROOT = Path.cwd()
DEV = ROOT / 'devices'


def fail(msg):
    print(f'\n[ERREUR] {msg}\nRien n\'a été modifié.')
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


def once_in_class(text, cls, anchor, label):
    a, b = class_span(text, cls)
    n = text[a:b].count(anchor)
    if n != 1:
        fail(f'Point d\'ancrage « {label} » trouvé {n} fois dans la classe {cls} (attendu : 1) :\n  {anchor!r}')
    return a, b


writes = {}

# ── models.py ────────────────────────────────────────────────────────────
p, s = load('models.py')
if 'integration = models.CharField' in s:
    print('models.py : déjà fait')
else:
    once(s, "('sensor', 'Capteur'),", 'types d\'appareils')
    old = "mqtt_topic = models.CharField(max_length=200"
    once(s, old, 'champ mqtt_topic')
    s = s.replace("('sensor', 'Capteur'),", "('sensor', 'Capteur'),\n        ('tv', 'Télévision'),")
    out = []
    for line in s.split('\n'):
        if old in line:
            indent = line[:len(line) - len(line.lstrip())]
            out.append(line.replace(old, old + ", blank=True, default=''"))
            out.append(indent + "# Appareils du commerce pilotés par le réseau (Samsung TV, WLED...)")
            out.append(indent + "integration = models.CharField(max_length=30, blank=True, default='')")
            out.append(indent + "host = models.CharField(max_length=100, blank=True, default='')")
        else:
            out.append(line)
    writes[p] = '\n'.join(out)

# ── serializers.py ───────────────────────────────────────────────────────
p, s = load('serializers.py')
if "'integration'" in s:
    print('serializers.py : déjà fait')
else:
    once(s, "'mqtt_topic',", 'champs du serializer')
    writes[p] = s.replace("'mqtt_topic',", "'mqtt_topic', 'integration', 'host',")

# ── views.py ─────────────────────────────────────────────────────────────
p, s = load('views.py')
if 'get_driver' in s:
    print('views.py : déjà fait')
else:
    imp = "from .mqtt import publish_command"
    once(s, imp, 'import publish_command')
    val = "        value = request.data.get('value')\n"
    pc = "    def perform_create(self, serializer):"
    once_in_class(s, 'DeviceViewSet', pc, 'perform_create')
    once_in_class(s, 'DeviceViewSet', val, 'lecture de value dans command')

    list_code = (
        "    def list(self, request, *args, **kwargs):\n"
        "        # Met à jour « en ligne » des appareils du commerce avant de répondre\n"
        "        refresh_integration_status(list(self.get_queryset()))\n"
        "        return super().list(request, *args, **kwargs)\n\n")
    cmd_code = (
        "\n        # Appareil du commerce (Samsung TV, WLED...) : pas de MQTT\n"
        "        try:\n"
        "            driver = get_driver(device)\n"
        "            if driver:\n"
        "                device.state.update(driver.execute(name, value))\n"
        "                device.is_online = True\n"
        "                device.save()\n"
        "                return Response(DeviceSerializer(device).data)\n"
        "        except IntegrationError as e:\n"
        "            if device.is_online:\n"
        "                device.is_online = False\n"
        "                device.save(update_fields=['is_online'])\n"
        "            return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)\n\n")

    a, b = class_span(s, 'DeviceViewSet')
    body = s[a:b]
    body = body.replace(pc, list_code + pc, 1)
    body = body.replace(val, val + cmd_code, 1)
    s = s[:a] + body + s[b:]
    s = s.replace(imp, imp + "\nfrom .integrations import get_driver, refresh_integration_status, IntegrationError", 1)
    writes[p] = s

# ── écriture (seulement si tout est passé) ───────────────────────────────
for path, content in writes.items():
    path.write_text(content, encoding='utf-8')
    print(f'{path.name} : modifié')

(ROOT / 'tokens').mkdir(exist_ok=True)
if not (DEV / 'integrations' / '__init__.py').exists():
    print('\n[ATTENTION] Le dossier devices/integrations/ est absent : extrais l\'archive avant de continuer.')

print('''
Terminé. Étapes suivantes :
  python manage.py makemigrations devices
  python manage.py migrate
''')
