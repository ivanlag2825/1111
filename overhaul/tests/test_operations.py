"""Execute generated decisions and daily effects; not an HOI4 engine simulation."""
from datetime import timedelta
from pathlib import Path
import sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'overhaul/tools')]
from clausewitz import parse
from generate_operations import generate,TARGETS,validate_geography
from generate_war_adaptation import generate as generate_war
from test_war_adaptation import EmittedLifecycle,day


class OperationsRuntime(EmittedLifecycle):
 def __init__(self,output):
  super().__init__(output)
  self.effects.update({n.key:n for n in parse((output/'common/scripted_effects/hro_operations_effects.txt').read_text())})
  self.daily=parse((output/'common/on_actions/hro_operations_on_actions.txt').read_text())[0].one('on_daily').one('effect').value
  self.decisions={n.key:n for category in parse((output/'common/decisions/hro_operations.txt').read_text()) for n in category.value}
 def condition(self,nodes,s,tag=None,previous=None):
  tag=tag or s['tag']
  def one(n):
   if n.key in ('OR','AND','NOT'):
    values=[self.condition([c],s,tag,previous) for c in n.value]
    return any(values) if n.key=='OR' else not all(values) if n.key=='NOT' else all(values)
   if n.key=='always':return n.value=='yes'
   if n.key.isdigit():return self.condition(n.value,s,tag,int(n.key))
   if n.key=='controller':return self.condition(n.value,s,s['states'][previous]['controller'],previous)
   if n.key=='any_neighbor_state':return any(self.condition(n.value,s,tag,region) for region in s['states'][previous].get('neighbors',[]))
   if n.key=='is_controlled_by':return s['states'][previous]['controller']==s['tag']
   if n.key=='has_war_with':return s['war'] and tag!=s['tag']
   if n.key=='has_intelligence_agency':return s.get('agency',False)
   if n.key=='has_full_control_of_state':return s['states'][int(n.value)]['controller']==tag
   if n.key in ('air_base','infrastructure'):return s['states'][previous][n.key]>float(n.value)
   return super(OperationsRuntime,self).condition([n],s,tag,previous)
  return all(one(n) for n in nodes)
 def execute(self,nodes,s):
  # Keep branches together so the parent interpreter preserves else semantics.
  if any(n.key and (n.key.isdigit() or n.key=='damage_building') for n in nodes):
   for n in nodes:
    if n.key.isdigit():
     prior=s.get('_region');s['_region']=int(n.key)
     self.execute(n.value,s);s['_region']=prior
    elif n.key=='damage_building':s['damage'].append((s['_region'],n.scalar('type'),float(n.scalar('damage'))))
    else:super().execute([n],s)
  else:super().execute(nodes,s)
 def choose(self,key,s):
  d=self.decisions['hro_ops_'+key]
  allowed=s['tag'] in ('GER','SOV') and self.condition(d.one('visible').value,s) and self.condition(d.one('available').value,s)
  cost=int(d.scalar('cost'))
  if not allowed or s['add_political_power']<cost:return False
  s['add_political_power']-=cost;self.execute(d.one('complete_effect').value,s);return True
 def days(self,s,count):
  for _ in range(count):s['date']+=timedelta(days=1);self.tick(s)


class OperationsTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.output=Path(self.temp.name);generate_war(self.output);self.report=generate(self.output);self.r=OperationsRuntime(self.output)
 def country(self,tag='GER'):
  enemy='SOV' if tag=='GER' else 'GER'
  return dict(tag=tag,date=day('1941.6.22'),war=True,aggressor='GER',capitulated=False,enemy_capitulated=False,
   flags={},variables={},ideas={'native_idea'},events=[],controlled=set(),enemy_controlled={vp for _,vp,*_ in TARGETS[tag]},
   states={state:dict(controller=enemy,air_base=3,infrastructure=4,neighbors=[]) for state,*_ in TARGETS[tag]},
   add_political_power=2000,damage=[],agency=True)
 def start(self,s):
  stem=s['tag'].lower()+'_195'
  self.assertTrue(self.r.choose('prepare_'+stem,s));self.r.days(s,35)
  self.assertTrue(self.r.choose('launch_'+stem,s))
 def test_preparation_cost_window_single_slot_and_no_early_attack(self):
  s=self.country();self.assertTrue(self.r.choose('prepare_ger_195',s));self.assertEqual(s['add_political_power'],1910)
  self.assertFalse(self.r.choose('prepare_ger_219',s));self.assertFalse(self.r.choose('launch_ger_195',s))
  self.r.days(s,34);self.assertNotIn('hro_ops_idea_assault',s['ideas'])
  self.r.days(s,1);self.assertTrue(self.r.choose('launch_ger_195',s));self.assertIn('hro_ops_idea_assault',s['ideas'])
  self.assertFalse(self.r.choose('launch_ger_195',s))
 def test_ready_window_expires_and_captured_target_cannot_launch(self):
  s=self.country();self.r.choose('prepare_ger_195',s);self.r.days(s,35)
  s['enemy_controlled'].remove(3151);s['controlled'].add(3151)
  self.assertFalse(self.r.choose('launch_ger_195',s))
  self.r.days(s,45);s['enemy_controlled'].add(3151)
  self.assertFalse(self.r.choose('launch_ger_195',s));self.assertTrue(self.r.choose('prepare_ger_219',s))
 def test_capture_during_preparation_discards_obsolete_plan(self):
  s=self.country();self.r.choose('prepare_ger_195',s);s['enemy_controlled'].remove(3151);self.r.days(s,35)
  self.assertFalse(self.r.flag(s,'hro_ops_ready'));self.assertNotIn('hro_ops_idea_assault',s['ideas'])
 def test_fourteen_day_assault_and_seven_day_exhaustion_steps(self):
  for tag in ('GER','SOV'):
   s=self.country(tag);self.start(s);self.r.days(s,13);self.assertIn('hro_ops_idea_assault',s['ideas'])
   self.r.days(s,1);self.assertNotIn('hro_ops_idea_assault',s['ideas']);self.assertIn('hro_ops_idea_exhaustion',s['ideas'])
   for tier in (2,3,4):
    self.r.days(s,6);self.assertNotIn('hro_ops_idea_exhaustion_'+str(tier),s['ideas'])
    self.r.days(s,1);self.assertIn('hro_ops_idea_exhaustion_'+str(tier),s['ideas'])
    self.assertEqual(len([i for i in s['ideas'] if i.startswith('hro_ops_idea_exhaustion')]),1)
   self.r.days(s,100);self.assertIn('hro_ops_idea_exhaustion_4',s['ideas'])
   self.assertFalse(self.r.choose('prepare_'+tag.lower()+'_219',s))
 def test_rest_freezes_escalation_has_supply_cost_and_clears_all_tiers(self):
  s=self.country();self.start(s);self.r.days(s,28)
  self.assertIn('hro_ops_idea_exhaustion_3',s['ideas']);self.assertTrue(self.r.choose('rest',s))
  self.r.days(s,20);self.assertIn('hro_ops_idea_exhaustion_3',s['ideas']);self.assertNotIn('hro_ops_idea_exhaustion_4',s['ideas'])
  self.r.days(s,1);self.assertFalse(any(i.startswith('hro_ops_idea_exhaustion') for i in s['ideas']))
  ideas=parse((self.output/'common/ideas/hro_operations_ideas.txt').read_text())[0].one('country')
  self.assertEqual(ideas.one('hro_ops_idea_rest').one('modifier').scalar('supply_consumption_factor'),'0.3')
 def test_completed_regrouping_unlocks_next_cycle_and_resets_fatigue(self):
  s=self.country();self.start(s);self.r.days(s,100);self.assertTrue(self.r.choose('rest',s))
  self.r.days(s,21);self.assertTrue(self.r.choose('prepare_ger_219',s));self.r.days(s,35)
  self.assertTrue(self.r.choose('launch_ger_219',s));self.r.days(s,14)
  self.assertIn('hro_ops_idea_exhaustion',s['ideas']);self.assertNotIn('hro_ops_idea_exhaustion_4',s['ideas'])
 def test_old_thirty_day_assault_is_capped_at_fourteen_days_after_upgrade(self):
  s=self.country();self.start(s);s['flags']['hro_ops_active']=s['date']+timedelta(days=30);s['expiry']['hro_ops_idea_assault']=s['date']+timedelta(days=30)
  self.r.days(s,14);self.assertNotIn('hro_ops_idea_assault',s['ideas']);self.assertIn('hro_ops_idea_exhaustion',s['ideas'])
 def test_old_timed_exhaustion_becomes_persistent_without_resetting_each_day(self):
  s=self.country();s['flags']['hro_ops_exhaustion']=s['date']+timedelta(days=60);s['ideas'].add('hro_ops_idea_exhaustion')
  self.r.tick(s);self.assertIsNone(s['flags']['hro_ops_exhaustion']);self.r.days(s,7)
  self.assertIn('hro_ops_idea_exhaustion_2',s['ideas'])
 def test_rest_cancels_attack_clears_exhaustion_only_on_completion_and_keeps_cooldown(self):
  s=self.country();self.start(s);self.r.days(s,14);self.assertTrue(self.r.choose('rest',s))
  self.r.days(s,20);self.assertIn('hro_ops_idea_exhaustion',s['ideas'])
  self.r.days(s,1);self.assertNotIn('hro_ops_idea_exhaustion',s['ideas']);self.assertFalse(self.r.choose('prepare_ger_219',s))
  t=self.country();self.start(t);self.assertTrue(self.r.choose('rest',t));self.assertNotIn('hro_ops_idea_assault',t['ideas'])
  self.r.days(t,40);self.assertNotIn('hro_ops_idea_exhaustion',t['ideas'])
 def test_legacy_decision_sabotage_is_removed_and_pending_projects_cancelled(self):
  self.assertFalse(any(key.startswith(('hro_ops_sabotage_', 'hro_ops_status_sabotage_')) for key in self.r.decisions))
  s=self.country();s['flags'].update({key:None for key in ['hro_ops_sabotage_ger_195_air_base','hro_ops_sabotage_busy','hro_ops_sabotage_wait']})
  self.r.tick(s);self.assertEqual(s['damage'],[])
  self.assertFalse(any(self.r.flag(s,key) for key in ['hro_ops_sabotage_ger_195_air_base','hro_ops_sabotage_busy','hro_ops_sabotage_wait']))
 def test_attack_council_success_once_and_no_compulsory_task(self):
  s=self.country();self.r.days(s,10);self.assertFalse(self.r.flag(s,'hro_ops_council_busy'))
  self.assertTrue(self.r.choose('council_attack_ger_195',s));self.assertFalse(self.r.choose('council_attack_ger_219',s))
  s['controlled'].add(3151);s['enemy_controlled'].discard(3151);self.r.days(s,1)
  self.assertEqual(s['add_political_power'],2055);self.assertEqual(s['army_experience'],50)
  self.assertIn('hro_ops_idea_council_attack',s['ideas']);self.r.days(s,5);self.assertEqual(s['army_experience'],50)
 def test_attack_council_failure_expires_and_cannot_reward_late_capture(self):
  s=self.country();self.r.choose('council_attack_ger_195',s);self.r.days(s,75)
  self.assertIn('hro_ops_idea_council_failure',s['ideas']);self.assertFalse(self.r.flag(s,'hro_ops_council_busy'))
  s['controlled'].add(3151);self.r.days(s,30);self.assertNotIn('hro_ops_idea_council_failure',s['ideas']);self.assertNotIn('army_experience',s)
 def defensive(self):
  s=self.country('SOV');s['controlled'].add(3151);s['enemy_controlled'].discard(3151);s['states'][195]['controller']='SOV';s['states'][195]['neighbors']=[219]
  return s
 def test_defensive_council_requires_frontier_and_rewards_sixty_days(self):
  s=self.defensive();s['states'][195]['neighbors']=[];self.assertFalse(self.r.choose('council_hold_sov_195',s))
  s['states'][195]['neighbors']=[219];self.assertTrue(self.r.choose('council_hold_sov_195',s));self.r.days(s,59)
  self.assertNotIn('army_experience',s);self.r.days(s,1);self.assertIn('hro_ops_idea_council_hold',s['ideas'])
 def test_losing_defensive_target_fails_once_even_if_reconquered(self):
  s=self.defensive();self.r.choose('council_hold_sov_195',s);s['controlled'].discard(3151);self.r.days(s,1)
  self.assertIn('hro_ops_idea_council_failure',s['ideas']);s['controlled'].add(3151);self.r.days(s,65);self.assertNotIn('army_experience',s)
 def test_peace_capitulation_and_end_date_cancel_without_rewards_or_penalty(self):
  for reason in ('war','capitulated','enemy_capitulated','date'):
   s=self.country();self.start(s);self.r.choose('council_attack_ger_195',s);self.r.choose('security',s)
   s[reason]=day('1947.1.1') if reason=='date' else False if reason=='war' else True
   self.r.tick(s);self.assertNotIn('hro_ops_idea_assault',s['ideas']);self.assertNotIn('hro_ops_idea_council_failure',s['ideas'])
   self.assertFalse(self.r.flag(s,'hro_ops_council_busy'));self.assertEqual(s['damage'],[]);self.assertIn('native_idea',s['ideas'])
   self.assertEqual(self.r.flag(s,'hro_ops_cooldown'),reason!='date')
 def test_reload_does_not_reset_deadlines(self):
  import copy
  s=self.country();self.start(s);self.r.days(s,10);saved=copy.deepcopy(s);self.r=OperationsRuntime(self.output)
  self.r.days(saved,10);self.assertIn('hro_ops_idea_exhaustion',saved['ideas'])
 def test_foreign_country_and_prewar_actions_unavailable(self):
  s=self.country();s['tag']='USA';self.assertFalse(self.r.choose('prepare_ger_195',s))
  s=self.country();s['war']=False;self.assertFalse(self.r.choose('prepare_ger_195',s));self.assertFalse(self.r.choose('security',s))
 def test_missing_map_fails_target_validation(self):
  with self.assertRaisesRegex(ValueError,'Operation target'):validate_geography(self.output)


if __name__=='__main__':unittest.main()
