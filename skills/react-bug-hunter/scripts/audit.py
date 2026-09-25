#!/usr/bin/env python3
"""react-bug-hunter: audita un proyecto React + Vite y genera reportes.

Uso:
    python3 scripts/audit.py RUTA_PROYECTO [--out DIR] [--format all]
                             [--baseline reporte.json] [--fail-on error]

Códigos de salida:
    0  sin hallazgos que superen --fail-on
    1  hay hallazgos con severidad >= --fail-on
    2  ruta inválida (no existe o no es carpeta)
    3  la carpeta no contiene archivos de código analizables
    4  el archivo --baseline no existe o no es un JSON válido
    5  un asset de la skill falta o está dañado
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from checks import SourceFile, run_checks  # noqa: E402
from report import (SEV_ORDER, compare, render_html,  # noqa: E402
                    render_json, render_markdown)

SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS = SKILL_DIR / 'assets'
IGNORED_DIRS = {'node_modules', 'dist', 'build', '.git', '.vite', 'coverage',
                'dist-ssr', '.next', 'reporte-bugs', 'fixtures'}
SOURCE_EXT = ('.js', '.jsx', '.ts', '.tsx', '.css')
MAX_FILE_BYTES = 1_000_000


class AuditError(Exception):
    def __init__(self, message, code, hint=''):
        super().__init__(message)
        self.code = code
        self.hint = hint


# ------------------------------------------------------------------ colores

USE_COLOR = (sys.stdout.isatty() or bool(os.environ.get('FORCE_COLOR'))) \
    and not os.environ.get('NO_COLOR')


def c(text, code):
    return f'\033[{code}m{text}\033[0m' if USE_COLOR else text


SEV_COLOR = {'error': '31', 'warning': '33', 'info': '36'}


# ------------------------------------------------------------------- carga

def load_rules():
    path = ASSETS / 'rules.json'
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        rules = {r['id']: r for r in data['reglas']}
        sevs = data['severidades']
    except FileNotFoundError:
        raise AuditError(f'No se encontró {path}', 5,
                         'Reinstala la skill: falta assets/rules.json.')
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise AuditError(f'assets/rules.json está dañado: {exc}', 5,
                         'Restaura el archivo desde el repositorio.')
    return rules, sevs


def load_template(name):
    path = ASSETS / name
    if not path.is_file():
        raise AuditError(f'Falta la plantilla {path}', 5,
                         'Reinstala la skill: falta un archivo de assets/.')
    return path.read_text(encoding='utf-8')


def collect_files(root, warnings, exclude=()):
    files = []
    skip = IGNORED_DIRS | set(exclude)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in skip
                             and not d.startswith('.'))
        for name in sorted(filenames):
            full = Path(dirpath) / name
            rel = full.relative_to(root).as_posix()
            is_index = rel == 'index.html'
            if not (name.endswith(SOURCE_EXT) or is_index):
                continue
            if name.endswith(('.config.js', '.config.ts')):
                continue
            if full.stat().st_size > MAX_FILE_BYTES:
                warnings.append(f'Se omitió {rel}: supera 1 MB.')
                continue
            try:
                text = full.read_text(encoding='utf-8-sig')
            except UnicodeDecodeError:
                text = full.read_text(encoding='latin-1')
                warnings.append(f'{rel} no es UTF-8; se leyó como latin-1.')
            files.append(SourceFile(rel, text))
    return files


def validate_project(path, warnings):
    root = Path(path).expanduser()
    if not root.exists():
        raise AuditError(f'La ruta "{path}" no existe.', 2,
                         'Revisa que escribiste bien la carpeta del '
                         'proyecto (usa la raíz, donde está package.json).')
    if not root.is_dir():
        raise AuditError(f'"{path}" es un archivo, no una carpeta.', 2,
                         'Pasa la carpeta raíz del proyecto, no un archivo '
                         'suelto.')
    root = root.resolve()
    pkg = root / 'package.json'
    if not pkg.is_file():
        warnings.append('No hay package.json: puede que esta no sea la '
                        'raíz de un proyecto Node/Vite.')
    else:
        try:
            deps = json.loads(pkg.read_text(encoding='utf-8'))
            all_deps = {**deps.get('dependencies', {}),
                        **deps.get('devDependencies', {})}
            if 'react' not in all_deps:
                warnings.append('package.json no declara "react": las reglas '
                                'de React podrían no aplicar.')
        except json.JSONDecodeError:
            warnings.append('package.json no es un JSON válido.')
    return root


def load_baseline(path):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
    except FileNotFoundError:
        raise AuditError(f'No existe el baseline "{path}".', 4,
                         'Primero genera un reporte con --format json y '
                         'pasa ese reporte.json.')
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise AuditError(f'El baseline "{path}" no es JSON válido: {exc}', 4,
                         'Usa el reporte.json generado por esta skill.')
    if not isinstance(data, dict) or not isinstance(
            data.get('hallazgos'), list):
        raise AuditError(f'"{path}" no tiene el formato de un reporte de '
                         'react-bug-hunter (falta "hallazgos").', 4,
                         'Usa el reporte.json generado por esta skill.')
    return data


# ---------------------------------------------------------------- auditoría

def fingerprint(rule, file, code):
    raw = f'{rule}|{file}|{" ".join(code.split())}'
    return hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]


def enrich(raw, rules, sevs):
    r = rules[raw.rule]
    fmt = {'archivo': raw.file, 'linea': raw.line, 'codigo': raw.code}
    return {
        'regla': raw.rule,
        'titulo': r['titulo'],
        'severidad': r['severidad'],
        'severidad_etiqueta': sevs[r['severidad']]['etiqueta'],
        'categoria': r['categoria'],
        'archivo': raw.file,
        'linea': raw.line,
        'codigo': raw.code,
        'detalle': raw.detail,
        'sintoma': r['sintoma'],
        'causa': r['causa'],
        'correccion': r['correccion'],
        'prompt': r['prompt'].format(**fmt),
        'ref': r['referencia'],
        'huella': fingerprint(raw.rule, raw.file, raw.code),
    }


def audit(project, baseline_path=None, exclude=()):
    warnings = []
    root = validate_project(project, warnings)
    rules, sevs = load_rules()
    baseline = load_baseline(baseline_path) if baseline_path else None
    files = collect_files(root, warnings, exclude)
    if not files:
        raise AuditError(
            f'No se encontraron archivos .js/.jsx/.ts/.tsx/.css ni '
            f'index.html en "{project}".', 3,
            'Verifica que la carpeta contiene el código (normalmente src/).')

    findings = [enrich(r, rules, sevs) for r in run_checks(files)]
    findings.sort(key=lambda f: (SEV_ORDER[f['severidad']], f['archivo'],
                                 f['linea']))
    by_sev, by_cat = {}, {}
    for f in findings:
        by_sev[f['severidad']] = by_sev.get(f['severidad'], 0) + 1
        by_cat[f['categoria']] = by_cat.get(f['categoria'], 0) + 1
    penalty = sum(sevs[f['severidad']]['penalizacion'] for f in findings)
    data = {
        'herramienta': 'react-bug-hunter',
        'version': '1.0.0',
        'proyecto': root.name,
        'ruta': str(root),
        'fecha': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'resumen': {
            'total': len(findings),
            'puntaje': max(0, 100 - penalty),
            'archivos_analizados': len(files),
            'por_severidad': by_sev,
            'por_categoria': by_cat,
        },
        'avisos': warnings,
        'hallazgos': findings,
    }
    if baseline is not None:
        data['comparacion'] = compare(findings, baseline)
    return data


def write_reports(data, out_dir, formats):
    out = Path(out_dir)
    try:
        out.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise AuditError(f'No se pudo crear "{out_dir}": {exc}', 2,
                         'Elige otra carpeta con --out.')
    written = []
    if 'json' in formats:
        p = out / 'reporte.json'
        p.write_text(render_json(data), encoding='utf-8')
        written.append(p)
    if 'md' in formats:
        p = out / 'reporte.md'
        p.write_text(render_markdown(load_template('report_template.md'),
                                     data), encoding='utf-8')
        written.append(p)
    if 'html' in formats:
        p = out / 'reporte.html'
        p.write_text(render_html(load_template('report_template.html'),
                                 data), encoding='utf-8')
        written.append(p)
    return written


def print_summary(data, written):
    s = data['resumen']
    print(c(f'\n🔎 react-bug-hunter · {data["proyecto"]}', '1'))
    print(f'   {s["archivos_analizados"]} archivos analizados · '
          f'{s["total"]} hallazgos · puntaje {s["puntaje"]}/100\n')
    for w in data['avisos']:
        print(c(f'   ⚠ {w}', '33'))
    for n, f in enumerate(data['hallazgos'], 1):
        sev = c(f'{f["severidad"]:<7}', SEV_COLOR[f['severidad']])
        print(f'  {n:>2}. {sev} {f["regla"]}  '
              f'{f["archivo"]}:{f["linea"]:<4} {f["titulo"]}')
    comp = data.get('comparacion')
    if comp:
        print(c(f'\n   Progreso: {len(comp["resueltos"])} resueltos · '
                f'{len(comp["nuevos"])} nuevos · '
                f'{len(comp["persisten"])} persisten', '36'))
    if written:
        print('\n   Reportes generados:')
        for p in written:
            print(f'   → {p}')
    print()


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='audit.py',
        description='Audita un proyecto React + Vite en busca de errores de '
                    'lógica, datos/API y visuales.')
    parser.add_argument('proyecto', help='carpeta raíz del proyecto')
    parser.add_argument('--out', default='reporte-bugs',
                        help='carpeta de salida (por defecto: reporte-bugs)')
    parser.add_argument('--format', default='all',
                        choices=['all', 'json', 'md', 'html', 'none'],
                        help='formato del reporte (por defecto: all)')
    parser.add_argument('--baseline',
                        help='reporte.json anterior para medir el progreso')
    parser.add_argument('--fail-on', default='error',
                        choices=['error', 'warning', 'info', 'never'],
                        help='severidad mínima que produce código de '
                             'salida 1 (por defecto: error)')
    parser.add_argument('--exclude', action='append', default=[],
                        metavar='CARPETA',
                        help='carpeta extra a ignorar (se puede repetir)')
    parser.add_argument('--quiet', action='store_true',
                        help='no imprimir el resumen en consola')
    args = parser.parse_args(argv)

    try:
        data = audit(args.proyecto, args.baseline, args.exclude)
        formats = {'all': {'json', 'md', 'html'}, 'none': set()}.get(
            args.format, {args.format})
        written = write_reports(data, args.out, formats)
    except AuditError as exc:
        print(c(f'✖ Error: {exc}', '31'), file=sys.stderr)
        if exc.hint:
            print(f'  Sugerencia: {exc.hint}', file=sys.stderr)
        return exc.code

    if not args.quiet:
        print_summary(data, written)
    if args.fail_on == 'never':
        return 0
    limit = SEV_ORDER[args.fail_on]
    failing = [f for f in data['hallazgos']
               if SEV_ORDER[f['severidad']] <= limit]
    return 1 if failing else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except BrokenPipeError:
        # La salida se cortó (por ejemplo `| head`); no es un error real.
        sys.stderr.close()
        sys.exit(0)
