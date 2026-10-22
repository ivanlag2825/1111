"""Execute native focus additions, monotone reform families and save migration."""
from pathlib import Path
from datetime import timedelta
from collections import Counter
import copy,tempfile,unittest,json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'overhaul/tools'),str(ROOT/'tools')]
from generate_native_military import generate,records,DAYS
from generate_war_adaptation import generate as war_generate
from generate_operations import generate as ops_generate
from generate_runtime import generate as runtime_generate
from test_runtime_aid import QueueRuntime
import test_builder as builders
import test_operations as operations
class NativeRuntime(QueueRuntime):
 def condition(self,nodes,s,tag=None,previous=None):
  def one(n):
   if n.key=='has_completed_focus':return n.value in s.get('completed',set())
   return super(NativeRuntime,self).condition([n],s,tag,previous)
  return all(one(n) for n in nodes)
class NativeMilitaryTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.p=Path(self.t.name)
  self.cats=builders.builder.read_catalogs(ROOT/'overhaul/data');self.ger=next(c for c in self.cats if c['tag']=='GER')
  builders.builder.author_country_content(self.p,self.cats,{'GER':0,'SOV':0});war_generate(self.p);ops_generate(self.p);self.meta=generate(self.p,self.cats);runtime_generate(self.p)
  self.r=NativeRuntime(self.p);self.entries=records();self.ideas={i['id']:i for i in self.ger['ideas']}
 def state(self,tag='GER'):return operations.OperationsTests().country(tag)
 def grant(self,s,record):self.r.call(record['effect'],s)
 def test_all_fiftynine_historical_native_military_nodes_are_attached_to_real_rewards(self):
  patches={p['id']:p for p in self.ger['native_patches']}
  expected={p['id'] for p in patches.values() if 'x' in p and 0<=p['x']<39}
  self.assertEqual({e['focus'] for e in self.entries},expected);self.assertEqual(self.meta['branches'],{'army':23,'air':19,'navy':17})
  for e in self.entries:self.assertIn(e['effect']+' = yes',patches[e['focus']]['extra_reward']);self.assertIn(e['idea'],self.ideas)
 def test_every_native_addition_grants_a_permanent_reform_real_timed_idea_and_research_once(self):
  for e in self.entries:
   s=self.state();self.grant(s,e);training='hro_native_training_'+e['branch']
   self.assertIn(e['idea'],s['ideas']);self.assertIn(training,s['ideas']);self.assertEqual(s['expiry'][training],s['date']+timedelta(days=DAYS));self.assertEqual(s['research'],[(e['tech'],1)])
   deadline=s['expiry'][training];s['date']+=timedelta(days=10);self.grant(s,e)
   self.assertEqual(s['expiry'][training],deadline);self.assertEqual(len(s['research']),1)
 def test_weaker_later_completed_focus_preserves_stronger_reform_without_stacking(self):
  by={e['focus']:e for e in self.entries};s=self.state()
  for fid in ('GER_instill_auftragstaktik','GER_develop_modern_maneuver_warfare','GER_the_prussian_legacy'):self.grant(s,by[fid])
  self.assertIn('hro_idea_ger_native_command_3',s['ideas']);self.assertNotIn('hro_idea_ger_native_command_1',s['ideas']);self.assertNotIn('hro_idea_ger_native_command_2',s['ideas'])
 def test_distinct_focus_refreshes_one_training_spirit_but_reload_and_same_reward_do_not(self):
  s=self.state();a,b=self.entries[:2];self.grant(s,a);old=s['expiry']['hro_native_training_army'];s['date']+=timedelta(days=20);self.grant(s,b)
  deadline=s['expiry']['hro_native_training_army'];self.assertEqual(deadline,old+timedelta(days=20));s=copy.deepcopy(s);self.r=NativeRuntime(self.p);self.grant(s,b);self.assertEqual(s['expiry']['hro_native_training_army'],deadline)
 def test_old_completed_focuses_reconcile_only_highest_permanent_reforms_without_research_or_timers(self):
  s=self.state();s['completed']={e['focus'] for e in self.entries};before=copy.deepcopy(s);self.r.call('hro_native_military_sync',s)
  chosen=[self.ideas[i] for i in s['ideas'] if i in self.ideas and '_native_' in i]
  self.assertEqual(len(chosen),15);self.assertEqual(len({i['family'] for i in chosen}),15)
  for i in chosen:self.assertEqual(i['stage'],max(a['stage'] for a in self.ideas.values() if a['family']==i['family']))
  self.assertFalse(s.get('research'));self.assertFalse(s.get('expiry'));self.assertFalse(any(i.startswith('hro_native_training_') for i in s['ideas']))
  self.assertEqual(s['variables'],before['variables'])
 def test_missing_permanent_spirit_is_restored_on_saved_heartbeat_without_replaying_timed_reward(self):
  s=self.state();s['completed']={'GER_the_prussian_legacy'};self.r.call('hro_runtime_seed',s);self.r.days(s,1)
  self.assertIn('hro_idea_ger_native_command_2',s['ideas']);s['ideas'].remove('hro_idea_ger_native_command_2');s=copy.deepcopy(s);self.r=NativeRuntime(self.p);self.r.days(s,1)
  self.assertIn('hro_idea_ger_native_command_2',s['ideas']);self.assertFalse(s.get('research'));self.assertFalse(any(i.startswith('hro_native_training_') for i in s['ideas']))
 def test_soviets_do_not_receive_german_native_additions(self):
  s=self.state('SOV');s['completed']={e['focus'] for e in self.entries};self.r.call('hro_native_military_sync',s)
  for e in self.entries:self.grant(s,e)
  self.assertFalse(any('_native_' in i for i in s['ideas']));self.assertFalse(s.get('research'))
 def test_new_permanent_families_do_not_add_global_army_attack_defence_organisation_or_factory_output(self):
  prohibited={'army_attack_factor','army_defence_factor','army_org_factor','industrial_capacity_factory'}
  for i in self.ger['ideas']:
   if '_native_' in i['id']:self.assertFalse(prohibited & i['modifiers'].keys(),i['id'])
