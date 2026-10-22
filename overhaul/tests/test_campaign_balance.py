"""Execute emitted phase transitions, bounded mobilisation and availability audit."""
from pathlib import Path
from datetime import timedelta,date
import tempfile,unittest,json,copy,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'overhaul/tools'),str(ROOT/'tools')]
from clausewitz import parse
from generate_campaign_balance import generate,identity,PHASES
from generate_operations import generate as ops_generate
from generate_war_adaptation import generate as war_generate
from generate_runtime import generate as runtime_generate
from generate_emergency import generate as city_generate
from test_runtime_aid import QueueRuntime
import test_operations as operations
import test_city_emergency as cities
import test_builder as builders

class CampaignBalanceTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.p=Path(self.t.name)
  war_generate(self.p);ops_generate(self.p);generate(self.p);runtime_generate(self.p);self.r=QueueRuntime(self.p)
 def state(self,tag):return operations.OperationsTests().country(tag)
 def tick(self,s):self.r.call('hro_campaign_balance_daily',s)
 def advance(self,s,days):
  for _ in range(days):s['date']+=timedelta(days=1);self.tick(s)
 def phase(self,s):return {i for i in s['ideas'] if i.startswith('hro_balance_')}
 def test_opening_is_one_real_spirit_per_country_and_duplicate_calls_do_not_advance_clock(self):
  for tag in PHASES:
   s=self.state(tag);self.tick(s);self.tick(s)
   self.assertEqual(s['variables']['hro_balance_war_days'],0);self.assertEqual(self.phase(s),{identity(tag,'opening')})
   self.advance(s,1);self.tick(s);self.assertEqual(s['variables']['hro_balance_war_days'],1)
 def test_historical_war_progresses_to_parity_in_1942_and_mature_in_1943(self):
  for tag in PHASES:
   s=self.state(tag);self.tick(s);self.advance(s,180)
   self.assertEqual(self.phase(s),{identity(tag,'opening')})
   self.advance(s,(date(1942,1,1)-s['date']).days);self.assertEqual(self.phase(s),{identity(tag,'parity')})
   self.advance(s,(date(1943,1,1)-s['date']).days);self.assertEqual(self.phase(s),{identity(tag,'mature')})
   self.assertEqual(s['variables']['hro_balance_war_days'],540)
 def test_late_war_cannot_skip_experience_just_because_calendar_is_1943(self):
  for tag in PHASES:
   s=self.state(tag);s['date']=date(1943,6,22);self.tick(s);self.assertEqual(self.phase(s),{identity(tag,'opening')})
   self.advance(s,179);self.assertEqual(self.phase(s),{identity(tag,'opening')})
   self.advance(s,1);self.assertEqual(self.phase(s),{identity(tag,'parity')})
   self.advance(s,360);self.assertEqual(self.phase(s),{identity(tag,'mature')})
 def test_peace_pauses_progress_rewar_reload_and_missing_spirit_never_reset_or_stack(self):
  s=self.state('GER');self.tick(s);self.advance(s,20);s['war']=False;self.advance(s,50)
  self.assertFalse(self.phase(s));self.assertEqual(s['variables']['hro_balance_war_days'],20)
  s=copy.deepcopy(s);self.r=QueueRuntime(self.p);s['war']=True;self.advance(s,1)
  self.assertEqual(s['variables']['hro_balance_war_days'],21);s['ideas'].discard(identity('GER','opening'));self.tick(s)
  self.assertEqual(self.phase(s),{identity('GER','opening')});self.assertEqual(s['variables']['hro_balance_war_days'],21)
 def test_capitulation_of_either_side_and_1947_clean_phase_spirits(self):
  for changes in ({'capitulated':True},{'enemy_capitulated':True},{'date':date(1947,1,1)}):
   s=self.state('SOV');self.tick(s);s.update(changes);self.tick(s);self.assertFalse(self.phase(s))
 def test_old_capped_counters_migrate_without_any_material_reward(self):
  for tag,var,count in [('GER','hro_off_ger_campaign_days',120),('SOV','hro_war_sov_war_days',240)]:
   s=self.state(tag);s['date']=date(1943,2,1);s['flags']['hro_off_ger_started' if tag=='GER' else 'hro_war_sov_started']=None;s['variables'][var]=count
   before=(s.get('add_political_power'),s.get('army_experience'),list(s.get('research',[])))
   self.tick(s);self.assertEqual(self.phase(s),{identity(tag,'mature')})
   self.assertEqual(before,(s.get('add_political_power'),s.get('army_experience'),s.get('research',[])))
 def test_saved_heartbeat_drives_balance_without_a_generic_daily_hook(self):
  s=self.state('GER');self.r.call('hro_runtime_seed',s);self.r.days(s,10)
  self.assertEqual(self.phase(s),{identity('GER','opening')});self.assertGreater(s['variables']['hro_balance_war_days'],0)

class MobilisationCapsTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.p=Path(self.t.name);city_generate(self.p);self.r=cities.Runtime(self.p)
  fixture=cities.CityEmergencyTests();fixture.setUp();self.addCleanup(fixture.doCleanups);self.s=fixture.s
  self.s['war']=True;self.s['vars']['hro_city_responses_completed']=3;self.s['flags']['hro_city_mobilization_active']=self.s['date']+timedelta(days=240);self.s.setdefault('flag_dates',{})['hro_city_mobilization_active']=self.s['date']
 def sync(self,when,days):
  self.s['date']=date(*when);self.s['vars']['hro_balance_war_days']=days;self.r.call('hro_city_sync',self.s)
 def test_three_responses_in_1941_are_still_only_first_tier_and_do_not_refresh_deadline(self):
  deadline=self.s['flags']['hro_city_mobilization_active'];self.sync((1941,7,1),9)
  self.assertIn('hro_idea_city_mobilization_1',self.s['ideas']);self.assertNotIn('hro_idea_city_mobilization_3',self.s['ideas']);self.assertEqual(self.s['expiry']['hro_idea_city_mobilization_1'],deadline)
 def test_mobilisation_phase_upgrades_replace_ideas_without_refresh_or_new_rewards(self):
  # A late-war start permits crossing both experience boundaries within240days
  # only via saved counters: explicitly exercise the synchronizer, not a replayed award.
  self.s['date']=date(1943,1,1);self.s['flags']['hro_city_mobilization_active']=date(1943,7,1);self.s['flag_dates']['hro_city_mobilization_active']=date(1942,11,3)
  for days,tier in [(0,1),(180,2),(540,3)]:
   self.sync((1943,1,1),days)
   actual={i for i in self.s['ideas'] if i.startswith('hro_idea_city_mobilization_')};self.assertEqual(actual,{f'hro_idea_city_mobilization_{tier}'})
   self.assertEqual(self.s['expiry'][f'hro_idea_city_mobilization_{tier}'],date(1943,7,1))
   self.assertEqual(self.s['manpower'],0);self.assertEqual(self.s['factories'],[])
 def test_elapsed_calendar_without_enough_war_experience_cannot_unlock_tier_three(self):
  self.s['flags']['hro_city_mobilization_active']=date(1943,7,1);self.s['flag_dates']['hro_city_mobilization_active']=date(1943,1,1)
  self.sync((1943,1,1),180);self.assertIn('hro_idea_city_mobilization_2',self.s['ideas'])
