#!/usr/bin/env python3
"""Instala react-bug-hunter en otro proyecto o para todos tus proyectos.

Uso:
    python3 scripts/install.py                         # ~/.claude/skills (todos tus proyectos)
    python3 scripts/install.py --project RUTA          # RUTA/.claude/skills (solo ese proyecto)
    python3 scripts/install.py --agent codex           # ~/.codex/skills

Después, en VS Code (extensión Claude Code) o en la terminal con `claude`,
escribe /react-bug-hunter en el chat.

Códigos de salida: 0 ok · 2 argumentos inválidos · 3 Python muy antiguo
"""

import argparse
import shutil
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
NAME = 'react-bug-hunter'
ITEMS = ['SKILL.md', 'README.md', 'scripts', 'assets', 'references', 'tests']


def main(argv=None):
    parser = argparse.ArgumentParser(description='Instala react-bug-hunter.')
    parser.add_argument('--agent', choices=['claude', 'codex'],
                        default='claude')
    parser.add_argument('--project', metavar='RUTA',
                        help='instalar solo en este proyecto')
    parser.add_argument('--force', action='store_true',
                        help='reemplazar una instalación existente')
    args = parser.parse_args(argv)

    if sys.version_info < (3, 8):
        print('✖ Se necesita Python 3.8 o superior.', file=sys.stderr)
        return 3
    if args.project:
        project = Path(args.project).expanduser()
        if not project.is_dir():
            print(f'✖ La carpeta de proyecto "{project}" no existe.',
                  file=sys.stderr)
            return 2
        base = project.resolve() / f'.{args.agent}' / 'skills'
    else:
        base = Path.home() / f'.{args.agent}' / 'skills'

    dest = base / NAME
    if dest.resolve() == SKILL:
        print(f'✔ La skill ya está en su lugar: {dest}')
        return 0
    if dest.exists():
        if not args.force:
            print(f'✖ Ya existe {dest}. Usa --force para reemplazarla.',
                  file=sys.stderr)
            return 2
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    ignore = shutil.ignore_patterns('__pycache__', '*.pyc')
    for item in ITEMS:
        src = SKILL / item
        if src.is_dir():
            shutil.copytree(src, dest / item, ignore=ignore)
        elif src.is_file():
            shutil.copy2(src, dest / item)

    print(f'✔ react-bug-hunter instalada en {dest}')
    print('  Abre el chat de Claude (VS Code o terminal) y escribe:')
    print('    /react-bug-hunter')
    return 0


if __name__ == '__main__':
    sys.exit(main())
