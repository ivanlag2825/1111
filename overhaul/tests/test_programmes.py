"""Execute the small flag/idea contract of generated programme lifecycle scripts.

This checks our lifecycle logic, not HOI4 timing or multiplayer synchronisation.
"""
import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from clausewitz import parse, walk

spec = importlib.util.spec_from_file_location('hro_programme_generator_tests', ROOT / 'overhaul/tools/generate_gameplay.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


def condition(nodes, state):
    def one(n):
        if n.key == 'has_country_flag':
            return n.value in state['flags']
        if n.key == 'NOT':
            return not condition(n.value, state)
        if n.key == 'OR':
            return any(one(x) for x in n.value)
        raise AssertionError('Unmodelled lifecycle condition: ' + n.key)
    return all(one(n) for n in nodes)


def execute(nodes, state, definitions):
    for n in nodes:
        if n.key == 'if':
            if condition(n.one('limit').value, state):
                execute([x for x in n.value if x.key != 'limit'], state, definitions)
        elif n.key == 'set_country_flag':
            state['flags'].add(n.value if isinstance(n.value, str) else n.scalar('flag'))
        elif n.key == 'clr_country_flag':
            state['flags'].discard(n.value)
        elif n.key == 'add_ideas':
            state['ideas'].add(n.value)
        elif n.key == 'remove_ideas':
            state['ideas'].discard(n.value)
        elif n.key == 'add_timed_idea':
            state['ideas'].add(n.scalar('idea'))
        elif n.key == 'army_experience':
            state['xp'] += float(n.value)
        elif n.key in ('custom_effect_tooltip', 'show_ideas_tooltip'):
            pass  # Presentation-only effects do not grant the previewed idea.
        elif n.key in definitions and n.value == 'yes':
            execute(definitions[n.key].value, state, definitions)
        else:
            raise AssertionError('Unmodelled lifecycle effect: ' + str(n.key))


class ProgrammeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)
        generator.generate(self.output)
        self.effects = {n.key: n for n in parse((self.output / 'common/scripted_effects/hro_programme_effects.txt').read_text())}
        roots = parse((self.output / 'common/decisions/hro_programmes.txt').read_text())
        self.decisions = {n.key: n for category in roots for n in category.value}
        self.prefix = 'hro_programme_ger_staff_rotation'
        self.decision = self.decisions[self.prefix]
        self.state = {'flags': set(), 'ideas': set(), 'xp': 0}

    def start(self):
        execute(self.decision.one('complete_effect').value, self.state, self.effects)

    def test_activation_has_real_cost_and_no_early_reward(self):
        self.assertGreater(int(self.decision.scalar('cost')), 0)
        self.assertGreater(int(self.decision.scalar('days_remove')), 0)
        self.start()
        self.assertEqual(self.state['xp'], 0)
        self.assertIn(self.prefix + '_working', self.state['ideas'])
        self.assertNotIn(self.prefix + '_benefit', self.state['ideas'])
        self.assertIn('hro_operations_programme_busy', self.state['flags'])

    def test_cancellation_then_late_completion_produces_no_reward(self):
        self.start()
        execute(self.effects[self.prefix + '_cancel'].value, self.state, self.effects)
        execute(self.effects[self.prefix + '_complete'].value, self.state, self.effects)
        self.assertEqual(self.state, {'flags': set(), 'ideas': set(), 'xp': 0})

    def test_completion_awards_once_and_locks_slot_until_result_expires(self):
        self.start()
        execute(self.effects[self.prefix + '_complete'].value, self.state, self.effects)
        self.assertEqual(self.state['xp'], 10)
        self.assertIn(self.prefix + '_benefit', self.state['ideas'])
        self.assertNotIn(self.prefix + '_working', self.state['ideas'])
        self.assertIn(self.prefix + '_done', self.state['flags'])
        self.assertIn('hro_operations_programme_result_active', self.state['flags'])
        self.assertNotIn('hro_operations_programme_busy', self.state['flags'])
        before = copy.deepcopy(self.state)
        execute(self.effects[self.prefix + '_complete'].value, self.state, self.effects)
        self.assertEqual(self.state, before)

    def test_stale_cancel_cannot_release_another_active_programme_slot(self):
        other = 'hro_programme_ger_signals_drill'
        self.state['flags'] = {other + '_active', 'hro_operations_programme_busy'}
        self.state['ideas'] = {other + '_working'}
        before = copy.deepcopy(self.state)
        execute(self.effects[self.prefix + '_cancel'].value, self.state, self.effects)
        self.assertEqual(self.state, before)

    def test_all_unlock_flags_match_country_catalogues(self):
        written = set()
        import json
        for name in ('ger', 'sov'):
            data = json.loads((ROOT / f'overhaul/data/{name}.json').read_text())
            written.update(flag for focus in data['focuses'] for flag in focus.get('flags', []))
        for n in walk([category for category in parse((self.output / 'common/decisions/hro_programmes.txt').read_text())]):
            if n.key == 'has_country_flag' and isinstance(n.value, str) and n.value.endswith('_unlocked'):
                self.assertIn(n.value, written)


if __name__ == '__main__':
    unittest.main()
