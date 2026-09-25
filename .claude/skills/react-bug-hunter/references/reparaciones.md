# Reparaciones automáticas (`fix.py`)

Esta guía explica **qué cambia** cada reparador de `scripts/fixers.py` y
**por qué es seguro**. Léela cuando el usuario pregunte cómo se corrigió
algo o cuando una reparación quede pendiente (✋).

## Garantías de seguridad

1. **Vista previa por defecto.** Sin `--apply` no se escribe nada: solo se
   generan `cambios.diff`, `fix.html` y `ENTREGA.md`.
2. **Verificación después de cada cambio.** Tras aplicar un reparador en
   memoria, `fix.py` vuelve a auditar el proyecto. El cambio **se acepta
   solo si**:
   - el hallazgo reparado desaparece, **y**
   - no aumenta ningún otro hallazgo (ninguna regresión).

   Si no se cumple, el cambio se descarta y el hallazgo queda como pendiente
   manual con el motivo «la reparación no pasó la verificación».
3. **Copia de seguridad.** Con `--apply`, los archivos originales se guardan
   en `.rbh-backup/<fecha>/` antes de escribir. `--undo` restaura la última
   copia byte a byte.
4. **Build.** Con `--verify-build` se ejecuta `npm run build`. Si falla, se
   restaura la copia automáticamente (código de salida 6).
5. **Formato respetado.** Se conserva la indentación de cada línea y los
   finales de línea (LF o CRLF de Windows).
6. **Orden.** Primero la cadena de `fetch` (R08 → R09 → R07), luego estado,
   cálculos y visuales. Así el `.catch` final ya ignora el `AbortError`.

## Qué hace cada reparador

| Regla | Antes | Después | Cuándo NO repara (queda ✋) |
|---|---|---|---|
| R01 | `cart.push(x)` + `setCart(cart)` | `setCart(prev => …)` inmutable. Si `x` es `{ ...p, quantity: 1 }`, suma cantidad cuando el producto ya existe | Mutadores distintos de `push` (`splice`, `sort`…) o en varias líneas |
| R02 | `setX(x)` | `setX([...x])` o `setX({ ...x })` según el `useState` inicial | — |
| R03 | `item.quantity + delta` | `Math.max(1, item.quantity + delta)` | — |
| R04 | `c.category !== item.category` | `c.id !== item.id` | Comparación con otra forma |
| R05 | `price - discountPercentage` | `price * (1 - discountPercentage / 100)` | El porcentaje se suma o aparece en otra forma |
| R06 | `title.includes(search)` | `title.toLowerCase().includes(search.trim().toLowerCase())` | — |
| R07 | cadena `fetch().then()` sin `.catch` | agrega `.catch` (ignora `AbortError`) y `.finally(() => setLoading(false))` si existe un estado de carga | `async/await` sin cadena `.then` |
| R08 | `.then((res) => res.json())` | revisa `res.ok` y lanza `Error('HTTP 404')` | Otra forma de leer la respuesta |
| R09 | `useEffect` con `fetch(url)` | `AbortController`, `{ signal }` y `return () => controller.abort()` | El efecto ya tiene cleanup |
| R10 | `key={index}` | `key={item.id}` usando la variable del `map` | No se encuentra el `map(item, index)` |
| C01 | `z-index: -1` | `z-index: 10` | — |
| C02 | `width: 300px` en `img` | `width: 100%` | — |
| C03 | texto con contraste < 4.5:1 | texto `#fff` (o `#111` en fondos claros); si hace falta, **oscurece el fondo manteniendo el tono** hasta llegar a 4.5:1 | No hay `background` en la misma regla |
| H01 | sin viewport | inserta `<meta name="viewport" …>` tras `<meta charset>` | No hay `<head>` |

## Ejemplo real (tienda de este repositorio)

```
✔  1. R08  src/App.jsx:23   Respuesta HTTP sin verificar
✔  2. R09  src/App.jsx:23   Efecto con fetch sin cancelación
✔  3. R07  src/App.jsx:23   fetch sin manejo de errores
✔  4. R01  src/App.jsx:32   Mutación directa del estado (+ R02)
...
13/13 hallazgos resueltos con 12 reparaciones · 0 pendientes · 3 archivos
Puntaje: 25/100 → 100/100
```

`(+ R02)` indica que la reparación de R01 también resolvió R02, porque
elimina el `setCart(cart)` que venía después del `push`.

## Cuando algo queda pendiente

1. Lee el **motivo** en la salida o en `reporte-fix/resumen.json`.
2. Busca la regla en `catalogo-reglas.md` y aplica el ejemplo ✅ a mano.
3. Vuelve a ejecutar `audit.py --baseline` para confirmar.
