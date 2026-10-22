"""Execute emitted emergency eligibility and one-shot expiry, without HOI4."""
from pathlib import Path
import sys,tempfile,unittest,copy
from itertools import combinations
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'overhaul/tools'),str(ROOT/'tools')]
from clausewitz import parse
from generate_last_chance import generate,CITIES,MODIFIERS
from generate_operations import generate as ops_generate
from generate_war_adaptation import generate as war_generate
from generate_runtime import generate as runtime_generate
from test_runtime_aid import QueueRuntime
import test_operations as operations

class LastRuntime(QueueRuntime):
 def condition(self,nodes,s,tag=None,previous=None):
  def one(n):
   if n.key=='has_war':return s['war']==(n.value=='yes')
   if n.key.isdigit():return int(n.key) in s.get('owned',set())
   return super(LastRuntime,self).condition([n],s,tag,previous)
  return all(one(n) for n in nodes)

class LastChanceTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.p=Path(self.t.name)
  war_generate(self.p);ops_generate(self.p);generate(self.p);runtime_generate(self.p)
  self.r=LastRuntime(self.p)
  self.r.triggers.update({n.key:n for n in parse((self.p/'common/scripted_triggers/hro_last_chance_triggers.txt').read_text())})
 def state(self,tag):
  s=operations.OperationsTests().country(tag);s['owned']={c[0] for c in CITIES[tag] if c[0]!=4};s['controlled']=set();s['enemy_controlled']=set();return s
 def eligible(self,s):return self.r.condition(parse(f'hro_last_chance_{s["tag"].lower()}_eligible = yes'),s)
 def test_each_of_six_city_pairs_qualifies_but_one_city_does_not(self):
  for tag,cities in CITIES.items():
   for pair in combinations(cities,2):
    s=self.state(tag);s['owned'].add(4);s['enemy_controlled']={pair[0][1]};self.assertFalse(self.eligible(s))
    s['enemy_controlled'].add(pair[1][1]);self.assertTrue(self.eligible(s))
 def test_vienna_before_annexation_does_not_count_and_former_control_is_remembered(self):
  s=self.state('GER');s['enemy_controlled']={6521,11666};self.assertFalse(self.eligible(s))
  s['controlled']={11666};self.r.call('hro_last_chance_daily',s);s['controlled']=set();self.assertTrue(self.eligible(s))
 def test_retake_or_allied_handover_no_longer_counts(self):
  s=self.state('SOV');s['enemy_controlled']={6380,3151};self.assertTrue(self.eligible(s))
  s['enemy_controlled']={6380};self.assertFalse(self.eligible(s))
 def test_no_war_or_capitulation_blocks_grant(self):
  for key,value in [('war',False),('capitulated',True)]:
   s=self.state('SOV');s['enemy_controlled']={6380,3151};s[key]=value
   self.r.call('hro_last_chance_sov_grant',s);self.assertNotIn('hro_last_chance_sov_idea',s['ideas'])
 def test_both_grants_expire_at_182_days_and_cannot_refresh_or_repeat_after_reload(self):
  for tag,cities in CITIES.items():
   s=self.state(tag);s['enemy_controlled']={c[1] for c in cities[:2]};stem='hro_last_chance_'+tag.lower()
   self.r.call(stem+'_grant',s);self.assertIn(stem+'_idea',s['ideas']);deadline=s['expiry'][stem+'_idea']
   s=copy.deepcopy(s);self.r=LastRuntime(self.p);self.r.triggers.update({n.key:n for n in parse((self.p/'common/scripted_triggers/hro_last_chance_triggers.txt').read_text())})
   s['queue']=[];self.r.days(s,181);self.r.call(stem+'_grant',s);self.assertEqual(s['expiry'][stem+'_idea'],deadline);self.assertIn(stem+'_idea',s['ideas'])
   self.r.days(s,1);self.assertNotIn(stem+'_idea',s['ideas']);self.r.call(stem+'_grant',s);self.assertNotIn(stem+'_idea',s['ideas'])
 def test_spirit_uses_additive_training_threshold_and_all_requested_costs(self):
  ideas=parse((self.p/'common/ideas/hro_last_chance_ideas.txt').read_text())[0].one('country')
  for idea in ideas.value:
   actual={n.key:float(n.value) for n in idea.one('modifier').value};self.assertEqual(actual,MODIFIERS)
   self.assertAlmostEqual(.20+actual['minimum_training_level'],.01)
