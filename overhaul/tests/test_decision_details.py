"""Delayed reward previews must show real values without granting those rewards."""
from pathlib import Path
import sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'overhaul/tools'),str(ROOT/'tools')]
from clausewitz import parse
from decision_details import describe
from generate_gameplay import generate as programmes_generate
from generate_emergency import generate as cities_generate
import test_city_emergency as citytests


class DecisionDetailsTests(unittest.TestCase):
 def test_daily_political_power_is_not_rendered_as_a_percentage(self):
  ru=describe({'political_power_gain':-.03,'industrial_capacity_factory':-.025},'russian')
  en=describe({'political_power_gain':-.03,'industrial_capacity_factory':-.025},'english')
  self.assertIn('−0,03',ru.replace('-','−'));self.assertIn('ПВ/день',ru);self.assertIn('-2.5%',en)
  self.assertNotIn('3%',ru);self.assertIn('-0.03 PP/day',en)
 def test_reinforcement_displays_percentage_points(self):
  self.assertIn('+4 п.п.',describe({'land_reinforce_rate':.04},'russian'))
  self.assertIn('+4 pp',describe({'land_reinforce_rate':.04},'english'))
 def test_all_programmes_preview_existing_reward_ideas_without_adding_them(self):
  with tempfile.TemporaryDirectory() as directory:
   output=Path(directory);programmes_generate(output)
   ideas={n.key for n in parse((output/'common/ideas/hro_programme_ideas.txt').read_text())[0].one('country').value}
   count=0
   for category in parse((output/'common/decisions/hro_programmes.txt').read_text()):
    for decision in category.value:
     effect=decision.one('complete_effect')
     benefit=effect.scalar('show_ideas_tooltip');self.assertIn(benefit,ideas)
     self.assertTrue(benefit.endswith('_benefit'));self.assertNotEqual(effect.scalar('add_ideas'),benefit)
     self.assertIsNone(effect.one('add_timed_idea'));count+=1
   self.assertEqual(count,36)
 def test_city_response_preview_does_not_grant_mobilisation_early(self):
  with tempfile.TemporaryDirectory() as directory:
   output=Path(directory);cities_generate(output);runtime=citytests.Runtime(output)
   fixture=citytests.CityEmergencyTests();fixture.setUp();self.addCleanup(fixture.doCleanups);state=fixture.s
   decision=next(iter(runtime.decisions.values()))
   runtime.execute(decision.one('complete_effect').value,state)
   self.assertIn('hro_idea_city_response_working',state['ideas'])
   self.assertFalse(any(idea.startswith('hro_idea_city_mobilization_') for idea in state['ideas']))
   self.assertEqual(state['manpower'],0);self.assertEqual(state['factories'],[])


if __name__=='__main__':unittest.main()
