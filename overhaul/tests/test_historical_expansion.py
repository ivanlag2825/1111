"""Execute history rewards against a small multi-country state model, not HOI4."""
from pathlib import Path
from datetime import timedelta
import copy,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'overhaul/tools')]
from clausewitz import parse,walk
from generate_historical_expansion import generate,REGIONS
from test_war_adaptation import EmittedLifecycle,day

class HistoryRuntime(EmittedLifecycle):
 def __init__(self,root):
  self.effects={n.key:n for n in parse((root/'common/scripted_effects/hro_history_expansion_effects.txt').read_text())};self.triggers={}
  self.events={n.scalar('id'):n for n in parse((root/'events/hro_history_expansion_events.txt').read_text()) if n.key in ('country_event','news_event')}
  self.world={}
  for tag in ('GER','SOV','FIN','FRA','ENG','ROM','HUN','ITA'):
   self.world[tag]=dict(tag=tag,date=day('1938.1.2'),wars=set(),joint=False,capitulated=False,exists=True,flags={},variables={},ideas=set(),events=[],completed=set(),controlled=set(),equipment=10000,manpower=100000)
  self.owners={146:'FIN',16:'FRA',**{sid:'SOV' for _,_,_,sid,_ in REGIONS}};self.controllers={1460:'FIN',11506:'FRA',**{p:'SOV' for _,_,_,_,p in REGIONS}};self.provinces={146:[1460],16:[11506],**{sid:[p] for _,_,_,sid,p in REGIONS}};self.near_front=set();self.created=[]
 def condition(self,nodes,s,tag=None,previous=None):
  def one(n):
   if n.key=='OR':return any(self.condition([c],s) for c in n.value)
   if n.key=='AND':return self.condition(n.value,s)
   if n.key=='NOT':return not self.condition(n.value,s)
   if n.key in self.world:return self.condition(n.value,self.world[n.key])
   if n.key and n.key.isdigit():return self.state_condition(n.value,int(n.key),s)
   if n.key=='exists':return s['exists']==(n.value=='yes')
   if n.key=='has_war_with':return n.value in s['wars']
   if n.key=='has_war_together_with':return s['joint']
   if n.key=='is_subject':return n.value=='no'
   if n.key=='is_in_faction_with':return False
   if n.key=='has_completed_focus':return n.value in s['completed']
   if n.key=='controls_province':return self.controllers[int(n.value)]==s['tag']
   if n.key=='has_manpower':return s['manpower']>float(n.value)
   if n.key=='has_equipment':return s['equipment']>float(n.value[0].value)
   return super(HistoryRuntime,self).condition([n],s)
  return all(one(n) for n in nodes)
 def state_condition(self,nodes,sid,s):
  for n in nodes:
   if n.key=='NOT':
    if self.state_condition(n.value,sid,s):return False
   elif n.key=='is_owned_by':
    if self.owners[sid]!=n.value:return False
   elif n.key=='is_fully_controlled_by':
    if not all(self.controllers[p]==n.value for p in self.provinces[sid]):return False
   elif n.key=='any_neighbor_state':
    if sid not in self.near_front:return False
   else:raise AssertionError(n.key)
  return True
 def execute(self,nodes,s):
  for n in nodes:
   if n.key=='name':continue
   if n.key in self.world:self.execute(n.value,self.world[n.key])
   elif n.key and n.key.isdigit():
    for child in n.value:
     self.assert_create(child,int(n.key))
   elif n.key=='transfer_state':
    sid=int(n.value);self.owners[sid]=s['tag']
    for p in self.provinces[sid]:self.controllers[p]=s['tag']
   elif n.key=='declare_war_on':
    target=n.scalar('target');s['wars'].add(target);self.world[target]['wars'].add(s['tag'])
   elif n.key=='add_manpower':s['manpower']+=int(n.value)
   elif n.key=='add_equipment_to_stockpile':s['equipment']+=int(n.scalar('amount'))
   elif n.key=='set_province_controller':self.controllers[int(n.value)]=s['tag']
   elif n.key=='division_template':s.setdefault('templates',[]).append(n.scalar('name'))
   elif n.key=='news_event':s['events'].append(n.scalar('id'))
   else:super().execute([n],s)
 def assert_create(self,node,sid):
  assert node.key=='create_unit';assert node.scalar('owner')=='GER'
  assert int(node.scalar('prioritize_location')) in self.provinces[sid]
  assert self.controllers[int(node.scalar('prioritize_location'))]=='GER'
  for _ in range(int(node.scalar('count'))):self.created.append((sid,node.scalar('division')))
 def tick(self,root='GER',days=0):
  for s in self.world.values():
   s['date']+=timedelta(days=days)
   for idea,expiry in s.get('expiry',{}).items():
    if s['date']>=expiry:s['ideas'].discard(idea)
  self.call('hro_history_expansion_daily',self.world[root])
 def choose(self,event,index,tag):
  self.execute(self.events[event].all('option')[index].value,self.world[tag])

class HistoricalExpansionTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);generate(self.root);self.r=HistoryRuntime(self.root)
 def test_czech_focus_once_and_reload_does_not_refresh_548_days(self):
  s=self.r.world['GER'];s['completed'].add('GER_demand_sudetenland');self.r.tick();expiry=s['expiry']['hro_history_czech_refit'];self.r.tick(days=200);self.assertEqual(s['expiry']['hro_history_czech_refit'],expiry);self.r.tick(days=348);self.assertNotIn('hro_history_czech_refit',s['ideas']);self.r.tick(days=1);self.assertNotIn('hro_history_czech_refit',s['ideas'])
 def test_renault_automatic_without_focus_and_tracks_paris_loss_recapture(self):
  s=self.r.world['GER'];self.r.tick();self.assertNotIn('hro_history_renault',s['ideas']);self.r.controllers[11506]='GER';self.r.tick(days=1);self.assertIn('hro_history_renault',s['ideas']);self.r.controllers[11506]='FRA';self.r.call('hro_history_renault_sync',s);self.assertNotIn('hro_history_renault',s['ideas']);self.r.controllers[11506]='GER';self.r.call('hro_history_renault_sync',s);self.assertIn('hro_history_renault',s['ideas'])
 def test_propaganda_has_fixed_august_cutoff_and_cannot_be_replayed(self):
  self.r.choose('hro.950',0,'GER');self.assertIn('hro_history_neubaufahrzeug_ger',self.r.world['GER']['ideas'])
  for tag in ('SOV','FRA','ENG'):self.assertIn('hro_history_neubaufahrzeug_fear',self.r.world[tag]['ideas'])
  for s in self.r.world.values():s['date']=day('1939.8.1')
  self.r.tick('SOV');self.r.tick('GER');self.r.choose('hro.950',0,'GER')
  for s in self.r.world.values():self.assertFalse(any('neubaufahrzeug' in i for i in s['ideas']))
 def test_allies_receive_bonus_only_on_actual_joint_entry_once(self):
  self.r.world['GER']['wars'].add('SOV');self.r.tick()
  for tag in ('ROM','HUN','ITA'):self.assertNotIn('hro_history_axis_blitz',self.r.world[tag]['ideas'])
  for tag in ('ROM','HUN','ITA'):
   s=self.r.world[tag];s['wars'].add('SOV');s['joint']=True;self.r.tick();self.assertIn('hro_history_axis_blitz',s['ideas']);expiry=s['expiry']['hro_history_axis_blitz'];self.r.tick(days=1);self.assertEqual(s['expiry']['hro_history_axis_blitz'],expiry)
  self.r.tick(days=730)
  for tag in ('ROM','HUN','ITA'):self.assertNotIn('hro_history_axis_blitz',self.r.world[tag]['ideas'])
 def test_mainila_diplomacy_transfers_only_karelia_without_war_or_repeat(self):
  s=self.r.world['SOV'];self.r.choose('hro.952',1,'SOV');self.assertEqual(self.r.owners[146],'SOV');self.assertFalse(s['wars']);self.assertIn('hro_history_mainila_agreement',s['ideas']);snapshot=copy.deepcopy(s);self.r.choose('hro.952',0,'SOV');self.r.choose('hro.952',1,'SOV');self.assertEqual(s,snapshot)
 def test_escalation_penalty_persists_past_six_months_and_ends_only_on_peace(self):
  s=self.r.world['SOV'];self.r.choose('hro.952',0,'SOV');self.r.execute(self.r.events['hro.953'].one('immediate').value,s);self.assertIn('FIN',s['wars']);self.assertIn('hro_history_mainila_crisis',s['ideas']);self.r.tick('SOV',days=200);self.assertIn('hro_history_mainila_crisis',s['ideas']);s['wars'].remove('FIN');self.r.tick('SOV');self.assertNotIn('hro_history_mainila_crisis',s['ideas'])
 def prepare_rear(self):
  self.r.world['GER']['wars'].add('SOV');self.r.world['SOV']['wars'].add('GER');s=self.r.world['GER'];self.r.call('hro_rear_begin_minsk',s);return s
 def test_rear_preparation_pays_once_and_spawns_only_two_weak_divisions(self):
  s=self.prepare_rear();self.assertEqual((s['equipment'],s['manpower']),(9400,94000));self.r.call('hro_rear_begin_minsk',s);self.assertEqual(s['equipment'],9400);self.r.tick(days=20);self.assertFalse(self.r.created);self.r.tick(days=1);self.assertEqual(len(self.r.created),2);self.assertEqual(self.r.controllers[216],'GER');self.assertEqual(self.r.owners[206],'SOV');self.r.tick(days=180);self.assertEqual(len(self.r.created),2)
 def test_rear_cancel_on_peace_or_front_approach_never_flips_state_or_spawns(self):
  for mode in ('peace','front'):
   self.setUp();s=self.prepare_rear()
   if mode=='peace':s['wars'].clear()
   else:self.r.near_front.add(206)
   self.r.tick(days=21);self.assertFalse(self.r.created);self.assertEqual(self.r.controllers[216],'SOV');self.assertEqual(s['equipment'],9400)
 def test_shortfall_prevents_spawning_or_equipment_subtraction(self):
  s=self.r.world['GER'];s['wars'].add('SOV');s['equipment']=599;self.r.call('hro_rear_begin_minsk',s);self.r.tick(days=21);self.assertFalse(self.r.created);self.assertEqual(s['equipment'],599)
 def test_militia_uses_native_escaped_division_strings_and_no_whole_state_transfer(self):
  for n in walk(parse((self.root/'common/scripted_effects/hro_history_expansion_effects.txt').read_text())):
   self.assertNotIn(n.key,('transfer_state','annex_country'))
   if n.key=='create_unit':
    raw=n.scalar('division');inner=raw[1:-1].replace('\\"','"');fields=parse(inner);template=next(x for x in fields if x.key=='division_template');self.assertEqual(template.value,'"hro_rear_militia"')

if __name__=='__main__':unittest.main()
