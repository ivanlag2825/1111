"""Run emitted specialization rewards and saved operation-profile callbacks."""
from pathlib import Path
import copy,json,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'overhaul/tools'),str(ROOT/'tools')]
from clausewitz import parse
from generate_operations import generate as ops_generate, MODS
from generate_war_adaptation import generate as war_generate
from generate_runtime import generate as runtime_generate
from spirit_lifecycle import author_spirit_assets
from test_runtime_aid import QueueRuntime
import test_builder as builder_tests
import test_operations as operation_tests


class SpecializationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.output=Path(self.temp.name)
  self.catalogues=builder_tests.builder.read_catalogs(ROOT/'overhaul/data')
  builder_tests.builder.author_country_content(self.output,self.catalogues,{'GER':0,'SOV':0})
  war_generate(self.output);ops_generate(self.output);runtime_generate(self.output)
  self.r=QueueRuntime(self.output)
  self.focuses={n.scalar('id'):n for n in parse((self.output/'common/national_focus/hro_country_focuses.txt').read_text())}
  self.ideas=parse((self.output/'common/ideas/hro_country_ideas.txt').read_text())[0].one('country')
 def country(self,tag='GER'):
  return operation_tests.OperationsTests().country(tag)
 def choose_profile(self,state,style):
  focus=self.focuses[f'hro_{state["tag"].lower()}_specialize_{style}']
  self.r.execute(focus.one('completion_reward').value,state)
 def start(self,state):
  stem=state['tag'].lower()+'_195'
  self.assertTrue(self.r.choose('prepare_'+stem,state));self.r.days(state,35)
  self.assertTrue(self.r.choose('launch_'+stem,state))
 def test_four_reciprocal_pairs_per_country_have_real_rewards_and_twentyone_day_cost(self):
  for catalogue in self.catalogues:
   focuses=[f for f in catalogue['focuses'] if '_specialize_' in f['id']];self.assertEqual(len(focuses),8)
   for f in focuses:
    self.assertEqual(f['cost'],3)
    other=self.focuses[f['mutually_exclusive'][0]]
    self.assertEqual(other.one('mutually_exclusive').scalar('focus'),f['id'])
    self.assertIn('hro_set_hro_idea_',f['reward']);self.assertIn('bonus = 1',f['reward'])
 def test_every_declared_continuation_requires_one_of_its_specializations(self):
  for catalogue in self.catalogues:
   entries={f['id']:f for f in catalogue['focuses']+catalogue['native_patches']}
   for gate in catalogue['choice_milestones']:
    self.assertIn(gate['alternatives'],entries[gate['target']]['prerequisites'])
 def test_decisive_focus_applies_real_idea_and_fourteen_day_profile_to_both_countries(self):
  for tag in ('GER','SOV'):
   s=self.country(tag);self.choose_profile(s,'decisive')
   self.assertIn(f'hro_idea_{tag.lower()}_specialize_decisive',s['ideas'])
   self.start(s);self.assertIn('hro_ops_idea_assault_decisive',s['ideas'])
   self.r.days(s,14);self.assertIn('hro_ops_idea_exhaustion_decisive',s['ideas'])
   self.r.days(s,7);self.assertIn('hro_ops_idea_exhaustion_2_decisive',s['ideas'])
 def test_sequential_focus_survives_old_fourteen_day_cutoff_then_uses_ten_day_steps(self):
  for tag in ('GER','SOV'):
   s=self.country(tag);self.choose_profile(s,'sequential');self.start(s)
   self.r.days(s,14);self.assertIn('hro_ops_idea_assault_sequential',s['ideas'])
   self.assertNotIn('hro_ops_idea_exhaustion_sequential',s['ideas'])
   self.r.days(s,7);self.assertIn('hro_ops_idea_exhaustion_sequential',s['ideas'])
   self.r.days(s,9);self.assertNotIn('hro_ops_idea_exhaustion_2_sequential',s['ideas'])
   self.r.days(s,1);self.assertIn('hro_ops_idea_exhaustion_2_sequential',s['ideas'])
 def test_choosing_doctrine_mid_operation_does_not_change_the_running_profile(self):
  s=self.country();self.start(s);self.r.days(s,5);self.choose_profile(s,'sequential')
  self.r.days(s,9);self.assertIn('hro_ops_idea_exhaustion',s['ideas'])
  self.assertNotIn('hro_ops_idea_assault_sequential',s['ideas'])
 def test_reload_keeps_profile_deadline_and_exactly_one_fatigue_tier(self):
  s=self.country();self.choose_profile(s,'sequential');self.start(s);self.r.days(s,18)
  saved=copy.deepcopy(s);self.r=QueueRuntime(self.output);self.r.days(saved,3)
  self.assertIn('hro_ops_idea_exhaustion_sequential',saved['ideas'])
  self.assertEqual(len([i for i in saved['ideas'] if i.startswith('hro_ops_idea_exhaustion')]),1)
 def test_regrouping_clears_all_profile_variants_and_does_not_remove_doctrine(self):
  for style in ('decisive','sequential'):
   s=self.country();self.choose_profile(s,style);self.start(s);self.r.days(s,40)
   self.assertTrue(self.r.choose('rest',s));self.r.days(s,21)
   self.assertFalse(any(i.startswith('hro_ops_idea_exhaustion') for i in s['ideas']))
   self.assertIn('hro_idea_ger_specialize_'+style,s['ideas'])
   self.assertFalse(self.r.flag(s,'hro_ops_style_'+style))
 def test_positive_second_and_third_tier_attack_is_preserved_for_all_styles(self):
  for suffix in ('','_decisive','_sequential'):
   self.assertEqual(MODS['exhaustion_2'+suffix][2]['army_attack_factor'],.30)
   self.assertEqual(MODS['exhaustion_3'+suffix][2]['army_attack_factor'],.05)
  self.assertEqual(MODS['exhaustion_decisive'][2]['supply_consumption_factor'],.3125)
  self.assertEqual(MODS['exhaustion_sequential'][2]['supply_consumption_factor'],.1875)
 def test_tank_choice_penalizes_the_other_chassis_without_general_army_attack(self):
  for tag in ('ger','sov'):
   heavy=self.ideas.one(f'hro_idea_{tag}_specialize_heavy')
   medium=self.ideas.one(f'hro_idea_{tag}_specialize_medium')
   self.assertIsNone(heavy.one('modifier').one('army_attack_factor'))
   self.assertEqual(float(heavy.one('equipment_bonus').one('heavy_tank_chassis').scalar('soft_attack')),.30)
   self.assertGreater(float(heavy.one('equipment_bonus').one('medium_tank_chassis').scalar('build_cost_ic')),0)
   self.assertGreater(float(medium.one('equipment_bonus').one('heavy_tank_chassis').scalar('build_cost_ic')),0)
 def test_air_and_weapon_specializations_have_real_positive_and_negative_equipment_stats(self):
  for tag in ('ger','sov'):
   for key in ('fighter','cas','infantry','artillery'):
    eq=self.ideas.one(f'hro_idea_{tag}_specialize_{key}').one('equipment_bonus')
    costs=[float(group.scalar('build_cost_ic')) for group in eq.value]
    self.assertTrue(any(v<0 for v in costs));self.assertTrue(any(v>0 for v in costs))
    self.assertTrue(all(group.scalar('instant')=='yes' for group in eq.value))
 def test_sprite_authoring_preserves_equipment_bonuses(self):
  def snapshot():
   ideas=parse((self.output/'common/ideas/hro_country_ideas.txt').read_text())[0].one('country')
   return {i.key:{g.key:[(n.key,n.value) for n in g.value] for g in i.one('equipment_bonus').value} for i in ideas.value if i.one('equipment_bonus')}
  before=snapshot();self.assertEqual(len(before),12);author_spirit_assets(self.output);self.assertEqual(before,snapshot())


if __name__=='__main__':unittest.main()
