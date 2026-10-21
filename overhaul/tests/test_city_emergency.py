"""Execute emitted city-control, response and temporary-mobilisation scripts."""
from datetime import date,timedelta
from pathlib import Path
import sys,tempfile,unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'overhaul/tools')]
from clausewitz import parse
from generate_emergency import generate,records,validate_geography


class Runtime:
    def __init__(self,output):
        self.effects={n.key:n for n in parse((output/'common/scripted_effects/hro_city_effects.txt').read_text())}
        self.decisions={n.key:n for n in parse((output/'common/decisions/hro_city_responses.txt').read_text())[0].value}
        self.daily=parse((output/'common/on_actions/hro_city_on_actions.txt').read_text())[0].one('on_daily').one('effect').value

    def condition(self,nodes,s,enemy=False):
        def one(n):
            if n.key in ('AND','limit'):return self.condition(n.value,s,enemy)
            if n.key=='OR':return any(one(c) for c in n.value)
            if n.key=='NOT':return not self.condition(n.value,s,enemy)
            if n.key=='original_tag':return (('GER' if enemy else s['tag'])==n.value)
            if n.key=='hro_war_eastern_war':return (s['war'] and not s['capitulated'] and not s['enemy_capitulated'] and s['date']<date(1947,1,1))==(n.value=='yes')
            if n.key=='controls_province':return int(n.value) in s['enemy' if enemy else 'controlled']
            if n.key=='any_enemy_country':return s['war'] and self.condition(n.value,s,True)
            if n.key=='has_country_flag':return n.value in s['flags'] and (s['flags'][n.value] is None or s['date']<s['flags'][n.value])
            if n.key=='has_idea':return n.value in s['ideas']
            if n.key=='check_variable':
                return all({'<':s['vars'].get(c.key,0)<float(c.value),'>':s['vars'].get(c.key,0)>float(c.value),'=':s['vars'].get(c.key,0)==float(c.value)}[c.op] for c in n.value)
            if n.key and n.key.isdigit():return self.condition(n.value,s,enemy)
            if n.key in ('is_owned_by','is_fully_controlled_by'):return s['capacity_owned']
            if n.key=='free_building_slots':return s['capacity_free']
            raise AssertionError('Unmodelled city condition '+str(n.key))
        return all(one(n) for n in nodes)

    def execute(self,nodes,s,scope=None):
        previous=None
        for n in nodes:
            if n.key in ('if','else_if'):
                matched=(n.key=='if' or previous is False) and self.condition(n.one('limit').value,s)
                if matched:self.execute([c for c in n.value if c.key!='limit'],s,scope)
                previous=matched if n.key=='if' else previous or matched
            elif n.key=='else':
                if previous is False:self.execute(n.value,s,scope)
                previous=None
            elif n.key=='set_country_flag':
                k=n.value if isinstance(n.value,str) else n.scalar('flag')
                s['flags'][k]=None if isinstance(n.value,str) or n.scalar('days') is None else s['date']+timedelta(days=int(n.scalar('days')))
            elif n.key=='clr_country_flag':s['flags'].pop(n.value,None)
            elif n.key in ('set_variable','add_to_variable'):
                for c in n.value:s['vars'][c.key]=float(c.value)+(s['vars'].get(c.key,0) if n.key=='add_to_variable' else 0)
            elif n.key=='add_ideas':s['ideas'].add(n.value)
            elif n.key=='remove_ideas':s['ideas'].discard(n.value)
            elif n.key=='add_timed_idea':
                s['ideas'].add(n.scalar('idea'));s['expiry'][n.scalar('idea')]=s['date']+timedelta(days=int(n.scalar('days')))
            elif n.key=='add_manpower':s['manpower']+=int(n.value)
            elif n.key=='add_tech_bonus':s['research'].append((n.scalar('category'),int(n.scalar('uses'))))
            elif n.key=='add_extra_state_shared_building_slots':s['slots']+=int(n.value)
            elif n.key=='add_building_construction':s['factories'].append((scope,n.scalar('type'),int(n.scalar('level'))))
            elif n.key=='country_event':s['events'].append(n.scalar('id'))
            elif n.key=='ROOT':self.execute(n.value,s,None)
            elif n.key and n.key.isdigit():self.execute(n.value,s,int(n.key))
            elif n.key in self.effects:self.execute(self.effects[n.key].value,s,scope)
            else:raise AssertionError('Unmodelled city effect '+str(n.key))

    def tick(self,s):
        for idea,expiry in list(s['expiry'].items()):
            if s['date']>=expiry:s['ideas'].discard(idea)
        self.execute(self.daily,s)
    def call(self,name,s):self.execute(self.effects[name].value,s)
    def advance(self,s,days):
        for _ in range(days):s['date']+=timedelta(days=1);self.tick(s)


class CityEmergencyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.output=Path(self.temp.name);generate(self.output);self.r=Runtime(self.output)
        self.s=dict(tag='SOV',date=date(1941,6,20),war=False,capitulated=False,enemy_capitulated=False,controlled={c['province'] for c in records()},enemy=set(),flags={},vars={},ideas={'native_red_army'},expiry={},manpower=0,research=[],factories=[],slots=0,events=[],capacity_owned=True,capacity_free=True)
        self.r.tick(self.s)

    def lose(self,key):
        c=next(c for c in records() if c['key']==key);self.s['war']=True
        self.s['controlled'].discard(c['province']);self.s['enemy'].add(c['province']);self.r.tick(self.s)
    def regain(self,key):
        c=next(c for c in records() if c['key']==key)
        self.s['enemy'].discard(c['province']);self.s['controlled'].add(c['province']);self.r.tick(self.s)
    def start(self,key):
        d=self.r.decisions[f'hro_city_{key}_response'];self.r.execute(d.one('complete_effect').value,self.s)
    def finish_timer(self,key):self.r.execute(self.r.decisions[f'hro_city_{key}_response'].one('remove_effect').value,self.s)

    def test_real_enemy_city_control_required_not_state_loss_or_friendly_handover(self):
        self.s['war']=True;self.s['capacity_owned']=False;self.r.tick(self.s)
        self.assertNotIn('hro_city_leningrad_lost',self.s['flags'])
        self.s['controlled'].discard(3151);self.r.tick(self.s)
        self.assertNotIn('hro_city_leningrad_lost',self.s['flags'])
        self.s['enemy'].add(3151);self.r.tick(self.s)
        self.assertIn('hro_city_leningrad_lost',self.s['flags'])

    def test_no_loss_rewards_at_peace_or_for_other_country(self):
        self.s['controlled'].discard(525);self.s['enemy'].add(525);self.r.tick(self.s)
        self.assertNotIn('hro_city_kiev_lost',self.s['flags'])
        self.s.update(tag='GER',war=True);self.r.tick(self.s)
        self.assertNotIn('hro_city_kiev_lost',self.s['flags'])

    def test_multiple_losses_have_one_bounded_shock_and_soften_after_war_days(self):
        for c in records():self.lose(c['key'])
        self.assertEqual(self.s['ideas'] & {f'hro_idea_city_crisis_{n}' for n in range(1,4)},{'hro_idea_city_crisis_3'})
        self.r.advance(self.s,90)
        self.assertFalse(any('city_crisis' in i for i in self.s['ideas']))
        self.assertTrue(all(self.s['vars']['hro_city_'+c['key']+'_days']==90 for c in records()))

    def test_capital_city_loss_has_double_weight_and_response_reduces_it(self):
        self.lose('moscow')
        self.assertIn('hro_idea_city_crisis_2',self.s['ideas'])
        self.lose('minsk')
        self.assertIn('hro_idea_city_crisis_3',self.s['ideas'])
        self.r.call('hro_city_moscow_finish',self.s)
        self.assertIn('hro_idea_city_crisis_1',self.s['ideas'])
        self.assertNotIn('hro_idea_city_crisis_3',self.s['ideas'])

    def test_peace_pauses_crisis_days_and_cleans_work_and_penalties(self):
        self.lose('minsk');self.start('minsk');self.s['war']=False;before=self.s['vars']['hro_city_minsk_days']
        self.r.advance(self.s,100)
        self.assertEqual(self.s['vars']['hro_city_minsk_days'],before)
        self.assertNotIn('hro_city_response_busy',self.s['flags'])
        self.assertFalse(any('city_crisis' in i or 'response_working' in i for i in self.s['ideas']))
        self.assertIn('native_red_army',self.s['ideas'])

    def test_no_early_rewards_and_public_focus_finish_cannot_duplicate_timer_reward(self):
        self.lose('kiev');self.start('kiev')
        self.assertEqual(self.s['manpower'],0);self.assertEqual(self.s['factories'],[])
        self.r.call('hro_city_kiev_finish',self.s);count=self.s['manpower'];factories=list(self.s['factories'])
        self.finish_timer('kiev');self.r.call('hro_city_kiev_finish',self.s)
        self.assertEqual(self.s['manpower'],count);self.assertEqual(self.s['factories'],factories)
        self.assertEqual(self.s['vars']['hro_city_responses_completed'],1)

    def test_focus_for_different_city_does_not_cancel_occupied_project_slot(self):
        self.lose('minsk');self.lose('kiev');self.start('minsk')
        self.r.call('hro_city_kiev_finish',self.s)
        self.assertIn('hro_city_response_busy',self.s['flags']);self.assertIn('hro_city_minsk_active',self.s['flags'])
        self.assertIn('hro_idea_city_response_working',self.s['ideas'])
        self.finish_timer('minsk');self.assertNotIn('hro_city_response_busy',self.s['flags'])

    def test_stale_cancel_does_not_unlock_another_city(self):
        self.lose('minsk');self.lose('kiev');self.start('minsk');self.finish_timer('minsk');self.start('kiev')
        self.r.call('hro_city_minsk_cancel',self.s)
        self.assertIn('hro_city_response_busy',self.s['flags']);self.assertIn('hro_city_kiev_active',self.s['flags'])

    def test_response_guards_country_war_and_loss_and_capacity_fallback_is_research(self):
        self.r.call('hro_city_moscow_finish',self.s);self.assertEqual(self.s['manpower'],0)
        self.lose('moscow');self.s['capacity_owned']=False;self.r.call('hro_city_moscow_finish',self.s)
        self.assertEqual(self.s['factories'],[]);self.assertEqual(self.s['manpower'],120000)
        self.assertIn(('industry',2),self.s['research']);self.assertIn('hro_city_moscow_responded',self.s['flags'])

    def test_repeated_city_capture_cannot_farm_rewards_or_events(self):
        self.lose('minsk');self.r.call('hro_city_minsk_finish',self.s);self.regain('minsk')
        before=(self.s['manpower'],len(self.s['events']),self.s['vars']['hro_city_liberated_total'])
        for _ in range(3):self.lose('minsk');self.regain('minsk');self.r.call('hro_city_minsk_finish',self.s)
        self.assertEqual((self.s['manpower'],len(self.s['events']),self.s['vars']['hro_city_liberated_total']),before)

    def test_mobilisation_tiers_do_not_stack_or_refresh_active_window(self):
        self.lose('minsk');self.r.call('hro_city_minsk_finish',self.s);expiry=self.s['flags']['hro_city_mobilization_active']
        self.r.advance(self.s,10)
        for key in ('kiev','kharkov'):self.lose(key);self.r.call('hro_city_'+key+'_finish',self.s)
        self.assertEqual(self.s['flags']['hro_city_mobilization_active'],expiry)
        self.assertEqual(self.s['ideas'] & {f'hro_idea_city_mobilization_{n}' for n in range(1,4)},{'hro_idea_city_mobilization_3'})
        self.r.advance(self.s,240);self.assertFalse(any('city_mobilization' in i for i in self.s['ideas']))

    def test_winner_can_mobilize_without_surrendering_any_city(self):
        self.s['war']=True;self.r.call('hro_city_orderly_mobilization',self.s);before=self.s['manpower']
        self.assertIn('hro_idea_city_mobilization_1',self.s['ideas']);self.assertFalse(any(k.endswith('_lost') for k in self.s['flags']))
        self.r.call('hro_city_orderly_mobilization',self.s);self.assertEqual(self.s['manpower'],before)

    def test_liberation_window_requires_actual_recapture_and_is_finite(self):
        self.s['war']=True;self.r.call('hro_city_start_liberation_offensive',self.s)
        self.assertNotIn('hro_idea_city_liberation_offensive',self.s['ideas'])
        self.lose('minsk');self.regain('minsk');self.r.call('hro_city_start_liberation_offensive',self.s)
        self.assertIn('hro_idea_city_liberation_offensive',self.s['ideas'])
        self.r.advance(self.s,180);self.r.call('hro_city_start_liberation_offensive',self.s)
        self.assertNotIn('hro_idea_city_liberation_offensive',self.s['ideas'])

    def test_capitulated_opponent_cleans_crisis_even_when_faction_war_continues(self):
        self.lose('moscow');self.s['enemy_capitulated']=True;before=self.s['vars']['hro_city_moscow_days'];self.r.advance(self.s,20)
        self.assertEqual(self.s['vars']['hro_city_moscow_days'],before);self.assertFalse(any('city_crisis' in i for i in self.s['ideas']))

    def test_map_validation_rejects_kiev_chernihiv_confusion(self):
        # A deliberately wrong state/province fixture must fail before packaging.
        states=self.output/'history/states';states.mkdir(parents=True)
        (states/'202.txt').write_text('state={id=202 provinces={3568} history={victory_points={3568 3}}}')
        with self.assertRaisesRegex(ValueError,'Missing city state|does not match'):validate_geography(self.output)


if __name__=='__main__':unittest.main()
