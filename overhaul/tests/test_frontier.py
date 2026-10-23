"""Execute emitted 1.4 programmes across costs, reloads and expiry boundaries."""
from pathlib import Path
from datetime import timedelta
import copy,json,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'overhaul/tools'),str(ROOT/'tools')]
from clausewitz import parse,walk
import generate_frontier as frontier
from generate_war_adaptation import generate as war_generate
from test_war_adaptation import EmittedLifecycle,day
import test_war_adaptation as war_tests

class FrontierRuntime(EmittedLifecycle):
 def __init__(self,p):
  self.effects={n.key:n for f in (p/'common/scripted_effects').glob('*.txt') for n in parse(f.read_text())}
  self.triggers={n.key:n for f in (p/'common/scripted_triggers').glob('*.txt') for n in parse(f.read_text())}
  self.decisions={n.key:n for category in parse((p/'common/decisions/hro_frontier.txt').read_text()) for n in category.value}
  self.events={n.scalar('id'):n for n in parse((p/'events/hro_frontier_events.txt').read_text()) if n.key=='country_event'}
  self.daily=parse('hro_frontier_daily = yes')
 def condition(self,nodes,s,tag=None,previous=None):
  def one(n):
   if n.key=='OR':return any(one(c) for c in n.value)
   if n.key=='hro_supported_country':return (s['tag'] in ('GER','SOV'))==(n.value=='yes')
   if n.key=='has_completed_focus':return n.value in s.get('completed',set())
   if n.key=='has_tech':return n.value in s.get('techs',set())
   if n.key=='always':return n.value=='yes'
   if n.key=='has_equipment':return all(s['equipment'].get(c.key,0)>float(c.value) for c in n.value)
   if n.key=='has_fuel':return s['fuel']>float(n.value)
   return super(FrontierRuntime,self).condition([n],s,tag,previous)
  return all(one(n) for n in nodes)
 def execute(self,nodes,s):
  special={'set_technology','add_fuel','add_equipment_to_stockpile'}
  if not any(n.key in special for n in nodes):
   return super().execute(nodes,s)
  pending=[]
  for n in nodes:
   if n.key not in special:pending.append(n);continue
   if pending:super().execute(pending,s);pending=[]
   if n.key=='set_technology':s.setdefault('techs',set()).update(c.key for c in n.value if c.key!='popup')
   elif n.key=='add_fuel':s['fuel']+=int(n.value)
   elif n.key=='add_equipment_to_stockpile':s['equipment'][n.scalar('type')]+=int(n.scalar('amount'))
  if pending:super().execute(pending,s)
 def choose(self,k,s):
  d=self.decisions[k]
  if not self.condition(d.one('visible').value,s) or not self.condition(d.one('available').value,s):return False
  cost=int(d.scalar('cost'))
  if s['add_political_power']<cost:return False
  s['add_political_power']-=cost;self.execute(d.one('complete_effect').value,s);return True
 def days(self,s,n):
  for _ in range(n):s['date']+=timedelta(days=1);self.tick(s)

class FrontierTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.p=Path(self.t.name)
  war_generate(self.p);self.report=frontier.generate(self.p);self.r=FrontierRuntime(self.p)
 def state(self,tag='GER'):
  s=war_tests.WarAdaptationTests().country(tag,'1941.6.22');s.update(add_political_power=1000,equipment={'motorized_equipment':150,'support_equipment':300,'infantry_equipment':2000},fuel=5000,techs=set(),expiry={},completed={f'hro_{tag.lower()}_frontier_bureau',f'hro_{tag.lower()}_operational_depots','hro_ger_motor_transport_standards','hro_ger_front_air_programme'})
  return s
 def option(self,s,event,j):self.r.execute([n for n in self.r.events[event].all('option')[j].value if n.key!='name'],s)
 def test_programme_cost_preparation_completion_exclusivity_and_reload(self):
  s=self.state();self.assertTrue(self.r.choose('hro_frontier_programme_armour',s));self.assertEqual(s['add_political_power'],900)
  self.assertIn('hro_frontier_retooling',s['ideas']);self.assertNotIn('hro_frontier_industry_armour',s['ideas'])
  self.assertFalse(self.r.choose('hro_frontier_programme_air',s));self.r.days(s,29)
  self.assertIn('hro_frontier_retooling',s['ideas']);s=copy.deepcopy(s);self.r=FrontierRuntime(self.p);self.r.days(s,1)
  self.assertNotIn('hro_frontier_retooling',s['ideas']);self.assertIn('hro_frontier_industry_armour',s['ideas'])
  expiry=s['expiry']['hro_frontier_industry_armour'];self.r.call('hro_frontier_finish_armour',s);self.assertEqual(s['expiry']['hro_frontier_industry_armour'],expiry)
  self.r.days(s,180);self.assertNotIn('hro_frontier_industry_armour',s['ideas']);self.assertFalse(self.r.choose('hro_frontier_programme_air',s))
  self.r.days(s,90);self.assertTrue(self.r.choose('hro_frontier_programme_air',s))
 def test_programmes_require_unlock_and_survive_peace_but_not_capitulation(self):
  s=self.state();s['completed'].clear();self.assertFalse(self.r.choose('hro_frontier_programme_air',s))
  s=self.state();s['war']=False;self.assertTrue(self.r.choose('hro_frontier_programme_air',s));self.r.days(s,30);self.assertIn('hro_frontier_industry_air',s['ideas'])
  s['capitulated']=True;self.r.days(s,1);self.assertNotIn('hro_frontier_industry_air',s['ideas']);s['capitulated']=False;self.r.days(s,1);self.assertNotIn('hro_frontier_industry_air',s['ideas']);self.assertFalse(self.r.choose('hro_frontier_programme_armour',s))
 def test_all_three_programmes_have_distinct_equipment_tradeoffs(self):
  ideas={n.key:n for n in parse((self.p/'common/ideas/hro_frontier_ideas.txt').read_text())[0].one('country').value}
  for key in ('armour','air','supply'):
   eq=ideas['hro_frontier_industry_'+key].one('equipment_bonus');values=[float(n.scalar('build_cost_ic')) for n in eq.value]
   self.assertTrue(any(v<0 for v in values));self.assertTrue(any(v>0 for v in values));self.assertTrue(all(n.scalar('instant')=='yes' for n in eq.value))
 def test_reserve_checks_every_resource_and_does_not_charge_on_failure(self):
  for resource in ('fuel','motorized_equipment','support_equipment','infantry_equipment'):
   s=self.state()
   if resource=='fuel':s['fuel']-=1
   else:s['equipment'][resource]-=1
   saved=copy.deepcopy(s);self.assertFalse(self.r.choose('hro_frontier_prepare_reserve',s));self.assertEqual(s,saved)
 def test_reserve_consumes_exact_stock_once_waits_21_days_and_cannot_stack(self):
  s=self.state();self.assertTrue(self.r.choose('hro_frontier_prepare_reserve',s));self.assertEqual(s['fuel'],0);self.assertEqual(set(s['equipment'].values()),{0});self.assertEqual(s['add_political_power'],950)
  self.r.call('hro_frontier_load_reserve',s);self.assertEqual(s['fuel'],0)
  self.r.days(s,20);self.assertNotIn('hro_frontier_reserve_ready',s['flags']);self.r.days(s,1);self.assertIn('hro_frontier_reserve_ready',s['flags'])
  s=copy.deepcopy(s);self.r=FrontierRuntime(self.p);self.r.days(s,130);s['equipment']={k:10000 for k in s['equipment']};s['fuel']=50000
  self.assertFalse(self.r.choose('hro_frontier_prepare_reserve',s))
 def test_reserve_requires_operation_is_mutually_exclusive_and_keeps_fatigue(self):
  for option in ('tempo','relief'):
   s=self.state();self.r.choose('hro_frontier_prepare_reserve',s);self.r.days(s,21)
   self.assertFalse(self.r.choose('hro_frontier_deploy_'+option,s));s['flags']['hro_ops_exhaustion']=None;s['variables']['hro_ops_exhaustion_days']=21
   s['flags']['hro_ops_rest']=None;self.assertFalse(self.r.choose('hro_frontier_deploy_'+option,s));del s['flags']['hro_ops_rest']
   self.assertTrue(self.r.choose('hro_frontier_deploy_'+option,s));self.assertNotIn('hro_frontier_reserve_ready',s['flags']);self.assertEqual(s['variables']['hro_ops_exhaustion_days'],21)
   self.assertFalse(self.r.choose('hro_frontier_deploy_'+('relief' if option=='tempo' else 'tempo'),s))
   self.r.days(s,14);self.assertNotIn('hro_frontier_reserve_'+option,s['ideas'])
 def test_each_german_action_has_one_shared_lock_and_no_refresh(self):
  for key,(_,_,cost,days,_,_) in frontier.GER_ACTIONS.items():
   s=self.state();action='hro_frontier_ger_'+key+'_activate';self.assertTrue(self.r.choose(action,s));self.assertEqual(s['add_political_power'],1000-cost)
   for other in frontier.GER_ACTIONS:self.assertFalse(self.r.choose('hro_frontier_ger_'+other+'_activate',s))
   self.r.days(s,days);self.assertNotIn('hro_frontier_ger_'+key,s['ideas']);self.r.days(s,90-days);self.assertTrue(self.r.choose(action,s))
 def test_combat_benefits_do_not_reappear_after_peace(self):
  s=self.state();self.r.choose('hro_frontier_ger_fighter_sweep_activate',s);s['war']=False;self.r.days(s,1);self.assertNotIn('hro_frontier_ger_fighter_sweep',s['ideas'])
  s['war']=True;self.r.days(s,1);self.assertNotIn('hro_frontier_ger_fighter_sweep',s['ideas']);self.assertFalse(self.r.choose('hro_frontier_ger_cas_surge_activate',s))
 def test_school_focus_awards_research_bonus_once_and_never_auto_researches(self):
  for tag in ('GER','SOV'):
   s=self.state(tag);s['completed'].add(f'hro_{tag.lower()}_school_urban')
   self.r.tick(s);self.assertFalse(s['techs'])
   effect=f'hro_frontier_grant_{tag.lower()}_urban'
   self.r.call(effect,s);self.assertFalse(s['techs']);self.assertEqual(len(s['research']),1);self.assertEqual(s['army_experience'],25)
   s=copy.deepcopy(s);self.r=FrontierRuntime(self.p);self.r.call(effect,s);self.r.tick(s)
   self.assertEqual(len(s['research']),1);self.assertEqual(s['army_experience'],25);self.assertFalse(s['techs'])
   s=self.state(tag);s['techs'].add(f'hro_tech_{tag.lower()}_forest');self.r.call(effect,s)
   self.assertFalse(s.get('research'));self.assertEqual(s['army_experience'],25)
 def test_all_historical_events_guard_date_war_unlock_and_single_choice(self):
  for index,record in enumerate(frontier.HISTORY,930):
   s=self.state(record['tag']);s['variables']['hro_war_sov_war_days']=180;s['date']=day(record['date']);self.r.tick(s);self.assertNotIn(f'hro.{index}',s['events'])
   self.r.days(s,1);self.assertIn(f'hro.{index}',s['events']);self.r.tick(s);self.assertEqual(s['events'].count(f'hro.{index}'),1)
   self.option(s,f'hro.{index}',0);first='hro_frontier_history_'+record['key']+'_0';other=first[:-1]+'1';self.assertIn(first,s['ideas']);expiry=s['expiry'][first]
   self.option(s,f'hro.{index}',1);self.option(s,f'hro.{index}',0);self.assertNotIn(other,s['ideas']);self.assertEqual(s['expiry'][first],expiry)
   self.r.days(s,record['options'][0][-1]);self.assertNotIn(first,s['ideas'])
 def test_stale_historical_popup_gives_nothing_after_peace(self):
  s=self.state('GER');s['date']=day('1944.1.1');self.r.tick(s);s['war']=False;self.option(s,'hro.931',0)
  self.assertFalse(any(i.startswith('hro_frontier_history') for i in s['ideas']))
 def test_1947_cancels_pending_and_ready_programmes_without_refunds(self):
  s=self.state();s['date']=day('1946.12.20');self.r.choose('hro_frontier_programme_armour',s);self.r.choose('hro_frontier_prepare_reserve',s);self.r.days(s,12)
  self.assertFalse(any(i.startswith('hro_frontier') for i in s['ideas']));self.assertNotIn('hro_frontier_reserve_pending',s['flags']);self.assertEqual(s['fuel'],0)
 def test_new_focuses_are_short_linked_and_have_symmetric_school_exclusions(self):
  for tag in ('ger','sov'):
   c=json.loads((ROOT/'overhaul/data'/f'{tag}.json').read_text());f={x['id']:x for x in c['focuses']}
   for key in frontier.SCHOOLS:
    x=f[f'hro_{tag}_school_{key}'];self.assertEqual(x['cost'],3);self.assertTrue(x['prerequisites']);other=x['mutually_exclusive'][0];self.assertIn(x['id'],f[other]['mutually_exclusive'])
   self.assertTrue(all(f[f'hro_{tag}_{k}']['reward'] for k in ('frontier_bureau','operational_depots')))

class FrontierSchemaTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name)
  self.mod=self.root/'mod';frontier.generate(self.mod)
  self.game=self.root/'game';u=self.game/'common/units/fixture.txt';u.parent.mkdir(parents=True)
  u.write_text('sub_units = { infantry = {} engineer = {} motorized = {} mechanized = {} logistics_company = {} }')
  self.schema=self.root/'schema';p=self.schema/'Config/stats.cwt';p.parent.mkdir(parents=True)
  p.write_text('alias[unit_stat:maximum_speed] = float\nalias[unit_stat:supply_consumption_factor] = float\nalias[unit_stat:fuel_consumption_factor] = float\n')
 def test_school_grants_resolve_to_real_units_and_supported_stats(self):
  audit=frontier.audit_technologies(self.mod,self.game,self.schema)
  self.assertEqual(audit['technologies'],8);self.assertEqual(audit['grant_references'],0)
 def test_unknown_technology_unit_and_misspelled_stat_fail_closed(self):
  p=self.mod/'common/technologies/hro_front_schools.txt';original=p.read_text()
  for old,new,error in [('infantry =','imaginary_unit =','missing unit'),('maximum_speed =','maximum_speeed =','Unknown school stat')]:
   p.write_text(original.replace(old,new))
   with self.assertRaisesRegex(ValueError,error):frontier.audit_technologies(self.mod,self.game,self.schema)
  p.write_text(original)
 def test_unknown_granted_school_technology_fails_closed(self):
  p=self.mod/'common/scripted_effects/hro_frontier_effects.txt';p.write_text(p.read_text()+'\nbad_grant = { set_technology = { hro_tech_missing = 1 } }')
  with self.assertRaisesRegex(ValueError,'Unknown school technology'):frontier.audit_technologies(self.mod,self.game,self.schema)
