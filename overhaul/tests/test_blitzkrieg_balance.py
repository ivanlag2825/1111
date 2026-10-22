"""Execute the changed eligibility, migration and optional programme contracts."""
import copy,json,tempfile,unittest,sys
from pathlib import Path
from datetime import timedelta
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'overhaul/tools'),str(ROOT/'tools')]
from clausewitz import parse,walk
import test_war_stories as stories
import test_war_adaptation as war
day=war.day
import test_city_emergency as cities
from focus_timetable import schedule,date_floor,START


class BlitzkriegBalanceTests(unittest.TestCase):
 def setUp(self):
  self.fixture=stories.WarStoriesTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
  self.r=self.fixture.r;self.p=self.fixture.p
 def test_old_completed_german_reforms_restore_only_highest_permanent_tier_without_repayment(self):
  s=self.fixture.state('GER');s['completed']={'hro_ger_combined_exercises','hro_ger_armour_maintenance_school','hro_ger_operational_command_system','hro_ger_tooling_audit','hro_ger_procurement_register'}
  before=(s['add_political_power'],s.get('army_experience'),list(s.get('research',[])))
  for _ in range(2):self.r.call('hro_war_stories_daily',s)
  self.assertEqual({i for i in s['ideas'] if i.startswith('hro_idea_ger_blitzkrieg_')},{'hro_idea_ger_blitzkrieg_3'})
  self.assertIn('hro_idea_ger_civilian_builders_2',s['ideas']);self.assertNotIn('hro_idea_ger_civilian_builders_1',s['ideas'])
  self.assertEqual(before,(s['add_political_power'],s.get('army_experience'),s.get('research',[])))
 def test_city_belt_effect_and_save_migration_enforce_both_date_and_war_age(self):
  for date,age,eligible in [('1941.12.31',200,False),('1942.1.1',179,False),('1942.1.1',180,True)]:
   s=self.fixture.state();s['date']=day(date);s['variables']['hro_war_sov_war_days']=age;s['completed']={'hro_sov_hold_city_belt'}
   self.r.call('hro_story_city_belt_apply',s);self.assertEqual('hro_idea_sov_hold_city_belt' in s['ideas'],eligible)
   s['ideas'].add('hro_idea_sov_hold_city_belt');self.r.call('hro_war_stories_daily',s)
   self.assertEqual('hro_idea_sov_hold_city_belt' in s['ideas'],eligible)
   s['war']=False;self.r.call('hro_war_stories_daily',s);self.assertNotIn('hro_idea_sov_hold_city_belt',s['ideas'])
 def test_recon_shock_has_real_combat_costs_and_recovers_on_schedule(self):
  s=self.fixture.state();self.fixture.start(s)
  defs={n.key:n for n in parse((self.p/'common/ideas/hro_war_stories_ideas.txt').read_text())[0].one('country').value}
  self.assertIn('hro_story_recon_blind',s['ideas'])
  mods=defs['hro_story_recon_blind'].one('modifier')
  self.assertLess(float(mods.scalar('planning_speed')),0);self.assertLess(float(mods.scalar('army_org_regain')),0)
  self.assertEqual(float(mods.scalar('intel_from_operatives_factor')),-1)
  self.r.days(s,60);self.assertFalse({'hro_story_recon_blind','hro_story_recon_recovering'}&s['ideas'])
 def test_optional_panzer_training_is_paid_nonstacking_and_has_both_cost_and_expiry(self):
  s=self.fixture.state('GER');s['completed']={'hro_ger_combined_exercises'};s['add_political_power']=200
  key='hro_story_ger_panzer_drill';self.assertTrue(self.fixture.choose(s,key));self.assertEqual(s['add_political_power'],130)
  self.assertFalse(self.fixture.choose(s,key));self.assertIn('hro_story_panzer_drill',s['ideas'])
  self.r.days(s,60);self.assertNotIn('hro_story_panzer_drill',s['ideas']);self.assertFalse(self.fixture.choose(s,key))
  self.r.days(s,120);self.assertTrue(self.fixture.choose(s,key));self.assertEqual(s['add_political_power'],60)
 def test_two_soviet_focuses_have_no_industrial_research_or_production_rewards(self):
  cat=json.loads((ROOT/'overhaul/data/sov.json').read_text());f={x['id']:x for x in cat['focuses']}
  for k in ('hro_sov_gosplan_responsibility','hro_sov_foreign_policy_staff'):
   self.assertFalse(any(n.key=='add_tech_bonus' and n.scalar('category')=='industry' for n in walk(parse(f[k]['reward']))))
  i=next(x for x in cat['ideas'] if x['id']=='hro_idea_sov_foreign_tooling_1')
  self.assertNotIn('license_production_speed',i['modifiers']);self.assertNotIn('research_speed_factor',i['modifiers'])
 def test_full_adaptation_cannot_be_injected_into_1941_save_with_240_war_days(self):
  f=war.WarAdaptationTests();f.setUp();self.addCleanup(f.doCleanups);s=f.country('SOV','1941.12.31')
  s['flags'].update(hro_war_sov_started=None,hro_war_sov_reform_authorized=None,hro_war_sov_adapted=None)
  s['variables']['hro_war_sov_war_days']=240;s['ideas'].add('hro_idea_war_sov_adapted')
  f.runtime.call('hro_war_sov_apply_reform',s);self.assertNotIn('hro_idea_war_sov_adapted',s['ideas'])
  s['date']=day('1942.1.1');f.runtime.call('hro_war_sov_apply_reform',s);self.assertIn('hro_idea_war_sov_adapted',s['ideas'])
  before=list(s['events']);s['ideas'].discard('hro_idea_war_sov_adapted');f.runtime.call('hro_war_sov_apply_reform',s)
  self.assertIn('hro_idea_war_sov_adapted',s['ideas']);self.assertEqual(s['events'],before)
 def test_city_morale_loss_is_bounded_and_does_not_add_an_industrial_penalty(self):
  f=cities.CityEmergencyTests();f.setUp();self.addCleanup(f.doCleanups)
  f.lose('minsk');self.assertIn('hro_idea_city_crisis_1',f.s['ideas'])
  ideas={n.key:n for n in parse((f.output/'common/ideas/hro_city_ideas.txt').read_text())[0].one('country').value}
  for tier in (1,2,3):
   mods=ideas[f'hro_idea_city_crisis_{tier}'].one('modifier');self.assertLess(float(mods.scalar('army_attack_factor')),0);self.assertLess(float(mods.scalar('army_defence_factor')),0);self.assertIsNone(mods.one('industrial_capacity_factory'))
  f.r.advance(f.s,90);self.assertFalse({f'hro_idea_city_crisis_{i}' for i in (1,2,3)}&f.s['ideas'])


class TimetableTests(unittest.TestCase):
 def test_historical_rule_does_not_bypass_lower_date_and_and_or_are_respected(self):
  nodes=parse('OR = { has_game_rule = { rule = HRO_PACING option = HRO_OPEN } date > 1937.1.1 }')
  self.assertEqual(date_floor(nodes).date(),day('1937.1.2'))
  self.assertEqual(date_floor(parse('OR = { date > 1938.1.1 date > 1937.1.1 }')).date(),day('1937.1.2'))
 def test_single_slot_waits_for_date_and_charges_fractional_native_duration(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'common/national_focus/test.txt';p.parent.mkdir(parents=True)
   p.write_text('focus_tree = { focus = { id = GER_A cost = 3.5 } focus = { id = GER_B cost = 1 prerequisite = { focus = GER_A } available = { date > 1936.2.1 } } }')
   r=schedule(Path(t),['GER_B'],deadline='1936.2.10',political_starts={})
   self.assertTrue(r['feasible']);self.assertEqual(r['focus_days'],31.5);self.assertEqual(r['completed'],'1936-02-09T00:00:00')
   self.assertEqual(r['schedule'][0]['finish'],'1936-01-25T12:00:00');self.assertEqual(r['idle_days'],7.5)
 def test_incompatible_goals_fail_and_missed_end_date_is_reported(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'common/national_focus/test.txt';p.parent.mkdir(parents=True)
   p.write_text('focus_tree = { focus = { id = GER_A cost = 10 mutually_exclusive = { focus = GER_B } } focus = { id = GER_B cost = 10 mutually_exclusive = { focus = GER_A } } }')
   with self.assertRaises(ValueError):schedule(Path(t),['GER_A','GER_B'],political_starts={})
   self.assertFalse(schedule(Path(t),['GER_A'],deadline='1936.2.1',political_starts={})['feasible'])
