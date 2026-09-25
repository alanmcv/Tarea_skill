"""Reparadores automáticos, uno por regla.

Cada reparador recibe la lista de líneas del archivo (se modifica en el
lugar), el hallazgo enriquecido (dict con 'linea', 'regla', ...) y el texto
completo del archivo. Devuelve una explicación en español de lo que cambió o
lanza NotFixable si el caso no es seguro de reparar automáticamente.

fix.py vuelve a auditar después de cada reparación y la descarta si el
hallazgo no desaparece o si aparece un problema nuevo.
"""

import re

from checks import QTY_RE, STATE_RE, contrast_ratio, luminance, parse_color


class NotFixable(Exception):
    pass


def indent_of(line):
    return line[:len(line) - len(line.lstrip())]


def _idx(f, lines):
    i = f['linea'] - 1
    if not 0 <= i < len(lines):
        raise NotFixable('la línea del hallazgo ya no existe')
    return i


def _setter_for(text, var):
    for name, setter in STATE_RE.findall(text):
        if name == var:
            return setter
    return None


def _state_is_array(text, var):
    return bool(re.search(
        rf'const\s*\[\s*{var}\s*,\s*\w+\s*\]\s*=\s*(?:React\.)?useState\(\s*\[',
        text))


# ------------------------------------------------------------------- CSS

def fix_c01(lines, f, text):
    i = _idx(f, lines)
    new = re.sub(r'z-index\s*:\s*-\s*\d+', 'z-index: 10', lines[i])
    if new == lines[i]:
        raise NotFixable('no se encontró el z-index negativo')
    lines[i] = new
    return ('Se cambió el z-index negativo por 10: el panel fijo ahora se '
            'dibuja encima del contenido.')


def fix_c02(lines, f, text):
    i = _idx(f, lines)
    m = re.search(r'(?<![-\w])width\s*:\s*(\d+)px', lines[i])
    if not m:
        raise NotFixable('no se encontró el ancho fijo')
    lines[i] = lines[i][:m.start()] + 'width: 100%' + lines[i][m.end():]
    return (f'Se reemplazó width: {m.group(1)}px por width: 100%: la imagen '
            f'se adapta al ancho de la tarjeta sin desbordarse.')


def _block_range(lines, i):
    start = i
    while start >= 0 and '{' not in lines[start]:
        start -= 1
    end = i
    while end < len(lines) and '}' not in lines[end]:
        end += 1
    if start < 0 or end >= len(lines):
        raise NotFixable('no se pudo delimitar la regla CSS')
    return start, end


def _hex(rgb):
    return '#' + ''.join(f'{max(0, min(255, int(c))):02x}' for c in rgb)


def fix_c03(lines, f, text):
    i = _idx(f, lines)
    start, end = _block_range(lines, i)
    bg_line, bg = None, None
    for k in range(start, end + 1):
        m = re.search(r'background(?:-color)?\s*:\s*([^;]+)', lines[k])
        if m and parse_color(m.group(1)):
            bg_line, bg = k, parse_color(m.group(1))
    if bg is None:
        raise NotFixable('no se encontró el color de fondo')
    m = re.search(r'(?<![-\w])color\s*:\s*([^;]+)', lines[i])
    if not m:
        raise NotFixable('no se encontró la propiedad color')
    old_fg = m.group(1).strip()
    old_ratio = contrast_ratio(parse_color(old_fg), bg)
    white, dark = (255, 255, 255), (17, 17, 17)
    extra = ''
    if contrast_ratio(white, bg) >= 4.5:
        best, ratio = '#fff', contrast_ratio(white, bg)
    elif luminance(bg) > 0.3 and contrast_ratio(dark, bg) >= 4.5:
        best, ratio = '#111', contrast_ratio(dark, bg)
    else:
        # Fondo de color medio: se oscurece hasta que el texto blanco cumpla
        darker = bg
        for _ in range(60):
            darker = tuple(c * 0.95 for c in darker)
            if contrast_ratio(white, darker) >= 4.5:
                break
        new_bg = _hex(darker)
        lines[bg_line] = re.sub(
            r'(background(?:-color)?\s*:\s*)[^;]+',
            lambda mm: mm.group(1) + new_bg, lines[bg_line], count=1)
        best, ratio = '#fff', contrast_ratio(white, darker)
        extra = f' y se oscureció el fondo a {new_bg} (mismo tono)'
    lines[i] = lines[i][:m.start(1)] + best + lines[i][m.end(1):]
    return (f'Contraste {old_ratio:.2f}:1 → {ratio:.2f}:1 (WCAG AA pide 4.5:1)'
            f'. Se cambió el texto de {old_fg} a {best}{extra}.')


# ------------------------------------------------------------------ HTML

def fix_h01(lines, f, text):
    tag = '<meta name="viewport" content="width=device-width, initial-scale=1.0" />'
    for k, line in enumerate(lines):
        if re.search(r'<meta\s+charset', line, re.I):
            lines.insert(k + 1, indent_of(line) + tag)
            break
    else:
        for k, line in enumerate(lines):
            if '<head' in line.lower():
                lines.insert(k + 1, indent_of(line) + '  ' + tag)
                break
        else:
            raise NotFixable('no hay <head> en index.html')
    return ('Se agregó <meta name="viewport">: en el celular la página usa '
            'el ancho real de la pantalla.')


# ------------------------------------------------------------ JS: estado

MERGE_RE = re.compile(
    r'^\{\s*\.\.\.(\w+)\s*,\s*(quantity|qty|cantidad)\s*:\s*1\s*\}$')


def fix_r01(lines, f, text):
    i = _idx(f, lines)
    m = re.match(r'^(\s*)(\w+)\.push\((.*)\)\s*;?\s*$', lines[i])
    if not m:
        raise NotFixable('solo se repara automáticamente el patrón x.push(...)'
                         ' en una sola línea')
    ind, var, arg = m.group(1), m.group(2), m.group(3).strip()
    setter = _setter_for(text, var)
    if not setter:
        raise NotFixable(f'no se encontró el setter de {var}')
    # Quitar el setX(x) que suele venir después (R02)
    for k in range(i + 1, min(len(lines), i + 4)):
        if re.match(rf'^\s*{setter}\(\s*{var}\s*\)\s*;?\s*$', lines[k]):
            del lines[k]
            break
    mm = MERGE_RE.match(arg)
    if mm:
        item, qty = mm.group(1), mm.group(2)
        new = [
            f'{ind}{setter}((prev) => {{',
            f'{ind}  const found = prev.find((i) => i.id === {item}.id)',
            f'{ind}  if (found) {{',
            f'{ind}    return prev.map((i) =>',
            f'{ind}      i.id === {item}.id ? {{ ...i, {qty}: i.{qty} + 1 }} : i',
            f'{ind}    )',
            f'{ind}  }}',
            f'{ind}  return [...prev, {arg}]',
            f'{ind}}})',
        ]
        why = (f'Se reemplazó {var}.push + {setter}({var}) por una '
               f'actualización inmutable con {setter}(prev => ...). Si el '
               f'producto ya está en el carrito se suma 1 a {qty} en vez de '
               f'duplicar la fila (evita keys repetidas).')
    else:
        new = [f'{ind}{setter}((prev) => [...prev, {arg}])']
        why = (f'Se reemplazó {var}.push por {setter}(prev => [...prev, ...]): '
               f'React recibe un arreglo nuevo y vuelve a renderizar.')
    lines[i:i + 1] = new
    return why


def fix_r02(lines, f, text):
    i = _idx(f, lines)
    m = re.search(r'\b(set\w+)\(\s*(\w+)\s*\)', lines[i])
    if not m:
        raise NotFixable('no se encontró setX(x)')
    setter, var = m.group(1), m.group(2)
    copy = f'[...{var}]' if _state_is_array(text, var) else f'{{ ...{var} }}'
    lines[i] = lines[i][:m.start()] + f'{setter}({copy})' + lines[i][m.end():]
    return f'Se pasa una copia nueva ({copy}) para que React detecte el cambio.'


def fix_r03(lines, f, text):
    i = _idx(f, lines)
    m = QTY_RE.search(lines[i])
    if not m:
        raise NotFixable('no se encontró la suma de cantidad')
    expr = m.group(0)
    lines[i] = lines[i][:m.start()] + f'Math.max(1, {expr})' + lines[i][m.end():]
    return (f'Se envolvió `{expr}` en Math.max(1, ...): la cantidad nunca '
            f'baja de 1.')


def fix_r04(lines, f, text):
    i = _idx(f, lines)
    m = re.search(r'(\w+)\.(\w+)(\s*!==?\s*)(\w+)\.\2\b', lines[i])
    if not m:
        raise NotFixable('no se encontró la comparación del filter')
    field = m.group(2)
    new = f'{m.group(1)}.id{m.group(3)}{m.group(4)}.id'
    lines[i] = lines[i][:m.start()] + new + lines[i][m.end():]
    return (f'El filter ahora compara por id en vez de {field}: solo se '
            f'elimina el producto elegido.')


def fix_r05(lines, f, text):
    i = _idx(f, lines)
    m = re.search(
        r'([\w.]+)\s*-\s*([\w.]*(?:percent|percentage|porcentaje|pct)\w*)',
        lines[i], re.I)
    if not m:
        raise NotFixable('solo se repara el patrón precio - porcentaje')
    new = f'{m.group(1)} * (1 - {m.group(2)} / 100)'
    lines[i] = lines[i][:m.start()] + new + lines[i][m.end():]
    return (f'El porcentaje ahora se convierte: {new}. Antes se restaba '
            f'{m.group(2)} como si fueran dólares.')


def fix_r06(lines, f, text):
    i = _idx(f, lines)
    m = re.search(r'([\w.]+)\.includes\(\s*(\w+)\s*\)', lines[i])
    if not m:
        raise NotFixable('no se encontró el includes')
    new = (f'{m.group(1)}.toLowerCase().includes('
           f'{m.group(2)}.trim().toLowerCase())')
    lines[i] = lines[i][:m.start()] + new + lines[i][m.end():]
    return ('La búsqueda compara ambos textos en minúsculas y sin espacios '
            'extra: «phone» encuentra «iPhone».')


def fix_r10(lines, f, text):
    i = _idx(f, lines)
    for k in range(i, max(-1, i - 5), -1):
        m = re.search(r'\.map\(\s*\(\s*(\w+)\s*,\s*(index|idx|i)\s*\)', lines[k])
        if m:
            new = re.sub(r'key=\{\s*(index|idx|i)\s*\}',
                         f'key={{{m.group(1)}.id}}', lines[i])
            if new != lines[i]:
                lines[i] = new
                return f'La key ahora es {m.group(1)}.id (estable).'
    raise NotFixable('no se encontró la variable del map para usar su id')


# ------------------------------------------------------------ JS: fetch

def _statement_end(lines, i, col):
    """Devuelve la línea donde termina la cadena que empieza en (i, col)."""
    depth, seen, quote = 0, False, None
    j, k = i, col
    while j < len(lines):
        line = lines[j]
        while k < len(line):
            ch = line[k]
            if quote:
                if ch == '\\':
                    k += 1
                elif ch == quote:
                    quote = None
            elif ch in '\'"`':
                quote = ch
            elif ch in '([{':
                depth += 1
                seen = True
            elif ch in ')]}':
                depth -= 1
                if depth < 0:
                    return j
                if depth == 0 and seen:
                    rest = line[k + 1:].strip()
                    nxt = rest or next(
                        (l.strip() for l in lines[j + 1:] if l.strip()), '')
                    if not nxt.startswith('.'):
                        return j
            k += 1
        j, k = j + 1, 0
    raise NotFixable('no se pudo encontrar el final de la cadena de fetch')


def _fetch_line(lines, f):
    i = _idx(f, lines)
    if 'fetch(' not in lines[i]:
        raise NotFixable('la línea ya no contiene fetch')
    return i


def fix_r08(lines, f, text):
    i = _fetch_line(lines, f)
    pat = re.compile(r'\.then\(\s*\(?(\w+)\)?\s*=>\s*\1\.json\(\)\s*\)')
    for k in range(i, min(len(lines), i + 8)):
        m = pat.search(lines[k])
        if not m:
            continue
        res = m.group(1)
        if lines[k].strip() == m.group(0):
            ind = indent_of(lines[k])
            lines[k:k + 1] = [
                f'{ind}.then(({res}) => {{',
                f'{ind}  if (!{res}.ok) throw new Error(`HTTP ${{{res}.status}}`)',
                f'{ind}  return {res}.json()',
                f'{ind}}})',
            ]
        else:
            lines[k] = (lines[k][:m.start()] +
                        f'.then(({res}) => {{ if (!{res}.ok) throw new Error('
                        f'`HTTP ${{{res}.status}}`); return {res}.json() }})' +
                        lines[k][m.end():])
        return ('Antes de leer el JSON se revisa res.ok: un 404/500 ahora se '
                'trata como error en vez de romper la app.')
    raise NotFixable('no se encontró .then(res => res.json())')


def fix_r09(lines, f, text):
    i = _fetch_line(lines, f)
    start = next((k for k in range(i, max(-1, i - 15), -1)
                  if 'useEffect(' in lines[k]), None)
    end = next((k for k in range(i, min(len(lines), i + 40))
                if re.match(r'^\s*\}\s*,\s*\[', lines[k])), None)
    if start is None or end is None:
        raise NotFixable('no se pudo delimitar el useEffect')
    body = '\n'.join(lines[start:end])
    if re.search(r'return\s*\(\s*\)\s*=>', body):
        raise NotFixable('el efecto ya tiene una función de limpieza')
    line = lines[i]
    if re.search(r'fetch\(\s*[^,()]+\s*\)', line):
        line = re.sub(r'fetch\(\s*([^,()]+?)\s*\)',
                      r'fetch(\1, { signal: controller.signal })', line, 1)
    elif re.search(r'fetch\([^,]+,\s*\{', line):
        line = re.sub(r'(fetch\([^,]+,\s*\{)', r'\1 signal: controller.signal,',
                      line, 1)
    else:
        raise NotFixable('la llamada a fetch tiene una forma no soportada')
    lines[i] = line
    ind = indent_of(lines[start]) + '  '
    lines.insert(end, f'{ind}return () => controller.abort()')
    lines.insert(end, '')
    lines.insert(start + 1, f'{ind}const controller = new AbortController()')
    return ('El efecto crea un AbortController y lo aborta al limpiar: una '
            'búsqueda vieja ya no puede sobrescribir resultados nuevos.')


def fix_r07(lines, f, text):
    i = _fetch_line(lines, f)
    col = lines[i].index('fetch(')
    j = _statement_end(lines, i, col)
    tail = lines[j].rstrip()
    semi = tail.endswith(';')
    if semi:
        lines[j] = tail[:-1]
    if j + 1 < len(lines) and lines[j + 1].lstrip().startswith('.'):
        raise NotFixable('la cadena continúa de forma inesperada')
    nxt = lines[i + 1] if i + 1 < len(lines) else ''
    ind = indent_of(nxt) if nxt.lstrip().startswith('.') and i != j \
        else indent_of(lines[i]) + '  '
    new = [
        f'{ind}.catch((err) => {{',
        f"{ind}  if (err.name !== 'AbortError') console.error("
        f"'Error al cargar datos:', err)",
        f'{ind}}})',
    ]
    loading = next((s for v, s in STATE_RE.findall(text)
                    if 'loading' in v.lower() or 'cargando' in v.lower()), None)
    chain = '\n'.join(lines[i:j + 1])
    why = ('Se agregó .catch para que un fallo de red no rompa la app')
    if loading and '.finally(' not in chain:
        new.append(f'{ind}.finally(() => {loading}(false))')
        why += (f' y .finally({loading}(false)) para que «Cargando...» '
                f'siempre termine')
    if semi:
        new[-1] += ';'
    lines[j + 1:j + 1] = new
    return why + '.'


FIXERS = {
    'R01': fix_r01, 'R02': fix_r02, 'R03': fix_r03, 'R04': fix_r04,
    'R05': fix_r05, 'R06': fix_r06, 'R07': fix_r07, 'R08': fix_r08,
    'R09': fix_r09, 'R10': fix_r10, 'C01': fix_c01, 'C02': fix_c02,
    'C03': fix_c03, 'H01': fix_h01,
}

# Orden de aplicación: primero la cadena de fetch (R08 → R09 → R07) para que
# el .catch final ya conozca el AbortController; luego estado y visuales.
PRIORITY = ['R08', 'R09', 'R07', 'R01', 'R02', 'R03', 'R04', 'R05', 'R06',
            'R10', 'C01', 'C02', 'C03', 'H01']
