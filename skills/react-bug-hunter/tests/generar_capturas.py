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


def run(args, cwd=SKILL):
    env = dict(os.environ, FORCE_COLOR='1')
    p = subprocess.run(args, cwd=cwd, env=env, capture_output=True,
                       text=True)
    return p.stdout + p.stderr + f'código de salida: {p.returncode}\n'


def fit_height(blocks):
    lines = sum(out.count('\n') + 2 for _, out in blocks)
    return 150 + lines * 21


def shot(chrome, page, png, width=1100, height=800):
    subprocess.run([chrome, '--headless', '--no-sandbox', '--disable-gpu',
                    '--hide-scrollbars', f'--window-size={width},{height}',
                    f'--screenshot={png}', page.as_uri()],
                   check=True, capture_output=True)
    print(f'✔ {png.relative_to(SKILL)}')


def main():
    chrome = find_chrome()
    EVID.mkdir(exist_ok=True)
    repo = SKILL.parent.parent
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        antes = tmp / 'reporte-antes'
        despues = tmp / 'reporte-despues'

        out = run(AUDIT + ['.', '--out', 'reporte-antes'], cwd=repo)
        shutil.rmtree(repo / 'reporte-antes', ignore_errors=True)
        page = tmp / 'p1.html'
        blocks = [('python3 skills/react-bug-hunter/scripts/audit.py . '
                   '--out reporte-antes', out)]
        page.write_text(terminal_page('react-bug-hunter · auditoría',
                                      blocks), 'utf-8')
        shot(chrome, page, EVID / '01-auditoria-exitosa.png', 1100,
             fit_height(blocks))

        run(AUDIT + [str(FIX / 'app_con_bugs'), '--out', str(antes)])
        shot(chrome, antes / 'reporte.html', EVID / '02-reporte-html.png',
             1100, 1400)

        out = run(AUDIT + ['tests/fixtures/app_corregida', '--out',
                           str(despues), '--baseline',
                           str(antes / 'reporte.json')])
        out = out.replace(str(tmp), '/tmp')
        page = tmp / 'p3.html'
        blocks = [('python3 scripts/audit.py tests/fixtures/app_corregida '
                   '--baseline reporte-antes/reporte.json', out)]
        page.write_text(terminal_page('react-bug-hunter · progreso', blocks),
                        'utf-8')
        shot(chrome, page, EVID / '03-progreso-baseline.png', 1100,
             fit_height(blocks))

        cases = [
            ('python3 scripts/audit.py ./no-existe',
             AUDIT + ['./no-existe', '--format', 'none']),
            ('python3 scripts/audit.py tests/fixtures/app_con_bugs/package.json',
             AUDIT + ['tests/fixtures/app_con_bugs/package.json',
                      '--format', 'none']),
            ('python3 scripts/audit.py tests/fixtures/sin_codigo',
             AUDIT + ['tests/fixtures/sin_codigo', '--format', 'none']),
            ('python3 scripts/audit.py tests/fixtures/app_con_bugs '
             '--baseline tests/fixtures/baseline_invalido/reporte.json',
             AUDIT + ['tests/fixtures/app_con_bugs', '--format', 'none',
                      '--baseline',
                      'tests/fixtures/baseline_invalido/reporte.json']),
        ]
        blocks = [(cmd, run(args).replace(str(SKILL) + '/', ''))
                  for cmd, args in cases]
        page = tmp / 'p4.html'
        page.write_text(terminal_page('react-bug-hunter · entradas inválidas',
                                      blocks), 'utf-8')
        shot(chrome, page, EVID / '04-errores-entrada.png', 1100,
             fit_height(blocks))

        out = run([sys.executable, '-m', 'unittest', 'discover', '-s',
                   'tests', '-v'])
        page = tmp / 'p5.html'
        blocks = [('python3 -m unittest discover -s tests -v', out)]
        page.write_text(terminal_page('react-bug-hunter · pruebas', blocks),
                        'utf-8')
        shot(chrome, page, EVID / '05-pruebas-unitarias.png', 1250,
             fit_height(blocks))


if __name__ == '__main__':
    main()
