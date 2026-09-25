"""Pruebas de react-bug-hunter.

Ejecutar desde la carpeta de la skill:
    python3 -m unittest discover -s tests -v
"""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
FIX = SKILL / 'tests' / 'fixtures'
sys.path.insert(0, str(SKILL / 'scripts'))

import audit  # noqa: E402
from checks import contrast_ratio, parse_color  # noqa: E402

EXPECTED_BUGGY = {'R01', 'R02', 'R03', 'R04', 'R05', 'R06', 'R07', 'R08',
                  'R09', 'C01', 'C02', 'C03', 'H01'}


def run(*args):
    """Ejecuta el CLI y devuelve (código, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = audit.main([str(a) for a in args])
    return code, out.getvalue(), err.getvalue()


class CasoExitoso(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_detecta_todos_los_errores_de_la_app(self):
        code, stdout, _ = run(FIX / 'app_con_bugs', '--out', self.out)
        self.assertEqual(code, 1)
        data = json.loads((self.out / 'reporte.json').read_text('utf-8'))
        rules = {f['regla'] for f in data['hallazgos']}
        self.assertEqual(rules, EXPECTED_BUGGY)
        self.assertIn('13 hallazgos', stdout)

    def test_ubica_archivo_y_linea_correctos(self):
        run(FIX / 'app_con_bugs', '--out', self.out, '--format', 'json')
        data = json.loads((self.out / 'reporte.json').read_text('utf-8'))
        where = {f['regla']: (f['archivo'], f['linea'])
                 for f in data['hallazgos']}
        self.assertEqual(where['R01'], ('src/App.jsx', 32))
        self.assertEqual(where['R04'], ('src/App.jsx', 44))
        self.assertEqual(where['R05'], ('src/App.jsx', 53))
        self.assertEqual(where['C01'], ('src/App.css', 106))
        self.assertEqual(where['C03'], ('src/App.css', 89))

    def test_app_corregida_no_tiene_hallazgos(self):
        code, stdout, _ = run(FIX / 'app_corregida', '--out', self.out)
        self.assertEqual(code, 0)
        self.assertIn('0 hallazgos', stdout)
        self.assertIn('100/100', stdout)

    def test_genera_los_tres_reportes_con_las_plantillas(self):
        run(FIX / 'app_con_bugs', '--out', self.out, '--quiet')
        md = (self.out / 'reporte.md').read_text('utf-8')
        html = (self.out / 'reporte.html').read_text('utf-8')
        self.assertIn('## Detalle para la entrega', md)
        self.assertIn('Prompt sugerido', md)
        self.assertNotIn('{{', md)
        self.assertIn('<article class="finding sev-error"', html)
        self.assertNotIn('{{', html)

    def test_baseline_muestra_progreso(self):
        base = self.out / 'antes'
        run(FIX / 'app_con_bugs', '--out', base, '--format', 'json', '--quiet')
        code, stdout, _ = run(FIX / 'app_corregida', '--out', self.out,
                              '--baseline', base / 'reporte.json')
        self.assertEqual(code, 0)
        self.assertIn('13 resueltos', stdout)
        data = json.loads((self.out / 'reporte.json').read_text('utf-8'))
        self.assertEqual(len(data['comparacion']['resueltos']), 13)
        self.assertEqual(data['comparacion']['nuevos'], [])

    def test_fail_on_controla_el_codigo_de_salida(self):
        code, _, _ = run(FIX / 'app_con_bugs', '--format', 'none',
                         '--fail-on', 'never', '--quiet')
        self.assertEqual(code, 0)


class EntradasInvalidas(unittest.TestCase):
    def test_ruta_inexistente(self):
        code, _, err = run('/no/existe/proyecto', '--format', 'none')
        self.assertEqual(code, 2)
        self.assertIn('no existe', err)
        self.assertIn('Sugerencia', err)

    def test_archivo_en_vez_de_carpeta(self):
        code, _, err = run(FIX / 'app_con_bugs' / 'package.json',
                           '--format', 'none')
        self.assertEqual(code, 2)
        self.assertIn('es un archivo', err)

    def test_carpeta_sin_codigo(self):
        code, _, err = run(FIX / 'sin_codigo', '--format', 'none')
        self.assertEqual(code, 3)
        self.assertIn('No se encontraron archivos', err)

    def test_baseline_json_roto(self):
        code, _, err = run(FIX / 'app_con_bugs', '--format', 'none',
                           '--baseline',
                           FIX / 'baseline_invalido' / 'reporte.json')
        self.assertEqual(code, 4)
        self.assertIn('no es JSON válido', err)

    def test_baseline_inexistente(self):
        code, _, err = run(FIX / 'app_con_bugs', '--format', 'none',
                           '--baseline', '/no/existe.json')
        self.assertEqual(code, 4)

    def test_aviso_si_no_hay_package_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'App.jsx').write_text('export default 1\n')
            code, stdout, _ = run(tmp, '--format', 'none')
        self.assertEqual(code, 0)
        self.assertIn('No hay package.json', stdout)

    def test_formato_desconocido(self):
        with self.assertRaises(SystemExit) as ctx, \
                contextlib.redirect_stderr(io.StringIO()):
            audit.main([str(FIX / 'app_con_bugs'), '--format', 'pdf'])
        self.assertEqual(ctx.exception.code, 2)


class Utilidades(unittest.TestCase):
    def test_contraste_blanco_negro(self):
        self.assertAlmostEqual(contrast_ratio((0, 0, 0), (255, 255, 255)),
                               21, places=1)

    def test_parse_color(self):
        self.assertEqual(parse_color('#fff'), (255, 255, 255))
        self.assertEqual(parse_color('rgb(10, 20, 30)'), (10, 20, 30))
        self.assertEqual(parse_color('white'), (255, 255, 255))
        self.assertIsNone(parse_color('transparent'))


if __name__ == '__main__':
    unittest.main()
