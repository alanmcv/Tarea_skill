# Catálogo de reglas de react-bug-hunter

Cada regla corresponde a un `id` de `assets/rules.json`. Los reportes enlazan
aquí con `references/catalogo-reglas.md#<ancla>`. Úsalo para **explicar** el
error al estudiante y para **aplicar** la corrección correcta.

Categorías: **lógica**, **datos / API**, **visual**.

---

<a id="r01-mutacion-directa-del-estado"></a>
## R01 · Mutación directa del estado (lógica, error)

React decide si vuelve a renderizar comparando la referencia nueva con la
anterior (`Object.is`). `push`, `splice`, `sort` o `x[0] = ...` cambian el
contenido pero **no** la referencia.

```jsx
// ❌ Mal
cart.push({ ...product, quantity: 1 })
setCart(cart)

// ✅ Bien (además suma cantidad si ya existe)
setCart((prev) => {
  const found = prev.find((i) => i.id === product.id)
  if (found) {
    return prev.map((i) =>
      i.id === product.id ? { ...i, quantity: i.quantity + 1 } : i
    )
  }
  return [...prev, { ...product, quantity: 1 }]
})
```

**Cómo probarlo:** agrega un producto y comprueba que el contador del
carrito sube de inmediato. Agrega el mismo dos veces: debe quedar una fila
con cantidad 2 (sin advertencia de keys duplicadas en consola).

<a id="r02-setstate-con-la-misma-referencia"></a>
## R02 · setState con la misma referencia (lógica, error)

Casi siempre aparece junto a R01. `setCart(cart)` después de mutar `cart`
no hace nada. Corrige ambas líneas a la vez con la forma funcional
`setCart(prev => ...)`.

<a id="r03-cantidad-sin-limite-inferior"></a>
## R03 · Cantidad sin límite inferior (lógica, error)

```jsx
// ❌ Mal: con delta = -1 puede llegar a 0, -1, -2...
{ ...item, quantity: item.quantity + delta }

// ✅ Opción A: mínimo 1
{ ...item, quantity: Math.max(1, item.quantity + delta) }

// ✅ Opción B: quitar el producto al llegar a 0
setCart((prev) =>
  prev
    .map((i) => (i.id === id ? { ...i, quantity: i.quantity + delta } : i))
    .filter((i) => i.quantity > 0)
)
```

Prefiere identificar el ítem por `id` en vez de por índice.

<a id="r04-eliminacion-por-campo-no-unico"></a>
## R04 · Eliminación por campo no único (lógica, error)

```jsx
// ❌ Mal: borra todos los productos de la misma categoría
cart.filter((c) => c.category !== item.category)

// ✅ Bien
cart.filter((c) => c.id !== item.id)
```

**Cómo probarlo:** agrega dos productos de la misma categoría y elimina
uno; el otro debe seguir en el carrito.

<a id="r05-porcentaje-usado-como-monto"></a>
## R05 · Porcentaje usado como monto (datos / API, error)

En DummyJSON `discountPercentage` es un **porcentaje** (ej. `12.96`), no
dólares. Restarlo al precio da un total incorrecto.

```js
// ❌ Mal
sum + (item.price - item.discountPercentage) * item.quantity

// ✅ Si la UI muestra el precio original (lo más coherente):
sum + item.price * item.quantity

// ✅ Si se quiere aplicar el descuento, mostrarlo también en la UI:
sum + item.price * (1 - item.discountPercentage / 100) * item.quantity
```

**Cómo probarlo:** agrega dos productos, suma a mano los precios que ves y
compáralo con el total del carrito.

<a id="r06-busqueda-sensible-a-mayusculas"></a>
## R06 · Búsqueda sensible a mayúsculas (lógica, advertencia)

La API `/products/search?q=` ya filtra sin distinguir mayúsculas. Un
segundo filtro local con `includes` sin normalizar **descarta** resultados
válidos (`"phone"` no coincide con `"iPhone"`).

```js
const term = search.trim().toLowerCase()
products.filter((p) => p.title.toLowerCase().includes(term))
```

<a id="r07-fetch-sin-manejo-de-errores"></a>
## R07 · fetch sin manejo de errores (datos / API, error)

Sin `.catch`, un fallo de red deja `loading` en `true` para siempre.

```js
fetch(url, { signal: controller.signal })
  .then((res) => {
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return res.json()
  })
  .then((data) => setProducts(data.products ?? []))
  .catch((err) => {
    if (err.name !== 'AbortError') setError(err.message)
  })
  .finally(() => setLoading(false))
```

Muestra el error en la UI: `{error && <p className="error">{error}</p>}`.

**Cómo probarlo:** en DevTools → Network marca «Offline» y recarga; debe
aparecer el mensaje de error y desaparecer «Cargando...».

<a id="r08-respuesta-http-sin-verificar"></a>
## R08 · Respuesta HTTP sin verificar (datos / API, advertencia)

`fetch` **no** rechaza la promesa con un 404 o 500. Hay que revisar
`res.ok` (ver el ejemplo de R07). Protege también el acceso a datos con
`data.products ?? []`.

<a id="r09-efecto-con-fetch-sin-cancelacion"></a>
## R09 · Efecto con fetch sin cancelación (datos / API, advertencia)

Cada tecla en el buscador dispara un `fetch`. Si una respuesta antigua
llega tarde, sobrescribe los resultados nuevos (condición de carrera).

```js
useEffect(() => {
  const controller = new AbortController()
  fetch(url, { signal: controller.signal }) /* ... */
  return () => controller.abort()
}, [search])
```

<a id="r10-key-con-el-indice-del-arreglo"></a>
## R10 · key con el índice del arreglo (lógica, advertencia)

`key={index}` hace que React confunda filas al borrar o reordenar. Usa
`key={item.id}`. Si hay ids repetidos, el problema real suele ser R01
(elementos duplicados en el estado).

<a id="c01-z-index-negativo-en-panel-posicionado"></a>
## C01 · z-index negativo en panel posicionado (visual, error)

Un panel `position: fixed` con `z-index: -1` se dibuja **detrás** del
`body`: el botón «Carrito» parece no hacer nada.

```css
.cart { position: fixed; z-index: 10; }
```

<a id="c02-imagen-con-ancho-fijo-que-desborda"></a>
## C02 · Imagen con ancho fijo que desborda (visual, error)

Si la grid usa `minmax(240px, 1fr)`, una imagen de `300px` se sale de la
tarjeta cuando la columna mide menos de 300px.

```css
.card img { width: 100%; height: 200px; object-fit: contain; }
```

**Cómo probarlo:** reduce el ancho de la ventana o usa el modo
responsive de DevTools (360px).

<a id="c03-contraste-de-texto-insuficiente"></a>
## C03 · Contraste de texto insuficiente (visual, error)

La skill calcula la relación de contraste WCAG 2.1:
`(L1 + 0.05) / (L2 + 0.05)` con la luminancia relativa de cada color.
El mínimo para texto normal (nivel AA) es **4.5:1**.

| Texto | Fondo | Contraste | Resultado |
|---|---|---|---|
| `#5a9ae0` | `#4a90d9` | 1.14:1 | ❌ ilegible |
| `#fff` | `#4a90d9` | 3.34:1 | ❌ no cumple AA |
| `#fff` | `#2a6fb8` | 5.17:1 | ✅ cumple AA |

<a id="h01-falta-meta-viewport"></a>
## H01 · Falta meta viewport (visual, advertencia)

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
```

Sin ella los móviles renderizan a ~980px y reducen la página.

---

## Limitaciones conocidas

- El análisis es **estático** (expresiones regulares y un parser CSS
  simple): no ejecuta la app. Puede haber falsos positivos (por ejemplo
  `x.push` sobre una copia local con el mismo nombre que el estado) y
  falsos negativos (errores que dependen de datos en tiempo de ejecución).
- El contraste solo se evalúa cuando `color` y `background` están en la
  **misma regla** CSS.
- Siempre confirma cada hallazgo en el navegador antes de corregirlo.
