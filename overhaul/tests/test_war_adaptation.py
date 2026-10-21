"""Execute the emitted war lifecycle, not a second implementation of its rules.

This small interpreter checks dates, scopes, flags and idea transitions. It does
not model engine combat, the native DLC systems, event UI or multiplayer sync.
"""
from datetime import date, timedelta
import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from clausewitz import parse, walk

spec = importlib.util.spec_from_file_location('hro_war_generator_tests', ROOT / 'overhaul/tools/generate_war_adaptation.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


def day(value):
    return date(*map(int, value.split('.')))


class EmittedLifecycle:
    def __init__(self, output):
        self.effects = {n.key: n for n in parse((output / 'common/scripted_effects/hro_war_effects.txt').read_text())}
        self.triggers = {n.key: n for n in parse((output / 'common/scripted_triggers/hro_war_triggers.txt').read_text())}
        self.daily = parse((output / 'common/on_actions/hro_war_on_actions.txt').read_text())[0].one('on_daily').one('effect').value

    def flag(self, state, identity):
        if identity not in state['flags']:
            return False
        expires = state['flags'][identity]
        return expires is None or state['date'] < expires

    def condition(self, nodes, state, tag=None, previous=None):
        tag = tag or state['tag']
        def one(n):
            if n.key in ('AND', 'limit'):
                return self.condition(n.value, state, tag, previous)
            if n.key == 'OR':
                return any(one(child) for child in n.value)
            if n.key == 'NOT':
                return not self.condition(n.value, state, tag, previous)
            if n.key == 'original_tag':
                return tag == n.value
            if n.key == 'has_capitulated':
                capitulated = state['capitulated'] if tag == state['tag'] else state.get('enemy_capitulated', False)
                return capitulated == (n.value == 'yes')
            if n.key == 'date':
                target = day(n.value)
                return {'>': state['date'] > target, '<': state['date'] < target,
                        '=': state['date'] == target}[n.op]
            if n.key == 'has_country_flag':
                return self.flag(state, n.value)
            if n.key == 'has_idea':
                return n.value in state['ideas']
            if n.key == 'check_variable':
                def compare(child):
                    value, target = state['variables'].get(child.key, 0), float(child.value)
                    return {'>': value > target, '<': value < target,
                            '=': value == target, '>=': value >= target, '<=': value <= target}[child.op]
                return all(compare(child) for child in n.value)
            if n.key == 'any_enemy_country':
                enemy = 'GER' if tag == 'SOV' else 'SOV'
                return state['war'] and self.condition(n.value, state, enemy, tag)
            if n.key == 'has_offensive_war_with':
                return state['war'] and tag == state['aggressor'] and n.value == 'PREV' and previous != tag
            if n.key in self.triggers:
                result = self.condition(self.triggers[n.key].value, state, tag, previous)
                return result == (n.value == 'yes')
            raise AssertionError('Unsupported emitted condition: ' + str(n.key))
        return all(one(n) for n in nodes)

    def execute(self, nodes, state):
        prior = None
        for n in nodes:
            if n.key in ('if', 'else_if'):
                matched = (n.key == 'if' or prior is False) and self.condition(n.one('limit').value, state)
                if matched:
                    self.execute([child for child in n.value if child.key != 'limit'], state)
                prior = matched if n.key == 'if' else prior or matched
            elif n.key == 'else':
                if prior is False:
                    self.execute(n.value, state)
                prior = None
            elif n.key == 'set_country_flag':
                identity = n.value if isinstance(n.value, str) else n.scalar('flag')
                expiry = None if isinstance(n.value, str) or n.scalar('days') is None else state['date'] + timedelta(days=int(n.scalar('days')))
                state['flags'][identity] = expiry
            elif n.key == 'clr_country_flag':
                state['flags'].pop(n.value, None)
            elif n.key in ('set_variable', 'add_to_variable'):
                for child in n.value:
                    value = float(child.value)
                    state['variables'][child.key] = value if n.key == 'set_variable' else state['variables'].get(child.key, 0) + value
            elif n.key == 'add_ideas':
                state['ideas'].add(n.value)
            elif n.key == 'remove_ideas':
                state['ideas'].discard(n.value)
            elif n.key == 'country_event':
                state['events'].append(n.scalar('id'))
            elif n.key in self.effects and n.value == 'yes':
                self.execute(self.effects[n.key].value, state)
            else:
                raise AssertionError('Unsupported emitted effect: ' + str(n.key))

    def call(self, name, state):
        self.execute(self.effects[name].value, state)

    def tick(self, state, when=None):
        if when is not None:
            state['date'] = day(when)
        self.execute(self.daily, state)

    def advance(self, state, when):
        target = day(when)
        while state['date'] < target:
            state['date'] += timedelta(days=1)
            self.tick(state)


class WarAdaptationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name)
        generator.generate(self.output)
        self.runtime = EmittedLifecycle(self.output)

    def country(self, tag, when='1941.6.22', war=True, aggressor='GER'):
        return {'tag': tag, 'date': day(when), 'war': war, 'aggressor': aggressor,
                'capitulated': False, 'enemy_capitulated': False, 'flags': {}, 'variables': {},
                'ideas': {'SOV_native_restriction'}, 'events': []}

    def test_soviet_surprise_requires_defensive_first_eastern_war(self):
        sov = self.country('SOV')
        self.runtime.tick(sov)
        self.assertIn(generator.SOV_PENALTIES[0], sov['ideas'])
        self.assertIn('hro_war_sov_started', sov['flags'])
        offensive = self.country('SOV', aggressor='SOV')
        self.runtime.tick(offensive)
        self.assertTrue(self.runtime.flag(offensive, 'hro_war_sov_started'))
        self.assertFalse(set(generator.SOV_PENALTIES) & offensive['ideas'])
        self.assertFalse(offensive['events'])

    def test_prewar_completed_reform_waits_120_days_then_activates_without_reclick(self):
        sov = self.country('SOV', war=False)
        self.runtime.call('hro_war_sov_complete_adaptation', sov)
        self.assertNotIn('hro_idea_war_sov_adapted', sov['ideas'])
        sov['war'] = True
        self.runtime.tick(sov)
        self.runtime.advance(sov, '1941.10.19')  # 119 days after 22 June
        self.assertNotIn('hro_idea_war_sov_adapted', sov['ideas'])
        self.runtime.advance(sov, '1941.10.20')  # 120 days
        self.assertIn('hro_idea_war_sov_adapted', sov['ideas'])
        self.assertFalse(set(generator.SOV_PENALTIES) & sov['ideas'])
        self.assertIn('SOV_native_restriction', sov['ideas'])

    def test_preparation_mitigates_acute_crisis_without_skipping_timer(self):
        sov = self.country('SOV')
        self.runtime.tick(sov)
        self.runtime.call('hro_war_sov_reorganize_fronts', sov)
        self.assertIn(generator.SOV_PENALTIES[1], sov['ideas'])
        self.assertNotIn(generator.SOV_PENALTIES[0], sov['ideas'])
        self.runtime.call('hro_war_sov_complete_adaptation', sov)
        self.assertNotIn('hro_idea_war_sov_adapted', sov['ideas'])
        self.assertTrue(self.runtime.flag(sov, 'hro_war_sov_acute_phase'))

    def test_unreformed_crisis_softens_after_120_days_even_without_any_focus(self):
        sov = self.country('SOV')
        self.runtime.tick(sov)
        self.runtime.advance(sov, '1941.10.20')
        self.assertEqual(set(generator.SOV_PENALTIES) & sov['ideas'], {generator.SOV_PENALTIES[2]})
        self.runtime.call('hro_war_sov_reorganize_fronts', sov)
        self.assertFalse(set(generator.SOV_PENALTIES) & sov['ideas'])

    def test_offensive_soviet_alternative_can_earn_reform_without_surprise(self):
        sov = self.country('SOV', aggressor='SOV')
        self.runtime.call('hro_war_sov_complete_adaptation', sov)
        self.runtime.tick(sov)
        self.runtime.advance(sov, '1941.10.20')
        self.assertIn('hro_idea_war_sov_adapted', sov['ideas'])
        self.assertFalse(set(generator.SOV_PENALTIES) & sov['ideas'])

    def test_german_summer_war_does_not_apply_winter_until_november(self):
        ger = self.country('GER')
        self.runtime.tick(ger)
        self.assertFalse(set(generator.GER_PENALTIES) & ger['ideas'])
        self.runtime.tick(ger, '1941.10.31')
        self.assertFalse(set(generator.GER_PENALTIES) & ger['ideas'])
        self.runtime.tick(ger, '1941.11.1')
        self.assertIn(generator.GER_PENALTIES[0], ger['ideas'])
        self.runtime.tick(ger, '1942.1.1')
        self.assertIn(generator.GER_PENALTIES[0], ger['ideas'])
        self.runtime.tick(ger, '1942.4.1')
        self.assertFalse(set(generator.GER_PENALTIES) & ger['ideas'])

    def test_first_winter_and_later_winters_are_distinct(self):
        ger = self.country('GER', '1941.11.1')
        self.runtime.tick(ger)
        self.runtime.tick(ger, '1942.4.1')
        self.runtime.tick(ger, '1942.11.1')
        self.assertEqual(set(generator.GER_PENALTIES) & ger['ideas'], {generator.GER_PENALTIES[2]})
        self.assertEqual(ger['events'].count('hro.302'), 1)

    def test_winter_preparation_and_full_reform_remember_prewar_completion(self):
        ger = self.country('GER', war=False)
        self.runtime.call('hro_war_ger_prepare_winter', ger)
        self.runtime.call('hro_war_ger_complete_winter_adaptation', ger)
        self.assertNotIn('hro_idea_war_ger_adapted', ger['ideas'])
        ger['war'] = True
        self.runtime.tick(ger)
        self.assertNotIn('hro_idea_war_ger_adapted', ger['ideas'])
        self.runtime.tick(ger, '1941.11.1')
        self.assertNotIn('hro_idea_war_ger_adapted', ger['ideas'])
        self.runtime.advance(ger, '1941.12.15')
        self.assertNotIn('hro_idea_war_ger_adapted', ger['ideas'])
        self.runtime.advance(ger, '1941.12.16')
        self.assertIn('hro_idea_war_ger_adapted', ger['ideas'])
        self.assertFalse(set(generator.GER_PENALTIES) & ger['ideas'])

    def test_prepared_services_only_mitigate_without_full_logistics_reform(self):
        ger = self.country('GER', '1941.11.1')
        self.runtime.call('hro_war_ger_prepare_winter', ger)
        self.runtime.tick(ger)
        self.assertEqual(set(generator.GER_PENALTIES) & ger['ideas'], {generator.GER_PENALTIES[1]})
        self.runtime.call('hro_war_ger_complete_winter_adaptation', ger)
        self.assertNotIn('hro_idea_war_ger_adapted', ger['ideas'])
        self.runtime.advance(ger, '1941.12.16')
        self.assertIn('hro_idea_war_ger_adapted', ger['ideas'])
        self.assertFalse(set(generator.GER_PENALTIES) & ger['ideas'])

    def test_peace_capitulation_and_campaign_end_remove_only_new_penalties(self):
        for tag in ('GER', 'SOV'):
            for cause in ('peace', 'capitulation', 'campaign_end'):
                with self.subTest(tag=tag, cause=cause):
                    country = self.country(tag, '1941.11.1')
                    self.runtime.tick(country)
                    if cause == 'peace':
                        country['war'] = False
                    elif cause == 'capitulation':
                        country['capitulated'] = True
                    else:
                        country['date'] = day('1947.1.1')
                    self.runtime.tick(country)
                    self.assertFalse(set(generator.SOV_PENALTIES + generator.GER_PENALTIES) & country['ideas'])
                    self.assertIn('SOV_native_restriction', country['ideas'])

    def test_rewar_cannot_reset_soviet_timer_or_farm_completion_notifications(self):
        sov = self.country('SOV')
        self.runtime.tick(sov)
        self.runtime.advance(sov, '1941.6.30')
        self.assertEqual(sov['variables']['hro_war_sov_war_days'], 8)
        sov['war'] = False
        self.runtime.advance(sov, '1941.7.31')
        self.assertEqual(sov['variables']['hro_war_sov_war_days'], 8)
        sov['war'] = True
        self.runtime.advance(sov, '1941.8.30')
        self.assertEqual(sov['variables']['hro_war_sov_war_days'], 38)
        self.runtime.call('hro_war_sov_complete_adaptation', sov)
        self.runtime.advance(sov, '1941.11.20')
        self.assertEqual(sov['variables']['hro_war_sov_war_days'], 120)
        for _ in range(3):
            self.runtime.call('hro_war_sov_complete_adaptation', sov)
            self.runtime.tick(sov)
        self.assertEqual(sov['events'].count('hro.301'), 1)
        self.assertEqual(sov['events'].count('hro.303'), 1)

    def test_capitulated_opponent_clears_penalties_and_pauses_front_experience(self):
        for tag, variable in (('SOV', 'hro_war_sov_war_days'), ('GER', 'hro_war_ger_winter_days')):
            with self.subTest(tag=tag):
                country = self.country(tag, '1941.11.1')
                self.runtime.tick(country)
                self.runtime.advance(country, '1941.11.10')
                self.assertEqual(country['variables'][variable], 9)
                self.assertTrue(set(generator.SOV_PENALTIES + generator.GER_PENALTIES) & country['ideas'])
                country['enemy_capitulated'] = True
                # The overall faction war can continue even after this front ends.
                self.runtime.advance(country, '1941.12.31')
                self.assertEqual(country['variables'][variable], 9)
                self.assertFalse(set(generator.SOV_PENALTIES + generator.GER_PENALTIES) & country['ideas'])
                self.assertIn('SOV_native_restriction', country['ideas'])

    def test_winter_experience_pauses_in_warm_seasons_and_peace(self):
        ger = self.country('GER', '1941.3.20')
        self.runtime.call('hro_war_ger_complete_winter_adaptation', ger)
        self.runtime.tick(ger)
        self.runtime.advance(ger, '1941.3.31')
        self.assertEqual(ger['variables']['hro_war_ger_winter_days'], 11)
        self.runtime.advance(ger, '1941.10.31')
        self.assertEqual(ger['variables']['hro_war_ger_winter_days'], 11)
        ger['war'] = False
        self.runtime.advance(ger, '1941.11.20')
        self.assertEqual(ger['variables']['hro_war_ger_winter_days'], 11)
        ger['war'] = True
        self.runtime.advance(ger, '1941.12.24')
        self.assertEqual(ger['variables']['hro_war_ger_winter_days'], 45)
        self.assertIn('hro_idea_war_ger_adapted', ger['ideas'])

    def test_repeated_public_reform_calls_cannot_advance_experience_counters(self):
        for tag, effect, variable in (
            ('SOV', 'hro_war_sov_complete_adaptation', 'hro_war_sov_war_days'),
            ('GER', 'hro_war_ger_complete_winter_adaptation', 'hro_war_ger_winter_days')):
            with self.subTest(tag=tag):
                country = self.country(tag, '1941.11.1')
                self.runtime.tick(country)
                for _ in range(50):
                    self.runtime.call(effect, country)
                self.assertEqual(country['variables'][variable], 0)
                self.assertFalse(any(i.endswith('_adapted') for i in country['ideas']))

    def test_other_countries_and_wrong_country_effects_are_untouched(self):
        country = self.country('USA', '1941.11.1')
        initial = copy.deepcopy(country)
        self.runtime.tick(country)
        for name in ('hro_war_sov_reorganize_fronts', 'hro_war_sov_complete_adaptation',
                     'hro_war_ger_prepare_winter', 'hro_war_ger_complete_winter_adaptation'):
            self.runtime.call(name, country)
        self.assertEqual(country, initial)

    def test_daily_dispatch_has_country_scope_without_global_rescoping(self):
        nodes = list(walk(self.runtime.daily))
        self.assertFalse(any(n.key in ('every_country', 'GER', 'SOV') for n in nodes))
        self.assertEqual([n.value for n in nodes if n.key == 'original_tag'], ['SOV', 'GER'])

    def test_extra_permanent_rewards_keep_stack_budget(self):
        result = generator.generate(self.output)
        for country, modifiers in result['permanent_rewards'].items():
            with self.subTest(country=country):
                self.assertLessEqual(modifiers.get('army_org_factor', 0), .10)
                self.assertGreaterEqual(modifiers.get('supply_consumption_factor', 0), -.10)
                self.assertGreaterEqual(modifiers.get('winter_attrition_factor', 0), -.50)

    def test_winter_windows_include_january_and_end_exactly_in_april(self):
        ger = self.country('GER', '1940.1.1')
        self.runtime.tick(ger)
        self.assertIn(generator.GER_PENALTIES[0], ger['ideas'])
        self.runtime.tick(ger, '1940.3.31')
        self.assertTrue(set(generator.GER_PENALTIES) & ger['ideas'])
        self.runtime.tick(ger, '1940.4.1')
        self.assertFalse(set(generator.GER_PENALTIES) & ger['ideas'])


if __name__ == '__main__':
    unittest.main()
