"""Detectores de errores para proyectos React + Vite.

Cada detector recibe la lista de archivos del proyecto y devuelve hallazgos
crudos: (id_regla, archivo, linea, codigo, detalle). La metadata de cada regla
(titulo, severidad, correccion, prompt...) vive en assets/rules.json.
"""

import re
from dataclasses import dataclass, field

JS_EXT = ('.js', '.jsx', '.ts', '.tsx')
CSS_EXT = ('.css',)


@dataclass
class SourceFile:
    rel: str
    text: str
    lines: list = field(init=False)

    def __post_init__(self):
        self.lines = self.text.splitlines()

    @property
    def is_js(self):
        return self.rel.endswith(JS_EXT)

    @property
    def is_css(self):
        return self.rel.endswith(CSS_EXT)


@dataclass
class RawFinding:
    rule: str
    file: str
    line: int
    code: str
    detail: str = ''


def _is_comment(line):
    s = line.strip()
    return s.startswith('//') or s.startswith('*') or s.startswith('/*')


# ---------------------------------------------------------------- JS / JSX

STATE_RE = re.compile(
    r'const\s*\[\s*(\w+)\s*,\s*(set\w+)\s*\]\s*=\s*(?:React\.)?useState\b'
)
MUTATORS = 'push|pop|shift|unshift|splice|sort|reverse|fill|copyWithin'


def state_vars(src):
    return STATE_RE.findall(src.text)


def check_state_mutation(files, ctx):
    """R01 mutación directa y R02 setter con la misma referencia."""
    out = []
    for f in files:
        if not f.is_js:
            continue
        for var, setter in state_vars(f):
            mut = re.compile(
                rf'\b{var}\s*\.\s*({MUTATORS})\s*\('
                rf'|\b{var}\s*\[[^\]]+\]\s*=(?!=)'
                rf'|\b{var}\s*\.\s*\w+\s*=(?!=)'
            )
            same = re.compile(rf'\b{setter}\(\s*{var}\s*\)')
            for i, line in enumerate(f.lines, 1):
                if _is_comment(line):
                    continue
                m = mut.search(line)
                if m:
                    out.append(RawFinding(
                        'R01', f.rel, i, line.strip(),
                        f'El estado `{var}` se modifica en el lugar '
                        f'(`{m.group(0).strip()}`).'))
                if same.search(line):
                    out.append(RawFinding(
                        'R02', f.rel, i, line.strip(),
                        f'`{setter}` recibe la misma referencia `{var}`.'))
    return out


QTY_RE = re.compile(
    r'\b\w+\.(quantity|qty|cantidad|count|amount)\s*\+\s*([A-Za-z_]\w*)'
)
QTY_GUARD = re.compile(
    r'Math\.max|>\s*0|>=\s*1|<\s*1\b|<=\s*0|===?\s*0|\.filter\('
)


def check_qty_bounds(files, ctx):
    """R03 cantidad + delta sin límite inferior."""
    out = []
    for f in files:
        if not f.is_js:
            continue
        for i, line in enumerate(f.lines, 1):
            m = QTY_RE.search(line)
            if not m or _is_comment(line):
                continue
            window = '\n'.join(f.lines[max(0, i - 6): i + 5])
            if not QTY_GUARD.search(window):
                out.append(RawFinding(
                    'R03', f.rel, i, line.strip(),
                    f'`{m.group(1)} + {m.group(2)}` puede quedar en 0 o '
                    f'negativo si `{m.group(2)}` es negativo.'))
    return out


UNIQUE_FIELDS = {'id', '_id', 'key', 'uuid', 'sku', 'slug', 'code',
                 'productId', 'itemId'}
REMOVE_RE = re.compile(
    r'\.filter\(\s*\(?\s*(\w+)\s*\)?\s*=>\s*\1\.(\w+)\s*!==?\s*(\w+)\.(\w+)'
)


def check_remove_by_field(files, ctx):
    """R04 filter que elimina por un campo no único."""
    out = []
    for f in files:
        if not f.is_js:
            continue
        for i, line in enumerate(f.lines, 1):
            m = REMOVE_RE.search(line)
            if not m or _is_comment(line):
                continue
            left, right = m.group(2), m.group(4)
            if left == right and left not in UNIQUE_FIELDS:
                out.append(RawFinding(
                    'R04', f.rel, i, line.strip(),
                    f'Se filtra por `{left}`, que puede repetirse entre '
                    f'elementos distintos.'))
    return out


PERCENT_RE = re.compile(
    r'[-+]\s*\(?\s*[\w.]*(percent|percentage|porcentaje|pct)\w*',
    re.IGNORECASE,
)


def check_percent_as_amount(files, ctx):
    """R05 porcentaje sumado o restado como si fuera dinero."""
    out = []
    for f in files:
        if not f.is_js:
            continue
        for i, line in enumerate(f.lines, 1):
            if _is_comment(line) or '/ 100' in line or '/100' in line:
                continue
            m = PERCENT_RE.search(line)
            if m:
                out.append(RawFinding(
                    'R05', f.rel, i, line.strip(),
                    f'`{m.group(0).strip()}` opera un porcentaje sin '
                    f'dividir entre 100.'))
    return out


SEARCH_RE = re.compile(
    r'\.includes\(\s*(\w*(search|query|term|filter|busqueda|texto)\w*)\s*\)',
    re.IGNORECASE,
)
NORMALIZE_RE = re.compile(r'toLowerCase|toLocaleLowerCase|toUpperCase')


def check_case_search(files, ctx):
    """R06 búsqueda con includes sin normalizar mayúsculas."""
    out = []
    for f in files:
        if not f.is_js:
            continue
        for i, line in enumerate(f.lines, 1):
            m = SEARCH_RE.search(line)
            if m and not NORMALIZE_RE.search(line) and not _is_comment(line):
                out.append(RawFinding(
                    'R06', f.rel, i, line.strip(),
                    f'`includes({m.group(1)})` distingue mayúsculas.'))
    return out


FETCH_RE = re.compile(r'\bfetch\s*\(')
EFFECT_END_RE = re.compile(r'^\s*\}\s*,\s*\[')


def check_fetch(files, ctx):
    """R07 sin catch, R08 sin res.ok, R09 useEffect sin cancelación."""
    out = []
    for f in files:
        if not f.is_js:
            continue
        for i, line in enumerate(f.lines, 1):
            if not FETCH_RE.search(line) or _is_comment(line):
                continue
            before = f.lines[max(0, i - 12): i - 1]
            effect_start = None
            for j in range(len(before) - 1, -1, -1):
                if 'useEffect(' in before[j]:
                    effect_start = i - len(before) + j
                    break
            end = min(len(f.lines), i + 20)
            for k in range(i, min(len(f.lines), i + 40)):
                if EFFECT_END_RE.search(f.lines[k]):
                    end = k + 1
                    break
            chain = '\n'.join(f.lines[i - 1: end])
            has_try = any(re.search(r'\btry\b', b) for b in before)
            if '.catch(' not in chain and not has_try:
                out.append(RawFinding(
                    'R07', f.rel, i, line.strip(),
                    'La cadena de fetch no tiene .catch ni try/catch.'))
            if not re.search(r'\.ok\b|\.status\b', chain):
                out.append(RawFinding(
                    'R08', f.rel, i, line.strip(),
                    'No se revisa res.ok antes de leer el cuerpo.'))
            if effect_start is not None:
                body = '\n'.join(f.lines[effect_start - 1: end])
                if not re.search(
                        r'AbortController|signal|ignore|cancel', body):
                    out.append(RawFinding(
                        'R09', f.rel, i, line.strip(),
                        f'El useEffect de la línea {effect_start} no aborta '
                        f'la petición anterior.'))
    return out


INDEX_KEY_RE = re.compile(r'key=\{\s*(index|idx|i)\s*\}')


def check_index_key(files, ctx):
    """R10 key={index}."""
    out = []
    for f in files:
        if not f.is_js:
            continue
        for i, line in enumerate(f.lines, 1):
            m = INDEX_KEY_RE.search(line)
            if m:
                out.append(RawFinding(
                    'R10', f.rel, i, line.strip(),
                    f'Se usa `{m.group(1)}` como key.'))
    return out


# --------------------------------------------------------------------- CSS

@dataclass
class CssBlock:
    file: str
    selector: str
    start_line: int
    decls: dict  # propiedad -> (valor, linea, texto)


def _strip_comments(text):
    return re.sub(r'/\*.*?\*/',
                  lambda m: '\n' * m.group(0).count('\n'), text, flags=re.S)


def parse_css(src):
    text = _strip_comments(src.text)
    blocks = []
    for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', text):
        selector = m.group(1).strip()
        if selector.startswith('@'):
            continue
        body_start = m.start(2)
        decls = {}
        offset = 0
        for part in m.group(2).split(';'):
            if ':' in part:
                prop, val = part.split(':', 1)
                pos = body_start + offset + len(part) - len(part.lstrip())
                line = text.count('\n', 0, pos) + 1
                decls[prop.strip().lower()] = (
                    val.strip(), line, part.strip())
            offset += len(part) + 1
        start = text.count('\n', 0, m.start(1) + len(m.group(1))
                           - len(m.group(1).lstrip())) + 1
        blocks.append(CssBlock(src.rel, selector, start, decls))
    return blocks


def check_z_index(files, ctx):
    """C01 z-index negativo en elemento fixed/absolute."""
    out = []
    for b in ctx['css_blocks']:
        z = b.decls.get('z-index')
        pos = b.decls.get('position', ('',))[0]
        if z and re.match(r'-\d', z[0]) and pos in ('fixed', 'absolute'):
            out.append(RawFinding(
                'C01', b.file, z[1], z[2],
                f'`{b.selector}` es position: {pos} con z-index {z[0]}.'))
    return out


def check_img_width(files, ctx):
    """C02 imagen con ancho fijo mayor que la columna mínima de la grid."""
    out = []
    mins = []
    for b in ctx['css_blocks']:
        for prop in ('grid-template-columns', 'grid'):
            v = b.decls.get(prop)
            if v:
                m = re.search(r'minmax\(\s*(\d+)px', v[0])
                if m:
                    mins.append((int(m.group(1)), b.file, v[1]))
    for b in ctx['css_blocks']:
        if not re.search(r'\bimg\b', b.selector):
            continue
        w = b.decls.get('width')
        if not w:
            continue
        m = re.fullmatch(r'(\d+)px', w[0])
        if not m or 'max-width' in b.decls:
            continue
        width = int(m.group(1))
        smaller = [x for x in mins if x[0] < width]
        if smaller:
            col, gfile, gline = min(smaller)
            detail = (f'La imagen mide {width}px pero la columna de la grid '
                      f'puede medir {col}px ({gfile}:{gline}).')
        elif width >= 320:
            detail = f'Ancho fijo de {width}px sin max-width: 100%.'
        else:
            continue
        out.append(RawFinding('C02', b.file, w[1], w[2], detail))
    return out


NAMED = {
    'white': (255, 255, 255), 'black': (0, 0, 0), 'red': (255, 0, 0),
    'green': (0, 128, 0), 'blue': (0, 0, 255), 'gray': (128, 128, 128),
    'grey': (128, 128, 128), 'yellow': (255, 255, 0),
    'orange': (255, 165, 0), 'silver': (192, 192, 192),
}
COLOR_TOKEN = re.compile(
    r'#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|\b(' + '|'.join(NAMED) + r')\b')


def parse_color(value):
    """Devuelve (r, g, b) del primer color del valor, o None."""
    m = COLOR_TOKEN.search(value or '')
    if not m:
        return None
    tok = m.group(0).lower()
    if tok in NAMED:
        return NAMED[tok]
    if tok.startswith('#'):
        h = tok[1:]
        if len(h) in (3, 4):
            h = ''.join(c * 2 for c in h[:3])
        if len(h) not in (6, 8):
            return None
        return tuple(int(h[k:k + 2], 16) for k in (0, 2, 4))
    nums = re.findall(r'[\d.]+', tok)
    if len(nums) < 3:
        return None
    return tuple(int(float(n)) for n in nums[:3])


def luminance(rgb):
    def chan(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (chan(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def check_contrast(files, ctx):
    """C03 color de texto vs fondo por debajo de 4.5:1."""
    out = []
    for b in ctx['css_blocks']:
        fg = b.decls.get('color')
        bg = b.decls.get('background-color') or b.decls.get('background')
        if not fg or not bg:
            continue
        c1, c2 = parse_color(fg[0]), parse_color(bg[0])
        if not c1 or not c2:
            continue
        ratio = contrast_ratio(c1, c2)
        if ratio < 4.5:
            out.append(RawFinding(
                'C03', b.file, fg[1], fg[2],
                f'`{b.selector}`: contraste {ratio:.2f}:1 entre {fg[0]} y '
                f'{bg[0]} (mínimo 4.5:1).'))
    return out


# -------------------------------------------------------------------- HTML

def check_viewport(files, ctx):
    """H01 index.html sin meta viewport."""
    out = []
    for f in files:
        if f.rel == 'index.html' and not re.search(
                r'name\s*=\s*["\']viewport["\']', f.text):
            line = next((i for i, l in enumerate(f.lines, 1)
                         if '<head' in l), 1)
            out.append(RawFinding(
                'H01', f.rel, line, f.lines[line - 1].strip() if f.lines
                else '', 'No existe <meta name="viewport"> en <head>.'))
    return out


CHECKS = [
    check_state_mutation, check_qty_bounds, check_remove_by_field,
    check_percent_as_amount, check_case_search, check_fetch,
    check_index_key, check_z_index, check_img_width, check_contrast,
    check_viewport,
]


def run_checks(files):
    ctx = {'css_blocks': [b for f in files if f.is_css for b in parse_css(f)]}
    found = []
    for check in CHECKS:
        found.extend(check(files, ctx))
    found.sort(key=lambda r: (r.file, r.line, r.rule))
    return found
