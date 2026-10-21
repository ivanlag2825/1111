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

    def test_city_requires_actual_german_vp_control_and_recorded_soviet_loss(self):
        self.s['controlled'].add(193);self.s['enemy_flags'].add('hro_city_kiev_lost');self.r.tick(self.s)
        self.assertNotIn('hro_off_ger_kiev_awarded',self.s['flags'])
        self.s['controlled'].add(525);self.s['enemy_flags'].clear();self.r.tick(self.s)
        self.assertNotIn('hro_off_ger_kiev_awarded',self.s['flags'])
        self.capture('kiev');self.assertIn('hro_off_ger_kiev_awarded',self.s['flags'])

    def test_repeat_capture_cannot_farm_city_rewards_or_notifications(self):
        self.capture('minsk');before=(self.s['add_political_power'],self.s['army_experience'],len(self.s['research']))
        for _ in range(3):
            self.s['controlled'].discard(11370);self.r.tick(self.s);self.capture('minsk')
        self.assertEqual(before,(self.s['add_political_power'],self.s['army_experience'],len(self.s['research'])))
        self.assertEqual(self.s['events'].count('hro.611'),1)
        self.assertEqual(self.s['variables']['hro_off_ger_cities'],1)

    def test_actual_soviet_city_loss_script_unlocks_the_german_capture_reward(self):
        output=Path(self.temp.name);city_generate(output);sov_runtime=SovietCityLifecycle(output)
        sov=dict(tag='SOV',date=day('1941.6.22'),war=True,capitulated=False,enemy_capitulated=False,
                 controlled={c['province'] for c in offensive.records()},enemy=set(),flags={},vars={},ideas=set(),
                 expiry={},manpower=0,research=[],factories=[],slots=0,events=[],capacity_owned=True,capacity_free=True)
        sov_runtime.tick(sov)
        sov['controlled'].discard(11370);sov['enemy'].add(11370);sov_runtime.tick(sov)
        self.s['enemy_flags']=sov['flags'];self.s['controlled'].add(11370);self.r.tick(self.s)
        self.assertIn('hro_off_ger_minsk_awarded',self.s['flags'])
        self.assertEqual(self.s['add_political_power'],60)
        self.assertEqual(self.s['army_experience'],40)

    def test_city_tiers_never_stack_or_refresh_the_existing_120_day_window(self):
        self.capture('minsk');expiry=self.s['flags']['hro_off_ger_city_window']
        self.r.advance(self.s,'1941.7.22');self.capture('kiev');self.capture('kharkov')
        self.assertEqual(self.s['flags']['hro_off_ger_city_window'],expiry)
        self.assertEqual(set(offensive.CITY_IDEAS)&self.s['ideas'],{offensive.CITY_IDEAS[2]})
        self.r.advance(self.s,'1941.10.20');self.assertFalse(set(offensive.CITY_IDEAS)&self.s['ideas'])
        self.capture('moscow');self.assertIn(offensive.CITY_IDEAS[2],self.s['ideas'])
        self.assertGreater(self.s['flags']['hro_off_ger_city_window'],expiry)

    def test_peace_both_capitulations_and_1947_clear_temporary_advantages(self):
        self.capture('minsk')
        for key,value in [('war',False),('capitulated',True),('enemy_capitulated',True),('date',day('1947.1.1'))]:
            with self.subTest(cause=key):
                s=copy.deepcopy(self.s);s[key]=value;self.r.tick(s)
                self.assertFalse(set(offensive.LAUNCH_IDEAS+offensive.CITY_IDEAS)&s['ideas'])
                self.assertIn('native_sentinel',s['ideas'])

    def test_public_capture_effect_has_country_war_and_capitulation_guards(self):
        self.s['controlled'].add(6380);self.s['enemy_flags'].add('hro_city_moscow_lost')
        for key,value in [('tag','SOV'),('war',False),('capitulated',True),('enemy_capitulated',True)]:
            with self.subTest(cause=key):
                s=copy.deepcopy(self.s);s[key]=value;self.r.call('hro_off_ger_moscow_capture',s)
                self.assertNotIn('hro_off_ger_moscow_awarded',s['flags'])
                self.assertNotIn('add_political_power',s)

    def test_daily_offensive_dispatch_does_not_touch_foreign_countries(self):
        for tag in ['SOV','USA']:
            s=copy.deepcopy(self.s);s['tag']=tag;before=copy.deepcopy(s)
            self.r.execute(self.r.off_daily,s);self.assertEqual(s,before)


if __name__=='__main__':unittest.main()
