# react-bug-hunter 🔎

Una skill para agentes de IA (Claude Code o Codex) que **audita proyectos
React + Vite**. Detecta errores de lógica, de datos/API y visuales, explica
cada uno, genera un reporte listo para entregar y **mide el progreso** después
de corregir.

> Ejemplo real: en la tienda de este repositorio (`Tarea_skill`) encuentra
> 13 problemas en 3 archivos, entre ellos los 10 errores del ejercicio, con el archivo
> y la línea exactos.

---

## 1. ¿Para qué sirve y cuándo usarla?

| Úsala cuando… | No la uses cuando… |
|---|---|
| Quieras saber qué bugs tiene una app React/Vite | El proyecto no es JavaScript/React |
| Tengas un ejercicio de depuración y debas documentar cada error | Necesites pruebas en tiempo de ejecución (no ejecuta la app) |
| Hayas corregido y quieras comprobar qué quedó resuelto | |

Qué detecta (14 reglas, en `assets/rules.json`):

| Categoría | Reglas |
|---|---|
| **Lógica** | R01 estado mutado · R02 setState con misma referencia · R03 cantidad negativa · R04 borrar por campo no único · R06 búsqueda sensible a mayúsculas · R10 `key={index}` |
| **Datos / API** | R05 porcentaje usado como dinero · R07 `fetch` sin `.catch` · R08 sin `res.ok` · R09 `useEffect` sin `AbortController` |
| **Visual** | C01 `z-index` negativo · C02 imagen que desborda la grid · C03 contraste WCAG < 4.5:1 · H01 falta `meta viewport` |

---

## 2. Requisitos

- **Python 3.8 o superior**. Solo usa la biblioteca estándar, así que no hace falta `pip install`.
- Bash, para `install.sh` y `demo.sh`. En Windows usa Git Bash o WSL; `audit.py` también funciona directo con `python`.
- Opcional: Claude Code o Codex para usarla como skill. El script también se puede ejecutar solo.

Comprueba tu versión:

```bash
python3 --version
```

---

## 3. Instalación

```bash
git clone https://github.com/alanmcv/Tarea_skill.git
cd Tarea_skill/skills/react-bug-hunter

# Opción A: instalar para Claude Code (todas tus sesiones)
scripts/install.sh                     # → ~/.claude/skills/react-bug-hunter

# Opción B: solo para un proyecto
scripts/install.sh --scope project --project ~/mi-app   # → ~/mi-app/.claude/skills/

# Opción C: para Codex
scripts/install.sh --agent codex       # → ~/.codex/skills/react-bug-hunter
```

Con eso el agente ve la skill. Pruébala escribiendo en Claude Code: *«revisa
los bugs de mi app React»*.

**Sin instalar nada**, el script también funciona directo:

```bash
python3 scripts/audit.py /ruta/a/tu/proyecto
```

---

## 4. Uso

```bash
python3 scripts/audit.py PROYECTO [opciones]
```

| Opción | Descripción | Por defecto |
|---|---|---|
| `--out DIR` | Carpeta donde se escriben los reportes | `reporte-bugs` |
| `--format` | `all`, `json`, `md`, `html` o `none` | `all` |
| `--baseline FILE` | `reporte.json` anterior para comparar | — |
| `--fail-on` | `error`, `warning`, `info` o `never` | `error` |
| `--exclude CARPETA` | Carpeta extra a ignorar (se puede repetir) | — |
| `--quiet` | No imprimir el resumen | — |

Siempre se ignoran `node_modules`, `dist`, `build`, `.git`, las carpetas ocultas y `fixtures`.

### Códigos de salida

| Código | Significado | Qué hacer |
|---|---|---|
| `0` | Sin hallazgos (según `--fail-on`) | Nada 🎉 |
| `1` | Hay hallazgos | Revisa el reporte |
| `2` | La ruta no existe o es un archivo | Pasa la carpeta raíz del proyecto |
| `3` | No hay archivos `.js/.jsx/.ts/.tsx/.css` ni `index.html` | Verifica que sea la carpeta correcta |
| `4` | `--baseline` no existe o no es JSON válido | Usa un `reporte.json` generado por la skill |
| `5` | Falta o está dañado un archivo de `assets/` | Reinstala la skill |

Todos los errores muestran un mensaje en español y una **Sugerencia**.

---

## 5. Ejemplo de entrada y resultado esperado

**Entrada:** la tienda de este repositorio.

```bash
cd Tarea_skill
python3 skills/react-bug-hunter/scripts/audit.py . --out reporte-antes
```

**Salida esperada (consola):**

```
🔎 react-bug-hunter · Tarea_skill
   6 archivos analizados · 13 hallazgos · puntaje 25/100

   1. error   C02  src/App.css:65   Imagen con ancho fijo que desborda
   2. error   C03  src/App.css:89   Contraste de texto insuficiente
   3. error   C01  src/App.css:106  z-index negativo en panel posicionado
   4. error   R07  src/App.jsx:23   fetch sin manejo de errores
   5. error   R01  src/App.jsx:32   Mutación directa del estado
   6. error   R02  src/App.jsx:33   setState con la misma referencia
   7. error   R03  src/App.jsx:38   Cantidad sin límite inferior
   8. error   R04  src/App.jsx:44   Eliminación por campo no único
   9. error   R05  src/App.jsx:53   Porcentaje usado como monto
  10. warning H01  index.html:3    Falta meta viewport
  11. warning R08  src/App.jsx:23   Respuesta HTTP sin verificar
  12. warning R09  src/App.jsx:23   Efecto con fetch sin cancelación
  13. warning R06  src/App.jsx:59   Búsqueda sensible a mayúsculas

   Reportes generados:
   → reporte-antes/reporte.json
   → reporte-antes/reporte.md
   → reporte-antes/reporte.html
```

Además se crean tres archivos:

- `reporte.html`: reporte visual con puntaje, filtros por categoría y una tarjeta por error.
- `reporte.md`: un bloque por error con **síntoma, archivo y línea, corrección y prompt sugerido**, en el mismo formato que pide la entrega.
- `reporte.json`: datos para otras herramientas o para usarlo como `--baseline`.

**Después de corregir:**

```bash
python3 skills/react-bug-hunter/scripts/audit.py . --out reporte-despues \
  --baseline reporte-antes/reporte.json
```

```
   0 hallazgos · puntaje 100/100
   Progreso: 13 resueltos · 0 nuevos · 0 persisten
```

---

## 6. Flujo completo con el agente

`SKILL.md` define el flujo que sigue la IA:

1. **Auditar** con `scripts/audit.py`. Guarda el reporte inicial.
2. **Interpretar** el código de salida. Ante los códigos 2 a 5, muestra el error y se detiene.
3. **Explicar** cada hallazgo con `references/catalogo-reglas.md`, que tiene código ❌/✅ y cómo probarlo.
4. **Corregir** en el orden de `references/flujo-correccion.md` (primero API, luego estado, cálculos y al final los visuales).
5. **Verificar** con `--baseline`: debe mostrar `N resueltos · 0 nuevos`.
6. **Entregar** usando el `reporte.md`, que ya tiene la plantilla de cada error.

---

## 7. Pruebas y demostración

```bash
cd skills/react-bug-hunter

# 15 pruebas automáticas (casos exitosos y entradas inválidas)
python3 -m unittest discover -s tests -v

# Demostración completa para la presentación
scripts/demo.sh
```

`demo.sh` ejecuta, en orden:

1. ✅ Auditoría de la app con errores: 13 hallazgos, código 1.
2. ✅ Auditoría de la app corregida comparada con la anterior: 13 resueltos, código 0.
3. ❌ Una ruta que no existe: código 2.
4. ❌ Un archivo en vez de una carpeta: código 2.
5. ❌ Una carpeta sin código: código 3.
6. ❌ Un baseline con JSON roto: código 4.

Las capturas de cada caso están en [`evidencias/`](evidencias/):

| Captura | Qué muestra |
|---|---|
| `01-auditoria-exitosa.png` | Salida en consola sobre la tienda |
| `02-reporte-html.png` | Reporte HTML generado |
| `03-progreso-baseline.png` | 13 resueltos después de corregir |
| `04-errores-entrada.png` | Las cuatro entradas inválidas y sus mensajes |
| `05-pruebas-unitarias.png` | Las 15 pruebas pasando |

Para regenerarlas hace falta Chromium o Chrome:

```bash
CHROME=/ruta/a/chromium python3 tests/generar_capturas.py
```

---

## 8. Estructura

```
react-bug-hunter/
├── SKILL.md                    # Instrucciones para el agente (cuándo y cómo usarla)
├── README.md                   # Este documento
├── scripts/
│   ├── audit.py                # CLI principal: validación, recorrido, reportes
│   ├── checks.py               # 11 detectores (regex JS/JSX, parser CSS, WCAG)
│   ├── report.py               # Render de plantillas + comparación con baseline
│   ├── install.sh              # Instalador para Claude Code / Codex
│   └── demo.sh                 # Demostración de principio a fin
├── assets/
│   ├── rules.json              # Catálogo de reglas (lo lee audit.py)
│   ├── report_template.md      # Plantilla del reporte Markdown (lo usa report.py)
│   └── report_template.html    # Plantilla del reporte HTML (lo usa report.py)
├── references/
│   ├── catalogo-reglas.md      # Explicación y código ❌/✅ por regla (lo lee el agente)
│   └── flujo-correccion.md     # Orden de corrección, verificación y entrega
├── tests/
│   ├── test_audit.py           # 15 pruebas con unittest
│   ├── generar_capturas.py     # Regenera las capturas de evidencias/
│   └── fixtures/               # App con errores, app corregida y entradas inválidas
└── evidencias/                 # Capturas de pantalla
```

**Cómo se usa cada carpeta:**

- `scripts/` contiene la lógica que se ejecuta.
- `assets/` guarda datos y plantillas que **consume el script**. Si falta alguno, la salida es el código 5.
- `references/` guarda conocimiento que **lee el agente** para explicar y corregir. Cada hallazgo del reporte enlaza a su sección con el campo `ref`.

---

## 9. Decisiones de diseño

1. **Solo biblioteca estándar de Python.** Cualquiera la instala copiando una carpeta, sin `npm` ni `pip`. El proyecto auditado puede ni siquiera tener `node_modules`.
2. **Las reglas son datos y no código.** Los textos (síntoma, corrección, prompt) viven en `rules.json`, así que se pueden mejorar o traducir sin tocar Python. Los detectores solo devuelven la regla, el archivo, la línea y el detalle.
3. **Análisis estático en lugar de ejecutar la app.** Es rápido, funciona sin internet y es reproducible. Como contrapartida puede haber falsos positivos, y por eso el flujo pide confirmarlos en el navegador (ver «Limitaciones» en `catalogo-reglas.md`).
4. **Contraste WCAG calculado de verdad.** C03 usa la fórmula oficial de luminancia relativa, no una lista de colores prohibidos. Por eso detectó que `#fff` sobre `#4a90d9` (3.34:1) tampoco cumple, y la versión corregida usa `#2a6fb8` (5.17:1).
5. **Huellas para el baseline.** Cada hallazgo tiene un hash de regla + archivo + código normalizado, así que la comparación funciona aunque cambien los números de línea.
6. **Códigos de salida distintos** para cada tipo de fallo. Así se puede usar en CI (`--fail-on warning`) y el agente sabe si continuar o detenerse.
7. **Salida en español orientada a la entrega.** El `reporte.md` reproduce el formato que pide el ejercicio (síntoma, archivo, línea, corrección y prompt) para que el estudiante complete lo que falta con su experiencia real.

---

## 10. Guion sugerido para la presentación (5 min)

1. **Problema (30 s).** Depurar a mano una app con 10 errores ocultos es lento
   y además hay que documentar cada uno. La skill automatiza la detección y
   prepara la documentación.
2. **Estructura (1 min).** Abrir `SKILL.md` y mostrar el `description` (cuándo
   se activa) y el flujo de 6 pasos. Luego explicar qué va en `scripts/`,
   `assets/` y `references/`.
3. **Demo del caso exitoso (1.5 min).** Ejecutar
   `python3 skills/react-bug-hunter/scripts/audit.py .` en la raíz del repo y
   abrir `reporte-bugs/reporte.html`. Filtrar por «Visual» y mostrar el cálculo
   del contraste.
4. **Progreso (30 s).** Ejecutar `scripts/demo.sh` y señalar el paso 2:
   `13 resueltos · 0 nuevos`.
5. **Errores (1 min).** En la misma demo, mostrar los pasos 3 a 6, cada uno
   con su mensaje, su sugerencia y un código de salida distinto.
6. **Decisiones (30 s).** Resumir la sección 9: sin dependencias, reglas como
   datos, análisis estático con limitaciones documentadas.
