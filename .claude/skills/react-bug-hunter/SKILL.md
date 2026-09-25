---
name: react-bug-hunter
description: Detecta Y REPARA automáticamente errores en apps React + Vite. Lógica (estado mutado, carrito que borra de más, cantidades negativas, búsqueda sensible a mayúsculas), datos/API (fetch sin manejo de errores, sin res.ok, condiciones de carrera, porcentajes mal calculados) y visuales (contraste WCAG, z-index negativo, imágenes que desbordan, falta de viewport). Muestra el diff antes de aplicar, guarda copia de seguridad, verifica con una re-auditoría y con npm run build (revierte si falla), permite deshacer y genera un ENTREGA.md con antes/después de cada error. Úsala cuando el usuario pida revisar, depurar, encontrar o corregir bugs en una app React/Vite, preparar la entrega de un ejercicio de depuración o comprobar que sus correcciones funcionan.
argument-hint: "[auditar | reparar | deshacer | demo] [ruta-del-proyecto]"
allowed-tools: Bash(python3 *), Bash(python *), Bash(py *), Bash(npm run build), Read, Grep, Glob
---

# react-bug-hunter 🔎🛠

Audita una app React + Vite, explica cada error, **lo repara automáticamente
con verificación** y deja lista la documentación de entrega.

Argumentos recibidos: `$ARGUMENTS`

## 0. Preparación (siempre)

1. **Carpeta de la skill (`SKILL_DIR`)**: es la carpeta de este `SKILL.md`.
   Normalmente `.claude/skills/react-bug-hunter` dentro del proyecto abierto;
   si no existe ahí, usa `~/.claude/skills/react-bug-hunter`.
2. **Python**: usa `python3`. Si no existe (típico en Windows) usa `python` o
   `py -3`. Solo se necesita la biblioteca estándar (3.8+).
3. **Proyecto (`PROYECTO`)**: la ruta que venga en los argumentos; si no hay,
   `.` (la raíz del proyecto abierto en VS Code).
4. **Modo**: la primera palabra de los argumentos:
   - vacío o `auditar` → **Modo A** (auditar y explicar).
   - `reparar` (o `fix`, `corregir`) → **Modo B** (reparar todo).
   - `deshacer` (o `undo`) → **Modo C**.
   - `demo` → **Modo D**.

Ejecuta los comandos desde la raíz del proyecto y **muestra al usuario la
salida relevante** (resúmenes, no volcados enormes).

## Modo A · Auditar y explicar

1. Ejecuta:
   ```bash
   python3 SKILL_DIR/scripts/audit.py PROYECTO --out reporte-antes
   ```
2. Revisa el código de salida:
   - `0`: sin hallazgos. Felicita y termina.
   - `1`: hay hallazgos. Continúa.
   - `2`, `3`, `4` o `5`: muestra el mensaje y la **Sugerencia** que imprimió
     el script y detente (ruta inválida, sin código, baseline roto, asset
     dañado).
3. Presenta una tabla: **# · regla · archivo:línea · qué pasa**, agrupada por
   Lógica / Datos-API / Visual. Para cada regla abre su sección en
   `references/catalogo-reglas.md` (el campo `ref` de `reporte-antes/reporte.json`
   es el ancla) y explica el síntoma con un ejemplo que el usuario pueda
   reproducir en el navegador.
4. Indica que el reporte visual está en `reporte-antes/reporte.html` y
   ofrece: «¿Quieres que los repare automáticamente? (`/react-bug-hunter reparar`)».

## Modo B · Reparar todo (flujo completo)

1. Guarda el estado inicial:
   `python3 SKILL_DIR/scripts/audit.py PROYECTO --out reporte-antes --quiet`
2. **Vista previa** (no modifica nada):
   ```bash
   python3 SKILL_DIR/scripts/fix.py PROYECTO --out reporte-fix
   ```
   Resume qué se va a reparar y los pendientes manuales (✋). Muestra 2-3
   fragmentos clave de `reporte-fix/cambios.diff`.
3. **Aplicar** (hay copia de seguridad y `--undo`, así que no hace falta pedir
   otra confirmación si el usuario invocó `reparar`):
   ```bash
   python3 SKILL_DIR/scripts/fix.py PROYECTO --apply --verify-build --out reporte-fix
   ```
   - Código `0`: todo reparado. `1`: quedan pendientes manuales.
   - Código `6`: el build falló y **se revirtió todo**. Muestra el error de
     build y no sigas.
   - Si el build se omitió por falta de `node_modules`, sugiere `npm i`.
4. **Verificar**:
   ```bash
   python3 SKILL_DIR/scripts/audit.py PROYECTO --out reporte-despues --baseline reporte-antes/reporte.json
   ```
   Debe decir `N resueltos · 0 nuevos`.
5. **Pendientes manuales**: para cada uno lee la regla en
   `references/catalogo-reglas.md` y sigue `references/flujo-correccion.md`
   para corregirlo a mano con Edit (un cambio por hallazgo). Vuelve al paso 4.
6. **Cierre**: informa el puntaje antes → después, que `reporte-fix/fix.html`
   muestra cada diff y que `reporte-fix/ENTREGA.md` ya tiene síntoma,
   archivo:línea original, corrección, diff y prompt de cada error. El
   estudiante debe completar «¿Tuviste que corregir el prompt?» y probar la
   app con `npm run dev` (tabla de pruebas en `references/flujo-correccion.md`).
   Recuerda que puede revertir con `/react-bug-hunter deshacer`.

## Modo C · Deshacer

`python3 SKILL_DIR/scripts/fix.py PROYECTO --undo`. Código `7` significa que no
hay copias de seguridad: díselo al usuario.

## Modo D · Demostración

`python3 SKILL_DIR/scripts/demo.py` ejecuta todo el flujo sobre una copia
temporal (no toca el proyecto): auditar, vista previa, aplicar, verificar,
deshacer y 6 entradas inválidas. Termina con una tabla de resultados esperado
vs obtenido.

## Reglas importantes

- Nunca edites a mano lo que `fix.py` puede reparar; úsalo para que quede
  copia de seguridad y verificación.
- Si crees que un hallazgo es falso positivo, dilo y no lo cambies (ver
  «Limitaciones» en `references/catalogo-reglas.md`).
- Cómo funciona cada reparación y por qué es segura:
  `references/reparaciones.md`.

## Archivos

| Carpeta | Contenido |
|---|---|
| `scripts/` | `audit.py` (detección y reportes), `checks.py` (14 detectores), `fix.py` (reparación con verificación, backup y undo), `fixers.py` (14 reparadores), `report.py`, `demo.py`, `install.py` |
| `assets/` | `rules.json` (catálogo de reglas), `report_template.{md,html}`, `fix_template.html`, `entrega_template.md` |
| `references/` | `catalogo-reglas.md`, `reparaciones.md`, `flujo-correccion.md` |
| `tests/` | 29 pruebas + fixtures (app con errores, app corregida, entradas inválidas) |
