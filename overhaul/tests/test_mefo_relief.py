"""Execute native-MEFO detection, tier replacement and clean shutdown."""
from pathlib import Path
import sys,tempfile,unittest,copy
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'overhaul/tools'),str(ROOT/'tools')]
from generate_mefo_relief import generate,RELIEF
from generate_war_adaptation import generate as war_generate
from generate_operations import generate as ops_generate
from generate_runtime import generate as runtime_generate
from test_runtime_aid import QueueRuntime
import test_operations as operations
class MefoRuntime(QueueRuntime):
 def condition(self,nodes,s,tag=None,previous=None):
  def one(n):
   if n.key=='has_completed_focus':return n.value in s.get('completed',set())
   if n.key=='has_dynamic_modifier':return n.scalar('modifier') in s.get('dynamic',set())
   return super(MefoRuntime,self).condition([n],s,tag,previous)
  return all(one(n) for n in nodes)
class MefoReliefTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.p=Path(self.t.name)
  war_generate(self.p);ops_generate(self.p);generate(self.p);runtime_generate(self.p);self.r=MefoRuntime(self.p)
 def state(self,tag='GER'):return operations.OperationsTests().country(tag)
 def tick(self,s):self.r.call('hro_mefo_relief_daily',s)
 def own(self,s):return {i for i in s['ideas'] if i.startswith('hro_mefo_relief_')}
 def test_native_dynamic_mefo_grants_relief_and_caps_only_harmful_growth(self):
  s=self.state();s['dynamic']={'GER_mefo_bills_modifier'};s['variables']['GER_monthly_consumer_goods_increase']=.02;before=dict(s['variables']);before['GER_monthly_consumer_goods_increase']=.01;self.tick(s)
  self.assertEqual(self.own(s),{'hro_mefo_relief_1'});self.assertEqual(s['variables'],before)
 def test_each_completed_industrial_milestone_replaces_previous_tier_without_stacking(self):
  s=self.state();s['dynamic']={'GER_mefo_bills_modifier'}
  for completed,tier in [(set(),1),({'hro_ger_supplier_standards'},2),({'hro_ger_mature_procurement'},3)]:
   s['completed']=completed;self.tick(s);self.tick(s);self.assertEqual(self.own(s),{f'hro_mefo_relief_{tier}'})
 def test_no_mefo_ended_mefo_and_soviets_do_not_get_relief(self):
  for tag,active,ended in [('GER',False,False),('GER',True,True),('SOV',True,False)]:
   s=self.state(tag);s['dynamic']={'GER_mefo_bills_modifier'} if active else set()
   if ended:s['ideas'].add('GER_mefo_bills_ended')
   self.tick(s);self.assertFalse(self.own(s))
 def test_native_legacy_idea_is_supported_but_removal_cleans_all_relief_tiers(self):
  s=self.state();s['ideas'].add('GER_mefo_bills');self.tick(s);self.assertEqual(self.own(s),{'hro_mefo_relief_1'})
  s['ideas'].remove('GER_mefo_bills');self.tick(s);self.assertFalse(self.own(s))
 def test_reload_repairs_missing_spirit_without_manpower_pp_or_new_debt(self):
  s=self.state();s['dynamic']={'GER_mefo_bills_modifier'};s['completed']={'hro_ger_mature_procurement'};self.tick(s);s['ideas'].discard('hro_mefo_relief_3')
  s=copy.deepcopy(s);before=dict(s['variables']);self.r=MefoRuntime(self.p);self.tick(s)
  self.assertEqual(self.own(s),{'hro_mefo_relief_3'});self.assertEqual(s['variables'],before)

 def test_conquest_economy_is_supported_even_after_mefo_ended(self):
  s=self.state();s['dynamic']={'GER_economy_of_conquest_modifier'};s['ideas'].add('GER_mefo_bills_ended');s['completed']={'hro_ger_mature_procurement'}
  s['variables'].update(GER_industrial_consumer_goods_factor=1.5,GER_monthly_consumer_goods_increase=.04)
  self.tick(s);self.assertEqual(self.own(s),{'hro_mefo_relief_3'})
  self.assertEqual(s['variables']['GER_industrial_consumer_goods_factor'],0);self.assertEqual(s['variables']['GER_monthly_consumer_goods_increase'],0)
  s['variables']['GER_industrial_consumer_goods_factor']=.5;self.tick(s);self.assertEqual(s['variables']['GER_industrial_consumer_goods_factor'],0)
 def test_negative_native_reductions_are_never_raised_and_inactive_system_is_untouched(self):
  s=self.state();s['dynamic']={'GER_economy_of_conquest_modifier'};s['completed']={'hro_ger_mature_procurement'}
  s['variables'].update(GER_industrial_consumer_goods_factor=-.2,GER_monthly_consumer_goods_increase=-.01)
  before=dict(s['variables']);self.tick(s);self.assertEqual(s['variables'],before)
  s['dynamic']=set();s['variables']['GER_industrial_consumer_goods_factor']=2;self.tick(s)
  self.assertFalse(self.own(s));self.assertEqual(s['variables']['GER_industrial_consumer_goods_factor'],2)
