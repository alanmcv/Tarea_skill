#!/usr/bin/env bash
# Demostración de principio a fin de react-bug-hunter.
#
# Uso: scripts/demo.sh [PROYECTO]
#   PROYECTO  app a auditar (por defecto: tests/fixtures/app_con_bugs)
#
# Muestra: 1) auditoría con errores, 2) progreso tras corregir (baseline),
# 3) cuatro entradas inválidas y cómo responde la skill.
set -uo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
AUDIT="python3 $SKILL_DIR/scripts/audit.py"
FIX="$SKILL_DIR/tests/fixtures"
PROJECT=${1:-$FIX/app_con_bugs}
OUT=${DEMO_OUT:-$(mktemp -d)}

if { [ -t 1 ] || [ -n "${FORCE_COLOR:-}" ]; } && [ -z "${NO_COLOR:-}" ]; then B='\033[1;34m'; G='\033[1;32m'; R='\033[0m'; else B=''; G=''; R=''; fi
step() { printf "\n${B}━━ %s${R}\n$ %s\n" "$1" "$2"; }

step "1. Auditar la app con errores" "audit.py $PROJECT --out $OUT/antes"
$AUDIT "$PROJECT" --out "$OUT/antes"
echo "código de salida: $?"

step "2. Auditar la versión corregida y comparar con el baseline" \
  "audit.py app_corregida --out $OUT/despues --baseline $OUT/antes/reporte.json"
$AUDIT "$FIX/app_corregida" --out "$OUT/despues" --baseline "$OUT/antes/reporte.json"
echo "código de salida: $?"

step "3. Error: la ruta no existe" "audit.py ./no-existe"
$AUDIT ./no-existe --format none
echo "código de salida: $?"

step "4. Error: se pasa un archivo en vez de una carpeta" "audit.py package.json"
$AUDIT "$FIX/app_con_bugs/package.json" --format none
echo "código de salida: $?"

step "5. Error: carpeta sin código" "audit.py tests/fixtures/sin_codigo"
$AUDIT "$FIX/sin_codigo" --format none
echo "código de salida: $?"

step "6. Error: baseline con JSON roto" "audit.py app_con_bugs --baseline reporte_roto.json"
$AUDIT "$FIX/app_con_bugs" --format none --baseline "$FIX/baseline_invalido/reporte.json"
echo "código de salida: $?"

printf "\n${G}✔ Demo terminada.${R} Reportes en: %s\n" "$OUT"
printf '  Abre %s/antes/reporte.html en el navegador.\n' "$OUT"
