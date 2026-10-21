"""Builder and delivery contracts, using original synthetic game snippets."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from clausewitz import parse, walk

spec = importlib.util.spec_from_file_location('hro_builder_for_tests', ROOT / 'overhaul/tools/build_overhaul.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def tree(tag):
    return f'''# Synthetic fixture; not a Paradox file.
focus_tree = {{
 id = SYNTH_{tag}
 country = {{ factor = 0 modifier = {{ add = 10 original_tag = {tag} }} }}
 focus = {{
  id = {tag}_anchor x = 2 y = 0 cost = 10
  available = {{ has_war = no }}
  bypass = {{ has_capitulated = yes }}
  completion_reward = {{ add_political_power = 13 }}
 }}
}}
'''


def catalog(tag):
    stem = tag.lower()
    return {
        'tag': tag,
        'focuses': [{
            'id': f'hro_{stem}_test', 'branch': 'industry', 'row': 1, 'cost': 3,
            'name_ru': 'Проверка', 'name_en': 'Test', 'desc_ru': 'Программа.', 'desc_en': 'Programme.',
            'prerequisites': [[f'{tag}_anchor']], 'reward': 'add_political_power = 5',
        }],
        'ideas': [],
        'native_patches': [{
            'id': f'{tag}_anchor', 'cost': 5, 'earliest': '1938.1.1',
            'extra_reward': 'hro_test_progress = yes',
        }],
    }


class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.game = self.base / 'game'
        directory = self.game / 'common/national_focus'
        directory.mkdir(parents=True)
        for tag, filename in (('GER', 'germany.txt'), ('SOV', 'soviet.txt')):
            (directory / filename).write_text(tree(tag), encoding='utf-8')
        self.output = self.base / 'output'
        self.output.mkdir()

    def test_native_overlay_keeps_original_rewards_conditions_and_ids(self):
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in (self.game / 'common/national_focus').glob('*.txt')}
        report, offsets = builder.native_overlay(self.output, self.game, [catalog('GER'), catalog('SOV')])
        self.assertEqual(report['original_focus_counts'], {'GER': 1, 'SOV': 1})
        self.assertEqual(offsets, {'GER': 16, 'SOV': 16})
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in (self.game / 'common/national_focus').glob('*.txt')}
        self.assertEqual(before, after)
        document = parse((self.output / 'common/national_focus/germany.txt').read_text(encoding='utf-8-sig'))
        focus = next(n for n in walk(document) if n.key == 'focus' and n.scalar('id') == 'GER_anchor')
        self.assertEqual(focus.scalar('cost'), '5')
        self.assertEqual(focus.one('completion_reward').scalar('add_political_power'), '13')
        self.assertEqual(focus.one('completion_reward').scalar('hro_test_progress'), 'yes')
        self.assertEqual(focus.one('available').scalar('has_war'), 'no')
        self.assertEqual(focus.one('bypass').scalar('has_capitulated'), 'yes')
        self.assertIsNotNone(focus.one('available').one('OR'))

    def test_unknown_native_id_stops_overlay(self):
        changed = catalog('GER')
        changed['native_patches'][0]['id'] = 'GER_does_not_exist'
        with self.assertRaisesRegex(ValueError, 'Unknown native patch IDs'):
            builder.native_overlay(self.output, self.game, [changed, catalog('SOV')])

    def test_generated_focus_uses_or_within_and_between_prerequisite_groups(self):
        catalogs = [catalog('GER'), catalog('SOV')]
        catalogs[0]['focuses'][0]['prerequisites'] = [['GER_a', 'GER_b'], ['GER_c']]
        builder.author_country_content(self.output, catalogs, {'GER': 10, 'SOV': 20})
        document = parse((self.output / 'common/national_focus/hro_country_focuses.txt').read_text())
        focus = document[0]
        self.assertEqual([[n.value for n in p.all('focus')] for p in focus.all('prerequisite')],
                         [['GER_a', 'GER_b'], ['GER_c']])

    def test_main_tree_rewiring_and_absolute_layout_preserve_native_cleanup(self):
        path = self.game / 'common/national_focus/germany.txt'
        source = tree('GER').replace('focus_tree = {',
            'focus_tree = { focus = { id = GER_root x = 0 y = 0 cost = 5 }', 1)
        path.write_text(source.replace('id = GER_anchor x = 2 y = 0 cost = 10',
            'id = GER_anchor x = 2 y = 0 cost = 10 relative_position_id = GER_root '
            'prerequisite = { focus = GER_before } prerequisite = { focus = GER_old }'), encoding='utf-8')
        catalogs = [catalog('GER'), catalog('SOV')]
        patch = catalogs[0]['native_patches'][0]
        patch.update(prerequisites=[['hro_ger_route_a', 'hro_ger_route_b'], ['GER_core']],
                     x=4, y=6, relative_position_id=None, icon='GFX_focus_generic_industry_1')
        report, _ = builder.native_overlay(self.output, self.game, catalogs)
        native = next(f for f in parse((self.output / 'common/national_focus/germany.txt').read_text(encoding='utf-8-sig'))[0].all('focus')
                      if f.scalar('id') == 'GER_anchor')
        self.assertEqual([[n.value for n in p.all('focus')] for p in native.all('prerequisite')],
                         [['hro_ger_route_a', 'hro_ger_route_b'], ['GER_core']])
        self.assertEqual((native.scalar('x'), native.scalar('y')), ('4', '6'))
        self.assertIsNone(native.one('relative_position_id'))
        self.assertEqual(native.one('completion_reward').scalar('add_political_power'), '13')
        self.assertEqual(native.one('bypass').scalar('has_capitulated'), 'yes')
        self.assertEqual(native.one('available').scalar('has_war'), 'no')
        self.assertEqual(report['native_prerequisite_rewrites'], 1)

    def test_native_audit_rejects_undeclared_effect_or_graph_changes(self):
        original = parse(tree('GER'))
        changed = parse(tree('GER').replace('add_political_power = 13', 'add_political_power = 999'))
        with self.assertRaisesRegex(ValueError, 'Unexpected change'):
            builder.verify_native_preservation(original, changed, [])
        changed = parse(tree('GER').replace('x = 2', 'x = 4'))
        with self.assertRaisesRegex(ValueError, 'differs from declaration'):
            builder.verify_native_preservation(original, changed, [{'id': 'GER_anchor', 'x': 5}])

    def test_new_focus_renders_native_anchor_and_varied_icon(self):
        catalogs = [catalog('GER'), catalog('SOV')]
        catalogs[0]['focuses'][0].update(x=-2, y=1, relative_position_id='GER_anchor',
                                      icon='GFX_focus_GER_four_year_plan')
        builder.author_country_content(self.output, catalogs, {'GER': 100, 'SOV': 200})
        focus = parse((self.output / 'common/national_focus/hro_country_focuses.txt').read_text())[0]
        self.assertEqual((focus.scalar('x'), focus.scalar('y')), ('-2', '1'))
        self.assertEqual(focus.scalar('relative_position_id'), 'GER_anchor')
        self.assertEqual(focus.scalar('icon'), 'GFX_focus_GER_four_year_plan')

    def test_native_overlay_moves_continuous_panel_after_expanded_shared_rows(self):
        path = self.game / 'common/national_focus/germany.txt'
        original = tree('GER').replace('id = SYNTH_GER',
            'continuous_focus_position = { x = 500 y = 1300 } id = SYNTH_GER')
        path.write_text(original, encoding='utf-8')
        catalogs = [catalog('GER'), catalog('SOV')]
        catalogs[0]['focuses'][0].update(x=2, y=30)
        report, _ = builder.native_overlay(self.output, self.game, catalogs)
        compiled = parse((self.output / 'common/national_focus/germany.txt').read_text(encoding='utf-8-sig'))[0]
        self.assertEqual(compiled.one('continuous_focus_position').scalar('x'), '500')
        self.assertEqual(compiled.one('continuous_focus_position').scalar('y'), '4290')
        self.assertEqual(path.read_text(), original)
        self.assertEqual(report['continuous_focus_layout']['GER']['max_base_focus_y'], 30)

    def test_source_audit_rejects_undeclared_or_incorrect_continuous_panel_edit(self):
        original = tree('GER').replace('id = SYNTH_GER',
            'continuous_focus_position = { x = 500 y = 1300 } id = SYNTH_GER')
        changed = original.replace('y = 1300', 'y = 3900')
        with self.assertRaisesRegex(ValueError, 'Native tree fields'):
            builder.verify_native_preservation(parse(original), parse(changed), [])
        with self.assertRaisesRegex(ValueError, 'differs from declared'):
            builder.verify_native_preservation(parse(original), parse(changed), [],
                {'SYNTH_GER': {'x': 500, 'y': 999}})

    def test_combined_reform_envelope_counts_one_tier_and_war_reward(self):
        catalogs = [catalog('GER')]
        catalogs[0]['ideas'] = [
            {'family': 'hro_family_a', 'modifiers': {'industrial_capacity_factory': .08}},
            {'family': 'hro_family_a', 'modifiers': {'industrial_capacity_factory': .25}},
            {'family': 'hro_family_b', 'modifiers': {'industrial_capacity_factory': .05}},
        ]
        result = builder.permanent_reform_envelopes(catalogs,
            {'permanent_rewards': {'GER': {'industrial_capacity_factory': .10}}})
        self.assertEqual(result['countries']['GER']['industrial_capacity_factory'], .40)
        with self.assertRaisesRegex(ValueError, 'Combined permanent HRO bonus budget exceeded'):
            builder.permanent_reform_envelopes(catalogs,
                {'permanent_rewards': {'GER': {'industrial_capacity_factory': .30}}})

    def test_layout_audit_rejects_new_overlap(self):
        preview = builder.module('hro_preview_for_tests', ROOT / 'overhaul/tools/preview_trees.py')
        schematic = {'countries': {tag: {'new_vs_native_collision_candidates': [],
                                         'new_vs_new_collisions': [],
                                         'positions': {tag + '_anchor': [2, 0]}}
                                  for tag in ('GER', 'SOV')}}
        checked = builder.audit_integrated_layout(self.game, preview, schematic)
        self.assertEqual(checked['countries']['GER']['new_native_overlaps'], 0)
        schematic['countries']['GER']['new_vs_native_collision_candidates'] = [{'new': 'hro_ger_test'}]
        with self.assertRaisesRegex(ValueError, 'New focus base-layout overlaps'):
            builder.audit_integrated_layout(self.game, preview, schematic)
        schematic['countries']['GER']['new_vs_native_collision_candidates'] = []
        schematic['countries']['GER']['continuous_focus_panel'] = {'safe_below_all_focuses': False}
        with self.assertRaisesRegex(ValueError, 'Continuous focus panel can overlap'):
            builder.audit_integrated_layout(self.game, preview, schematic)

    def test_layout_audit_checks_newly_colliding_original_focuses(self):
        preview = builder.module('hro_preview_for_native_tests', ROOT / 'overhaul/tools/preview_trees.py')
        path = self.game / 'common/national_focus/germany.txt'
        path.write_text(tree('GER').replace('focus_tree = {',
            'focus_tree = { focus = { id = GER_leaf x = 4 y = 0 cost = 5 }', 1), encoding='utf-8')
        schematic = {'countries': {tag: {'new_vs_native_collision_candidates': [],
                                         'new_vs_new_collisions': [],
                                         'positions': {tag + '_anchor': [2, 0]}}
                                  for tag in ('GER', 'SOV')}}
        schematic['countries']['GER']['positions']['GER_leaf'] = [2, 0]
        with self.assertRaisesRegex(ValueError, 'Introduced native base-layout overlaps'):
            builder.audit_integrated_layout(self.game, preview, schematic)

    def test_same_tier_specialisations_are_in_setter_guard(self):
        catalogs = [catalog('GER'), catalog('SOV')]
        variants = []
        for identity in ('hro_idea_ger_a', 'hro_idea_ger_b'):
            variants.append({'id': identity, 'tag': 'GER', 'family': 'hro_family_test', 'stage': 3,
                             'name_ru': 'Выбор', 'name_en': 'Choice', 'desc_ru': 'Выбор.', 'desc_en': 'Choice.',
                             'modifiers': {'planning_speed': 0.01}})
        catalogs[0]['ideas'] = variants
        builder.author_country_content(self.output, catalogs, {'GER': 10, 'SOV': 20})
        document = parse((self.output / 'common/scripted_effects/hro_country_progression.txt').read_text())
        setter = next(n for n in document if n.key == 'hro_set_hro_idea_ger_a')
        guard = setter.one('if').one('limit')
        references = {n.value for n in walk(guard.value) if n.key == 'has_idea'}
        self.assertEqual(references, {'hro_idea_ger_a', 'hro_idea_ger_b'})

    def test_package_is_portable_and_has_no_installer(self):
        (self.output / 'OVERHAUL_BUILD_REPORT.json').write_text('{}')
        (self.output / 'descriptor.mod').write_text('name="Test"\nversion="0.2.0"\n')
        (self.output / 'README_RU.md').write_text('Read me.')
        archive = builder.package(self.output, self.base / 'release.zip')
        with zipfile.ZipFile(archive) as z:
            self.assertIsNone(z.testzip())
            self.assertIn('historical_reality_overhaul.mod', z.namelist())
            descriptor = z.read('historical_reality_overhaul.mod').decode('utf-8')
            self.assertIn('path="mod/historical_reality_overhaul"', descriptor)
            self.assertNotIn(str(self.base), descriptor)
            self.assertFalse(any(n.endswith(('.cmd', '.py')) for n in z.namelist()))

    def test_existing_archive_is_never_overwritten(self):
        (self.output / 'OVERHAUL_BUILD_REPORT.json').write_text('{}')
        path = self.base / 'release.zip'
        path.write_bytes(b'preserve')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            builder.package(self.output, path)
        self.assertEqual(path.read_bytes(), b'preserve')

    def test_unbuilt_source_folder_is_not_packaged(self):
        with self.assertRaisesRegex(ValueError, 'validated overhaul build'):
            builder.package(self.output, self.base / 'release.zip')


if __name__ == '__main__':
    unittest.main()
