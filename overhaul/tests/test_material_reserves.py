"""Execute one-shot coal additions and German recruitment without duplicate rewards."""
from pathlib import Path
import sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'overhaul/tools')]
from clausewitz import parse
from generate_reserves import generate,COAL,MANPOWER,IDEA,validate_geography


class MaterialReserveTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.output=Path(self.temp.name)
        generate(self.output)
        self.effects={n.key:n for n in parse((self.output/'common/scripted_effects/hro_reserves_effects.txt').read_text())}
    def state(self,tag):
        return dict(tag=tag,flags=set(),ideas=set(),manpower=0,coal={},owned=set(COAL.get(tag,{})),controlled=set(COAL.get(tag,{})))
    def condition(self,nodes,s,region=None):
        def one(n):
            if n.key=='NOT':return not self.condition(n.value,s,region)
            if n.key=='original_tag':return n.value==s['tag']
            if n.key=='has_country_flag':return n.value in s['flags']
            if n.key=='has_idea':return n.value in s['ideas']
            if n.key=='is_owned_by':return region in s['owned']
            if n.key=='is_fully_controlled_by':return region in s['controlled']
            if n.key.isdigit():return self.condition(n.value,s,int(n.key))
            raise AssertionError(n.key)
        return all(one(n) for n in nodes)
    def execute(self,nodes,s,region=None):
        for n in nodes:
            if n.key=='if':
                if self.condition(n.one('limit').value,s,region):self.execute([c for c in n.value if c.key!='limit'],s,region)
            elif n.key=='set_country_flag':s['flags'].add(n.value)
            elif n.key=='add_manpower':s['manpower']+=int(n.value)
            elif n.key=='add_ideas':s['ideas'].add(n.value)
            elif n.key=='add_resource':
                self.assertEqual(n.scalar('type'),'coal');s['coal'][region]=s['coal'].get(region,0)+int(n.scalar('amount'))
            elif n.key.isdigit():self.execute(n.value,s,int(n.key))
            else:raise AssertionError(n.key)
    def apply(self,s,tag=None):self.execute(self.effects['hro_reserves_'+(tag or s['tag']).lower()+'_apply'].value,s)
    def test_germany_gets_600_coal_one_million_once_and_two_recruitment_points(self):
        s=self.state('GER');self.apply(s);self.apply(s)
        self.assertEqual(sum(s['coal'].values()),600);self.assertEqual(s['manpower'],MANPOWER);self.assertIn(IDEA,s['ideas'])
        idea=parse((self.output/'common/ideas/hro_reserves_ideas.txt').read_text())[0].one('country').one(IDEA)
        self.assertEqual(float(idea.one('modifier').scalar('conscription')),.02)
    def test_ussr_gets_800_coal_without_german_manpower_or_idea(self):
        s=self.state('SOV');self.apply(s);self.apply(s)
        self.assertEqual(sum(s['coal'].values()),800);self.assertEqual(s['manpower'],0);self.assertNotIn(IDEA,s['ideas'])
    def test_lost_or_foreign_region_defers_its_coal_without_replaying_other_regions(self):
        s=self.state('GER');s['controlled'].remove(51);s['owned'].remove(67);self.apply(s)
        self.assertEqual(sum(s['coal'].values()),200);self.assertNotIn(51,s['coal']);self.assertNotIn(67,s['coal'])
        s['controlled'].add(51);s['owned'].add(67);self.apply(s)
        self.assertEqual(sum(s['coal'].values()),600);self.assertEqual(s['manpower'],MANPOWER)
    def test_missing_recruitment_spirit_restores_without_second_manpower_grant(self):
        s=self.state('GER');self.apply(s);s['ideas'].discard(IDEA);self.apply(s)
        self.assertIn(IDEA,s['ideas']);self.assertEqual(s['manpower'],MANPOWER)
    def test_foreign_countries_cannot_receive_country_rewards(self):
        s=self.state('USA');self.apply(s,'GER');self.apply(s,'SOV')
        self.assertEqual(s,self.state('USA'))
    def test_absent_coal_geography_fails_build_validation(self):
        with self.assertRaisesRegex(ValueError,'Coal expansion does not match'):
            validate_geography(self.output)


if __name__=='__main__':unittest.main()
