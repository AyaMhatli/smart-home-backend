"""
Étape « plusieurs maisons » : les écrans Accueil et Monitoring peuvent être
limités à une maison avec  ?home=<id>.

  GET /api/summary/?home=2
  GET /api/sensors/history/?period=24h&home=2

À lancer UNE FOIS depuis D:\\smarthome-backend :   python apply_home_scope.py
Sans ?home=, tout continue comme avant (toutes les maisons).
Le fichier n'est modifié que si toutes les vérifications passent.
"""
import ast
import os
import py_compile
import shutil
import sys
import tempfile

PATH = os.path.join('devices', 'views.py')
MARK = '# --- home-scope ---'

HELPER = '''

# --- home-scope ---
def _home_scope(request):
    """Retourne l'identifiant de la maison demandée (?home=), ou None pour toutes.
    Refuse une maison qui n'appartient pas à l'utilisateur."""
    from rest_framework.exceptions import NotFound, ValidationError
    from .models import Home
    raw = request.query_params.get('home')
    if raw in (None, ''):
        return None
    try:
        home_id = int(raw)
    except ValueError:
        raise ValidationError({'home': 'Identifiant de maison invalide.'})
    if not Home.objects.filter(id=home_id, owner=request.user).exists():
        raise NotFound('Maison introuvable.')
    return home_id
'''

SUMMARY = '''@api_view(['GET'])
def summary(request):
    """GET /api/summary/?home=<id> : données de l'écran Accueil."""
    home_id = _home_scope(request)
    devices = Device.objects.filter(owner=request.user)
    readings = SensorReading.objects.filter(device__owner=request.user,
                                            temperature__isnull=False)
    if home_id is not None:
        devices = devices.filter(home_id=home_id)
        readings = readings.filter(device__home_id=home_id)
    last = readings.first()
    lights = devices.filter(device_type='light')
    doors = devices.filter(device_type='door')
    return Response({
        'temperature': last.temperature if last else None,
        'humidity': last.humidity if last else None,
        'lights_on': sum(1 for d in lights if d.state.get('on')),
        'lights_total': lights.count(),
        'doors_locked': all(d.state.get('locked', True) for d in doors),
        'devices_total': devices.count(),
        'devices_online': devices.filter(is_online=True).count(),
    })
'''

HISTORY = '''@api_view(['GET'])
def sensor_history(request):
    """GET /api/sensors/history/?period=24h|7j|30j&home=<id> : écran Monitoring."""
    home_id = _home_scope(request)
    days = {'24h': 1, '7j': 7, '7d': 7, '30j': 30, '30d': 30}.get(
        request.query_params.get('period', '24h'), 1)
    since = timezone.now() - timedelta(days=days)
    readings = SensorReading.objects.filter(device__owner=request.user, timestamp__gte=since)
    if home_id is not None:
        readings = readings.filter(device__home_id=home_id)
    readings = readings.order_by('timestamp')[:500]
    return Response([{'timestamp': r.timestamp, 'temperature': r.temperature,
                      'humidity': r.humidity} for r in readings])
'''


def fail(msg):
    print('ERREUR :', msg)
    print('Rien n\'a été modifié.')
    sys.exit(1)


def span(tree, name):
    found = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
    if len(found) != 1:
        fail(f'la fonction « {name} » doit exister une seule fois dans views.py (trouvée {len(found)} fois).')
    n = found[0]
    first = min([n.lineno] + [d.lineno for d in n.decorator_list])
    return first, n.end_lineno


def main():
    if not os.path.exists(PATH):
        fail(f'{PATH} introuvable : lancez ce script depuis le dossier du projet (là où se trouve manage.py).')
    src = open(PATH, encoding='utf-8').read()
    if MARK in src:
        print('Déjà appliqué. Rien à faire.')
        return
    tree = ast.parse(src)
    lines = src.split('\n')
    for needed in ('timezone', 'timedelta', 'SensorReading', 'Device', 'api_view', 'Response'):
        if needed not in src:
            fail(f'« {needed} » n\'est pas importé dans views.py ; ce script ne sait pas s\'adapter.')

    # on remplace de bas en haut pour garder les numéros de ligne valables
    spans = sorted([(span(tree, 'summary'), SUMMARY), (span(tree, 'sensor_history'), HISTORY)],
                   key=lambda x: -x[0][0])
    for (a, b), new in spans:
        lines[a - 1:b] = new.rstrip('\n').split('\n')
    out = '\n'.join(lines).rstrip('\n') + '\n' + HELPER

    ast.parse(out)
    with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False, encoding='utf-8') as t:
        t.write(out)
    try:
        py_compile.compile(t.name, doraise=True)
    except py_compile.PyCompileError as e:
        os.unlink(t.name)
        fail(f'le résultat ne compile pas : {e}')
    os.unlink(t.name)

    shutil.copy(PATH, PATH + '.bak_home')
    open(PATH, 'w', encoding='utf-8').write(out)
    print('OK : Accueil et Monitoring acceptent maintenant ?home=<id>.')
    print(f'Sauvegarde de l\'ancien fichier : {PATH}.bak_home')


main()
