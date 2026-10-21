"""Main-tree reforms must actually call the war-adaptation interfaces."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from clausewitz import parse, walk

HOOKS = {
    'GER': {'hro_ger_motor_transport_standards': 'hro_war_ger_prepare_winter',
            'hro_ger_sustained_supply': 'hro_war_ger_complete_winter_adaptation'},
    'SOV': {'hro_sov_campaign_preparedness': 'hro_war_sov_reorganize_fronts',
            'hro_sov_front_feedback': 'hro_war_sov_complete_adaptation'},
}


class WarFocusContractTests(unittest.TestCase):
    def test_authored_main_focus_rewards_call_real_public_reforms_once(self):
        spec = importlib.util.spec_from_file_location('war_focus_contract_generator',
            ROOT / 'overhaul/tools/generate_war_adaptation.py')
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            generator.generate(output)
            effects = {n.key for n in parse((output / 'common/scripted_effects/hro_war_effects.txt').read_text())}
            for tag, expected in HOOKS.items():
                catalog = json.loads((ROOT / 'overhaul/data' / (tag.lower() + '.json')).read_text())
                focuses = {focus['id']: focus for focus in catalog['focuses']}
                for identity, public_effect in expected.items():
                    self.assertIn(public_effect, effects)
                    calls = [n for n in walk(parse(focuses[identity]['reward']))
                             if n.key == public_effect and n.value == 'yes']
                    self.assertEqual(len(calls), 1, identity)

    def test_soviet_war_reform_is_on_the_retained_lessons_route(self):
        catalog = json.loads((ROOT / 'overhaul/data/sov.json').read_text())
        patches = {p['id']: p for p in catalog['native_patches']}
        self.assertIn(['hro_sov_front_feedback'], patches['SOV_lessons_of_war']['prerequisites'])
        self.assertIn(['hro_sov_campaign_preparedness'], patches['SOV_desperate_measures']['prerequisites'])


if __name__ == '__main__':
    unittest.main()
