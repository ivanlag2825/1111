"""The preview must include the GUI panel that caused the reported overlap."""
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'overhaul/tools')]
from clausewitz import parse
from preview_trees import (continuous_panel_report, draw_country, generate,
                           load_continuous_positions, load_focuses, resolve_positions)


def fixture():
    return {n.scalar('id'): n for n in parse('focus={id=GER_army x=8 y=19 cost=5} focus={id=GER_inner_circle x=59 y=27 cost=5}')}


class PreviewPanelTests(unittest.TestCase):
    def test_old_overlay_is_reported_and_lowered_panel_passes(self):
        graph = fixture()
        old = continuous_panel_report(graph, {'x': 500, 'y': 1300})
        fixed = continuous_panel_report(graph, {'x': 500, 'y': 3900})
        self.assertFalse(old['safe_below_all_focuses'])
        self.assertTrue(fixed['safe_below_all_focuses'])
        self.assertEqual(fixed['required_top_gui_y'], 3900)
        self.assertEqual(fixed['position_gui'], {'x': 500, 'y': 3900})
        self.assertEqual(fixed['grid_bounds']['top'], 30)

    def test_preview_expands_around_complete_panel(self):
        graph = fixture()
        svg, dimensions = draw_country('GER', graph, resolve_positions(graph), set(), {}, {'x': 500, 'y': 3900})
        root = ET.fromstring(svg)
        panel = next(n for n in root if n.attrib.get('id') == 'continuous-panel-GER')
        rect = panel.find('{http://www.w3.org/2000/svg}rect')
        self.assertIsNotNone(rect)
        self.assertIn('safe', panel.attrib['class'])
        self.assertGreaterEqual(float(root.attrib['height']), float(rect.attrib['y']) + float(rect.attrib['height']))
        self.assertGreaterEqual(float(root.attrib['width']), float(rect.attrib['x']) + float(rect.attrib['width']))
        self.assertIn('Непрерывные фокусы', svg)
        _, old_dimensions = draw_country('GER', graph, resolve_positions(graph), set(), {})
        self.assertGreater(dimensions['height'], old_dimensions['height'])

    def test_conditional_focus_offset_is_included_in_clearance(self):
        graph = {n.scalar('id'): n for n in parse('focus={id=A x=0 y=4 offset={y=2 trigger={always=yes}}}')}
        report = continuous_panel_report(graph, {'x': 55, 'y': 1040})
        self.assertEqual(report['max_conditional_focus_y'], 6)
        self.assertFalse(report['safe_below_all_focuses'])
        self.assertEqual(report['required_top_gui_y'], 1170)

    def test_generate_reads_compiled_tree_field_without_changing_focus_api(self):
        with tempfile.TemporaryDirectory(prefix='hro-preview-test-') as temporary:
            mod = Path(temporary) / 'mod'
            directory = mod / 'common/national_focus'
            directory.mkdir(parents=True)
            for tag in ('GER', 'SOV'):
                (directory / (tag.lower() + '.txt')).write_text('''focus_tree={
                    id=test_''' + tag + ''' country={factor=0 modifier={add=10 original_tag=''' + tag + '''}}
                    continuous_focus_position={x=500 y=3900}
                    focus={id=''' + tag + '''_A x=8 y=27 cost=5}
                }''', encoding='utf-8')
            self.assertEqual(set(load_focuses(mod)), {'GER', 'SOV'})
            self.assertEqual(load_continuous_positions(mod)['GER'], {'x': 500, 'y': 3900})
            output = Path(temporary) / 'preview'
            report = generate(mod, output)
            for tag in ('GER', 'SOV'):
                self.assertTrue(report['countries'][tag]['continuous_focus_panel']['safe_below_all_focuses'])
                self.assertIn('continuous-panel-' + tag, (output / (tag + '_tree.svg')).read_text())
            html = (output / 'index.html').read_text()
            self.assertIn('id="continuous"', html)
            self.assertIn('разрешение игры не эмулируются', html)


if __name__ == '__main__':
    unittest.main()
