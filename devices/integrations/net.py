"""Petites fonctions réseau partagées par les pilotes (HTTP et UDP, sans bibliothèque externe)."""
import json
import socket
import urllib.error
import urllib.request

from .errors import IntegrationError


def http_text(url, timeout=3, method='GET', data=None, headers=None):
    """Retourne le texte de la réponse. Lève IntegrationError en cas de problème."""
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', 'ignore')
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise IntegrationError("L'appareil est protégé par un mot de passe. "
                                   "Désactivez-le dans les réglages de l'appareil.")
        raise IntegrationError("L'appareil a refusé la commande")
    except Exception:
        raise IntegrationError("L'appareil ne répond pas. Est-il allumé et sur le même Wi-Fi ?")


def http_json(url, timeout=3, **kw):
    try:
        return json.loads(http_text(url, timeout, **kw))
    except ValueError:
        raise IntegrationError("Réponse inattendue de l'appareil")


def try_json(url, timeout=0.8):
    """Pour la reconnaissance : le JSON reçu, ou None au moindre problème."""
    try:
        return json.loads(http_text(url, timeout))
    except (IntegrationError, ValueError):
        return None


def try_text(url, timeout=0.8):
    try:
        return http_text(url, timeout)
    except IntegrationError:
        return None


def udp_json(host, port, payload, timeout=1.0):
    """Envoie un message JSON en UDP et lit la réponse JSON."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    try:
        s.sendto(json.dumps(payload).encode(), (host, port))
        raw, _ = s.recvfrom(4096)
        return json.loads(raw.decode('utf-8', 'ignore'))
    except Exception:
        raise IntegrationError("L'appareil ne répond pas. Est-il allumé et sur le même Wi-Fi ?")
    finally:
        s.close()
