"""Regression checks for the native panel covering expanded main focuses."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'overhaul/tools')]
from clausewitz import parse
from native_layout_fix import choose_continuous_position, continuous_layout_report


def focuses(text):
    return {node.scalar('id'): node for node in parse(text)}


class ContinuousLayoutTests(unittest.TestCase):
    def test_panel_moves_below_expanded_graph_without_changing_native_x(self):
        graph = focuses('focus={id=GER_army y=19} focus={id=GER_inner_circle y=27}')
        position = choose_continuous_position(graph, {'x': 500, 'y': 1300})
        self.assertEqual(position, {'x': 500, 'y': 3900})
        self.assertGreater(position['y'], 27 * 130 + 250)

    def test_node_position_input_and_already_safe_native_position_are_preserved(self):
        graph = focuses('focus={id=A y=2}')
        panel = parse('continuous_focus_position={x=55 y=5000}')[0]
        self.assertEqual(choose_continuous_position(graph, panel), {'x': 55, 'y': 5000})

    def test_conditional_offsets_follow_relative_parent_chain(self):
        graph = focuses('''focus={id=A y=3 offset={y=1 trigger={always=yes}}}
            focus={id=B relative_position_id=A y=4 offset={y=2 trigger={always=yes}}}
            focus={id=C relative_position_id=B y=5}''')
        report = continuous_layout_report(graph, {'x': 55, 'y': 1600})
        self.assertEqual(report['max_base_focus_y'], 12)
        self.assertEqual(report['max_conditional_focus_y'], 15)
        self.assertEqual(report['position']['y'], 18 * 130)

    def test_inactive_and_negative_offsets_do_not_hide_lower_focuses(self):
        graph = focuses('''focus={id=A y=10 offset={y=-5 trigger={always=no}}
            offset={y=2 trigger={always=no}} offset={y=3 trigger={always=no}}}''')
        report = continuous_layout_report(graph)
        self.assertEqual(report['max_conditional_focus_y'], 15)
        self.assertEqual(report['position']['y'], 18 * 130)

    def test_unknown_anchor_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unknown relative focus layout anchor'):
            choose_continuous_position(focuses('focus={id=A y=1 relative_position_id=missing}'))

    def test_anchor_cycle_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Cyclic relative focus layout'):
            choose_continuous_position(focuses('focus={id=A y=1 relative_position_id=B} focus={id=B relative_position_id=A y=1}'))

    def test_empty_or_invalid_geometry_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'without focus bounds'):
            choose_continuous_position({})
        with self.assertRaisesRegex(ValueError, 'Non-finite'):
            choose_continuous_position(focuses('focus={id=A y=nan}'))


if __name__ == '__main__':
    unittest.main()
