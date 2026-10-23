"""Slot-based research, exact spirit migration and version-safe GUI additions."""
from pathlib import Path
import copy,json,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'overhaul/tools'),str(ROOT/'tools')]
from clausewitz import parse,walk
from build_overhaul import author_country_content,read_catalogs
from generate_frontier import generate as frontier_generate,SCHOOLS
from generate_research import generate,audit,converted,CHAINS,YEARS,FOLDER
from test_frontier import FrontierRuntime
import test_frontier
from generate_war_adaptation import generate as war_generate


def fixture_game(game):
 # Minimal original interface for structural tests; actual release checks run
 # against the user's 1.19.3 files, never this synthetic fixture.
 interface=game/'interface';interface.mkdir(parents=True)
 (interface/'countrytechtreeview.gui').write_text('''guiTypes = {
  containerWindowType = { name = "countrytechtreeview"
   containerWindowType = { name = "folder_tabs" buttonType = { name = "infantry_folder_tab" position = { x = 22 y = 0 } } }
   containerWindowType = { name = "support_folder" size = { width = 100%% height = 100%% } }
  }
  containerWindowType = { name = "techtree_support_folder_item" iconType = { name = "Icon" } }
  containerWindowType = { name = "techtree_support_folder_small_item" iconType = { name = "Icon" } }
 }''')
 icons={'tech_engineers','tech_engineers2','tech_mountaineers','tech_logistics_company','tech_maintenance_company','tech_field_hospital','tech_signal_company'}
 (interface/'Technologies.gfx').write_text('spriteTypes = { '+' '.join(f'spriteType = {{ name = "GFX_{i}_medium" texturefile = "gfx/interface/technologies/{i}.dds" }}' for i in icons)+' }')
 units=game/'common/units';units.mkdir(parents=True)
 (units/'fixture.txt').write_text('sub_units = { '+' '.join(i+' = {}' for i in ('infantry','engineer','motorized','mechanized','logistics_company','maintenance_company','field_hospital'))+' }')
 techs=game/'common/technologies';techs.mkdir()
 tags=game/'common/technology_tags';tags.mkdir()
 categories={'support_tech','mio_cat_tech_all_cruiser_and_modules'}
 for tag in ('ger','sov'):
  catalog=json.loads((ROOT/'overhaul/data'/f'{tag}.json').read_text())
  for f in catalog['focuses']:
   for n in walk(parse(f['reward'])):
    if n.key=='category' and isinstance(n.value,str):categories.add(n.value)
 (tags/'fixture.txt').write_text('technology_categories = { '+' '.join(sorted(categories))+' }')
 (techs/'fixture.txt').write_text('technologies = { '+' '.join(i+' = {}' for i in icons)+' }')


class ResearchTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.p=Path(self.temp.name)/'mod';self.game=Path(self.temp.name)/'game';fixture_game(self.game)
  self.catalogs=read_catalogs(ROOT/'overhaul/data')
  war_generate(self.p)
  author_country_content(self.p,self.catalogs,{'GER':0,'SOV':0});frontier_generate(self.p)
  self.report=generate(self.p,self.game,self.catalogs)
  self.techs={n.key:n for p in (self.p/'common/technologies').glob('hro*.txt') for root in parse(p.read_text()) for n in root.value}
  self.r=FrontierRuntime(self.p);self.records=converted(self.catalogs)
 def state(self,tag='GER'):return test_frontier.FrontierTests().state(tag)
 def researchable(self,k,s):
  t=self.techs[k]
  if k in s['techs'] or not self.r.condition(t.one('allow').value,s):return False
  if t.one('dependencies') and any(n.key not in s['techs'] for n in t.one('dependencies').value):return False
  if t.one('xor') and any(n.value in s['techs'] for n in t.one('xor').value):return False
  return True
 def finish(self,k,s):
  self.assertTrue(self.researchable(k,s));s['techs'].add(k)
  if effect:=self.techs[k].one('on_research_complete'):self.r.execute(effect.value,s)
 def test_full_generated_contract(self):
  report=audit(self.p,self.game,self.catalogs)
  self.assertEqual(report['technologies'],32);self.assertEqual(self.report['visible_per_country'],22)
 def test_every_country_has_22_research_nodes_and_foreign_reforms_are_inaccessible(self):
  for tag in ('GER','SOV'):
   s=self.state(tag)
   visible=[t.key for t in self.techs.values() if self.r.condition(t.one('allow_branch').value,s)]
   self.assertEqual(len(visible),22)
   self.assertFalse(any('_'+('sov' if tag=='GER' else 'ger')+'_' in k for k in visible))
  s=self.state('FRA');self.assertFalse(any(self.r.condition(t.one('allow_branch').value,s) for t in self.techs.values()))
 def test_new_campaign_and_completed_focus_do_not_grant_research(self):
  for tag in ('GER','SOV'):
   s=self.state(tag);s['completed'].update(f['id'] for c in self.catalogs if c['tag']==tag for f in c['focuses'])
   self.r.call('hro_research_migrate',s);self.r.call('hro_frontier_daily',s)
   self.assertFalse(s['techs']);self.assertFalse(s.get('research'))
 def test_all_12_old_spirits_migrate_once_and_preserve_unrelated_spirits(self):
  for tag in ('GER','SOV'):
   s=self.state(tag);rows=[r for r in self.records if r['tag']==tag];old={r['idea']['id'] for r in rows}
   s['ideas']=old|{'external_sentinel','hro_idea_war_sov_surprise'}
   self.r.call('hro_research_migrate',s)
   self.assertEqual(s['techs'],{r['tech'] for r in rows});self.assertEqual(s['ideas'],{'external_sentinel','hro_idea_war_sov_surprise'})
   before=copy.deepcopy(s);self.r=FrontierRuntime(self.p);self.r.call('hro_research_migrate',s);self.assertEqual(s,before)
 def test_existing_tech_and_old_spirit_clean_up_without_replaying_research_reward(self):
  r=self.records[0];s=self.state(r['tag']);s['techs'].add(r['tech']);s['ideas'].add(r['idea']['id'])
  self.r.call('hro_research_migrate',s);self.r.call('hro_set_'+r['idea']['id'],s)
  self.assertEqual(s['techs'],{r['tech']});self.assertNotIn(r['idea']['id'],s['ideas']);self.assertFalse(s.get('research'))
 def test_replacement_focus_only_grants_one_targeted_bonus_even_on_reload(self):
  for row in self.records:
   s=self.state(row['tag']);k='hro_set_'+row['idea']['id']
   self.r.call(k,s);self.assertFalse(s['techs']);self.assertFalse(any(i.startswith('hro_') for i in s['ideas']));self.assertEqual(len(s['research']),1)
   bonus=next(n for n in walk(self.r.effects[k].value) if n.key=='add_tech_bonus')
   self.assertEqual(bonus.scalar('technology'),row['tech']);self.assertEqual(bonus.scalar('bonus'),'1')
   s=copy.deepcopy(s);self.r=FrontierRuntime(self.p);self.r.call(k,s);self.assertEqual(len(s['research']),1)
 def test_wrong_country_cannot_claim_another_countrys_bonus(self):
  r=self.records[0];s=self.state('SOV');self.r.call('hro_set_'+r['idea']['id'],s)
  self.assertFalse(s['techs']);self.assertFalse(s.get('research'));self.assertFalse(any('bonus_issued' in f for f in s['flags']))
 def test_school_choices_are_permanent_symmetric_and_use_research_slots(self):
  for tag in ('ger','sov'):
   s=self.state(tag.upper());self.finish(f'hro_tech_{tag}_urban',s);self.finish(f'hro_tech_{tag}_river',s)
   self.assertFalse(self.researchable(f'hro_tech_{tag}_forest',s));self.assertFalse(self.researchable(f'hro_tech_{tag}_mobile',s))
   self.assertFalse(any(i.startswith('hro_') for i in s['ideas']))
 def test_support_chains_require_previous_stage_and_company_research(self):
  for key,(_,_,units,mods,icon) in CHAINS.items():
   s=self.state()
   first=f'hro_tech_front_{key}_1'
   if key!='winter':self.assertFalse(self.researchable(first,s));s['techs'].add(icon)
   self.assertFalse(self.researchable(f'hro_tech_front_{key}_3',s))
   for tier,year in enumerate(YEARS,1):
    k=f'hro_tech_front_{key}_{tier}';self.assertEqual(int(self.techs[k].scalar('start_year')),year);self.finish(k,s)
   for stat,v in mods.items():self.assertAlmostEqual(sum(float(self.techs[f'hro_tech_front_{key}_{t}'].scalar(stat)) for t in (1,2,3)),v*3)
 def test_research_completion_removes_legacy_spirit_in_same_effect(self):
  r=self.records[0];s=self.state(r['tag']);s['ideas'].add(r['idea']['id']);self.finish(r['tech'],s)
  self.assertNotIn(r['idea']['id'],s['ideas']);self.assertIn(r['tech'],s['techs'])
 def test_no_more_than_original_bonus_is_carried_across_migration(self):
  for row in self.records:
   for stat,value in row['idea']['modifiers'].items():self.assertEqual(float(self.techs[row['tech']].scalar(stat)),value)
 def test_generated_gui_is_utf8_without_bom_and_keeps_the_expected_root_token(self):
  p=self.p/'interface/countrytechtreeview.gui';data=p.read_bytes()
  self.assertFalse(data.startswith(b'\xef\xbb\xbf'))
  self.assertEqual(data.lstrip().split(None,1)[0],b'guiTypes')
 def test_audit_rejects_bom_even_though_the_python_parser_accepts_it(self):
  p=self.p/'interface/countrytechtreeview.gui';p.write_bytes(b'\xef\xbb\xbf'+p.read_bytes())
  with self.assertRaisesRegex(ValueError,'unsupported BOM'):audit(self.p,self.game,self.catalogs)
 def test_audit_rejects_unregistered_research_bonus_category(self):
  p=self.p/'common/scripted_effects/hro_bad_category.txt'
  p.write_text('bad = { add_tech_bonus = { name = test bonus = 0.5 uses = 1 category = cl_tech } }')
  with self.assertRaisesRegex(ValueError,'Unknown research category: cl_tech'):audit(self.p,self.game,self.catalogs)
 def test_audit_rejects_a_missing_grid_sprite_and_legacy_modifier_change(self):
  gui=self.p/'interface/countrytechtreeview.gui';original=gui.read_text(encoding='utf-8-sig')
  gui.write_text(original.replace('hro_tech_ger_urban_tree','missing_grid'))
  with self.assertRaisesRegex(ValueError,'Missing root grid'):audit(self.p,self.game,self.catalogs)
  gui.write_text(original)
  gfx=self.p/'interface/hro_research_icons.gfx';old=gfx.read_text();gfx.write_text(old.replace('GFX_hro_tech_ger_urban_medium','GFX_missing'))
  with self.assertRaisesRegex(ValueError,'Missing research sprite'):audit(self.p,self.game,self.catalogs)
  gfx.write_text(old)
  p=self.p/'common/technologies/hro_front_developments.txt';p.write_text(p.read_text().replace('planning_speed = 0.3','planning_speed = 0.99'))
  with self.assertRaisesRegex(ValueError,'Transferred modifiers differ'):audit(self.p,self.game,self.catalogs)
 def test_audit_rejects_native_ui_modification(self):
  p=self.p/'interface/countrytechtreeview.gui';p.write_text(p.read_text().replace('x = 22','x = 23'))
  with self.assertRaisesRegex(ValueError,'Vanilla research GUI changed'):audit(self.p,self.game,self.catalogs)
 def test_audit_rejects_prerequisite_cycle(self):
  p=self.p/'common/technologies/hro_front_developments.txt';p.write_text(p.read_text().replace('dependencies = { tech_maintenance_company = 1 }','dependencies = { hro_tech_front_maintenance_3 = 1 }'))
  with self.assertRaisesRegex(ValueError,'Research dependency cycle'):audit(self.p,self.game,self.catalogs)

if __name__=='__main__':unittest.main()
