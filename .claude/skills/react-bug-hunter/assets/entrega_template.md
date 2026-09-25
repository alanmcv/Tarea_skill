# Entrega · Corrección de errores en {{PROYECTO}}

> Generado por **react-bug-hunter** (`fix.py`) el {{FECHA}}.
> Revisa cada corrección en el navegador y completa lo marcado como _(completar)_.

| Métrica | Valor |
|---|---|
| Puntaje antes | **{{ANTES}}/100** ({{TOTAL_ANTES}} hallazgos) |
| Puntaje después | **{{DESPUES}}/100** |
| Correcciones aplicadas | {{APLICADAS}} |
| Pendientes de revisión manual | {{MANUALES}} |
| Verificación de build | {{BUILD}} |

## Errores corregidos

{{CORRECCIONES}}

## Pendientes (revisión manual)

{{PENDIENTES}}

## Cómo verifiqué

1. `python3 .claude/skills/react-bug-hunter/scripts/audit.py . --baseline reporte-antes/reporte.json`
   → todos los hallazgos aparecen como **resueltos**.
2. `npm run build` sin errores.
3. Prueba manual: buscar, filtrar, agregar el mismo producto dos veces, bajar
   la cantidad hasta 1, eliminar, comparar el total y pagar.
