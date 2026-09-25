#!/usr/bin/env python3
"""react-bug-hunter · reparación automática.

Uso:
    python3 scripts/fix.py PROYECTO                 # vista previa (no toca nada)
    python3 scripts/fix.py PROYECTO --apply         # aplica con copia de seguridad
    python3 scripts/fix.py PROYECTO --apply --verify-build
    python3 scripts/fix.py PROYECTO --only R01,C03  # solo algunas reglas
    python3 scripts/fix.py PROYECTO --undo          # restaura la última copia

Cómo funciona:
    1. Audita el proyecto en memoria.
    2. Toma el hallazgo de mayor prioridad y aplica su reparador.
    3. Vuelve a auditar: la reparación se acepta solo si ese hallazgo
       desaparece y no aparece ningún problema nuevo; si no, se descarta.
    4. Repite hasta que no queden hallazgos reparables.
    5. Con --apply guarda una copia en .rbh-backup/, escribe los cambios y,
       con --verify-build, ejecuta `npm run build`; si falla, revierte todo.

Genera en --out (por defecto reporte-fix/): cambios.diff, ENTREGA.md,
fix.html y resumen.json.

Códigos de salida:
    0  todo lo detectado quedó reparado (o no había nada)
    1  quedan hallazgos que requieren revisión manual
    2  ruta inválida · 3 sin código · 5 asset dañado (igual que audit.py)
    6  el build falló después de aplicar; los cambios se revirtieron
    7  --undo sin copias de seguridad disponibles
"""

import argparse
import difflib
import html
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit import (AuditError, c, collect_files, enrich,  # noqa: E402
                   load_rules, load_template, setup_console, validate_project)
from checks import SourceFile, run_checks  # noqa: E402
from fixers import FIXERS, PRIORITY, NotFixable  # noqa: E402
from report import CATEGORIAS, fill  # noqa: E402

BACKUP_DIR = '.rbh-backup'
MAX_STEPS = 200


# --------------------------------------------------------------- utilidades

def newline_of(text):
    return '\r\n' if '\r\n' in text else '\n'


def join_lines(lines, original):
    nl = newline_of(original)
    end = nl if original.endswith(('\n', '\r\n')) else ''
    return nl.join(lines) + end


def audit_memory(files, rules, sevs):
    srcs = [SourceFile(rel, text) for rel, text in files.items()]
    return [enrich(r, rules, sevs) for r in run_checks(srcs)]


def counts(findings):
    out = {}
    for f in findings:
        key = (f['regla'], f['archivo'])
        out[key] = out.get(key, 0) + 1
    return out


def score(findings, sevs):
    return max(0, 100 - sum(sevs[f['severidad']]['penalizacion']
                            for f in findings))


def file_diff(rel, old, new, context=3):
    return ''.join(difflib.unified_diff(
        old.splitlines(keepends=True), new.splitlines(keepends=True),
        fromfile=f'a/{rel}', tofile=f'b/{rel}', n=context))


# ---------------------------------------------------------------- reparación

def plan_fixes(root, rules, sevs, only=None, exclude=()):
    """Aplica reparaciones en memoria. No escribe nada en disco."""
    warnings = []
    loaded = collect_files(root, warnings, exclude)
    if not loaded:
        raise AuditError(f'No se encontraron archivos de código en "{root}".',
                         3, 'Verifica que la carpeta contiene src/.')
    original = {f.rel: f.text for f in loaded}
    files = dict(original)
    initial = audit_memory(files, rules, sevs)
    findings = initial
    by_print = {f['huella']: f for f in initial}
    by_rule = {}
    for f in initial:
        by_rule.setdefault((f['regla'], f['archivo']), f)

    def origin(f):
        # El hallazgo en el archivo original: por huella o, si el código de
        # esa línea ya cambió por otra reparación, por regla + archivo.
        return by_print.get(f['huella'],
                            by_rule.get((f['regla'], f['archivo']), f))

    applied, skipped = [], {}

    for _ in range(MAX_STEPS):
        pending = [f for f in findings if f['huella'] not in skipped
                   and (not only or f['regla'] in only)]
        if not pending:
            break
        pending.sort(key=lambda f: (PRIORITY.index(f['regla'])
                                    if f['regla'] in PRIORITY else 99,
                                    f['archivo'], f['linea']))
        f = pending[0]
        fixer = FIXERS.get(f['regla'])
        if fixer is None:
            skipped[f['huella']] = 'no hay reparador automático para esta regla'
            continue
        old_text = files[f['archivo']]
        lines = old_text.splitlines()
        try:
            why = fixer(lines, f, old_text)
        except NotFixable as exc:
            skipped[f['huella']] = str(exc)
            continue
        new_text = join_lines(lines, old_text)
        candidate = dict(files, **{f['archivo']: new_text})
        after = audit_memory(candidate, rules, sevs)
        before_c, after_c = counts(findings), counts(after)
        key = (f['regla'], f['archivo'])
        improved = after_c.get(key, 0) < before_c.get(key, 0)
        regress = [k for k, v in after_c.items() if v > before_c.get(k, 0)]
        if not improved or regress:
            skipped[f['huella']] = ('la reparación no pasó la verificación '
                                    '(se descartó)')
            continue
        side = sorted({k[0] for k, v in before_c.items()
                       if k != key and after_c.get(k, 0) < v})
        files = candidate
        findings = after
        applied.append({
            'tambien_resuelve': side,
            'regla': f['regla'], 'titulo': f['titulo'],
            'severidad': f['severidad'], 'categoria': f['categoria'],
            'archivo': f['archivo'],
            'linea': origin(f)['linea'],
            'codigo': origin(f)['codigo'], 'sintoma': f['sintoma'],
            'prompt': f['prompt'], 'ref': f['ref'], 'explicacion': why,
            'diff': file_diff(f['archivo'], old_text, new_text, context=2),
        })

    manual = []
    for f in findings:
        manual.append(dict(f, linea=origin(f)['linea'],
                           motivo=skipped.get(
            f['huella'], 'excluido con --only' if only else 'sin reparar')))
    changed = {rel: (original[rel], files[rel]) for rel in files
               if files[rel] != original[rel]}
    return {
        'proyecto': root.name,
        'ruta': str(root),
        'fecha': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'puntaje_antes': score(initial, sevs),
        'puntaje_despues': score(findings, sevs),
        'hallazgos_antes': len(initial),
        'aplicadas': applied,
        'manuales': manual,
        'cambios': changed,
        'avisos': warnings,
    }


# ----------------------------------------------------------- copia / undo

def make_backup(root, changed):
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    dest = root / BACKUP_DIR / stamp
    for rel, (old, _new) in changed.items():
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(old.encode('utf-8'))
    (dest / 'manifest.json').write_text(json.dumps({
        'fecha': stamp, 'archivos': sorted(changed)}, indent=2), 'utf-8')
    return dest


def restore_backup(root, dest):
    manifest = json.loads((dest / 'manifest.json').read_text('utf-8'))
    for rel in manifest['archivos']:
        (root / rel).write_bytes((dest / rel).read_bytes())
    shutil.rmtree(dest)
    base = root / BACKUP_DIR
    if base.is_dir() and not any(base.iterdir()):
        base.rmdir()
    return manifest['archivos']


def latest_backup(root):
    base = root / BACKUP_DIR
    if not base.is_dir():
        return None
    dirs = sorted(d for d in base.iterdir() if (d / 'manifest.json').is_file())
    return dirs[-1] if dirs else None


def run_build(root):
    """Devuelve (estado, detalle). estado: ok | fallo | omitido."""
    if not (root / 'package.json').is_file():
        return 'omitido', 'no hay package.json'
    if not (root / 'node_modules').is_dir():
        return 'omitido', 'no hay node_modules (ejecuta `npm i` primero)'
    npm = shutil.which('npm')
    if not npm:
        return 'omitido', 'npm no está instalado'
    try:
        p = subprocess.run([npm, 'run', 'build'], cwd=root, text=True,
                           capture_output=True, timeout=300,
                           encoding='utf-8', errors='replace')
    except subprocess.TimeoutExpired:
        return 'fallo', 'npm run build tardó más de 5 minutos'
    tail = '\n'.join((p.stdout + p.stderr).strip().splitlines()[-12:])
    return ('ok' if p.returncode == 0 else 'fallo'), tail


# ------------------------------------------------------------------ salidas

def render_entrega(template, plan, build):
    blocks = []
    for n, a in enumerate(plan['aplicadas'], 1):
        blocks.append('\n'.join([
            f'### Error {n}: {a["titulo"]} (`{a["regla"]}`)',
            '',
            f'- **Qué pasaba (síntoma):** {a["sintoma"]}',
            f'- **Archivo y línea:** `{a["archivo"]}:{a["linea"]}`',
            f'- **Código original:** `{a["codigo"]}`',
            f'- **Cómo se corrigió:** {a["explicacion"]}'
            + (f' (También resolvió: {", ".join(a["tambien_resuelve"])}.)'
               if a['tambien_resuelve'] else ''),
            f'- **Prompt sugerido para la IA:** "{a["prompt"]}"',
            '- **¿Tuviste que corregir el prompt?:** _(completar)_',
            '',
            '```diff',
            a['diff'].rstrip(),
            '```',
        ]))
    manual = [f'- `{m["regla"]}` {m["titulo"]} en `{m["archivo"]}:'
              f'{m["linea"]}`: {m["motivo"]}' for m in plan['manuales']]
    return fill(template, {
        'PROYECTO': plan['proyecto'],
        'FECHA': plan['fecha'],
        'ANTES': plan['puntaje_antes'],
        'DESPUES': plan['puntaje_despues'],
        'TOTAL_ANTES': plan['hallazgos_antes'],
        'APLICADAS': len(plan['aplicadas']),
        'MANUALES': len(plan['manuales']),
        'BUILD': build,
        'CORRECCIONES': '\n\n'.join(blocks) or '_No hubo correcciones._',
        'PENDIENTES': '\n'.join(manual) or 'Ninguno. ✅',
    })


def _diff_html(diff):
    out = []
    for line in diff.splitlines():
        cls = ('add' if line.startswith('+') and not line.startswith('+++')
               else 'del' if line.startswith('-') and not line.startswith('---')
               else 'hunk' if line.startswith('@@') else 'ctx')
        out.append(f'<span class="{cls}">{html.escape(line) or " "}</span>')
    return ''.join(out)  # cada <span> ya es un bloque: sin saltos extra


def render_fix_html(template, plan, build, mode):
    e = html.escape
    cards = []
    for n, a in enumerate(plan['aplicadas'], 1):
        extra = (f' <b>También resolvió: {e(", ".join(a["tambien_resuelve"]))}.</b>'
                 if a['tambien_resuelve'] else '')
        cards.append(f'''
<article class="fix sev-{e(a["severidad"])}" data-cat="{e(a["categoria"])}">
  <header><span class="num">{n}</span><span class="rule">{e(a["regla"])}</span>
  <h3>{e(a["titulo"])}</h3>
  <span class="cat">{e(CATEGORIAS.get(a["categoria"], a["categoria"]))}</span></header>
  <p class="loc"><code>{e(a["archivo"])}:{a["linea"]}</code></p>
  <p class="why">✔ {e(a["explicacion"])}{extra}</p>
  <pre class="diff">{_diff_html(a["diff"])}</pre>
</article>''')
    manual = ''.join(
        f'<li><b>{e(m["regla"])}</b> {e(m["titulo"])} '
        f'<code>{e(m["archivo"])}:{m["linea"]}</code> — {e(m["motivo"])}</li>'
        for m in plan['manuales']) or '<li>Ninguno ✅</li>'
    return fill(template, {
        'PROYECTO': e(plan['proyecto']),
        'FECHA': e(plan['fecha']),
        'MODO': e(mode),
        'ANTES': plan['puntaje_antes'],
        'DESPUES': plan['puntaje_despues'],
        'APLICADAS': len(plan['aplicadas']),
        'MANUALES': len(plan['manuales']),
        'ARCHIVOS': len(plan['cambios']),
        'BUILD': e(build),
        'TARJETAS': '\n'.join(cards) or '<p>No hubo correcciones.</p>',
        'PENDIENTES': manual,
    })


def write_outputs(out_dir, plan, build, mode):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    full = ''.join(file_diff(rel, old, new)
                   for rel, (old, new) in sorted(plan['cambios'].items()))
    (out / 'cambios.diff').write_text(full, 'utf-8')
    (out / 'ENTREGA.md').write_text(render_entrega(
        load_template('entrega_template.md'), plan, build), 'utf-8')
    (out / 'fix.html').write_text(render_fix_html(
        load_template('fix_template.html'), plan, build, mode), 'utf-8')
    data = {k: v for k, v in plan.items() if k != 'cambios'}
    data['archivos_modificados'] = sorted(plan['cambios'])
    data['build'] = build
    (out / 'resumen.json').write_text(
        json.dumps(data, ensure_ascii=False, indent=2), 'utf-8')
    return [out / n for n in ('fix.html', 'ENTREGA.md', 'cambios.diff',
                              'resumen.json')]


def print_plan(plan, apply):
    print(c(f'\n🛠  react-bug-hunter · reparación · {plan["proyecto"]}', '1'))
    print(f'   modo: {"APLICAR" if apply else "VISTA PREVIA (no se modificó nada)"}\n')
    for n, a in enumerate(plan['aplicadas'], 1):
        side = (f' (+ {", ".join(a["tambien_resuelve"])})'
                if a['tambien_resuelve'] else '')
        print(f'  {c("✔", "32")} {n:>2}. {a["regla"]}  '
              f'{a["archivo"]}:{a["linea"]:<4} {a["titulo"]}{side}')
    for m in plan['manuales']:
        print(f'  {c("✋", "33")}     {m["regla"]}  {m["archivo"]}:'
              f'{m["linea"]:<4} {m["titulo"]} — {m["motivo"]}')
    added = removed = 0
    for old, new in plan['cambios'].values():
        for line in difflib.unified_diff(old.splitlines(), new.splitlines(),
                                         lineterm=''):
            if line.startswith('+') and not line.startswith('+++'):
                added += 1
            elif line.startswith('-') and not line.startswith('---'):
                removed += 1
    resolved = plan['hallazgos_antes'] - len(plan['manuales'])
    print(f'\n   {resolved}/{plan["hallazgos_antes"]} hallazgos resueltos con '
          f'{len(plan["aplicadas"])} reparaciones · '
          f'{len(plan["manuales"])} pendientes · '
          f'{len(plan["cambios"])} archivos · +{added} −{removed} líneas')
    print(c(f'   Puntaje: {plan["puntaje_antes"]}/100 → '
            f'{plan["puntaje_despues"]}/100', '36'))


# --------------------------------------------------------------------- main

def main(argv=None):
    setup_console()
    parser = argparse.ArgumentParser(
        prog='fix.py',
        description='Repara automáticamente los errores que detecta '
                    'react-bug-hunter, con vista previa, copia de seguridad y '
                    'verificación.')
    parser.add_argument('proyecto', help='carpeta raíz del proyecto')
    parser.add_argument('--apply', action='store_true',
                        help='escribir los cambios (sin esto solo es vista previa)')
    parser.add_argument('--verify-build', action='store_true',
                        help='ejecutar `npm run build` y revertir si falla')
    parser.add_argument('--only', metavar='REGLAS',
                        help='solo estas reglas, separadas por coma (ej. R01,C03)')
    parser.add_argument('--undo', action='store_true',
                        help='restaurar la última copia de seguridad')
    parser.add_argument('--out', default='reporte-fix',
                        help='carpeta de reportes (por defecto: reporte-fix)')
    parser.add_argument('--exclude', action='append', default=[],
                        metavar='CARPETA', help='carpeta extra a ignorar')
    parser.add_argument('--show-diff', action='store_true',
                        help='imprimir el diff completo en consola')
    args = parser.parse_args(argv)

    try:
        root = validate_project(args.proyecto, [])
        if args.undo:
            dest = latest_backup(root)
            if not dest:
                print(c('✖ Error: no hay copias de seguridad para deshacer.',
                        '31'), file=sys.stderr)
                print(f'  Sugerencia: las copias se crean con --apply en '
                      f'{BACKUP_DIR}/.', file=sys.stderr)
                return 7
            restored = restore_backup(root, dest)
            print(c(f'↩  Se restauraron {len(restored)} archivos desde '
                    f'{dest.name}:', '36'))
            for rel in restored:
                print(f'   · {rel}')
            return 0

        rules, sevs = load_rules()
        only = None
        if args.only:
            only = {r.strip().upper() for r in args.only.split(',') if r.strip()}
            unknown = only - set(rules)
            if unknown:
                raise AuditError(
                    f'Regla(s) desconocida(s): {", ".join(sorted(unknown))}.',
                    2, f'Reglas válidas: {", ".join(sorted(rules))}.')
        plan = plan_fixes(root, rules, sevs, only, args.exclude)
    except AuditError as exc:
        print(c(f'✖ Error: {exc}', '31'), file=sys.stderr)
        if exc.hint:
            print(f'  Sugerencia: {exc.hint}', file=sys.stderr)
        return exc.code

    print_plan(plan, args.apply)
    if args.show_diff:
        for rel, (old, new) in sorted(plan['cambios'].items()):
            print(file_diff(rel, old, new))

    build = 'no verificado (usa --verify-build)'
    code = 0
    if args.apply and plan['cambios']:
        dest = make_backup(root, plan['cambios'])
        for rel, (_old, new) in plan['cambios'].items():
            (root / rel).write_bytes(new.encode('utf-8'))
        print(c(f'\n   💾 Copia de seguridad: {dest.relative_to(root)} '
                f'(deshacer con --undo)', '36'))
        if args.verify_build:
            print('   🔨 Ejecutando npm run build...')
            state, detail = run_build(root)
            if state == 'ok':
                build = 'npm run build ✅'
                print(c('   ✔ El build pasa con los cambios.', '32'))
            elif state == 'omitido':
                build = f'omitido: {detail}'
                print(c(f'   ⚠ Build omitido: {detail}', '33'))
            else:
                restore_backup(root, dest)
                build = 'falló → cambios revertidos'
                print(c('   ✖ El build falló; se revirtieron todos los '
                        'cambios.', '31'), file=sys.stderr)
                print(detail, file=sys.stderr)
                code = 6
    elif not args.apply and plan['cambios']:
        print('\n   Para aplicar: agrega --apply (se guarda copia de seguridad).')

    mode = ('revertido (el build falló)' if code else
            'aplicado' if args.apply else 'vista previa')
    written = write_outputs(args.out, plan, build, mode)
    print('\n   Reportes generados:')
    for p in written:
        print(f'   → {p}')
    print()
    if code:
        return code
    return 1 if plan['manuales'] else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.stderr.close()
        sys.exit(0)
