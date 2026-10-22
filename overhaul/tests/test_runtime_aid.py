"""Run queued native country events with ordinary daily hooks suppressed.

Unlike earlier tests, this executes the dispatcher/queue and preparation start
separately from mission execution. It is still not a game-engine simulation.
"""
from datetime import timedelta
from pathlib import Path
import copy,json,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'overhaul/tools'),str(ROOT/'tools')]
from clausewitz import parse
from generate_runtime import generate as runtime_generate
from generate_allied_aid import generate as aid_generate
from generate_operations import generate as ops_generate
from generate_war_adaptation import generate as war_generate
from test_operations import OperationsRuntime


class QueueRuntime(OperationsRuntime):
 def __init__(self,output):
  self.effects={}
  self.triggers={n.key:n for n in parse((output/'common/scripted_triggers/hro_war_triggers.txt').read_text())}
  self.daily=[]
  self.decisions={n.key:n for category in parse((output/'common/decisions/hro_operations.txt').read_text()) for n in category.value}
  for p in (output/'common/scripted_effects').glob('*.txt'):
   self.effects.update({n.key:n for n in parse(p.read_text())})
  self.events={n.scalar('id'):n for p in (output/'events').glob('*.txt') for n in parse(p.read_text()) if n.key=='country_event'}
 def condition(self,nodes,s,tag=None,previous=None):
  def one(n):
   if n.key in ('MON','ROM'):return self.condition(n.value,s,n.key,s['tag'])
   if tag in ('MON','ROM'):
    if n.key=='exists':return s['donors'][tag]['exists']==(n.value=='yes')
    if n.key=='has_capitulated':return s['donors'][tag]['capitulated']==(n.value=='yes')
    if n.key=='has_war_with':return s['donors'][tag]['enemy']
   return super(QueueRuntime,self).condition([n],s,tag,previous)
  return all(one(n) for n in nodes)
 def execute(self,nodes,s):
  if any(n.key=='country_event' for n in nodes):
   for n in nodes:
    if n.key=='country_event':
     s['events'].append(n.scalar('id'));s.setdefault('queue',[]).append((s['date']+timedelta(days=int(n.scalar('days','0'))),n.scalar('id')))
    else:super().execute([n],s)
  else:super().execute(nodes,s)
 def pump(self,s):
  due=[event for event in s.get('queue',[]) if event[0]<=s['date']]
  s['queue']=[event for event in s.get('queue',[]) if event[0]>s['date']]
  for _,identity in due:
   if event:=self.events.get(identity):
    if immediate:=event.one('immediate'):self.execute(immediate.value,s)
 def days(self,s,count):
  for _ in range(count):
   s['date']+=timedelta(days=1)
   for idea,expiry in s.get('expiry',{}).items():
    if s['date']>=expiry:s['ideas'].discard(idea)
   self.pump(s)  # Deliberately no on_daily execution.


class RuntimeAidTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.output=Path(self.temp.name)
  war_generate(self.output);ops_generate(self.output);aid_generate(self.output);runtime_generate(self.output)
  self.r=QueueRuntime(self.output)
 def country(self,tag='GER'):
  from test_operations import OperationsTests
  s=OperationsTests().country(tag)
  s['donors']={t:dict(exists=True,capitulated=False,enemy=False) for t in ('MON','ROM')}
  return s
 def test_no_generic_daily_hook_is_shipped_and_country_hooks_are_explicit(self):
  files=list((self.output/'common/on_actions').glob('*.txt'));self.assertEqual(len(files),1)
  hooks=parse(files[0].read_text())[0]
  self.assertIsNone(hooks.one('on_daily'));self.assertIsNotNone(hooks.one('on_daily_GER'));self.assertIsNotNone(hooks.one('on_daily_SOV'))
 def test_heartbeat_alone_drives_preparation_assault_and_weekly_fatigue(self):
  s=self.country();self.assertTrue(self.r.choose('prepare_ger_195',s));self.r.days(s,35)
  self.assertTrue(self.r.choose('launch_ger_195',s));self.r.days(s,14)
  self.assertNotIn('hro_ops_idea_assault',s['ideas']);self.assertIn('hro_ops_idea_exhaustion',s['ideas'])
  self.r.days(s,7);self.assertIn('hro_ops_idea_exhaustion_2',s['ideas'])
 def test_direct_deadline_starts_fatigue_even_when_all_daily_callbacks_are_missing(self):
  s=self.country();s['flags'].update({'hro_ops_ready':None,'hro_ops_ready_ger_195':None})
  self.assertTrue(self.r.choose('launch_ger_195',s));s['queue']=[e for e in s['queue'] if e[1]=='hro.810']
  self.r.days(s,14);self.assertIn('hro_ops_idea_exhaustion',s['ideas']);self.assertNotIn('hro_ops_idea_assault',s['ideas'])
 def test_direct_rest_deadline_clears_fatigue_without_daily_callbacks(self):
  s=self.country();s['flags']['hro_ops_exhaustion']=None;s['ideas'].add('hro_ops_idea_exhaustion_4')
  self.r.choose('rest',s);s['queue']=[e for e in s['queue'] if e[1]=='hro.811'];self.r.days(s,21)
  self.assertFalse(any(i.startswith('hro_ops_idea_exhaustion') for i in s['ideas']))
 def test_repeat_seed_and_reload_do_not_multiply_saved_heartbeat(self):
  s=self.country()
  for _ in range(10):self.r.call('hro_runtime_seed',s)
  self.assertEqual(len(s['queue']),1);saved=copy.deepcopy(s);self.r=QueueRuntime(self.output)
  self.r.call('hro_runtime_seed',saved);self.assertEqual(len(saved['queue']),1)
  self.r.days(saved,10);self.assertEqual(sum(e[1]=='hro.800' for e in saved['queue']),1)
 def test_country_hook_and_heartbeat_do_not_double_increment_same_day(self):
  s=self.country();s['flags'].update({'hro_ops_exhaustion':None,'hro_ops_exhaustion_initialized':None})
  self.r.call('hro_runtime_tick',s);value=s['variables']['hro_ops_exhaustion_days']
  self.r.call('hro_runtime_tick',s);self.assertEqual(s['variables']['hro_ops_exhaustion_days'],value)
 def test_each_allied_event_grants_the_specific_365_day_spirit_once(self):
  for tag,key in [('SOV','mongolian_horses'),('GER','romanian_fuel')]:
   s=self.country(tag);self.r.call('hro_runtime_seed',s);self.r.days(s,2)
   idea='hro_aid_'+key+'_idea';self.assertIn(idea,s['ideas']);expiry=s['expiry'][idea]
   self.assertEqual((expiry-s['date']).days,365)
   self.r.days(s,30);self.assertEqual(s['expiry'][idea],expiry)
   self.r.execute(self.r.events['hro.820' if tag=='SOV' else 'hro.821'].one('immediate').value,s)
   self.assertEqual(s['expiry'][idea],expiry)
 def test_missing_capitulated_or_enemy_donor_cannot_grant_help(self):
  for tag,donor,key in [('SOV','MON','mongolian_horses'),('GER','ROM','romanian_fuel')]:
   for field,value in [('exists',False),('capitulated',True),('enemy',True)]:
    s=self.country(tag);s['donors'][donor][field]=value;self.r.call('hro_runtime_seed',s);self.r.days(s,3)
    self.assertNotIn('hro_aid_'+key+'_idea',s['ideas'])
 def test_help_does_not_trigger_before_war_and_expires_without_repayment(self):
  s=self.country();s['war']=False;self.r.call('hro_runtime_seed',s);self.r.days(s,10)
  self.assertNotIn('hro_aid_romanian_fuel_idea',s['ideas']);s['war']=True;self.r.days(s,2)
  self.assertIn('hro_aid_romanian_fuel_idea',s['ideas']);self.r.days(s,365)
  self.assertNotIn('hro_aid_romanian_fuel_idea',s['ideas'])
 def test_cavalry_and_army_fuel_modifiers_have_no_unrequested_general_bonus(self):
  ideas=parse((self.output/'common/ideas/hro_allied_aid_ideas.txt').read_text())[0].one('country')
  cav=ideas.one('hro_aid_mongolian_horses_idea').one('modifier')
  fuel=ideas.one('hro_aid_romanian_fuel_idea').one('modifier')
  self.assertEqual([(n.key,n.value) for n in cav.value],[('modifier_army_sub_unit_cavalry_attack_factor','0.2')])
  self.assertEqual([(n.key,n.value) for n in fuel.value],[('army_fuel_consumption_factor','-0.2')])


if __name__=='__main__':unittest.main()
