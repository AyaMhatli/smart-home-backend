"""
devices/netscan.py : scan du réseau local, sans root et sans nmap.

Principe :
  1. On tente une connexion sur chaque adresse du réseau (port 80).
     Même si la connexion échoue, le système apprend l'adresse MAC des
     appareils présents (table ARP).
  2. On lit cette table avec « ip neigh ».
  3. On devine la marque grâce au début de l'adresse MAC (fichier ieee-data).
  4. On reconnaît les Samsung TV et les bandes WLED (voir integrations/).

Route : GET /api/network/scan/  (connecté obligatoire)
"""

import ipaddress
import re
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor

from rest_framework.decorators import api_view
from rest_framework.response import Response

from .integrations.discovery import identify

OUI_FILES = ['/usr/share/ieee-data/oui.txt', '/var/lib/ieee-data/oui.txt']

# Secours si le paquet ieee-data n'est pas installé
FALLBACK_VENDORS = {
    'B827EB': 'Raspberry Pi', 'DCA632': 'Raspberry Pi',
    'E45F01': 'Raspberry Pi', '2CCF67': 'Raspberry Pi',
    '240AC4': 'Espressif', '30AEA4': 'Espressif', '246F28': 'Espressif',
    'A4CF12': 'Espressif', '84F3EB': 'Espressif', 'BCDDC2': 'Espressif',
}

# Ports qui donnent un indice sur la façon de piloter l'appareil
PROBE_PORTS = {'mqtt': 1883, 'mqtts': 8883, 'web': 80, 'tuya': 6668}


# ── Fonctions pures (faciles à tester) ────────────────────────────────

def parse_oui(text):
    """Texte du fichier oui.txt -> {'A4CF12': 'Espressif Inc.', ...}"""
    vendors = {}
    for line in text.splitlines():
        m = re.match(r'^([0-9A-Fa-f]{6})\s+\(base 16\)\s+(.+)$', line.strip())
        if m:
            vendors[m.group(1).upper()] = m.group(2).strip()
    return vendors


def load_vendors():
    for path in OUI_FILES:
        try:
            with open(path, encoding='utf-8', errors='ignore') as f:
                vendors = parse_oui(f.read())
            if vendors:
                return vendors
        except OSError:
            continue
    return dict(FALLBACK_VENDORS)


def is_private_mac(mac):
    """Adresse « aléatoire » (téléphones modernes) : bit 2 du 1er octet."""
    try:
        return bool(int(mac.split(':')[0], 16) & 0x02)
    except ValueError:
        return False


def vendor_of(mac, vendors):
    return vendors.get(mac.replace(':', '').upper()[:6], '')


def parse_neigh(text, network):
    """Sortie de « ip -4 neigh show » -> {ip: mac} pour les appareils présents."""
    found = {}
    for line in text.splitlines():
        m = re.match(r'^(\d+\.\d+\.\d+\.\d+)\s.*lladdr\s+([0-9a-fA-F:]{17})\s+(\S+)', line.strip())
        if not m:
            continue
        ip, mac, state = m.group(1), m.group(2).lower(), m.group(3)
        if state in ('FAILED', 'INCOMPLETE'):
            continue
        if ipaddress.ip_address(ip) in network:
            found[ip] = mac
    return found


def parse_interface(text):
    """Sortie de « ip -4 -o addr show scope global » -> (ip, réseau)."""
    for line in text.splitlines():
        m = re.search(r'inet (\d+\.\d+\.\d+\.\d+)/(\d+)', line)
        if m:
            iface = ipaddress.ip_interface(f'{m.group(1)}/{m.group(2)}')
            net = iface.network
            if net.prefixlen < 24:  # on limite à 254 adresses
                net = ipaddress.ip_network(f'{iface.ip}/24', strict=False)
            return str(iface.ip), net
    return None, None


def parse_gateway(text):
    m = re.search(r'default via (\d+\.\d+\.\d+\.\d+)', text)
    return m.group(1) if m else None


# ── Accès au système ──────────────────────────────────────────────────

def _run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return ''


def _probe(ip, port, timeout):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        return s.connect_ex((ip, port)) == 0
    except OSError:
        return False
    finally:
        s.close()


def scan():
    my_ip, net = parse_interface(_run(['ip', '-4', '-o', 'addr', 'show', 'scope', 'global']))
    if net is None:
        return None
    gateway = parse_gateway(_run(['ip', 'route', 'show', 'default']))

    # 1. Réveiller le réseau : une tentative de connexion par adresse
    hosts = [str(h) for h in net.hosts()]
    with ThreadPoolExecutor(max_workers=100) as pool:
        list(pool.map(lambda ip: _probe(ip, 80, 1.0), hosts))

    # 2. Lire la table ARP
    neighbours = parse_neigh(_run(['ip', '-4', 'neigh', 'show']), net)
    neighbours.pop(my_ip, None)
    if gateway:
        neighbours.pop(gateway, None)

    # 3. Ports ouverts sur les appareils trouvés
    vendors = load_vendors()

    def inspect(item):
        ip, mac = item
        ports = [name for name, p in PROBE_PORTS.items() if _probe(ip, p, 0.5)]
        known = identify(ip) or {}
        return {
            'kind': known.get('kind', ''),   # 'samsung_tv', 'wled' ou '' (inconnu)
            'name': known.get('name', ''),
            'ip': ip,
            'mac': mac,
            'vendor': vendor_of(mac, vendors),
            'private_mac': is_private_mac(mac),
            'ports': ports,
        }

    with ThreadPoolExecutor(max_workers=20) as pool:
        devices = list(pool.map(inspect, neighbours.items()))
    devices.sort(key=lambda d: ipaddress.ip_address(d['ip']))
    return {'network': str(net), 'devices': devices}


@api_view(['GET'])
def scan_view(request):
    """GET /api/network/scan/ : appareils présents sur le réseau du serveur."""
    result = scan()
    if result is None:
        return Response({'error': 'Réseau introuvable'}, status=503)
    return Response(result)
