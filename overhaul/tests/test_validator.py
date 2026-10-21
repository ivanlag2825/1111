"""Synthetic script contracts; no game files and no assumption of 160 fixtures."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'overhaul/tools'))
from validate_overhaul import validate


def write(path, text, bom=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8-sig' if bom else 'utf-8')


def focus(identity, branch, prerequisites, reward, row=1):
    return {'id': identity, 'branch': branch, 'row': row, 'cost': 3,
            'name_ru': 'Название ' + identity, 'name_en': 'Title ' + identity,
            'desc_ru': 'Описание ' + identity, 'desc_en': 'Description ' + identity,
            'prerequisites': prerequisites, 'reward': reward}


def fixture(base, ger=None, sov=None):
    root = base / 'mod'
    catalogs = base / 'catalogues'
    family = 'hro_family_ger_industry'
    ideas = []
    for stage, output in ((0, -0.02), (1, 0), (2, 0.04)):
        identity = 'hro_idea_ger_industry_' + str(stage)
        ideas.append({'id': identity, 'family': family, 'stage': stage, 'tag': 'GER',
                      'initial': stage == 0, 'name_ru': 'Дух ' + str(stage), 'name_en': 'Spirit ' + str(stage),
                      'desc_ru': 'Описание духа ' + str(stage), 'desc_en': 'Spirit description ' + str(stage),
                      'modifiers': {'industrial_capacity_factory': output}})
    default_ger = {'tag': 'GER', 'focuses': [
        focus('hro_ger_early', 'industry', [['GER_A', 'GER_B']],
              'hro_set_hro_idea_ger_industry_1 = yes country_event = { id = hro.1 days = 1 }'),
        focus('hro_ger_late', 'industry', [['hro_ger_early']],
              'hro_set_hro_idea_ger_industry_2 = yes', 2),
    ], 'ideas': ideas, 'native_patches': [{'id': 'GER_A', 'cost': 5}]}
    default_sov = {'tag': 'SOV', 'focuses': [
        focus('hro_sov_training', 'army', [['SOV_A']], 'army_experience = 10')
    ], 'ideas': [], 'native_patches': [{'id': 'SOV_A', 'cost': 5}]}
    ger = copy.deepcopy(default_ger if ger is None else ger)
    sov = copy.deepcopy(default_sov if sov is None else sov)
    for data in (ger, sov):
        write(catalogs / (data['tag'].lower() + '.json'), json.dumps(data, ensure_ascii=False))
    def native(data, identity, x, mutex=None):
        patch = next((p for p in data['native_patches'] if p['id'] == identity), {})
        fields = ['id = ' + identity, 'x = ' + str(patch.get('x', x)),
                  'y = ' + str(patch.get('y', 0)), 'cost = ' + str(patch.get('cost', 5))]
        if mutex:
            fields.append('mutually_exclusive = { focus = ' + mutex + ' }')
        for group in patch.get('prerequisites', []):
            fields.append('prerequisite = { ' + ' '.join('focus = ' + p for p in group) + ' }')
        for key in ('relative_position_id', 'icon'):
            if patch.get(key):
                fields.append(key + ' = ' + patch[key])
        return 'focus = { ' + ' '.join(fields) + ' }'
    write(root / 'common/national_focus/germany.txt', '''focus_tree = {
        id = german_focus country = { factor = 0 modifier = { add = 10 tag = GER } }
        ''' + native(ger, 'GER_A', 0, 'GER_B') + '\n' + native(ger, 'GER_B', 2, 'GER_A') + '\n' +
        '\n'.join('shared_focus = ' + f['id'] for f in ger['focuses']) + '\n}')
    write(root / 'common/national_focus/soviet.txt', '''focus_tree = {
        id = soviet_focus country = { factor = 0 modifier = { add = 10 tag = SOV } }
        ''' + native(sov, 'SOV_A', 0) + '\n' +
        '\n'.join('shared_focus = ' + f['id'] for f in sov['focuses']) + '\n}')
    blocks = []
    locales = {'russian': {}, 'english': {}}
    for data in (ger, sov):
        for f in data['focuses']:
            groups = '\n'.join('prerequisite = { ' + ' '.join('focus = ' + p for p in g) + ' }'
                               for g in f['prerequisites'])
            mutex = 'mutually_exclusive = { ' + ' '.join('focus = ' + p for p in f.get('mutually_exclusive', [])) + ' }' if f.get('mutually_exclusive') else ''
            layout = ' x = ' + str(f.get('x', 20)) + ' y = ' + str(f.get('y', f.get('row', 1)))
            if f.get('relative_position_id'):
                layout += ' relative_position_id = ' + f['relative_position_id']
            if f.get('icon'):
                layout += ' icon = ' + f['icon']
            blocks.append('shared_focus = { id = ' + f['id'] + ' cost = ' + str(f['cost']) +
                          layout + ' ' + groups + ' ' + mutex +
                          ' available = { has_capitulated = no } completion_reward = { ' + f['reward'] + ' } }')
            for language, suffix in (('russian', 'ru'), ('english', 'en')):
                locales[language][f['id']] = f['name_' + suffix]
                locales[language][f['id'] + '_desc'] = f['desc_' + suffix]
    write(root / 'common/national_focus/hro_focuses.txt', '\n'.join(blocks))
    ideas_text, setters = [], []
    all_ideas = ger['ideas'] + sov['ideas']
    for idea in all_ideas:
        identity = idea['id']
        modifiers = ' '.join(k + ' = ' + str(v) for k, v in idea['modifiers'].items())
        ideas_text.append(identity + ' = { modifier = { ' + modifiers + ' } }')
        family_members = [i for i in all_ideas if i['family'] == idea['family']]
        guard = ' '.join('has_idea = ' + i['id'] for i in family_members if i['stage'] >= idea['stage'])
        removals = ' '.join('remove_ideas = ' + i['id'] for i in family_members)
        setters.append('hro_set_' + identity + ' = { if = { limit = { NOT = { OR = { ' + guard +
                       ' } } } ' + removals + ' add_ideas = ' + identity + ' } }')
        for language, suffix in (('russian', 'ru'), ('english', 'en')):
            locales[language][identity] = idea['name_' + suffix]
            locales[language][identity + '_desc'] = idea['desc_' + suffix]
    write(root / 'common/ideas/hro_ideas.txt', 'ideas = { country = { ' + '\n'.join(ideas_text) + ' } }')
    write(root / 'common/scripted_effects/hro_progression.txt', '\n'.join(setters))
    write(root / 'events/hro_events.txt', '''add_namespace = hro
        country_event = { id = hro.1 title = hro.1.t desc = hro.1.d
        is_triggered_only = yes fire_only_once = yes
        option = { name = hro.1.a add_political_power = 5 }
        }''')
    for language in locales:
        locales[language].update({'hro.1.t': 'Event title', 'hro.1.d': 'Event description', 'hro.1.a': 'Continue'})
        text = 'l_' + language + ':\n' + ''.join(' ' + k + ':0 ' + json.dumps(v, ensure_ascii=False) + '\n' for k, v in locales[language].items())
        write(root / f'localisation/{language}/hro_test_l_{language}.yml', text, True)
    return root, catalogs, ger, sov


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.mod, self.catalogues, self.ger, self.sov = fixture(self.base)

    def assert_invalid(self, fragment, with_catalogues=True):
        with self.assertRaisesRegex(ValueError, fragment):
            validate(self.mod, self.catalogues if with_catalogues else None)

    def replace(self, relative, old, new):
        p = self.mod / relative
        text = p.read_text(encoding='utf-8-sig')
        self.assertIn(old, text)
        p.write_text(text.replace(old, new), encoding='utf-8-sig')

    def test_valid_small_catalogue_and_or_alternative(self):
        result = validate(self.mod, self.catalogues)
        self.assertEqual(result['authored_focuses'], 3)
        self.assertEqual(result['focuses_per_country'], {'GER': 2, 'SOV': 1})
        self.assertEqual(result['native_focuses'], 3)
        self.assertEqual(result['idea_families'], 1)
        self.assertFalse(result['runtime_verified'])

    def test_mutually_exclusive_native_prerequisites_cannot_both_be_required(self):
        self.ger['focuses'][0]['prerequisites'] = [['GER_A'], ['GER_B']]
        fixture(self.base, self.ger, self.sov)
        self.assert_invalid('Unreachable focus')

    def test_or_group_is_not_mistaken_for_and(self):
        # GER_A and GER_B exclude each other, but either suffices.
        result = validate(self.mod, self.catalogues)
        self.assertEqual(result['authored_focuses'], 3)

    def test_new_focus_cycle_is_rejected(self):
        self.ger['focuses'][0]['prerequisites'] = [['hro_ger_late']]
        fixture(self.base, self.ger, self.sov)
        self.assert_invalid('prerequisite cycle')

    def test_cycle_through_a_rewired_native_focus_is_rejected(self):
        self.ger['native_patches'][0]['prerequisites'] = [['hro_ger_late']]
        fixture(self.base, self.ger, self.sov)
        self.assert_invalid('prerequisite cycle')

    def test_unknown_native_prerequisite_is_rejected(self):
        self.ger['native_patches'][0]['prerequisites'] = [['GER_missing']]
        fixture(self.base, self.ger, self.sov)
        self.assert_invalid('Unknown prerequisite GER_missing in GER_A')

    def test_missing_native_anchor_is_rejected(self):
        self.ger['focuses'][0]['prerequisites'] = [['GER_missing']]
        fixture(self.base, self.ger, self.sov)
        self.assert_invalid('Unknown prerequisite')

    def test_asymmetric_mutual_exclusion_is_rejected(self):
        self.ger['focuses'][0]['mutually_exclusive'] = ['hro_ger_late']
        fixture(self.base, self.ger, self.sov)
        self.assert_invalid('Asymmetric mutually exclusive')

    def test_unknown_scripted_effect_is_rejected(self):
        self.replace('common/national_focus/hro_focuses.txt', 'army_experience = 10', 'hro_missing_effect = yes')
        self.assert_invalid('Unknown overhaul scripted call')

    def test_unknown_event_is_rejected(self):
        self.replace('common/national_focus/hro_focuses.txt', 'id = hro.1 days', 'id = hro.999 days')
        self.assert_invalid('Unknown overhaul event')

    def test_unknown_idea_is_rejected(self):
        self.replace('common/national_focus/hro_focuses.txt', 'army_experience = 10', 'add_ideas = hro_idea_missing')
        self.assert_invalid('Unknown overhaul idea')

    def test_unwritten_unlock_flag_is_rejected(self):
        self.replace('common/national_focus/hro_focuses.txt',
                     'available = { has_capitulated = no }',
                     'available = { has_capitulated = no has_country_flag = hro_wrong_unlock }')
        self.assert_invalid('country flag is read but never set: hro_wrong_unlock')

    def test_localisation_requires_bom(self):
        p = self.mod / 'localisation/russian/hro_test_l_russian.yml'
        p.write_text(p.read_text(encoding='utf-8-sig'), encoding='utf-8')
        self.assert_invalid('missing UTF-8 BOM')

    def test_duplicate_localisation_keys_are_rejected(self):
        p = self.mod / 'localisation/english/hro_test_l_english.yml'
        with p.open('a', encoding='utf-8') as stream:
            stream.write(' hro.1.a:0 "Duplicate"\n')
        self.assert_invalid('Duplicate english localisation key')

    def test_missing_localisation_is_rejected(self):
        p = self.mod / 'localisation/russian/hro_test_l_russian.yml'
        text = p.read_text(encoding='utf-8-sig')
        p.write_text('\n'.join(line for line in text.splitlines() if not line.startswith(' hro.1.a:')) + '\n', encoding='utf-8-sig')
        self.assert_invalid('Missing russian localisation: hro.1.a')

    def test_initial_debuff_budget_is_enforced(self):
        self.ger['ideas'][0]['modifiers']['industrial_capacity_factory'] = -0.10
        fixture(self.base, self.ger, self.sov)
        self.assert_invalid('Initial debuff budget exceeded')

    def test_final_family_bonus_budget_is_enforced(self):
        self.ger['ideas'][2]['modifiers']['industrial_capacity_factory'] = 0.30
        fixture(self.base, self.ger, self.sov)
        self.assert_invalid('Final family bonus budget exceeded')

    def test_substantial_bounded_final_reform_is_allowed(self):
        self.ger['ideas'][2]['modifiers']['industrial_capacity_factory'] = 0.20
        fixture(self.base, self.ger, self.sov)
        self.assertEqual(validate(self.mod, self.catalogues)['ideas'], 3)

    def test_unguarded_setter_cannot_remove_a_higher_tier(self):
        self.replace('common/scripted_effects/hro_progression.txt',
                     'hro_set_hro_idea_ger_industry_1 = { if = { limit = { NOT = { OR = { has_idea = hro_idea_ger_industry_1 has_idea = hro_idea_ger_industry_2 } } }',
                     'hro_set_hro_idea_ger_industry_1 = { if = { limit = { always = yes }')
        self.assert_invalid('Family setter can regress stage')

    def test_same_tier_choice_is_not_overwritten(self):
        alternative = copy.deepcopy(self.ger['ideas'][2])
        alternative['id'] = 'hro_idea_ger_industry_alternative'
        self.ger['ideas'].append(alternative)
        fixture(self.base, self.ger, self.sov)
        result = validate(self.mod, self.catalogues)
        self.assertEqual(result['ideas'], 4)

    def test_wrong_country_attachment_is_rejected(self):
        self.replace('common/national_focus/germany.txt', 'tag = GER', 'tag = SOV')
        self.assert_invalid('attached to wrong country')

    def test_catalogue_and_compiled_graph_cannot_diverge(self):
        self.replace('common/national_focus/hro_focuses.txt', 'focus = GER_A focus = GER_B', 'focus = GER_A')
        self.assert_invalid('Compiled prerequisites differ')

    def test_duplicate_focus_layout_is_rejected(self):
        self.ger['focuses'][1]['row'] = 1
        fixture(self.base, self.ger, self.sov)
        self.assert_invalid('Overlapping catalogue focus positions')

    def test_explicit_positions_can_anchor_to_retained_native_focuses(self):
        for number, f in enumerate(self.ger['focuses'], 1):
            f.pop('row')
            f.update(x=0, y=number, relative_position_id='GER_A', icon='GFX_goal_generic_army_doctrines')
        fixture(self.base, self.ger, self.sov)
        self.assertEqual(validate(self.mod, self.catalogues)['authored_focuses'], 3)

    def test_distinct_layout_anchors_cannot_hide_an_overlap(self):
        self.ger['focuses'][0].update(x=2, y=1, relative_position_id='GER_A')
        self.ger['focuses'][1].update(x=0, y=1, relative_position_id='GER_B')
        fixture(self.base, self.ger, self.sov)
        self.assert_invalid('Overlapping catalogue focus positions')

    def test_relative_layout_cycles_are_rejected(self):
        self.ger['focuses'][0].update(x=0, y=1, relative_position_id='hro_ger_late')
        self.ger['focuses'][1].update(x=0, y=1, relative_position_id='hro_ger_early')
        fixture(self.base, self.ger, self.sov)
        self.assert_invalid('layout anchor cycle')

    def test_compiled_native_layout_must_match_catalogue_patch(self):
        self.ger['native_patches'][0].update(x=3, y=1)
        fixture(self.base, self.ger, self.sov)
        self.replace('common/national_focus/germany.txt', 'x = 3 y = 1', 'x = 4 y = 1')
        self.assert_invalid('Compiled native coordinates differ')

    def test_compiled_native_graph_must_match_catalogue_patch(self):
        self.sov['native_patches'][0]['prerequisites'] = []
        fixture(self.base, self.ger, self.sov)
        self.replace('common/national_focus/soviet.txt', 'cost = 5 }', 'cost = 5 prerequisite = { focus = GER_A } }')
        self.assert_invalid('Compiled native prerequisites differ')

    def milestone_fixture(self, groups):
        declaration = {'native': 'GER_C', 'requires': 'hro_ger_early'}
        self.ger['integrated_milestones'] = [declaration]
        self.ger['native_patches'].append({'id': 'GER_C', 'prerequisites': groups})
        fixture(self.base, self.ger, self.sov)
        path = self.mod / 'common/national_focus/germany.txt'
        text = path.read_text(encoding='utf-8')
        prerequisites = ''.join(' prerequisite = { ' + ' '.join('focus = ' + parent for parent in group) + ' }'
                                for group in groups)
        text = text.rstrip()[:-1] + '\n focus = { id = GER_C x = 8 y = 9 cost = 5' + prerequisites + ' }\n}'
        path.write_text(text, encoding='utf-8')

    def test_integrated_native_milestone_requires_new_core_transitively(self):
        self.milestone_fixture([['hro_ger_late']])
        result = validate(self.mod, self.catalogues)
        self.assertEqual(result['required_integrated_milestones'], 1)
        self.assertEqual(result['native_prerequisite_patches'], 1)

    def test_optional_or_side_branch_cannot_claim_main_tree_integration(self):
        self.milestone_fixture([['hro_ger_late', 'GER_A']])
        self.assert_invalid('can skip its required authored focus')

    def test_and_requirement_remains_mandatory_beside_other_native_path(self):
        self.milestone_fixture([['hro_ger_late'], ['GER_A', 'GER_B']])
        self.assertEqual(validate(self.mod, self.catalogues)['required_integrated_milestones'], 1)

    def test_unreachable_integrated_milestone_is_not_accepted_as_mandatory(self):
        self.milestone_fixture([['hro_ger_late'], ['GER_A'], ['GER_B']])
        self.assert_invalid('Integrated native milestone is unreachable')

    def test_numeric_formatting_roundoff_does_not_change_bonus_contract(self):
        self.ger['ideas'][2]['modifiers']['industrial_capacity_factory'] = 0.1 + 0.02
        fixture(self.base, self.ger, self.sov)
        self.replace('common/ideas/hro_ideas.txt', 'industrial_capacity_factory = 0.12000000000000001',
                     'industrial_capacity_factory = 0.12')
        result = validate(self.mod, self.catalogues)
        self.assertEqual(result['ideas'], 3)

    def test_programme_needs_a_completion_effect(self):
        write(self.mod / 'common/decisions/hro_programmes.txt', '''hro_category = {
            hro_programme = { cost = 50 days_remove = 30 complete_effect = { add_political_power = -1 } }
        }''')
        self.assert_invalid('Timed programme missing remove_effect')

    def test_build_placeholders_are_rejected(self):
        self.replace('common/national_focus/hro_focuses.txt', 'x = 20', 'x = @HRO_OFFSET@')
        self.assert_invalid('Unresolved build placeholder')

    def test_optional_keyword_audit_reports_invalid_engine_effect(self):
        self.replace('common/national_focus/hro_focuses.txt', 'army_experience = 10', 'totally_invalid_effect = 10')
        schema = self.base / 'schema/Config'
        schema.mkdir(parents=True)
        write(schema / 'test.cwt', '''alias[effect:if] = bool
alias[effect:remove_ideas] = scalar
alias[effect:add_ideas] = scalar
alias[effect:country_event] = scalar
alias[effect:add_political_power] = scalar
alias[effect:army_experience] = scalar
alias[trigger:has_idea] = scalar
alias[trigger:has_capitulated] = bool
industrial_capacity_factory = country
''')
        with self.assertRaisesRegex(ValueError, 'Unknown upstream effect keyword: totally_invalid_effect'):
            validate(self.mod, self.catalogues, schema.parent)


if __name__ == '__main__':
    unittest.main()
