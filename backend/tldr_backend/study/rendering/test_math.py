"""Math input/resource boundaries and local conversion; no provider requests."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path
import tempfile
import unittest

from .schema import validate_lesson,LessonValidationError
from .math_svg import validate_math,checked_svg,prepare_equations,math_dependencies
from .renderer import _run,_object_provenance

EXAMPLES=Path(__file__).resolve().parents[4]/'examples'
SVG='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path fill="currentColor" d="M0 0L20 20"/></svg>'


class MathBoundaryTests(unittest.TestCase):
    def test_supported_notation_and_closed_schema(self):
        expressions=[r'\frac{dy}{dx}=\lim_{h\to0}\frac{f(x+h)-f(x)}{h}',r'\begin{bmatrix}1&2\\3&4\end{bmatrix}',r'\int_0^1 x^2\,dx=\frac{1}{3}']
        for tex in expressions:self.assertEqual(validate_math(tex),tex)
        lesson=json.loads((EXAMPLES/'math.json').read_text())
        validate_lesson(lesson)
        lesson['chapters'][0]['scenes'][0]['objects'][1]['latex']='x^2'
        with self.assertRaises(LessonValidationError):validate_lesson(lesson)

    def test_program_file_network_and_dynamic_commands_rejected(self):
        for tex in (r'\input{secrets}',r'\href{https://example.com}{x}',r'\require{html}',r'\def\loop{\loop}\loop',r'\htmlClass{x}{y}',r'\includegraphics{x}',r'\csname input\endcsname',r'\begin {document}x\end{document}', 'x\\'):
            with self.subTest(tex=tex),self.assertRaises(ValueError):validate_math(tex)

    def test_invalid_or_excessive_input_rejected(self):
        for tex in ('', 'x'*601, '{'*21+'x'+'}'*21, r'\frac{1}{', 'x\0y', 'x'+r'\\x'*13):
            with self.subTest(tex=tex),self.assertRaises(ValueError):validate_math(tex)

    def test_svg_has_no_active_or_external_content(self):
        self.assertIn('#ffffff',checked_svg(SVG))
        for content in (SVG.replace('<path','<script'),SVG.replace('<path','<foreignObject'),SVG.replace('fill="currentColor"','onload="alert(1)"'),SVG.replace('fill="currentColor"','href="https://example.com"'),SVG.replace('viewBox="0 0 20 20"','viewBox="0 0 nan 20"'),SVG.replace('<path','<path xmlns="urn:foreign"')):
            with self.subTest(content=content),self.assertRaises((ValueError,ET.ParseError)):
                checked_svg(content)

    def test_notation_is_not_mislabelled_verified(self):
        obj={'kind':'equation','latex':'y=99','calculation':{'kind':'quadratic','inputs':{'a':1,'b':0,'c':0,'x':2}}}
        self.assertEqual(_object_provenance(obj),'conceptual')

    def test_equation_cache_reuse_and_corruption_recovery(self):
        lesson=json.loads((EXAMPLES/'math.json').read_text())
        if not math_dependencies()['ready']:self.skipTest('Local Node/math dependencies not installed')
        calls=[]
        def convert(args,**kwargs):
            calls.append(args)
            Path(args[-1]).write_text(json.dumps([SVG]))
        with tempfile.TemporaryDirectory() as folder:
            assets,_=prepare_equations(lesson,folder,convert,lambda:False)
            again,_=prepare_equations(lesson,folder,convert,lambda:False)
            self.assertEqual(assets,again);self.assertEqual(len(calls),1)
            Path(next(iter(assets.values()))['path']).write_text('broken')
            prepare_equations(lesson,folder,convert,lambda:False)
            self.assertEqual(len(calls),2)
            marker=Path(next(iter(assets.values()))['path']).with_suffix('.json')
            for record in (None,[],{}, {'sha256':None}, {'sha256':[]}, {'sha256':'not-a-digest'}):
                with self.subTest(marker=record):
                    marker.write_text(json.dumps(record),encoding='utf-8')
                    previous=len(calls)
                    recovered,_=prepare_equations(lesson,folder,convert,lambda:False)
                    self.assertEqual(recovered,assets)
                    self.assertEqual(len(calls),previous+1)
                    prepare_equations(lesson,folder,convert,lambda:False)
                    self.assertEqual(len(calls),previous+1)

    @unittest.skipUnless(math_dependencies()['ready'],'Local Node/math dependencies not installed')
    def test_real_offline_derivative_and_matrix_conversion(self):
        lesson=json.loads((EXAMPLES/'math.json').read_text())
        objects=lesson['chapters'][0]['scenes'][0]['objects']
        objects[0]['latex']=r'\frac{dy}{dx}=\lim_{h\to0}\frac{f(x+h)-f(x)}{h}'
        objects.append({'id':'matrix','kind':'equation','text':'A two by two matrix','label':'Matrix','latex':r'\begin{bmatrix}1&2\\3&4\end{bmatrix}'})
        with tempfile.TemporaryDirectory() as folder:
            assets,_=prepare_equations(lesson,folder,_run,lambda:False)
            self.assertEqual(len(assets),2)
            for value in assets.values():self.assertIn('<path',checked_svg(Path(value['path']).read_text()))
