"""Execute first-war recon, event choices, one prototype and costed projects."""
from pathlib import Path
from datetime import timedelta
import tempfile,unittest,copy,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'overhaul/tools'),str(ROOT/'tools')]
from clausewitz import parse
from generate_war_stories import generate,RECON_IDS
from generate_war_adaptation import generate as war_generate
from generate_operations import generate as ops_generate
from generate_runtime import generate as runtime_generate
from test_runtime_aid import QueueRuntime
from test_war_adaptation import day
import test_builder as builders
import test_operations as operations
class StoryRuntime(QueueRuntime):
 def condition(self,nodes,s,tag=None,previous=None):
  def one(n):
   if n.key=='has_tech':return n.value in s.get('techs',set())
   if n.key=='has_completed_focus':return n.value in s.get('completed',set())
   return super(StoryRuntime,self).condition([n],s,tag,previous)
  return all(one(n) for n in nodes)
 def execute(self,nodes,s):
  if any(n.key in ('set_technology','create_railway_gun') for n in nodes):
   for n in nodes:
    if n.key=='set_technology':s.setdefault('techs',set()).update(c.key for c in n.value if c.key!='popup')
    elif n.key=='create_railway_gun':s.setdefault('railguns',[]).append({c.key:c.value for c in n.value})
    else:super().execute([n],s)
  else:super().execute(nodes,s)
class WarStoriesTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.p=Path(self.t.name)
  self.cats=builders.builder.read_catalogs(ROOT/'overhaul/data');builders.builder.author_country_content(self.p,self.cats,{'GER':0,'SOV':0})
  war_generate(self.p);ops_generate(self.p);generate(self.p);runtime_generate(self.p);self.r=StoryRuntime(self.p)
  self.f={n.scalar('id'):n for n in parse((self.p/'common/national_focus/hro_country_focuses.txt').read_text())}
  self.d={n.key:n for n in parse((self.p/'common/decisions/hro_war_stories.txt').read_text())[0].value}
 def state(self,tag='SOV'):
  s=operations.OperationsTests().country(tag);s['controlled']={3151} if tag=='SOV' else {6521};s['enemy_controlled']-=s['controlled'];return s
 def start(self,s):self.r.call('hro_runtime_tick',s);self.r.call('hro_runtime_seed',s)
 def recon(self,s):return set(RECON_IDS)&s['ideas']
 def complete(self,s,focus):self.r.execute(self.f[focus].one('completion_reward').value,s)
 def option(self,s,event,index=0):self.r.execute([n for n in self.r.events[event].all('option')[index].value if n.key!='name'],s)
 def choose(self,s,key):
  d=self.d[key]
  if not self.r.condition(d.one('available').value,s):return False
  cost=int(d.scalar('cost'))
  if s['add_political_power']<cost:return False
  s['add_political_power']-=cost;self.r.execute(d.one('complete_effect').value,s);return True
 def test_blackout_is_present_on_first_tick_then_recovers_at_exact_days21_and60(self):
  s=self.state();self.start(s);self.assertEqual(self.recon(s),{RECON_IDS[0]})
  self.r.days(s,20);self.assertEqual(self.recon(s),{RECON_IDS[0]})
  self.r.days(s,1);self.assertEqual(self.recon(s),{RECON_IDS[1]})
  self.r.days(s,38);self.assertEqual(self.recon(s),{RECON_IDS[1]})
  self.r.days(s,1);self.assertFalse(self.recon(s))
 def test_recon_focus_cannot_skip_first21days_but_then_replaces_penalty_with_positive_spirit(self):
  s=self.state();self.start(s);self.complete(s,'hro_sov_front_recon_rebuild')
  self.assertEqual(self.recon(s),{RECON_IDS[0]});self.r.days(s,21);self.assertEqual(self.recon(s),{RECON_IDS[2]})
  self.assertEqual(s['research'],[('support_tech',1)])
 def test_soviet_first_attack_does_not_trigger_defensive_blackout(self):
  s=self.state();s['aggressor']='SOV';self.start(s);self.assertFalse(self.recon(s));self.assertNotIn('hro.911',s['events'])
 def test_reload_and_rewar_keep_original_recon_age_and_never_repeat_notification(self):
  s=self.state();self.start(s);self.r.days(s,10);s=copy.deepcopy(s);self.r=StoryRuntime(self.p);s['war']=False;self.r.days(s,5)
  self.assertFalse(self.recon(s));self.assertEqual(s['variables']['hro_war_sov_war_days'],10)
  s['war']=True;self.r.days(s,11);self.assertEqual(self.recon(s),{RECON_IDS[1]});self.assertEqual(s['events'].count('hro.911'),1)
 def test_capitulation_or_peace_removes_recon_and_late_save_does_not_reopen_blackout(self):
  s=self.state();self.start(s);s['capitulated']=True;self.r.days(s,1);self.assertFalse(self.recon(s))
  s=self.state();s['variables']['hro_war_sov_war_days']=240;s['flags']['hro_war_sov_started']=None;s['flags']['hro_war_sov_surprised']=None;self.start(s);self.assertFalse(self.recon(s));self.assertNotIn('hro.911',s['events'])
 def test_dora_focus_unlocks_tech_one_real_native_prototype_and_finite_trials_once(self):
  s=self.state('GER');self.complete(s,'hro_ger_dora_programme')
  self.assertIn('railway_gun',s['techs']);self.assertEqual(len(s['railguns']),1);self.assertEqual(s['railguns'][0]['location'],'6521')
  self.assertIn('hro_idea_ger_story_dora',s['ideas']);deadline=s['expiry']['hro_story_dora_trials'];self.assertEqual(deadline,s['date']+timedelta(days=90))
  s=copy.deepcopy(s);self.r=StoryRuntime(self.p);self.complete(s,'hro_ger_dora_programme');self.r.call('hro_war_stories_daily',s)
  self.assertEqual(len(s['railguns']),1);self.assertEqual(s['expiry']['hro_story_dora_trials'],deadline)
  self.r.days(s,90);self.assertNotIn('hro_story_dora_trials',s['ideas'])
 def test_dora_pending_delivery_waits_for_friendly_berlin_and_never_spawns_in_enemy_control(self):
  s=self.state('GER');s['controlled'].clear();self.complete(s,'hro_ger_dora_programme');self.assertFalse(s.get('railguns'))
  s['controlled'].add(6521);s['capitulated']=True;self.r.call('hro_war_stories_daily',s);self.assertFalse(s.get('railguns'))
  s['capitulated']=False;self.r.call('hro_war_stories_daily',s);self.r.call('hro_war_stories_daily',s);self.assertEqual(len(s['railguns']),1)
 def hero_state(self):
  s=self.state();s['date']=day('1941.8.20');s['variables']['hro_war_sov_war_days']=59;return s
 def test_kolobanov_requires_leningrad_defensive_war_and_a_valid_period(self):
  for changes in ({'controlled':set()},{'aggressor':'SOV'},{'date':day('1941.8.1')}):
   s=self.hero_state();s.update(changes);self.r.call('hro_war_stories_daily',s);self.assertNotIn('hro.912',s['events'])
  s=self.hero_state();self.r.call('hro_war_stories_daily',s);self.r.call('hro_war_stories_daily',s);self.assertEqual(s['events'].count('hro.912'),1)
 def test_kolobanov_choices_are_exclusive_issue_xp_and_research_once_and_expire(self):
  for index,idea in [(0,'hro_story_kolobanov_ambush'),(1,'hro_story_kolobanov_cadres')]:
   s=self.hero_state();self.option(s,'hro.912',index);self.assertIn(idea,s['ideas']);self.assertEqual(s['army_experience'],35);self.assertEqual(len(s['research']),1)
   self.option(s,'hro.912',1-index);self.option(s,'hro.912',index);self.assertEqual(s['army_experience'],35);self.assertEqual(len(s['research']),1)
   self.assertEqual(sum(i.startswith('hro_story_kolobanov_') for i in s['ideas']),1);self.r.days(s,180);self.assertNotIn(idea,s['ideas'])
 def test_stale_kolobanov_popup_cannot_award_after_peace_or_loss_of_city(self):
  for changes in ({'war':False},{'controlled':set()},{'enemy_capitulated':True}):
   s=self.hero_state();s.update(changes);self.option(s,'hro.912');self.assertFalse(s.get('research'));self.assertFalse(any('kolobanov' in i for i in s['ideas']))
 def test_tea_story_is_one_time_for_each_country_and_only_after_its_winter_focus(self):
  for tag,focus,ev in [('GER','hro_ger_field_kitchens','hro.913'),('SOV','hro_sov_field_workshops','hro.914')]:
   s=self.state(tag);s['date']=day('1942.1.10');self.r.call('hro_war_stories_daily',s);self.assertNotIn(ev,s['events'])
   s['completed']={focus};self.r.call('hro_war_stories_daily',s);self.r.call('hro_war_stories_daily',s);self.assertEqual(s['events'].count(ev),1)
   self.option(s,ev);deadline=s['expiry']['hro_story_hot_tea'];self.option(s,ev);self.assertEqual(s['expiry']['hro_story_hot_tea'],deadline)
   self.r.days(s,30);self.assertNotIn('hro_story_hot_tea',s['ideas'])
 def test_engineer_project_charges_once_has_real_duration_and_cannot_refresh_before_cooldown(self):
  for tag,focus,key in [('GER','hro_ger_modular_fortifications','hro_story_ger_fort_builders'),('SOV','hro_sov_modular_fortification_lines','hro_story_sov_fort_builders')]:
   s=self.state(tag);s['war']=False;s['completed']={focus};before=s['add_political_power']
   self.assertTrue(self.choose(s,key));self.assertEqual(s['add_political_power'],before-60);deadline=s['expiry']['hro_story_fort_builders'];self.assertEqual(deadline,s['date']+timedelta(days=120))
   self.assertFalse(self.choose(s,key));self.r.days(s,120);self.assertNotIn('hro_story_fort_builders',s['ideas']);self.assertFalse(self.choose(s,key))
   self.r.days(s,60);self.assertTrue(self.choose(s,key));self.assertEqual(s['add_political_power'],before-120)
 def test_recon_projects_require_matching_focus_war_and_german_agency(self):
  s=self.state('GER');key='hro_story_ger_captured_maps';s['completed']={'hro_ger_dummy_positions'};s['agency']=False;self.assertFalse(self.choose(s,key));s['agency']=True;self.assertTrue(self.choose(s,key))
  s=self.state();s['completed']={'hro_sov_front_recon_rebuild'};self.assertTrue(self.choose(s,'hro_story_sov_combat_recon'));s['war']=False;self.r.call('hro_war_stories_daily',s);self.assertNotIn('hro_story_combat_recon',s['ideas'])
 def test_eight_new_focuses_have_real_parent_links_and_no_political_power_only_rewards(self):
  new=[f for c in self.cats for f in c['focuses'] if f['id'] in ('hro_ger_dora_programme','hro_ger_modular_fortifications','hro_ger_dummy_positions','hro_ger_field_kitchens','hro_sov_modular_fortification_lines','hro_sov_front_recon_rebuild','hro_sov_tank_ambush_manuals','hro_sov_field_workshops')]
  self.assertEqual(len(new),8)
  for f in new:self.assertTrue(f['prerequisites']);self.assertTrue('hro_set_' in f['reward'] or 'hro_story_' in f['reward'])
