#!/usr/bin/env python3
"""Regenera las capturas de evidencias/ ejecutando la skill de verdad.

Requiere Chromium o Google Chrome en el PATH (o en la variable CHROME).
Uso, desde la carpeta de la skill:
    python3 tests/generar_capturas.py
"""

import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
FIX = SKILL / 'tests' / 'fixtures'
EVID = SKILL / 'evidencias'
AUDIT = [sys.executable, str(SKILL / 'scripts' / 'audit.py')]
FIXCMD = [sys.executable, str(SKILL / 'scripts' / 'fix.py')]

ANSI = {'1': 'font-weight:bold', '31': 'color:#ff6b6b', '33': 'color:#f5c451',
        '36': 'color:#5fd7e8', '1;34': 'color:#7aa2ff;font-weight:bold',
        '1;32': 'color:#7ee787;font-weight:bold'}


def find_chrome():
    for name in (os.environ.get('CHROME'), 'chromium', 'chromium-browser',
                 'google-chrome', 'chrome'):
        if name and shutil.which(name):
            return shutil.which(name)
    sys.exit('✖ No se encontró Chromium/Chrome. Define la variable CHROME.')


def ansi_to_html(text):
    out, pos = [], 0
    for m in re.finditer(r'\x1b\[([\d;]+)m', text):
        out.append(html.escape(text[pos:m.start()]))
        code = m.group(1)
        out.append('</span>' if code == '0' else
                   f'<span style="{ANSI.get(code, "")}">')
        pos = m.end()
    out.append(html.escape(text[pos:]))
    return ''.join(out)


def terminal_page(title, blocks):
    body = ''.join(
        f'<div class="cmd">$ {html.escape(cmd)}</div><pre>{ansi_to_html(out)}'
        f'</pre>' for cmd, out in blocks)
    return f'''<!doctype html><meta charset="utf-8"><style>
body{{margin:0;background:#1e2230;font:14px/1.45 'DejaVu Sans Mono',monospace;
color:#e6e6e6}} .bar{{background:#2b3042;padding:8px 14px;color:#aab}}
.bar i{{display:inline-block;width:11px;height:11px;border-radius:50%;
margin-right:6px}} .t{{padding:10px 18px}} .cmd{{color:#7ee787;margin-top:10px}}
pre{{margin:4px 0 8px;white-space:pre-wrap}}</style>
<div class="bar"><i style="background:#ff5f56"></i><i style="background:#ffbd2e">
</i><i style="background:#27c93f"></i> {html.escape(title)}</div>
<div class="t">{body}</div>'''


def run(args, cwd=SKILL, stderr=True):
    env = dict(os.environ, FORCE_COLOR='1')
    p = subprocess.run(args, cwd=cwd, env=env, capture_output=True,
                       text=True, encoding='utf-8')
    return (p.stdout + (p.stderr if stderr else '') +
            f'código de salida: {p.returncode}\n')


def fit_height(blocks):
    lines = sum(out.count('\n') + 2 for _, out in blocks)
    return 150 + lines * 21


def shot(chrome, page, png, width=1100, height=800):
    subprocess.run([chrome, '--headless', '--no-sandbox', '--disable-gpu',
                    '--hide-scrollbars', f'--window-size={width},{height}',
                    f'--screenshot={png}', page.as_uri()],
                   check=True, capture_output=True)
    print(f'✔ {png.relative_to(SKILL)}')


def terminal(chrome, tmp, name, title, blocks, width=1100):
    page = tmp / (name + '.html')
    page.write_text(terminal_page(title, blocks), 'utf-8')
    shot(chrome, page, EVID / (name + '.png'), width, fit_height(blocks))


def main():
    chrome = find_chrome()
    EVID.mkdir(exist_ok=True)
    for old in EVID.glob('*.png'):
        old.unlink()
    repo = SKILL.parent.parent.parent
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        clean = lambda text: (text.replace(str(tmp), '/tmp')
                              .replace(str(SKILL) + '/', ''))

        # 1. Auditoría de la tienda real (raíz del repo)
        out = run(AUDIT + ['.', '--out', str(tmp / 'antes-repo')], cwd=repo)
        terminal(chrome, tmp, '01-auditoria-consola',
                 '/react-bug-hunter · auditar', [(
                     'python3 .claude/skills/react-bug-hunter/scripts/audit.py'
                     ' . --out reporte-antes', clean(out))])

        # 2. Reporte HTML de la auditoría
        antes = tmp / 'antes'
        run(AUDIT + [str(FIX / 'app_con_bugs'), '--out', str(antes)])
        shot(chrome, antes / 'reporte.html', EVID / '02-reporte-html.png',
             1100, 1400)

        # 3. Reparación automática con build real (copia de la tienda)
        app = tmp / 'tienda'
        app.mkdir()
        for item in ('src', 'index.html', 'package.json', 'vite.config.js'):
            src = repo / item
            (shutil.copytree if src.is_dir() else shutil.copy2)(
                src, app / item)
        if (repo / 'node_modules').is_dir():
            try:
                (app / 'node_modules').symlink_to(repo / 'node_modules')
            except OSError:
                pass
        out = run(FIXCMD + [str(app), '--apply', '--verify-build', '--out',
                         str(tmp / 'fix')])
        terminal(chrome, tmp, '03-reparacion-automatica',
                 '/react-bug-hunter reparar', [(
                     'python3 .claude/skills/react-bug-hunter/scripts/fix.py'
                     ' . --apply --verify-build', clean(out))])

        # 4. Reporte HTML de reparaciones (diffs)
        shot(chrome, tmp / 'fix' / 'fix.html', EVID / '04-reparaciones-html.png',
             1100, 1500)

        # 5. Verificación contra el baseline
        base = tmp / 'antes-repo' / 'reporte.json'
        out = run(AUDIT + [str(app), '--out', str(tmp / 'despues'),
                           '--baseline', str(base)])
        terminal(chrome, tmp, '05-verificacion-baseline',
                 '/react-bug-hunter · verificar', [(
                     'python3 .claude/skills/react-bug-hunter/scripts/audit.py'
                     ' . --baseline reporte-antes/reporte.json', clean(out))])

        # 6. Entradas inválidas (audit y fix)
        cases = [
            ('audit.py ./no-existe', AUDIT + ['./no-existe', '--format', 'none']),
            ('audit.py tests/fixtures/app_con_bugs/package.json',
             AUDIT + ['tests/fixtures/app_con_bugs/package.json',
                      '--format', 'none']),
            ('audit.py tests/fixtures/sin_codigo',
             AUDIT + ['tests/fixtures/sin_codigo', '--format', 'none']),
            ('audit.py tests/fixtures/app_con_bugs --baseline '
             'tests/fixtures/baseline_invalido/reporte.json',
             AUDIT + ['tests/fixtures/app_con_bugs', '--format', 'none',
                      '--baseline',
                      'tests/fixtures/baseline_invalido/reporte.json']),
            ('fix.py tests/fixtures/app_con_bugs --undo',
             FIXCMD + ['tests/fixtures/app_con_bugs', '--undo']),
            ('fix.py tests/fixtures/app_con_bugs --only X99',
             FIXCMD + ['tests/fixtures/app_con_bugs', '--only', 'X99',
                    '--out', str(tmp / 'x')]),
        ]
        blocks = [(cmd, clean(run(args))) for cmd, args in cases]
        terminal(chrome, tmp, '06-errores-entrada',
                 'react-bug-hunter · entradas inválidas', blocks)

        # 7. Pruebas automáticas
        out = run([sys.executable, '-m', 'unittest', 'discover', '-s',
                   'tests', '-v'])
        terminal(chrome, tmp, '07-pruebas-unitarias',
                 'react-bug-hunter · pruebas',
                 [('python3 -m unittest discover -s tests -v', out)], 1250)

        # 8. Resumen de la demo
        out = run([sys.executable, str(SKILL / 'scripts' / 'demo.py'),
                   '--out', str(tmp / 'demo')], stderr=False)
        tail = out[out.index('━━ Resumen'):] if '━━ Resumen' in out else out
        terminal(chrome, tmp, '08-demo-resumen',
                 '/react-bug-hunter demo',
                 [('python3 .claude/skills/react-bug-hunter/scripts/demo.py',
                   clean(tail))])


if __name__ == '__main__':
    main()
