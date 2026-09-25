---
name: react-bug-hunter
description: Audita proyectos React + Vite en busca de errores de lógica (estado mutado, carrito que borra de más, cantidades negativas), de datos/API (fetch sin manejo de errores, porcentajes mal calculados, condiciones de carrera) y visuales (contraste WCAG, z-index negativo, imágenes que desbordan, falta de viewport). Genera un reporte JSON/Markdown/HTML con archivo, línea, síntoma, corrección y prompt sugerido, y mide el progreso contra un reporte anterior. Úsala cuando el usuario pida revisar, depurar o encontrar bugs en una app React/Vite, preparar la entrega de un ejercicio de depuración, o comprobar que sus correcciones resolvieron los errores.
---

# react-bug-hunter

Detecta errores frecuentes en apps React + Vite, explica cada uno y guía su
corrección hasta verificar que quedaron resueltos.

## Cuándo usarla

- «Revisa mi app React», «¿qué bugs tiene mi tienda?», «ayúdame a depurar».
- Ejercicios de depuración con N errores que hay que documentar.
- Después de corregir, para confirmar el progreso («¿ya quedó todo?»).

**No la uses** para proyectos que no son JavaScript/React (el script avisa si
no encuentra `react` en `package.json`) ni como sustituto de pruebas en el
navegador.

## Requisitos

- Python 3.8+ (solo biblioteca estándar, sin `pip install`).
- El proyecto a auditar: carpeta raíz con `package.json`, `index.html` y `src/`.

## Flujo

Sigue estos pasos en orden. `<skill>` es la carpeta de esta skill.

1. **Auditar y guardar el estado inicial**

   ```bash
   python3 <skill>/scripts/audit.py <proyecto> --out reporte-antes
   ```

   Genera `reporte.json`, `reporte.md` y `reporte.html` con las plantillas de
   `assets/`. Las reglas están en `assets/rules.json`.

2. **Interpretar la salida** según el código de salida:
   - `0` sin hallazgos · `1` hay hallazgos (continúa al paso 3).
   - `2` ruta inválida · `3` sin código analizable · `4` baseline inválido ·
     `5` falta un asset de la skill. En estos casos muestra al usuario el
     mensaje y la **Sugerencia** que imprime el script y detente.

3. **Explicar los hallazgos.** Resume la tabla al usuario agrupando por
   categoría. Para cada regla abre la sección correspondiente de
   `references/catalogo-reglas.md` (el campo `ref` del JSON es el ancla) y
   explica el síntoma con un ejemplo que el usuario pueda reproducir.

4. **Corregir** (solo si el usuario lo pide). Sigue el orden y las reglas de
   `references/flujo-correccion.md`: un cambio por hallazgo, respetando el
   estilo del proyecto. Si crees que un hallazgo es falso positivo, dilo y no
   cambies el código.

5. **Verificar el progreso**

   ```bash
   python3 <skill>/scripts/audit.py <proyecto> --out reporte-despues \
     --baseline reporte-antes/reporte.json
   ```

   Debe mostrar `N resueltos · 0 nuevos`. Si hay nuevos, revisa la última
   corrección. Luego ejecuta `npm run build` en el proyecto si es posible.

6. **Entregar.** Indica al usuario que `reporte-antes/reporte.md` ya tiene un
   bloque por error (síntoma, archivo:línea, corrección, prompt sugerido) y
   que debe completar «¿Tuviste que corregir el prompt?» con su experiencia.
   Recomienda la prueba manual de la tabla en `references/flujo-correccion.md`.

## Opciones útiles

| Opción | Efecto |
|---|---|
| `--format json\|md\|html\|all\|none` | Qué reportes escribir (por defecto `all`) |
| `--baseline FILE` | Compara con un `reporte.json` anterior |
| `--fail-on error\|warning\|info\|never` | Severidad que produce salida 1 (útil en CI) |
| `--exclude CARPETA` | Ignora una carpeta extra (repetible) |
| `--quiet` | Sin resumen en consola |

## Archivos

- `scripts/audit.py` — CLI: valida la entrada, recorre archivos, arma el reporte.
- `scripts/checks.py` — detectores (regex para JS/JSX, parser CSS, contraste WCAG).
- `scripts/report.py` — renderiza las plantillas y compara con el baseline.
- `scripts/install.sh` — instala la skill para Claude Code o Codex.
- `scripts/demo.sh` — demostración completa (caso exitoso + errores).
- `assets/rules.json` — catálogo de reglas: severidad, síntoma, corrección, prompt.
- `assets/report_template.md`, `assets/report_template.html` — plantillas de reporte.
- `references/catalogo-reglas.md` — explicación y código ❌/✅ de cada regla.
- `references/flujo-correccion.md` — orden de corrección, verificación y formato de entrega.
