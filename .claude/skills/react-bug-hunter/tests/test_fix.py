"""Pruebas del reparador automático (fix.py).

Cada prueba trabaja sobre una copia temporal del fixture, así los fixtures
nunca se modifican.
"""

import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SKILL = Path(__file__).resolve().parent.parent
FIX = SKILL / 'tests' / 'fixtures'
sys.path.insert(0, str(SKILL / 'scripts'))

import audit  # noqa: E402
import fix  # noqa: E402


def run(module, *args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = module.main([str(a) for a in args])
    return code, out.getvalue(), err.getvalue()


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(Path(root).rglob('*')) if p.is_file()
            and '.rbh-backup' not in p.parts}


class ReparacionBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.proj = Path(self.tmp.name) / 'app'
        shutil.copytree(FIX / 'app_con_bugs', self.proj)
        self.out = Path(self.tmp.name) / 'reporte'

    def tearDown(self):
        self.tmp.cleanup()


class CasoExitoso(ReparacionBase):
    def test_vista_previa_no_modifica_nada(self):
        before = snapshot(self.proj)
        code, stdout, _ = run(fix, self.proj, '--out', self.out)
        self.assertEqual(code, 0)
        self.assertIn('VISTA PREVIA', stdout)
        self.assertEqual(snapshot(self.proj), before)
        self.assertFalse((self.proj / '.rbh-backup').exists())
        self.assertTrue((self.out / 'cambios.diff').read_text('utf-8'))

    def test_apply_repara_los_13_hallazgos(self):
        code, stdout, _ = run(fix, self.proj, '--apply', '--out', self.out)
        self.assertEqual(code, 0)
        self.assertIn('13/13 hallazgos resueltos', stdout)
        self.assertIn('25/100 → 100/100', stdout)
        code, stdout, _ = run(audit, self.proj, '--format', 'none')
        self.assertEqual(code, 0)
        self.assertIn('0 hallazgos', stdout)

    def test_codigo_reparado_es_el_esperado(self):
        run(fix, self.proj, '--apply', '--out', self.out)
        app = (self.proj / 'src' / 'App.jsx').read_text('utf-8')
        css = (self.proj / 'src' / 'App.css').read_text('utf-8')
        self.assertIn('setCart((prev) => {', app)
        self.assertIn('Math.max(1, item.quantity + delta)', app)
        self.assertIn('c.id !== item.id', app)
        self.assertIn('item.discountPercentage / 100', app)
        self.assertIn('controller.abort()', app)
        self.assertIn("if (!res.ok) throw new Error", app)
        self.assertIn('.finally(() => setLoading(false))', app)
        self.assertNotIn('cart.push', app)
        self.assertIn('z-index: 10', css)
        self.assertIn('width: 100%', css)

    def test_genera_entrega_html_y_resumen(self):
        run(fix, self.proj, '--apply', '--out', self.out)
        entrega = (self.out / 'ENTREGA.md').read_text('utf-8')
        page = (self.out / 'fix.html').read_text('utf-8')
        data = json.loads((self.out / 'resumen.json').read_text('utf-8'))
        self.assertIn('### Error 1:', entrega)
        self.assertIn('```diff', entrega)
        self.assertIn('`src/App.jsx:32`', entrega)  # línea ORIGINAL de R01
        self.assertNotIn('{{', entrega)
        self.assertNotIn('{{', page)
        self.assertIn('class="diff"', page)
        self.assertEqual(len(data['aplicadas']), 12)
        self.assertEqual(data['puntaje_despues'], 100)

    def test_undo_restaura_exactamente(self):
        before = snapshot(self.proj)
        run(fix, self.proj, '--apply', '--out', self.out)
        self.assertNotEqual(snapshot(self.proj), before)
        code, stdout, _ = run(fix, self.proj, '--undo')
        self.assertEqual(code, 0)
        self.assertIn('Se restauraron 3 archivos', stdout)
        self.assertEqual(snapshot(self.proj), before)
        self.assertFalse((self.proj / '.rbh-backup').exists())

    def test_es_idempotente(self):
        run(fix, self.proj, '--apply', '--out', self.out)
        code, stdout, _ = run(fix, self.proj, '--apply', '--out', self.out)
        self.assertEqual(code, 0)
        self.assertIn('0 reparaciones', stdout)

    def test_only_limita_las_reglas(self):
        code, stdout, _ = run(fix, self.proj, '--apply', '--only', 'c01,H01',
                              '--out', self.out)
        self.assertEqual(code, 1)  # quedan pendientes
        data = json.loads((self.out / 'resumen.json').read_text('utf-8'))
        self.assertEqual({a['regla'] for a in data['aplicadas']},
                         {'C01', 'H01'})
        self.assertEqual(len(data['manuales']), 11)

    def test_respeta_finales_de_linea_windows(self):
        css = self.proj / 'src' / 'App.css'
        css.write_bytes(css.read_bytes().replace(b'\n', b'\r\n'))
        run(fix, self.proj, '--apply', '--out', self.out)
        data = css.read_bytes()
        self.assertIn(b'z-index: 10;\r\n', data)
        self.assertNotIn(b'\n', data.replace(b'\r\n', b''))


class ErroresYSeguridad(ReparacionBase):
    def test_build_fallido_revierte_todo(self):
        before = snapshot(self.proj)
        with mock.patch.object(fix, 'run_build',
                               return_value=('fallo', 'SyntaxError simulado')):
            code, _, err = run(fix, self.proj, '--apply', '--verify-build',
                               '--out', self.out)
        self.assertEqual(code, 6)
        self.assertIn('se revirtieron', err)
        self.assertEqual(snapshot(self.proj), before)

    def test_build_omitido_sin_node_modules(self):
        code, stdout, _ = run(fix, self.proj, '--apply', '--verify-build',
                              '--out', self.out)
        self.assertEqual(code, 0)
        self.assertIn('Build omitido', stdout)

    def test_undo_sin_copias(self):
        code, _, err = run(fix, self.proj, '--undo')
        self.assertEqual(code, 7)
        self.assertIn('no hay copias de seguridad', err)

    def test_regla_desconocida(self):
        code, _, err = run(fix, self.proj, '--only', 'X99', '--out', self.out)
        self.assertEqual(code, 2)
        self.assertIn('X99', err)

    def test_ruta_inexistente(self):
        code, _, err = run(fix, '/no/existe', '--out', self.out)
        self.assertEqual(code, 2)

    def test_caso_no_reparable_queda_pendiente(self):
        app = self.proj / 'src' / 'App.jsx'
        app.write_text(app.read_text('utf-8').replace(
            'cart.push({ ...product, quantity: 1 })',
            'cart.splice(0, 0, { ...product, quantity: 1 })'), 'utf-8')
        code, stdout, _ = run(fix, self.proj, '--apply', '--out', self.out)
        self.assertEqual(code, 1)
        self.assertIn('✋', stdout)
        data = json.loads((self.out / 'resumen.json').read_text('utf-8'))
        pending = {m['regla']: m['motivo'] for m in data['manuales']}
        self.assertIn('R01', pending)
        self.assertIn('x.push', pending['R01'])


if __name__ == '__main__':
    unittest.main()
