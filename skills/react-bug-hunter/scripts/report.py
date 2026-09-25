"""Generación de reportes (JSON, Markdown, HTML) y comparación con baseline.

Las plantillas están en assets/: report_template.md y report_template.html.
Los marcadores tienen la forma {{NOMBRE}} y se reemplazan aquí.
"""

import html
import json

CATEGORIAS = {
    'logica': 'Lógica',
    'datos-api': 'Datos / API',
    'visual': 'Visual',
}
SEV_ORDER = {'error': 0, 'warning': 1, 'info': 2}


def fill(template, values):
    for key, val in values.items():
        template = template.replace('{{' + key + '}}', str(val))
    return template


def compare(current, baseline):
    """Compara huellas de hallazgos actuales contra un reporte anterior."""
    old = {f['huella']: f for f in baseline.get('hallazgos', [])}
    new = {f['huella']: f for f in current}
    return {
        'resueltos': [old[h] for h in old if h not in new],
        'nuevos': [new[h] for h in new if h not in old],
        'persisten': [new[h] for h in new if h in old],
    }


# ---------------------------------------------------------------- Markdown

def _md_escape(text):
    return text.replace('|', '\\|')


def render_markdown(template, data):
    s = data['resumen']
    rows = ['| Severidad | Cantidad |', '|---|---|']
    for sev, label in (('error', 'Errores'), ('warning', 'Advertencias'),
                       ('info', 'Sugerencias')):
        rows.append(f'| {label} | {s["por_severidad"].get(sev, 0)} |')
    rows.append('')
    rows.append('| Categoría | Cantidad |')
    rows.append('|---|---|')
    for cat, label in CATEGORIAS.items():
        rows.append(f'| {label} | {s["por_categoria"].get(cat, 0)} |')

    index = ['| # | Regla | Severidad | Archivo:línea | Qué pasa |',
             '|---|---|---|---|---|']
    blocks = []
    for n, f in enumerate(data['hallazgos'], 1):
        index.append(
            f'| {n} | {f["regla"]} {_md_escape(f["titulo"])} | '
            f'{f["severidad"]} | `{f["archivo"]}:{f["linea"]}` | '
            f'{_md_escape(f["detalle"])} |')
        blocks.append('\n'.join([
            f'### Error {n}: {f["titulo"]} (`{f["regla"]}`)',
            '',
            f'- **Qué pasaba (síntoma):** {f["sintoma"]}',
            f'- **Archivo y línea:** `{f["archivo"]}:{f["linea"]}`',
            f'- **Código:** `{f["codigo"]}`',
            f'- **Causa:** {f["causa"]} {f["detalle"]}',
            f'- **Cómo corregirlo:** {f["correccion"]}',
            f'- **Prompt sugerido para la IA:** "{f["prompt"]}"',
            '- **¿Tuviste que corregir el prompt?:** _(completar)_',
            f'- **Referencia:** `references/catalogo-reglas.md#{f["ref"]}`',
        ]))
    if not blocks:
        index = ['No se encontraron problemas. ✅']

    comp = data.get('comparacion')
    if comp:
        lines = [
            f'- Resueltos: **{len(comp["resueltos"])}**',
            f'- Nuevos: **{len(comp["nuevos"])}**',
            f'- Persisten: **{len(comp["persisten"])}**',
            '',
        ]
        for f in comp['resueltos']:
            lines.append(f'- ✅ `{f["regla"]}` {f["titulo"]} '
                         f'(`{f["archivo"]}:{f["linea"]}`)')
        for f in comp['nuevos']:
            lines.append(f'- 🆕 `{f["regla"]}` {f["titulo"]} '
                         f'(`{f["archivo"]}:{f["linea"]}`)')
        comparison = '\n'.join(lines)
    else:
        comparison = '_Sin baseline: ejecuta con `--baseline reporte.json` ' \
                     'después de corregir para ver el progreso._'

    return fill(template, {
        'PROYECTO': data['proyecto'],
        'FECHA': data['fecha'],
        'PUNTAJE': s['puntaje'],
        'TOTAL': s['total'],
        'ARCHIVOS': s['archivos_analizados'],
        'RESUMEN': '\n'.join(rows),
        'INDICE': '\n'.join(index),
        'HALLAZGOS': '\n\n'.join(blocks),
        'COMPARACION': comparison,
    })


# -------------------------------------------------------------------- HTML

def render_html(template, data):
    e = html.escape
    s = data['resumen']
    cards = []
    for n, f in enumerate(data['hallazgos'], 1):
        cards.append(f'''
<article class="finding sev-{e(f["severidad"])}" data-cat="{e(f["categoria"])}">
  <header>
    <span class="num">{n}</span>
    <span class="rule">{e(f["regla"])}</span>
    <h3>{e(f["titulo"])}</h3>
    <span class="badge">{e(f["severidad_etiqueta"])}</span>
  </header>
  <p class="loc"><code>{e(f["archivo"])}:{f["linea"]}</code>
     · {e(CATEGORIAS.get(f["categoria"], f["categoria"]))}</p>
  <pre><code>{e(f["codigo"])}</code></pre>
  <dl>
    <dt>Síntoma</dt><dd>{e(f["sintoma"])}</dd>
    <dt>Causa</dt><dd>{e(f["causa"])} <strong>{e(f["detalle"])}</strong></dd>
    <dt>Corrección</dt><dd>{e(f["correccion"])}</dd>
    <dt>Prompt sugerido</dt><dd class="prompt">{e(f["prompt"])}</dd>
  </dl>
</article>''')
    if not cards:
        cards = ['<p class="empty">No se encontraron problemas. ✅</p>']

    comp = data.get('comparacion')
    if comp:
        items = ''.join(
            f'<li class="ok">✅ {e(f["regla"])} {e(f["titulo"])} '
            f'<code>{e(f["archivo"])}:{f["linea"]}</code></li>'
            for f in comp['resueltos'])
        items += ''.join(
            f'<li class="new">🆕 {e(f["regla"])} {e(f["titulo"])} '
            f'<code>{e(f["archivo"])}:{f["linea"]}</code></li>'
            for f in comp['nuevos'])
        comparison = (
            f'<section class="compare"><h2>Progreso contra baseline</h2>'
            f'<div class="stats"><div><b>{len(comp["resueltos"])}</b>'
            f'resueltos</div><div><b>{len(comp["nuevos"])}</b>nuevos</div>'
            f'<div><b>{len(comp["persisten"])}</b>persisten</div></div>'
            f'<ul>{items}</ul></section>')
    else:
        comparison = ''

    score = s['puntaje']
    score_class = 'good' if score >= 80 else 'mid' if score >= 50 else 'bad'
    return fill(template, {
        'PROYECTO': e(data['proyecto']),
        'FECHA': e(data['fecha']),
        'PUNTAJE': score,
        'PUNTAJE_CLASE': score_class,
        'TOTAL': s['total'],
        'ERRORES': s['por_severidad'].get('error', 0),
        'ADVERTENCIAS': s['por_severidad'].get('warning', 0),
        'LOGICA': s['por_categoria'].get('logica', 0),
        'DATOS': s['por_categoria'].get('datos-api', 0),
        'VISUAL': s['por_categoria'].get('visual', 0),
        'ARCHIVOS': s['archivos_analizados'],
        'COMPARACION': comparison,
        'HALLAZGOS': '\n'.join(cards),
    })


def render_json(data):
    return json.dumps(data, ensure_ascii=False, indent=2)
