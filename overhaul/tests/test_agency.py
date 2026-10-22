"""Execute emitted native callbacks and daily damage waves, not the HOI4 engine."""
from datetime import date,timedelta
from pathlib import Path
import copy,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'overhaul/tools'),str(ROOT/'tools')]
from clausewitz import parse
from generate_agency import generate,MISSIONS,audit_operations
from spirit_lifecycle import author_spirit_assets


class Runtime:
 def __init__(self,output):
  self.effects={n.key:n for n in parse((output/'common/scripted_effects/hro_agency_effects.txt').read_text())}
  self.operations={n.key:n for n in parse((output/'common/operations/hro_agency_operations.txt').read_text())}
 def has(self,flags,key,s):return key in flags and (flags[key] is None or s['date']<flags[key])
 def condition(self,nodes,s,scope=None,previous=None):
  scope=scope or s['actor']
  def one(n):
   if n.key in ('AND','OR','NOT'):
    values=[self.condition([c],s,scope,previous) for c in n.value]
    return any(values) if n.key=='OR' else not all(values) if n.key=='NOT' else all(values)
   if n.key=='FROM':return self.condition(n.value,s,s['target'],scope)
   if n.key=='has_intelligence_agency':return s.get('agency',True)
   if n.key=='custom_trigger_tooltip':return self.condition([c for c in n.value if c.key!='tooltip'],s,scope,previous)
   if n.key in ('GER','SOV','ROOT'):return self.condition(n.value,s,s['actor'] if n.key=='ROOT' else n.key,scope)
   if n.key=='original_tag':return scope==n.value
   if n.key=='hro_war_eastern_war':return s['war'] and not s['capitulated'] and not s['enemy_capitulated'] and s['date']<date(1947,1,1)
   if n.key=='has_war_with':return s['war'] and scope!=s['actor']
   if n.key=='has_capitulated':return s['enemy_capitulated']==(n.value=='yes')
   if n.key=='has_country_flag':return self.has(s['countries'][scope],n.value,s)
   if n.key=='has_state_flag':return self.has(s['states'][scope]['flags'],n.value,s)
   if n.key=='is_fully_controlled_by':return s['states'][scope]['controller']==previous and s['states'][scope]['full']
   if n.key in ('air_base','infrastructure','rail_way','supply_node'):return s['states'][scope][n.key]>float(n.value)
   if n.key=='has_finished_collecting_for_operation':return s.get('collected',True)
   if n.key=='is_running_operation':return (n.scalar('operation'),n.scalar('target')) in s['running']
   if n.key=='check_variable':return all(s['variables'].get(c.key,0)>float(c.value) for c in n.value)
   raise AssertionError('Unmodelled agency trigger '+str(n.key))
  return all(one(n) for n in nodes)
 def execute(self,nodes,s,scope=None,previous=None):
  scope=scope or s['actor'];prior=None
  for n in nodes:
   if n.key in ('if','else_if'):
    matched=(n.key=='if' or prior is False) and self.condition(n.one('limit').value,s,scope,previous)
    if matched:self.execute([c for c in n.value if c.key!='limit'],s,scope,previous)
    prior=matched if n.key=='if' else prior or matched
   elif n.key=='else':
    if prior is False:self.execute(n.value,s,scope,previous)
    prior=None
   elif n.key in ('ROOT','GER','SOV'):self.execute(n.value,s,s['actor'] if n.key=='ROOT' else n.key,scope)
   elif n.key in ('set_country_flag','set_state_flag'):
    key=n.value if isinstance(n.value,str) else n.scalar('flag')
    expiry=None if isinstance(n.value,str) else s['date']+timedelta(days=int(n.scalar('days')))
    (s['countries'][scope] if n.key=='set_country_flag' else s['states'][scope]['flags'])[key]=expiry
   elif n.key=='hro_runtime_seed':pass  # Full saved heartbeat tested in test_runtime.
   elif n.key=='clr_state_flag':s['states'][scope]['flags'].pop(n.value,None)
   elif n.key=='every_controlled_state':
    for region,data in s['states'].items():
     if data['controller']==scope:self.execute(n.value,s,region,scope)
   elif n.key=='clr_country_flag':s['countries'][scope].pop(n.value,None)
   elif n.key in ('set_variable','add_to_variable'):
    for c in n.value:s['variables'][c.key]=float(c.value)+(s['variables'].get(c.key,0) if n.key=='add_to_variable' else 0)
   elif n.key=='random_controlled_state':
    candidates=[state for state,data in s['states'].items() if data['controller']==scope and self.condition(n.one('limit').value,s,state,scope)]
    # Deterministic choice lets tests assert eligibility, uniqueness and scope.
    if candidates:self.execute([c for c in n.value if c.key not in ('limit','prioritize')],s,candidates[0],scope)
   elif n.key=='damage_building':s['damage'].append((scope,n.scalar('type'),float(n.scalar('damage'))))
   elif n.key=='custom_effect_tooltip':pass
   elif n.key in self.effects:self.execute(self.effects[n.key].value,s,scope,previous)
   else:raise AssertionError('Unmodelled agency effect '+str(n.key))
 def call(self,name,s):self.execute(self.effects[name].value,s)
 def callback(self,kind,action,s):self.execute(self.operations['hro_operation_'+kind].one(action).value,s,scope='OPERATION')
 def start(self,kind,s):
  s['running'].add(('hro_operation_'+kind,s['target']));self.callback(kind,'on_start',s)
 def finish(self,kind,s):
  s['running'].discard(('hro_operation_'+kind,s['target']));self.callback(kind,'outcome_execute',s)
 def days(self,s,days):
  for _ in range(days):
   s['date']+=timedelta(days=1);self.call('hro_agency_daily',s)


class AgencyTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.output=Path(self.temp.name)
  generate(self.output);self.r=Runtime(self.output)
 def country(self,actor='GER',count=12):
  target='SOV' if actor=='GER' else 'GER'
  return dict(actor=actor,target=target,date=date(1941,6,22),war=True,capitulated=False,enemy_capitulated=False,
   countries={actor:{},target:{}},running=set(),variables={},damage=[],
   states={state:dict(controller=target,full=True,air_base=5,infrastructure=5,rail_way=5,supply_node=1,flags={}) for state in range(1,count+1)})
 def test_native_operations_have_real_agents_network_equipment_and_three_phases(self):
  for kind,mission in MISSIONS.items():
   n=self.r.operations['hro_operation_'+kind]
   self.assertEqual(n.scalar('operatives'),'2');self.assertEqual(int(n.scalar('network_strength')),mission['network'])
   self.assertEqual(len(n.all('phases')),3);self.assertEqual(n.one('on_start').value[0].key,'ROOT')
   self.assertGreater(float(n.scalar('risk_chance')),0);self.assertIsNotNone(n.one('equipment').one('civilian_factories'))
 def test_preview_and_start_do_not_damage_buildings(self):
  s=self.country();self.r.callback('air','outcome_potential',s);self.assertEqual(s['damage'],[])
  self.r.start('air',s);self.assertEqual(s['damage'],[]);self.r.days(s,14);self.assertEqual(s['damage'],[])
 def test_waves_hit_six_distinct_states_on_days_fifteen_thirtyfive_and_completion(self):
  for actor in ('GER','SOV'):
   s=self.country(actor);self.r.start('air',s);self.r.days(s,15)
   self.assertEqual(len(s['damage']),6);self.assertEqual(len({x[0] for x in s['damage']}),6)
   self.assertTrue(all(x[1:] == ('air_base',6) for x in s['damage']))
   self.r.days(s,19);self.assertEqual(len(s['damage']),6)
   self.r.days(s,1);self.assertEqual(len(s['damage']),12)
   self.r.days(s,25);self.r.finish('air',s);self.assertEqual(len(s['damage']),18)
 def test_final_callback_is_once_and_does_not_repeat_earlier_waves(self):
  s=self.country();self.r.start('air',s);self.r.days(s,60);self.r.finish('air',s);count=len(s['damage'])
  self.r.finish('air',s);self.r.call('hro_agency_ger_air_wave_1',s);self.assertEqual(len(s['damage']),count)
 def test_cancelled_operation_stops_future_waves_without_repairing_old_damage(self):
  s=self.country();self.r.start('air',s);self.r.days(s,15);s['running'].clear();self.r.days(s,30)
  self.r.finish('air',s);self.assertEqual(len(s['damage']),6);self.assertNotIn('hro_agency_busy',s['countries']['GER'])
 def test_logistics_damage_covers_railway_infrastructure_and_hubs(self):
  s=self.country();self.r.start('logistics',s);self.r.days(s,15)
  self.assertEqual(len(s['damage']),18)
  self.assertEqual({(b,d) for _,b,d in s['damage']},{('rail_way',5),('infrastructure',3),('supply_node',1)})
 def test_security_halves_all_damage_at_time_of_each_wave(self):
  s=self.country();s['countries']['SOV']['hro_ops_security']=None;self.r.start('logistics',s);self.r.days(s,15)
  self.assertEqual({(b,d) for _,b,d in s['damage']},{('rail_way',2.5),('infrastructure',1.5),('supply_node',.5)})
  s['countries']['SOV'].clear();self.r.days(s,20);self.assertIn((1,'rail_way',5),s['damage'])
 def test_friendly_neutral_contested_or_missing_objects_cannot_be_hit(self):
  s=self.country(count=5);s['states'][1]['controller']='GER';s['states'][2]['controller']='USA';s['states'][3]['full']=False;s['states'][4]['air_base']=0
  self.r.start('air',s);self.r.days(s,15);self.assertEqual(s['damage'],[(5,'air_base',6)])
 def test_objects_are_rechecked_before_each_wave(self):
  s=self.country(count=3);self.r.start('air',s);self.r.days(s,15)
  for region in s['states'].values():region['controller']='GER'
  self.r.days(s,20);self.r.finish('air',s);self.assertEqual(len(s['damage']),3)
 def test_cooldown_starts_after_completion_not_preparation(self):
  s=self.country();self.r.callback('air','on_start',s)
  self.assertNotIn('hro_agency_air_cooldown',s['countries']['GER'])
  self.assertNotIn('hro_agency_busy',s['countries']['GER'])
  self.r.start('air',s);self.r.days(s,60);self.r.finish('air',s)
  expiry=s['countries']['GER']['hro_agency_air_cooldown'];self.assertEqual(expiry,s['date']+timedelta(days=150))
  self.r.start('air',s);self.assertNotIn('hro_agency_ger_air_planned',s['countries']['GER'])
  self.assertEqual(s['countries']['GER']['hro_agency_air_cooldown'],expiry)
 def test_actual_availability_remains_true_after_preparation_and_locks_only_after_finish(self):
  s=self.country();operation=self.r.operations['hro_operation_air']
  self.assertTrue(self.r.condition(operation.one('available').value,s))
  self.r.callback('air','on_start',s)
  self.assertTrue(self.r.condition(operation.one('available').value,s))
  self.assertTrue(self.r.condition(operation.one('requirements').value,s))
  self.r.finish('air',s)
  self.assertFalse(self.r.condition(operation.one('available').value,s))
  self.assertTrue(self.r.condition(operation.one('requirements').value,s))
 def test_upgrade_unlocks_old_preparation_without_applying_new_cooldown(self):
  s=self.country();s['collected']=False
  s['countries']['GER'].update({'hro_agency_ger_air_active':None,'hro_agency_cooldown':s['date']+timedelta(days=100),'hro_agency_busy':None})
  s['running'].add(('hro_operation_air','SOV'));self.r.days(s,1)
  self.assertNotIn('hro_agency_cooldown',s['countries']['GER']);self.assertNotIn('hro_agency_air_cooldown',s['countries']['GER'])
  self.assertIn('hro_agency_ger_air_planned',s['countries']['GER']);self.assertEqual(s['damage'],[])
 def test_preparation_does_not_count_execution_days_or_apply_damage(self):
  s=self.country();s['collected']=False;self.r.start('air',s);self.r.days(s,50)
  self.assertEqual(s['damage'],[]);self.assertNotIn('hro_agency_air_cooldown',s['countries']['GER'])
  self.assertEqual(s['variables']['hro_agency_ger_air_days'],0)
  s['collected']=True;self.r.days(s,15);self.assertEqual(len(s['damage']),6)
 def test_native_completion_awards_waves_even_if_daily_execution_poll_was_missed(self):
  s=self.country();self.r.callback('air','on_start',s);self.r.finish('air',s)
  self.assertEqual(len(s['damage']),18);self.r.finish('air',s);self.assertEqual(len(s['damage']),18)
 def test_next_mission_after_cooldown_has_fresh_once_only_waves(self):
  s=self.country();self.r.start('air',s);self.r.days(s,60);self.r.finish('air',s)
  self.r.days(s,150);self.r.start('air',s);self.r.days(s,15)
  self.assertEqual(len(s['damage']),24)
  self.r.call('hro_agency_ger_air_wave_1',s);self.assertEqual(len(s['damage']),24)
 def test_accelerated_completion_resolves_remaining_waves_once(self):
  s=self.country();self.r.start('air',s);self.r.days(s,10);self.r.finish('air',s)
  self.assertEqual(len(s['damage']),18);self.assertEqual(len({x[0] for x in s['damage']}),6)
 def test_reload_does_not_reset_wave_counter_or_grant_twice(self):
  s=self.country();self.r.start('air',s);self.r.days(s,20);saved=copy.deepcopy(s);self.r=Runtime(self.output)
  self.r.days(saved,15);self.assertEqual(len(saved['damage']),12)
 def test_peace_capitulation_or_1947_cancel_without_later_callback_damage(self):
  for reason in ('war','capitulated','enemy_capitulated','date'):
   s=self.country();self.r.start('air',s);s[reason]=date(1947,1,1) if reason=='date' else False if reason=='war' else True
   self.r.call('hro_agency_daily',s);self.r.finish('air',s);self.assertEqual(s['damage'],[])
 def test_owned_assets_and_broken_phase_reference_audit(self):
  author_spirit_assets(self.output);self.assertEqual(audit_operations(self.output),[])
  p=self.output/'common/operations/hro_agency_operations.txt';p.write_text(p.read_text().replace('hro_agency_phase_infiltration =','hro_missing_phase ='))
  self.assertTrue(any('Unknown agency phase' in message for message in audit_operations(self.output)))


if __name__=='__main__':unittest.main()
