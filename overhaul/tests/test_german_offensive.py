"""Execute the emitted first-offensive and one-shot city conquest lifecycle."""
import copy,importlib.util,tempfile,unittest
from pathlib import Path
from test_war_adaptation import EmittedLifecycle,day,generator as war_generator
from test_city_emergency import Runtime as SovietCityLifecycle
from generate_emergency import generate as city_generate
from clausewitz import parse

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('hro_offensive_tests',ROOT/'overhaul/tools/generate_offensive.py')
offensive=importlib.util.module_from_spec(spec);spec.loader.exec_module(offensive)


class OffensiveLifecycle(EmittedLifecycle):
    def __init__(self,output):
        super().__init__(output)
        self.effects.update({n.key:n for n in parse((output/'common/scripted_effects/hro_offensive_effects.txt').read_text())})
        self.off_daily=parse((output/'common/on_actions/hro_offensive_on_actions.txt').read_text())[0].one('on_daily').one('effect').value
    def tick(self,state,when=None):
        super().tick(state,when)
        self.execute(self.off_daily,state)


class GermanOffensiveTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        output=Path(self.temp.name);war_generator.generate(output);offensive.generate(output)
        self.r=OffensiveLifecycle(output)
        self.s=dict(tag='GER',date=day('1941.6.22'),war=True,aggressor='GER',capitulated=False,enemy_capitulated=False,
                    flags={},variables={},ideas={'native_sentinel'},events=[],controlled=set(),enemy_flags=set(),research=[])
        self.r.tick(self.s)
    def capture(self,key):
        c=next(c for c in offensive.records() if c['key']==key)
        self.s['controlled'].add(c['province']);self.s['enemy_flags'].add('hro_city_'+key+'_lost')
        self.r.tick(self.s)
    def temporary(self):return set(offensive.LAUNCH_IDEAS+offensive.CITY_IDEAS)&self.s['ideas']

    def test_launch_changes_at_60_and_expires_exactly_at_120_actual_war_days(self):
        self.assertIn(offensive.LAUNCH_IDEAS[0],self.s['ideas'])
        self.r.advance(self.s,'1941.8.20');self.assertIn(offensive.LAUNCH_IDEAS[0],self.s['ideas'])
        self.r.advance(self.s,'1941.8.21');self.assertEqual(self.temporary(),{offensive.LAUNCH_IDEAS[1]})
        self.r.advance(self.s,'1941.10.19');self.assertIn(offensive.LAUNCH_IDEAS[1],self.s['ideas'])
        self.r.advance(self.s,'1941.10.20');self.assertFalse(self.temporary())
        self.assertEqual(self.s['events'].count('hro.601'),1)

    def test_soviet_first_attack_does_not_grant_german_launch_even_after_rewar(self):
        s=copy.deepcopy(self.s);s.update(aggressor='SOV',flags={},variables={},ideas={'native_sentinel'},events=[])
        self.r.tick(s);self.assertFalse(set(offensive.LAUNCH_IDEAS)&s['ideas'])
        s['war']=False;self.r.tick(s);s.update(war=True,aggressor='GER');self.r.tick(s)
        self.assertFalse(set(offensive.LAUNCH_IDEAS)&s['ideas']);self.assertNotIn('hro.601',s['events'])

    def test_peace_pauses_campaign_clock_without_reset_or_second_launch_event(self):
        self.r.advance(self.s,'1941.7.2');self.assertEqual(self.s['variables']['hro_off_ger_campaign_days'],10)
        self.s['war']=False;self.r.advance(self.s,'1941.8.2');self.assertFalse(self.temporary())
        self.assertEqual(self.s['variables']['hro_off_ger_campaign_days'],10)
        self.s['war']=True;self.r.advance(self.s,'1941.8.12')
        self.assertEqual(self.s['variables']['hro_off_ger_campaign_days'],20)
        self.assertEqual(self.s['events'].count('hro.601'),1)

    def test_winter_suppresses_launch_while_its_war_clock_keeps_running(self):
        s=copy.deepcopy(self.s);s.update(date=day('1941.11.1'),flags={},variables={},ideas={'native_sentinel'},events=[])
        self.r.tick(s);self.assertFalse(set(offensive.LAUNCH_IDEAS)&s['ideas'])
        self.r.advance(s,'1942.4.1');self.assertEqual(s['variables']['hro_off_ger_campaign_days'],120)
        self.assertFalse(set(offensive.LAUNCH_IDEAS)&s['ideas'])









    def test_peace_both_capitulations_and_1947_clear_temporary_advantages(self):
        self.capture('minsk')
        for key,value in [('war',False),('capitulated',True),('enemy_capitulated',True),('date',day('1947.1.1'))]:
            with self.subTest(cause=key):
                s=copy.deepcopy(self.s);s[key]=value;self.r.tick(s)
                self.assertFalse(set(offensive.LAUNCH_IDEAS+offensive.CITY_IDEAS)&s['ideas'])
                self.assertIn('native_sentinel',s['ideas'])


    def test_daily_offensive_dispatch_does_not_touch_foreign_countries(self):
        for tag in ['SOV','USA']:
            s=copy.deepcopy(self.s);s['tag']=tag;before=copy.deepcopy(s)
            self.r.execute(self.r.off_daily,s);self.assertEqual(s,before)

    def test_city_captures_grant_no_automatic_rewards_or_notifications(self):
        before=(self.s.get('add_political_power',0),self.s.get('army_experience',0),list(self.s['research']))
        for city in offensive.records():self.capture(city['key'])
        self.assertEqual(before,(self.s.get('add_political_power',0),self.s.get('army_experience',0),self.s['research']))
        self.assertFalse(set(offensive.CITY_IDEAS)&self.s['ideas'])
        self.assertEqual(self.s['events'],['hro.601'])

    def test_old_save_city_spirits_and_window_are_removed_without_repaying_rewards(self):
        self.s['ideas'].update(offensive.CITY_IDEAS);self.s['flags']['hro_off_ger_city_window']=None
        self.s['flags']['hro_off_ger_minsk_awarded']=None
        self.r.call('hro_off_ger_sync',self.s)
        self.assertFalse(set(offensive.CITY_IDEAS)&self.s['ideas'])
        self.assertNotIn('hro_off_ger_city_window',self.s['flags'])
        self.assertNotIn('add_political_power',self.s)

    def test_real_soviet_city_loss_hurts_soviets_without_paying_germany(self):
        output=Path(self.temp.name);city_generate(output);runtime=SovietCityLifecycle(output)
        sov=dict(tag='SOV',date=day('1941.6.22'),war=True,capitulated=False,enemy_capitulated=False,
                 controlled={c['province'] for c in offensive.records()},enemy=set(),flags={},vars={},ideas=set(),
                 expiry={},manpower=0,research=[],factories=[],slots=0,events=[],capacity_owned=True,capacity_free=True)
        runtime.tick(sov);sov['controlled'].discard(11370);sov['enemy'].add(11370);runtime.tick(sov)
        self.assertIn('hro_idea_city_crisis_1',sov['ideas']);self.assertIn('hro.501',sov['events'])
        self.s['enemy_flags']=set(sov['flags']);self.capture('minsk')
        self.assertNotIn('add_political_power',self.s);self.assertFalse(set(offensive.CITY_IDEAS)&self.s['ideas'])


if __name__=='__main__':unittest.main()
