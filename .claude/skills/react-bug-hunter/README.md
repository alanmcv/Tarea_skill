# react-bug-hunter 🔎🛠

Skill para **Claude Code** (VS Code o terminal) que **detecta y repara
automáticamente** errores en apps React + Vite. También deja lista la
documentación de entrega.

```
/react-bug-hunter            → audita y explica cada error
/react-bug-hunter reparar    → repara todo con verificación, backup y build
/react-bug-hunter deshacer   → vuelve al estado anterior
/react-bug-hunter demo       → demostración completa (no toca tu proyecto)
```

> Resultado real en la tienda de este repositorio: **13 hallazgos → 13
> resueltos**, puntaje **25 → 100**, `npm run build` ✅, en un solo comando.

---

## 1. ¿Qué hace y cuándo usarla?

| Úsala cuando… | No la uses cuando… |
|---|---|
| Quieras saber qué bugs tiene una app React/Vite | El proyecto no es JavaScript/React |
| Quieras **corregirlos automáticamente** sin romper nada | Necesites pruebas de extremo a extremo en el navegador |
| Tengas que documentar cada error para una entrega | |
| Quieras comprobar que tus correcciones funcionaron | |

### Las 4 etapas

| Etapa | Qué hace | Script |
|---|---|---|
| 🔎 **Detectar** | 14 reglas en 3 categorías, con archivo y línea exactos | `audit.py` |
| 🛠 **Reparar** | 14 reparadores. Cada cambio se vuelve a auditar y se descarta si no resuelve el hallazgo o si crea otro problema | `fix.py` |
| ✅ **Verificar** | Copia de seguridad, `npm run build` con reversión automática si falla, y comparación con el reporte inicial (baseline) | `fix.py`, `audit.py --baseline` |
| 📄 **Documentar** | `ENTREGA.md` con síntoma, archivo:línea original, diff antes/después y prompt de cada error, más reportes HTML | `fix.py` |

### Reglas

| Categoría | Reglas |
|---|---|
| **Lógica** | R01 estado mutado · R02 setState con la misma referencia · R03 cantidad negativa · R04 eliminar por campo no único · R06 búsqueda sensible a mayúsculas · R10 `key={index}` |
| **Datos / API** | R05 porcentaje usado como dinero · R07 `fetch` sin `.catch` · R08 sin revisar `res.ok` · R09 `useEffect` sin `AbortController` |
| **Visual** | C01 `z-index` negativo · C02 imagen que desborda la grid · C03 contraste WCAG < 4.5:1 (calculado con la fórmula oficial) · H01 falta `meta viewport` |

---

## 2. Requisitos

- **Python 3.8 o superior**. Solo usa la biblioteca estándar, así que no hace falta `pip install`.
  - Windows: instálalo desde python.org y marca «Add to PATH». El comando puede ser `python` o `py`.
- **VS Code con la extensión Claude Code** (o `claude` en la terminal), para usar `/react-bug-hunter`.
- Opcional: Node + `npm i` en el proyecto, para que `--verify-build` ejecute `npm run build`.

Comprueba tu versión:

```bash
python3 --version     # Windows: python --version
```

---

## 3. Instalación

### Opción A: ya está instalada en este repositorio ✅

La skill vive en `.claude/skills/react-bug-hunter/`. Claude Code carga
**automáticamente** las skills de esa carpeta, así que alcanza con clonar el repo y
abrirlo en VS Code:

```bash
git clone https://github.com/alanmcv/Tarea_skill.git
cd Tarea_skill
npm i          # opcional: permite verificar el build
code .
```

Luego abre el panel de **Claude Code** en VS Code, escribe `/` y elige
**react-bug-hunter**, o escribe directamente `/react-bug-hunter`.

### Opción B: usarla en cualquier otro proyecto

```bash
# Para todos tus proyectos (~/.claude/skills/react-bug-hunter)
python3 .claude/skills/react-bug-hunter/scripts/install.py

# Solo en un proyecto concreto (RUTA/.claude/skills/react-bug-hunter)
python3 .claude/skills/react-bug-hunter/scripts/install.py --project RUTA

# Para Codex
python3 .claude/skills/react-bug-hunter/scripts/install.py --agent codex
```

> Si `/react-bug-hunter` no aparece en el chat, recarga la ventana de VS Code
> (`Ctrl+Shift+P` → «Developer: Reload Window»), o abre una conversación nueva.

### Opción C: sin Claude, solo con los scripts

```bash
python3 .claude/skills/react-bug-hunter/scripts/audit.py RUTA_PROYECTO
python3 .claude/skills/react-bug-hunter/scripts/fix.py RUTA_PROYECTO --apply
```

---

## 4. Uso desde el chat (VS Code)

| Escribes | Qué hace Claude |
|---|---|
| `/react-bug-hunter` | Audita el proyecto abierto, explica cada error agrupado por categoría y ofrece repararlos |
| `/react-bug-hunter reparar` | Muestra la vista previa, aplica con copia de seguridad, ejecuta `npm run build`, verifica con el baseline y resume el antes/después |
| `/react-bug-hunter deshacer` | Restaura los archivos originales |
| `/react-bug-hunter demo` | Ejecuta la demostración completa sobre una copia temporal |
| `/react-bug-hunter auditar ../otra-app` | Audita otra carpeta |

También se activa sola si escribes, por ejemplo, *«encuentra los bugs de
mi tienda React»*.

---

## 5. Uso por consola

### `audit.py` (detectar)

```bash
python3 scripts/audit.py PROYECTO [--out DIR] [--format all|json|md|html|none]
                         [--baseline reporte.json] [--fail-on error|warning|info|never]
                         [--exclude CARPETA] [--quiet]
```

### `fix.py` (reparar)

```bash
python3 scripts/fix.py PROYECTO                     # vista previa, no modifica nada
python3 scripts/fix.py PROYECTO --apply             # aplica con copia en .rbh-backup/
python3 scripts/fix.py PROYECTO --apply --verify-build   # + npm run build (revierte si falla)
python3 scripts/fix.py PROYECTO --only R01,C03      # solo algunas reglas
python3 scripts/fix.py PROYECTO --show-diff         # imprime el diff completo
python3 scripts/fix.py PROYECTO --undo              # restaura la última copia
```

### Códigos de salida

| Código | Significado | Qué hacer |
|---|---|---|
| `0` | Todo bien (sin hallazgos o todo reparado) | 🎉 |
| `1` | Hay hallazgos o pendientes manuales | Revisa el reporte |
| `2` | Ruta inválida o regla desconocida en `--only` | Pasa la carpeta raíz o una regla válida |
| `3` | No hay archivos de código | Revisa que la carpeta sea la correcta |
| `4` | `--baseline` no existe o no es JSON válido | Usa un `reporte.json` generado por la skill |
| `5` | Falta o está dañado un archivo de `assets/` | Reinstala la skill |
| `6` | El build falló después de reparar, **cambios revertidos** | Revisa el error de build mostrado |
| `7` | `--undo` sin copias de seguridad | Nada que deshacer |

Todos los errores muestran un mensaje en español y una **Sugerencia**.

---

## 6. Ejemplo de entrada y resultado esperado

**Entrada:** la tienda de este repositorio, que tiene 10 errores del ejercicio.

```
/react-bug-hunter reparar
```

que ejecuta, entre otros:

```bash
python3 .claude/skills/react-bug-hunter/scripts/fix.py . --apply --verify-build
```

**Salida esperada:**

```
🛠  react-bug-hunter · reparación · Tarea_skill
   modo: APLICAR

  ✔  1. R08  src/App.jsx:23   Respuesta HTTP sin verificar
  ✔  2. R09  src/App.jsx:23   Efecto con fetch sin cancelación
  ✔  3. R07  src/App.jsx:23   fetch sin manejo de errores
  ✔  4. R01  src/App.jsx:32   Mutación directa del estado (+ R02)
  ✔  5. R03  src/App.jsx:38   Cantidad sin límite inferior
  ✔  6. R04  src/App.jsx:44   Eliminación por campo no único
  ✔  7. R05  src/App.jsx:53   Porcentaje usado como monto
  ✔  8. R06  src/App.jsx:59   Búsqueda sensible a mayúsculas
  ✔  9. C01  src/App.css:106  z-index negativo en panel posicionado
  ✔ 10. C02  src/App.css:65   Imagen con ancho fijo que desborda
  ✔ 11. C03  src/App.css:89   Contraste de texto insuficiente
  ✔ 12. H01  index.html:3    Falta meta viewport

   13/13 hallazgos resueltos con 12 reparaciones · 0 pendientes · 3 archivos · +30 −12 líneas
   Puntaje: 25/100 → 100/100

   💾 Copia de seguridad: .rbh-backup/20260925-195254 (deshacer con --undo)
   🔨 Ejecutando npm run build...
   ✔ El build pasa con los cambios.

   Reportes generados:
   → reporte-fix/fix.html        (diff coloreado de cada reparación)
   → reporte-fix/ENTREGA.md      (documento de entrega)
   → reporte-fix/cambios.diff    (parche completo)
   → reporte-fix/resumen.json
```

Ejemplo de un bloque de `ENTREGA.md`:

````markdown
### Error 4: Mutación directa del estado (`R01`)
- **Qué pasaba (síntoma):** Se hace clic en «Agregar» y la interfaz no cambia…
- **Archivo y línea:** `src/App.jsx:32`
- **Código original:** `cart.push({ ...product, quantity: 1 })`
- **Cómo se corrigió:** Se reemplazó cart.push + setCart(cart) por una actualización
  inmutable… (También resolvió: R02.)
- **Prompt sugerido para la IA:** "En src/App.jsx línea 32 tengo…"
- **¿Tuviste que corregir el prompt?:** _(completar)_

```diff
-    cart.push({ ...product, quantity: 1 })
-    setCart(cart)
+    setCart((prev) => {
+      const found = prev.find((i) => i.id === product.id)
...
```
````

---

## 7. Pruebas, manejo de errores y demostración

```bash
cd .claude/skills/react-bug-hunter
python3 -m unittest discover -s tests -v    # 29 pruebas
python3 scripts/demo.py                     # demo completa (añade --pausa para ir paso a paso)
```

**Pruebas (29):**

- Detección: encuentra los 13 hallazgos con su línea exacta, la app corregida da 0 y el baseline funciona.
- Reparación: la vista previa no toca nada, `--apply` resuelve 13 de 13 y el código resultante es el esperado. Además es idempotente, respeta los finales de línea CRLF de Windows y acepta `--only`.
- Seguridad: si el build falla se revierte todo, `--undo` restaura byte a byte, y lo que no se puede reparar queda pendiente con su motivo.
- Entradas inválidas: ruta inexistente, archivo en vez de carpeta, carpeta sin código, JSON roto, regla desconocida y `--undo` sin copias.

**`demo.py`** ejecuta 11 pasos y termina con una tabla *esperado vs
obtenido*. Todos los pasos dan ✔.

### Capturas ([`evidencias/`](evidencias/))

| Captura | Qué muestra |
|---|---|
| `01-auditoria-consola.png` | Auditoría de la tienda: 13 hallazgos |
| `02-reporte-html.png` | Reporte HTML interactivo con filtros |
| `03-reparacion-automatica.png` | `fix.py --apply --verify-build`: 13/13 y build ✅ |
| `04-reparaciones-html.png` | `fix.html` con el diff de cada reparación |
| `05-verificacion-baseline.png` | 13 resueltos · 0 nuevos |
| `06-errores-entrada.png` | 6 entradas inválidas con su mensaje y código |
| `07-pruebas-unitarias.png` | 29 pruebas en verde |
| `08-demo-resumen.png` | Resumen de la demo: 11/11 ✔ |

Para regenerarlas hace falta Chromium o Chrome:
`CHROME=/ruta/a/chrome python3 tests/generar_capturas.py`.

---

## 8. Estructura

```
.claude/skills/react-bug-hunter/
├── SKILL.md                    # Qué es, cuándo usarla y el flujo por modos ($ARGUMENTS)
├── README.md
├── scripts/
│   ├── audit.py                # Detectar: validación, recorrido, reportes, baseline
│   ├── checks.py               # 14 detectores (regex JS/JSX, parser CSS, WCAG)
│   ├── fix.py                  # Reparar: vista previa, verificación, backup, build, undo
│   ├── fixers.py               # 14 reparadores (uno por regla)
│   ├── report.py               # Render de plantillas y comparación con baseline
│   ├── demo.py                 # Demostración de principio a fin (multiplataforma)
│   └── install.py              # Instalador (usuario / proyecto / Codex)
├── assets/
│   ├── rules.json              # Catálogo de reglas: severidad, síntoma, corrección, prompt
│   ├── report_template.md      # Reporte de auditoría (Markdown)
│   ├── report_template.html    # Reporte de auditoría (HTML con filtros)
│   ├── fix_template.html       # Reporte de reparaciones (diffs coloreados)
│   └── entrega_template.md     # Documento de entrega
├── references/
│   ├── catalogo-reglas.md      # Explicación y código ❌/✅ de cada regla
│   ├── reparaciones.md         # Qué cambia cada reparador y por qué es seguro
│   └── flujo-correccion.md     # Orden de corrección, prueba manual y formato de entrega
├── tests/
│   ├── test_audit.py           # 15 pruebas de detección
│   ├── test_fix.py             # 14 pruebas de reparación y seguridad
│   ├── generar_capturas.py     # Regenera evidencias/
│   └── fixtures/               # App con errores, app corregida y entradas inválidas
└── evidencias/                 # 8 capturas
```

**Cómo se usa cada carpeta:**

- `scripts/` contiene el código que se ejecuta.
- `assets/` guarda los datos y plantillas que **consumen los scripts**. Si falta alguno, la salida es el código 5.
- `references/` guarda el conocimiento que **lee Claude** para explicar hallazgos y resolver los pendientes. Cada hallazgo enlaza a su sección con el campo `ref`.

---

## 9. Decisiones de diseño

1. **Detectar y además reparar.** Encontrar errores ayuda. Corregirlos de forma verificable ahorra el trabajo. La reparación usa código determinista y no la IA, así que el mismo proyecto siempre da el mismo resultado.
2. **Verificación por cambio.** Después de cada reparación se vuelve a auditar, y el cambio solo se acepta si su hallazgo baja y ningún otro sube. Por eso una reparación nunca introduce un error que la skill sepa detectar.
3. **Tres redes de seguridad.** La vista previa es el comportamiento por defecto, siempre hay copia de seguridad con `--undo`, y `npm run build` revierte los cambios si falla.
4. **Solo biblioteca estándar de Python.** Cualquiera la instala copiando una carpeta, en Windows, Mac o Linux, y el proyecto auditado no necesita dependencias.
5. **Reglas como datos.** Los textos (síntoma, corrección, prompt) viven en `rules.json`, así que se pueden editar sin tocar el código.
6. **Contraste WCAG calculado de verdad.** C03 usa la luminancia relativa oficial. Por eso detectó que `#fff` sobre `#4a90d9` (3.34:1) tampoco cumple, y el reparador oscurece el fondo manteniendo el tono hasta superar 4.5:1.
7. **Líneas originales en la entrega.** Aunque las reparaciones desplazan líneas, `ENTREGA.md` muestra la línea y el código **originales** de cada error, que es lo que pide el ejercicio.
8. **Respeta tu código.** Mantiene la indentación y los finales de línea CRLF/LF, y no reformatea archivos completos.
