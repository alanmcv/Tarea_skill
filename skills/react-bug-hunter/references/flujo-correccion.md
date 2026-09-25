# Flujo de corrección y entrega

Guía para el agente sobre **cómo corregir** los hallazgos y **cómo
documentarlos**. Léela en el paso 4 del flujo de `SKILL.md`.

## 1. Orden de corrección recomendado

Corrige de más grave a menos grave y agrupa lo que comparte causa:

1. **Datos / API** (R07, R08, R09): sin datos no se puede probar nada más.
2. **Estado** (R01 + R02 juntos, luego R03, R04): el carrito depende de ellos.
3. **Cálculos** (R05) y **búsqueda** (R06).
4. **Visuales** (C01, C02, C03, H01): cambios pequeños en CSS/HTML.

## 2. Reglas para cada corrección

- Un cambio por hallazgo; no reescribas archivos completos.
- Respeta el estilo del proyecto (en este repo: 2 espacios, comillas
  simples, sin punto y coma; ver `AGENTS.md`).
- Nunca silencies un hallazgo cambiando el nombre de una variable para
  «engañar» al detector: corrige la causa.
- Si un hallazgo es un falso positivo, explícalo al usuario y no cambies
  el código (ver «Limitaciones conocidas» en `catalogo-reglas.md`).
- Tras cada grupo de cambios ejecuta `npm run build` si el proyecto tiene
  dependencias instaladas.

## 3. Verificación

```bash
# 1) Guardar el estado inicial
python3 <skill>/scripts/audit.py <proyecto> --out reporte-antes

# 2) ...corregir...

# 3) Medir el progreso
python3 <skill>/scripts/audit.py <proyecto> --out reporte-despues \
  --baseline reporte-antes/reporte.json
```

El resumen debe mostrar `N resueltos · 0 nuevos`. Si aparecen **nuevos**,
una corrección introdujo otro problema: revísala antes de seguir.

## 4. Prueba manual que el usuario debe hacer

| Acción | Resultado esperado |
|---|---|
| Buscar «phone» | Aparecen productos aunque tengan mayúscula |
| Filtrar por categoría | Solo productos de esa categoría |
| Agregar 2 veces el mismo producto | 1 fila con cantidad 2, contador actualizado |
| Pulsar «-» con cantidad 1 | No baja de 1 (o se elimina) |
| Eliminar un producto | Solo desaparece ese |
| Comparar total | Igual a la suma de precio × cantidad visibles |
| Abrir carrito | El panel se ve encima de la página |
| Ventana de 360px | Las imágenes no se salen de las tarjetas |
| DevTools → Offline | Mensaje de error, no «Cargando...» infinito |

## 5. Formato de entrega (por cada error)

El `reporte.md` ya trae un bloque por hallazgo con esta estructura. Pide al
usuario que lo complete con lo que realmente hizo:

```markdown
### Error N: <título>
- **Qué pasaba (síntoma):** ...
- **Archivo y línea:** `src/App.jsx:44`
- **Cómo lo corregí:** ...
- **Prompt usado con la IA:** "..."
- **¿Tuve que corregir el prompt?:** sí/no, por qué
```

No inventes el campo «¿Tuve que corregir el prompt?»: es experiencia
personal del estudiante.
