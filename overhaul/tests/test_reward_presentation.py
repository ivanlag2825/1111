"""All public focus rewards must preserve higher reforms and hide housekeeping."""
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'overhaul/tools')]
from clausewitz import parse,walk
from validate_overhaul import _run_idea_setter
from generate_war_adaptation import generate as war_generate
from generate_emergency import generate as city_generate
spec=importlib.util.spec_from_file_location('reward_presentation_builder',ROOT/'overhaul/tools/build_overhaul.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)


class RewardPresentationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.output=Path(self.temp.name)
        self.catalogs=builder.read_catalogs(ROOT/'overhaul/data')
        builder.author_country_content(self.output,self.catalogs,{'GER':0,'SOV':0});war_generate(self.output);city_generate(self.output)
        self.effects={n.key:n for p in (self.output/'common/scripted_effects').glob('*.txt') for n in parse(p.read_text())}

    def visible_removals(self,nodes,stack=()):
        found=[]
        for n in nodes:
            if n.key=='hidden_effect':continue
            if n.key=='remove_ideas':found.append((stack,n.value))
            if isinstance(n.value,list):found+=self.visible_removals(n.value,stack)
            elif n.key in self.effects:
                self.assertNotIn(n.key,stack)
                found+=self.visible_removals(self.effects[n.key].value,stack+(n.key,))
        return found

    def test_no_authored_or_appended_focus_reward_exposes_housekeeping_removals(self):
        for c in self.catalogs:
            scripts=[(f['id'],f['reward']) for f in c['focuses']]+[(p['id'],p['extra_reward']) for p in c['native_patches'] if p.get('extra_reward')]
            for identity,script in scripts:
                with self.subTest(focus=identity):self.assertEqual(self.visible_removals(parse(script)),[])

    def test_every_reform_card_is_display_only_and_real_mutation_is_guarded(self):
        for c in self.catalogs:
            for idea in c['ideas']:
                setter=self.effects['hro_set_'+idea['id']]
                self.assertEqual(setter.scalar('show_ideas_tooltip'),idea['id'])
                self.assertEqual({n.key for n in setter.value},{'custom_effect_tooltip','show_ideas_tooltip','hidden_effect'})
                self.assertIsNotNone(setter.one('hidden_effect').one('if').one('limit'))

    def test_every_actual_reform_adds_upgrades_and_preserves_equal_or_higher_tiers(self):
        checks=0
        for c in self.catalogs:
            for idea in c['ideas']:
                setter='hro_set_'+idea['id'];sentinel='unrelated_native_idea'
                self.assertEqual(_run_idea_setter(self.effects[setter].value,{sentinel},self.effects),{sentinel,idea['id']})
                for old in c['ideas']:
                    if old['family']!=idea['family']:continue
                    before={sentinel,old['id']};after=_run_idea_setter(self.effects[setter].value,before,self.effects)
                    self.assertEqual(after,before if old['stage']>=idea['stage'] else {sentinel,idea['id']});checks+=1
        self.assertGreater(checks,300)

    def test_reported_german_focuses_preserve_late_staff_and_field_command(self):
        c=next(c for c in self.catalogs if c['tag']=='GER')
        for focus_id in ['hro_ger_staff_curriculum','hro_ger_replacement_march_battalions']:
            # Resolve the actual focus setter, without assuming a display name or family.
            focus=next(f for f in c['focuses'] if f['id']==focus_id)
            calls=[n.key for n in walk(parse(focus['reward'])) if n.key.startswith('hro_set_')]
            self.assertTrue(calls)
            for setter in calls:
                target=next(i for i in c['ideas'] if 'hro_set_'+i['id']==setter)
                for late in c['ideas']:
                    if late['family']==target['family'] and late['stage']>target['stage']:
                        self.assertEqual(_run_idea_setter(self.effects[setter].value,{late['id']},self.effects),{late['id']})


if __name__=='__main__':unittest.main()
