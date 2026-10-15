import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from esp_html_ui.__main__ import main
from esp_html_ui.codegen import cpp_string, generate
from esp_html_ui.compiler import compile_document
from esp_html_ui.model import CompileError


class CompilerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def compile(self, body, css="", head="", **kwargs):
        (self.root / "ui.css").write_text(css, encoding="utf-8")
        path = self.root / "ui.html"
        path.write_text(f'<!doctype html><html><head><link rel="stylesheet" href="ui.css">{head}</head><body>{body}</body></html>', encoding="utf-8")
        return compile_document(path, **kwargs)

    def test_cascade_specificity_inline_important_and_shorthand(self):
        doc = self.compile('<button id="go" class="action" style="padding: 8px; color: red">Go</button>',
                           '.action { padding-left: 1px !important; color: green !important; } #go { color: blue; padding: 4px; }')
        style = doc.nodes[1].style
        self.assertEqual(style["color"], [0x008000, 255])
        self.assertEqual([style[f"padding-{side}"] for side in ("top", "right", "bottom", "left")], [8, 8, 8, 1])

    def test_shorthand_and_longhand_source_order(self):
        doc = self.compile('<span id="x">X</span>', '#x { padding: 1px 2px 3px 4px; padding-left: 9px; gap: 2px 6px; }')
        style = doc.nodes[1].style
        self.assertEqual([style[f"padding-{side}"] for side in ("top", "right", "bottom", "left")], [1, 2, 3, 9])
        self.assertEqual((style["row-gap"], style["column-gap"]), (2, 6))

    def test_variables_inherit_computed_values_and_fallback(self):
        doc = self.compile('<div style="--base: blue"><span id="x">X</span></div>',
                           ':root { --base: red; --alias: var(--base); } span { color: var(--alias); background-color: var(--missing, rgb(0, 0, 255)); }')
        self.assertEqual(doc.nodes[2].style["color"], [0xff0000, 255])
        self.assertEqual(doc.nodes[2].style["background-color"], [0x0000ff, 255])

    def test_cyclic_variable_can_use_fallback(self):
        doc = self.compile('<span>X</span>', ':root { --a: var(--b); --b: var(--a); } span { color: var(--a, red); }')
        self.assertEqual(doc.nodes[1].style["color"], [0xff0000, 255])

    def test_cycles_remain_invalid_even_with_fallback_inside_cycle(self):
        doc = self.compile('<span>X</span>', ':root { --a: var(--b, red); --b: var(--a); } span { color: var(--a, blue); }')
        self.assertEqual(doc.nodes[1].style["color"], [0x0000ff, 255])

    def test_custom_property_initial_uses_consumer_fallback(self):
        doc = self.compile('<span>X</span>', ':root { --a: red; } span { --a: initial; color: var(--a, blue); }')
        self.assertEqual(doc.nodes[1].style["color"], [0x0000ff, 255])

    def test_all_members_of_branched_variable_cycle_are_invalid(self):
        doc = self.compile('<span>X</span>', ':root { --a: var(--b) var(--c); --b: var(--d); --c: var(--d, red); --d: var(--a); } span { color: var(--c, blue); }')
        self.assertEqual(doc.nodes[1].style["color"], [0x0000ff, 255])

    def test_initial_uses_property_initial_not_heading_default(self):
        doc = self.compile('<h1>X</h1>', 'h1 { font-size: initial; width: initial; }')
        self.assertEqual(doc.nodes[1].style["font-size"], 16)
        self.assertEqual(doc.nodes[1].style["width"], ["auto", 0])

    def test_undefined_variable_is_a_diagnostic(self):
        with self.assertRaisesRegex(CompileError, "Undefined or cyclic CSS variable"):
            self.compile('<span>X</span>', 'span { color: var(--missing); }')

    def test_static_selector_combinators_and_structure(self):
        doc = self.compile('<section><span>A</span><span id="b">B</span></section>',
                           'section > span + span:nth-child(2) { color: #123456; }')
        self.assertEqual(doc.nodes[3].style["color"], [0x123456, 255])

    def test_inheritance_initial_unset_and_explicit_inherit(self):
        doc = self.compile('<div><span id="a">A</span><span id="b">B</span></div>',
                           'body { color: red; font-size: 20px; } div { padding: 8px; } #a { padding: inherit; color: initial; } #b { color: unset; }')
        self.assertEqual(doc.nodes[2].style["padding-left"], 8)
        self.assertEqual(doc.nodes[2].style["color"], [0xffffff, 255])
        self.assertEqual(doc.nodes[3].style["color"], [0xff0000, 255])
        self.assertEqual(doc.nodes[3].style["font-size"], 20)

    def test_embedded_and_linked_styles_keep_document_order(self):
        doc = self.compile('<span>X</span>', 'span { color: red; }', '<style>span { color: blue; }</style>')
        self.assertEqual(doc.nodes[1].style["color"], [0x0000ff, 255])

    def test_html_entities_comments_and_whitespace(self):
        doc = self.compile('<p id="x"> A &amp;<!--hidden--> B\n C </p>')
        self.assertEqual(doc.nodes[1].text, 'A & B C')

    def test_pre_whitespace_and_hidden_disabled_attributes(self):
        doc = self.compile('<button id="x" hidden disabled style="white-space: pre"> A\n B </button>')
        self.assertEqual(doc.nodes[1].text, ' A\n B ')
        self.assertTrue(doc.nodes[1].hidden)
        self.assertTrue(doc.nodes[1].disabled)

    def test_duplicate_ids_and_html_repair_are_errors(self):
        for body, message in [('<p id="x">A</p><span id="x">B</span>', 'Duplicate id'),
                              ('<div><span>A</div>', 'Invalid HTML')]:
            with self.subTest(body=body), self.assertRaisesRegex(CompileError, message):
                self.compile(body)

    def test_unsupported_markup_does_not_silently_disappear(self):
        for body, message in [('<img src="a.png">', 'Unsupported HTML tag'),
                              ('<button onclick="run()">Run</button>', 'Unsupported attribute'),
                              ('<div>Text</div>', 'Put container text'),
                              ('<p>A<span>B</span></p>', 'Nested/rich text')]:
            with self.subTest(body=body), self.assertRaisesRegex(CompileError, message):
                self.compile(body)

    def test_unsupported_styles_report_source_positions(self):
        for css, message in [('p { position: absolute; }', 'Unsupported CSS property'),
                             ('p { width: 3em; }', 'Unsupported value'),
                             ('button:active { color: red; }', 'Dynamic selector'),
                             ('@media (width: 320px) { p { color: red; } }', 'at-rules'),
                             ('p { font-size: 17px; }', 'compiled font'),
                             ('p { flex-wrap: wrap-reverse; }', 'Unsupported value')]:
            with self.subTest(css=css), self.assertRaisesRegex(CompileError, message) as error:
                self.compile('<p>X</p><button>Go</button>', css)
            self.assertIn('ui.css:1:', str(error.exception))

    def test_missing_font_is_diagnosed(self):
        with self.assertRaisesRegex(CompileError, 'additional font'):
            self.compile('<p>温度</p>')

    def test_cpp_strings_do_not_allow_literal_or_escape_injection(self):
        self.assertEqual(cpp_string('"\\\n\x01f'), '"\\"\\\\\\012\\001f"')
        self.assertEqual(cpp_string('??/'), '"\\?\\?/"')
        result = self.compile('<button id="a&quot;">Go</button>')
        self.assertIn('bind(1, "a\\""', generate(result)['counter.cpp'])

    def test_name_and_viewport_validation(self):
        for kwargs in [{"name": "class"}, {"name": "char32_t"}, {"name": "bad-name"}, {"width": 0}, {"height": 4097}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(CompileError):
                self.compile('<span>X</span>', **kwargs)

    def test_generated_output_is_reproducible_across_directories(self):
        a = generate(self.compile('<button id="go">Go</button>'))
        with tempfile.TemporaryDirectory() as elsewhere:
            other = Path(elsewhere)
            for source in self.root.iterdir():
                (other / source.name).write_bytes(source.read_bytes())
            b = generate(compile_document(other / 'ui.html'))
        self.assertEqual(a, b)
        manifest = json.loads(a['counter.json'])
        self.assertEqual(manifest['ids'], ['go'])
        self.assertEqual(manifest['dependencies']['html5lib'], '1.1')

    def test_failed_cli_compile_keeps_previous_outputs(self):
        self.compile('<p>X</p>')
        output = self.root / 'generated'
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['compile', str(self.root / 'ui.html'), '--output', str(output)]), 0)
        original = (output / 'counter.cpp').read_bytes()
        (self.root / 'ui.css').write_text('p { width: garbage; }', encoding='utf-8')
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['compile', str(self.root / 'ui.html'), '--output', str(output)]), 1)
        self.assertEqual((output / 'counter.cpp').read_bytes(), original)

    def test_unsupported_literal_value_is_diagnosed_in_unused_rule(self):
        with self.assertRaisesRegex(CompileError, 'Unsupported value'):
            self.compile('<p>X</p>', '.unused { width: 1em; }')

    def test_sample_compiles(self):
        example = Path(__file__).resolve().parents[1] / 'examples/counter/ui.html'
        doc = compile_document(example)
        self.assertEqual(len(doc.nodes), 11)
        self.assertEqual([node.id for node in doc.nodes if node.id], ['value', 'increment', 'reset'])


if __name__ == '__main__':
    unittest.main()
