# Tienda Tech (ejercicio de depuración)

Esta tienda con carrito **tiene exactamente 10 errores**: algunos de lógica, otros de datos/API y otros visuales.

## Cómo ejecutarla

```bash
npm install
npm run dev
```

Abre la dirección que muestra la terminal (normalmente http://localhost:5173).

## Tu tarea

1. Usa la aplicación (busca, filtra, agrega al carrito, cambia cantidades, elimina, paga) y anota todo lo que funcione o se vea mal.
2. Encuentra la causa de cada error en el código.
3. Corrígelos. Puedes usar IA, pero debes **entender y probar** cada cambio.
4. Entrega, por cada uno de los 10 errores:
   - Qué pasaba (síntoma).
   - En qué archivo y línea estaba la causa.
   - Cómo lo corregiste.
   - El prompt que usaste con la IA y si tuviste que corregirlo.

Los datos vienen de https://dummyjson.com/products

---

## 🔎🛠 Skill: `react-bug-hunter`

Este repositorio incluye una skill para **Claude Code** que detecta **y repara
automáticamente** los errores de esta tienda (y de cualquier app React + Vite).
Hace una copia de seguridad antes de cambiar nada, verifica cada cambio, ejecuta
`npm run build` y genera el documento de entrega.

- Ubicación: [`.claude/skills/react-bug-hunter/`](.claude/skills/react-bug-hunter/)
- Documentación completa: [`README de la skill`](.claude/skills/react-bug-hunter/README.md)
- Capturas: [`evidencias/`](.claude/skills/react-bug-hunter/evidencias/)

**Uso rápido en VS Code:** abre esta carpeta, abre el chat de Claude Code y escribe:

```
/react-bug-hunter            → auditar y explicar
/react-bug-hunter reparar    → reparar todo (backup + build + ENTREGA.md)
/react-bug-hunter deshacer   → volver al estado original
/react-bug-hunter demo       → demostración completa
```

Requisito: Python 3.8+ (sin dependencias extra).
