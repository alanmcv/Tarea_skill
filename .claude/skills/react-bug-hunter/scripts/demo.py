#!/usr/bin/env python3
"""Demostración de principio a fin de react-bug-hunter (Windows, Mac, Linux).

Uso:
    python3 scripts/demo.py [--out DIR] [--pausa]

Trabaja sobre una COPIA temporal de tests/fixtures/app_con_bugs, así que no
modifica nada del proyecto. Pasos:
    1. Auditar                      → 13 hallazgos (código 1)
    2. Vista previa de reparación   → diff sin tocar archivos
    3. Aplicar reparación           → copia de seguridad + 13/13 resueltos
    4. Re-auditar con baseline      → 13 resueltos · 0 nuevos (código 0)
    5. Deshacer                     → archivos idénticos al original
    6. Entradas inválidas           → mensajes claros y códigos 2, 3, 4, 7
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL / 'scripts'
FIX = SKILL / 'tests' / 'fixtures'
PY = sys.executable

sys.path.insert(0, str(SCRIPTS))
from audit import setup_console  # noqa: E402

COLOR = (sys.stdout.isatty() or os.environ.get('FORCE_COLOR')) \
    and not os.environ.get('NO_COLOR')


def paint(text, code):
    return f'\033[{code}m{text}\033[0m' if COLOR else text


def step(title, shown, args, cwd, pause):
    print(paint(f'\n━━ {title}', '1;34'))
    print(paint(f'$ {shown}', '32'))
    sys.stdout.flush()
    code = subprocess.call(args, cwd=cwd)
    print(f'código de salida: {code}')
    if pause:
        input(paint('   [Enter] para continuar...', '2'))
    return code


def main():
    setup_console()
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--out', help='carpeta donde dejar los reportes')
    parser.add_argument('--pausa', action='store_true',
                        help='esperar Enter entre pasos (para presentar)')
    args = parser.parse_args()

    work = Path(tempfile.mkdtemp(prefix='rbh-demo-'))
    out = Path(args.out).resolve() if args.out else work / 'reportes'
    app = work / 'tienda'
    shutil.copytree(FIX / 'app_con_bugs', app)
    audit = [PY, str(SCRIPTS / 'audit.py')]
    fix = [PY, str(SCRIPTS / 'fix.py')]
    p = args.pausa
    results = []

    print(paint('🔎🛠  Demo de react-bug-hunter', '1'))
    print(f'   Copia de trabajo: {app}')

    results.append(('Auditar', 1, step(
        '1. Auditar la tienda con errores',
        'audit.py tienda --out reportes/antes',
        audit + [str(app), '--out', str(out / 'antes')], work, p)))
    results.append(('Vista previa', 0, step(
        '2. Vista previa de las reparaciones (no modifica archivos)',
        'fix.py tienda',
        fix + [str(app), '--out', str(out / 'vista-previa')], work, p)))
    results.append(('Aplicar', 0, step(
        '3. Aplicar las reparaciones (con copia de seguridad)',
        'fix.py tienda --apply --verify-build',
        fix + [str(app), '--apply', '--verify-build', '--out',
               str(out / 'fix')], work, p)))
    results.append(('Verificar', 0, step(
        '4. Volver a auditar y comparar con el reporte inicial',
        'audit.py tienda --baseline reportes/antes/reporte.json',
        audit + [str(app), '--out', str(out / 'despues'), '--baseline',
                 str(out / 'antes' / 'reporte.json')], work, p)))
    results.append(('Deshacer', 0, step(
        '5. Deshacer (restaurar la copia de seguridad)',
        'fix.py tienda --undo', fix + [str(app), '--undo'], work, p)))

    errors = [
        ('Ruta inexistente', 2, 'audit.py ./no-existe',
         audit + ['./no-existe', '--format', 'none']),
        ('Archivo en vez de carpeta', 2, 'audit.py tienda/package.json',
         audit + [str(app / 'package.json'), '--format', 'none']),
        ('Carpeta sin código', 3, 'audit.py sin_codigo',
         audit + [str(FIX / 'sin_codigo'), '--format', 'none']),
        ('Baseline con JSON roto', 4,
         'audit.py tienda --baseline reporte_roto.json',
         audit + [str(app), '--format', 'none', '--baseline',
                  str(FIX / 'baseline_invalido' / 'reporte.json')]),
        ('Deshacer sin copias', 7, 'fix.py tienda --undo',
         fix + [str(app), '--undo']),
        ('Regla desconocida', 2, 'fix.py tienda --only X99',
         fix + [str(app), '--only', 'X99', '--out', str(work / 'x')]),
    ]
    for n, (name, expected, shown, cmd) in enumerate(errors, 1):
        results.append((name, expected, step(
            f'6.{n} Entrada inválida: {name.lower()}', shown, cmd, work, p)))

    print(paint('\n━━ Resumen', '1;34'))
    ok = True
    for name, expected, got in results:
        good = expected == got
        ok &= good
        mark = paint('✔', '32') if good else paint('✖', '31')
        print(f'  {mark} {name:<28} esperado {expected} · obtenido {got}')
    print(f'\n  Reportes: {out}')
    print(f'  Abre {out / "fix" / "fix.html"} y '
          f'{out / "antes" / "reporte.html"} en el navegador.')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
