#!/usr/bin/env bash
# Instala react-bug-hunter como skill de Claude Code o Codex.
#
# Uso:
#   scripts/install.sh [--agent claude|codex] [--scope user|project] [--project DIR]
#
# Ejemplos:
#   scripts/install.sh                          # ~/.claude/skills/react-bug-hunter
#   scripts/install.sh --scope project --project ~/mi-app
#   scripts/install.sh --agent codex            # ~/.codex/skills/react-bug-hunter
set -euo pipefail

AGENT=claude
SCOPE=user
PROJECT=$(pwd)
SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
NAME=react-bug-hunter

while [ $# -gt 0 ]; do
  case "$1" in
    --agent) AGENT=${2:-}; shift 2 ;;
    --scope) SCOPE=${2:-}; shift 2 ;;
    --project) PROJECT=${2:-}; shift 2 ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "✖ Opción desconocida: $1 (usa --help)" >&2; exit 2 ;;
  esac
done

case "$AGENT" in claude|codex) ;; *) echo "✖ --agent debe ser claude o codex" >&2; exit 2 ;; esac
case "$SCOPE" in
  user) BASE="$HOME/.$AGENT/skills" ;;
  project)
    [ -d "$PROJECT" ] || { echo "✖ La carpeta de proyecto '$PROJECT' no existe" >&2; exit 2; }
    BASE="$(cd "$PROJECT" && pwd)/.$AGENT/skills" ;;
  *) echo "✖ --scope debe ser user o project" >&2; exit 2 ;;
esac

if ! command -v python3 >/dev/null 2>&1; then
  echo "✖ Se necesita python3 (3.8 o superior)." >&2
  exit 3
fi
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' || {
  echo "✖ Tu python3 es muy antiguo; instala 3.8 o superior." >&2; exit 3; }

DEST="$BASE/$NAME"
mkdir -p "$DEST"
for item in SKILL.md README.md scripts assets references tests; do
  cp -R "$SKILL_DIR/$item" "$DEST/"
done
find "$DEST" -name __pycache__ -type d -prune -exec rm -rf {} +
chmod +x "$DEST/scripts/"*.py "$DEST/scripts/"*.sh

echo "✔ react-bug-hunter instalada en $DEST"
echo "  Prueba: python3 \"$DEST/scripts/audit.py\" <carpeta-de-tu-proyecto>"
