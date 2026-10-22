"""Chapter headings, useful rewards and the army culmination are content contracts."""
from pathlib import Path
import json,sys,tempfile,unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'overhaul/tools')]
from clausewitz import parse,walk
from generate_groups import generate
from preview_trees import draw_country,resolve_positions


class FocusGroupTests(unittest.TestCase):
    def setUp(self):
        self.catalogs=[json.loads((ROOT/'overhaul/data'/f'{tag}.json').read_text()) for tag in ('ger','sov')]

    def test_every_group_links_a_real_gui_container_and_localised_title(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);groups=generate(root,self.catalogs)
            definitions={n.key:n for n in parse((root/'common/focus_inlay_windows/hro_group_headers.txt').read_text())}
            windows={n.scalar('name').strip('"') for n in parse((root/'interface/hro_focus_groups.gui').read_text())[0].all('containerWindowType')}
            for catalog in self.catalogs:
                self.assertTrue(groups[catalog['tag']])
                for group in catalog['groups']:
                    self.assertIn(definitions[group['id']].scalar('window_name').strip('"'),windows)
                    self.assertGreaterEqual(group['width'],6)
                    self.assertEqual(group['y'],0)
                    for lang in ('russian','english'):
                        loc=root/f'localisation/{lang}/hro_groups_l_{lang}.yml'
                        self.assertTrue(loc.read_bytes().startswith(b'\xef\xbb\xbf'))
                        self.assertIn(group['id']+':0',loc.read_text(encoding='utf-8-sig'))

    def test_preview_includes_headers_above_first_focus_row(self):
        nodes={n.scalar('id'):n for n in parse('focus={id=A x=4 y=2 cost=5}')}
        groups=[{'id':'hro_group_test','x':0,'y':0,'width':8,'name_ru':'Красная армия'}]
        svg,_=draw_country('SOV',nodes,resolve_positions(nodes),set(),{},None,groups)
        self.assertIn('chapter-hro_group_test',svg)
        self.assertIn('Красная армия',svg)
        self.assertNotIn('y="-128',svg)

    def test_no_authored_focus_relies_only_on_political_power_or_small_experience(self):
        for catalog in self.catalogs:
            for focus in catalog['focuses']:
                keys={n.key for n in walk(parse(focus['reward']))}
                useful={'add_tech_bonus','add_research_slot','add_building_construction','add_timed_idea'}
                spirits={('hro_set_'+i['id']):i for i in catalog['ideas']}
                reforms=[spirits[k] for k in keys if k in spirits]
                real_reform=any(i.get('modifiers') or i.get('equipment_bonus') for i in reforms)
                self.assertTrue(keys & useful or real_reform or any(k and k.startswith(('hro_war_','hro_city_')) for k in keys),focus['id'])

    def test_glory_of_red_army_grants_a_major_permanent_combat_reform(self):
        sov=next(c for c in self.catalogs if c['tag']=='SOV')
        ideas={i['id']:i for i in sov['ideas']}
        patches={p['id']:p for p in sov['native_patches']}
        for identity in ('SOV_the_glory_of_the_red_army','SOV_the_glory_of_the_red_army_alt'):
            setters=[n.key[8:] for n in walk(parse(patches[identity]['extra_reward'])) if n.key and n.key.startswith('hro_set_')]
            combat=[ideas[k] for k in setters if ideas[k]['modifiers'].get('army_attack_factor',0)>=.25]
            self.assertTrue(combat,identity)
            self.assertGreaterEqual(combat[0]['modifiers'].get('army_defence_factor',0),.20)
            self.assertEqual(combat[0]['stage'],3)


if __name__=='__main__':unittest.main()
