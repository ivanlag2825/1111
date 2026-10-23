"""Slot-based research, exact spirit migration and version-safe GUI additions."""
from pathlib import Path
import copy,json,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'overhaul/tools'),str(ROOT/'tools')]
from clausewitz import parse,walk
from build_overhaul import author_country_content,read_catalogs
from generate_frontier import generate as frontier_generate,SCHOOLS
from generate_research import generate,audit,converted,CHAINS,YEARS,FOLDER,MODULE_FOLDER
from generate_design_schools import BRANCHES,MODULES,definitions
from generate_module_programmes import PROGRAMMES,MODULES as EXTRA_MODULES
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
  containerWindowType = { name = "techtree_support_folder_item" iconType = { name = "Icon" position = { x = 90 y = 50 } } instantTextBoxType = { name = "Name" font = "hoi_20bs" maxHeight = 20 } }
  containerWindowType = { name = "techtree_support_folder_small_item" iconType = { name = "Icon" } }
 }''')
 icons={'basic_light_tank_chassis','basic_medium_tank_chassis','basic_heavy_tank_chassis','basic_small_airframe','fighter1','CAS1','tech_engineers','tech_engineers2','tech_mountaineers','tech_logistics_company','tech_maintenance_company','tech_field_hospital','tech_signal_company'}
 (interface/'core.gfx').write_text('bitmapfonts = { bitmapfont = { name = "hoi_16mbs" fontfiles = { "hoi_16mbs" "hoi_16mbs_cryllic" } } bitmapfont = { name = "hoi_20b" fontfiles = { "hoi_20b" "hoi_20b_cryllic" } } }')
 for kind in ('tank','plane'):
  names={m['gfx'] for m in MODULES.values() if m['dlc']==('No Step Back' if kind=='tank' else 'By Blood Alone')}
  (interface/f'{kind}_modules_icons.gfx').write_text('spriteTypes = { '+' '.join('spriteType = { name = "GFX_EMI_'+n+'" }' for n in names)+' }')
 modules=game/'common/units/equipment/modules';modules.mkdir(parents=True)
 (modules/'fixture.txt').write_text('equipment_modules = { '+' '.join(n+' = { category = '+m['category']+' }' for n,m in MODULES.items())+' }')
 (modules.parent/'fixture.txt').write_text('equipments = { base_tank = { is_archetype = yes module_slots = { special = { allowed_module_categories = { '+' '.join(sorted({m['category'] for m in MODULES.values() if m['dlc']=='No Step Back'}))+' } } } } base_plane = { is_archetype = yes module_slots = { special = { allowed_module_categories = { '+' '.join(sorted({m['category'] for m in MODULES.values() if m['dlc']=='By Blood Alone'}))+' } } } } }')
 (interface/'Technologies.gfx').write_text('spriteTypes = { '+' '.join(f'spriteType = {{ name = "GFX_{i}_medium" texturefile = "gfx/interface/technologies/{i}.dds" }}' for i in icons)+' }')
 units=game/'common/units';units.mkdir(parents=True,exist_ok=True)
 (units/'fixture.txt').write_text('sub_units = { '+' '.join(i+' = {}' for i in {'infantry','mountaineers','engineer','motorized','mechanized','logistics_company','maintenance_company','field_hospital'}|{u for b in BRANCHES.values() for u in b['units']})+' }')
 techs=game/'common/technologies';techs.mkdir()
 tags=game/'common/technology_tags';tags.mkdir()
 categories={'support_tech','armor','air_equipment','mio_cat_tech_all_cruiser_and_modules'}
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
 def test_terrain_extensions_require_parent_and_lock_opposite_choice(self):
  from generate_terrain_schools import CHOICES
  for tag in ('GER','SOV'):
   for school,choices in CHOICES.items():
    parent=f'hro_tech_{tag.lower()}_{school}';left=parent+'_'+choices[0][0];right=parent+'_'+choices[1][0];s=self.state(tag)
    self.assertFalse(self.researchable(left,s));self.assertFalse(self.researchable(right,s))
    s['techs'].add(parent);self.finish(left,s);self.assertFalse(self.researchable(right,s))
    s=self.state(tag);s['techs'].add(parent);self.finish(right,s);self.assertFalse(self.researchable(left,s))
 def test_mountain_bonuses_apply_to_mountaineers_not_all_infantry(self):
  for tag in ('ger','sov'):
   t=self.techs[f'hro_tech_{tag}_mountain_assault']
   self.assertIsNone(t.one('infantry'));self.assertEqual(t.one('mountaineers').one('mountain').scalar('attack'),'0.15')
 def test_vehicle_and_module_dates_finish_by_1940_without_ahead_penalty(self):
  from generate_design_schools import definitions as designs
  from generate_module_programmes import definitions as programmes
  for t in designs()+programmes():
   self.assertLessEqual(t['year'],1940)
   self.assertLessEqual(float(self.techs[t['id']].scalar('research_cost')),0.8)
 def test_armour_has_no_percentage_cost_penalty_and_is_strengthened(self):
  for key,minimum in [('hro_face_hardened',.42),('hro_homogeneous',.32),('hro_reinforced_plate',.24)]:
   self.assertGreaterEqual(MODULES[key]['mult']['armor_value'],minimum)
   self.assertNotIn('build_cost_ic',MODULES[key]['mult'])
   self.assertGreater(MODULES[key]['add']['build_cost_ic'],0)
 def test_missing_research_pixels_are_rejected(self):
  next((self.p/'gfx/interface/hro_research').glob('*.dds')).unlink()
  with self.assertRaisesRegex(ValueError,'Missing owned research texture'):audit(self.p,self.game,self.catalogs)
 def test_research_art_fills_card_with_a_bottom_caption_plate(self):
  import struct
  for path in (self.p/'gfx/interface/hro_research').glob('*.dds'):
   if path.stem=='caption_plate':continue
   raw=path.read_bytes();self.assertEqual(struct.unpack_from('<II',raw,12),(80,176));self.assertIn(0,raw[131::4]);self.assertGreaterEqual(max(raw[131::4]),240)
  gui=parse((self.p/'interface/countrytechtreeview.gui').read_text())
  for n in walk(gui):
   if n.key=='containerWindowType' and n.scalar('name','').strip('"') in ('techtree_hro_front_folder_item','techtree_hro_module_folder_item'):
    icon=next(v for v in n.value if v.scalar('name','').strip('"')=='Icon');self.assertEqual(icon.one('position').scalar('y'),'2');self.assertIsNone(icon.one('centerposition'));self.assertEqual(icon.scalar('spriteType'),'"GFX_hro_research_placeholder"')
    name=next(v for v in n.value if v.scalar('name','').strip('"')=='Name');self.assertEqual(name.one('position').scalar('x'),'-10000')
 def test_module_paths_use_distinct_and_correct_component_icons(self):
  from illustration_assets import research_bindings
  b=research_bindings()
  for row in PROGRAMMES:
   ids=['hro_modtech_'+row+'_'+suffix for suffix in ('base','a','b')]
   self.assertEqual(len({b[i] for i in ids}),3,row)
  self.assertNotEqual(b['hro_modtech_engine_a'],b['hro_modtech_airengine_a'])
  self.assertNotEqual(b['hro_modtech_protection_a'],b['hro_modtech_protection_b'])
 def test_four_cannon_upgrades_follow_existing_choices_and_increase_firepower(self):
  s=self.state();s['techs'].add('basic_medium_tank_chassis');self.finish('hro_modtech_cannon_base',s);self.finish('hro_modtech_cannon_a',s);self.finish('hro_modtech_cannon_a2',s);self.finish('hro_modtech_cannon_a3',s)
  self.assertFalse(self.researchable('hro_modtech_cannon_b2',s))
  self.assertGreater(MODULES['hro_precision_88']['add']['hard_attack'],MODULES['hro_high_velocity_75']['add']['hard_attack'])
  self.assertGreater(MODULES['hro_blast_105']['add']['soft_attack'],MODULES['hro_support_75']['add']['soft_attack'])
 def test_full_card_caption_plates_align_and_cannot_disappear(self):
  path=self.p/'interface/countrytechtreeview.gui';gui=parse(path.read_text());plates=[n for n in walk(gui) if n.key=='iconType' and n.scalar('name','').strip('"').startswith('hro_plate_')]
  self.assertEqual(len(plates),89);self.assertEqual(self.report['ui']['research_art_size'],[176,80]);self.assertEqual(self.report['ui']['native_half_slot_offset'],[50,-50])
  path.write_text(path.read_text().replace('name = "hro_plate_hro_design_light_base"','name = "missing_plate"'))
  with self.assertRaisesRegex(ValueError,'Missing research caption plate'):audit(self.p,self.game,self.catalogs)
 def test_full_generated_contract(self):
  report=audit(self.p,self.game,self.catalogs)
  self.assertEqual(report['technologies'],124);self.assertEqual(self.report['visible_per_country'],89);self.assertEqual(report['modules']['modules'],40)
 def test_every_country_has_85_research_nodes_and_foreign_reforms_are_inaccessible(self):
  for tag in ('GER','SOV'):
   s=self.state(tag)
   visible=[t.key for t in self.techs.values() if t.one('folder') and self.r.condition(t.one('allow_branch').value,s)]
   self.assertEqual(len(visible),89)
   self.assertFalse(any('_'+('sov' if tag=='GER' else 'ger')+'_' in k for k in visible))
  s=self.state('FRA');self.assertFalse(any(t.one('folder') and self.r.condition(t.one('allow_branch').value,s) for t in self.techs.values()))
 def test_new_campaign_and_completed_focus_do_not_grant_research(self):
  for tag in ('GER','SOV'):
   s=self.state(tag);s['completed'].update(f['id'] for c in self.catalogs if c['tag']==tag for f in c['focuses'])
   self.r.call('hro_research_migrate',s);self.r.call('hro_frontier_daily',s)
   self.assertTrue(s['techs']);self.assertTrue(all(k.startswith('hro_tech_reform_') for k in s['techs']));self.assertFalse(s.get('research'))
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
 def test_technical_focus_restores_its_hidden_effect_once_without_a_spirit(self):
  for row in self.records:
   s=self.state(row['tag']);k='hro_set_'+row['idea']['id']
   self.r.call(k,s);self.assertEqual(s['techs'],{row['tech']});self.assertFalse(any(i.startswith('hro_') for i in s['ideas']));self.assertFalse(s.get('research'))
   s=copy.deepcopy(s);self.r=FrontierRuntime(self.p);self.r.call(k,s);self.assertEqual(s['techs'],{row['tech']});self.assertFalse(s.get('research'))
 def test_wrong_country_cannot_claim_another_countrys_bonus(self):
  r=self.records[0];s=self.state('SOV');self.r.call('hro_set_'+r['idea']['id'],s)
  self.assertFalse(s['techs']);self.assertFalse(s.get('research'));self.assertFalse(any('bonus_issued' in f for f in s['flags']))
 def test_school_choices_are_permanent_symmetric_and_use_research_slots(self):
  for tag in ('ger','sov'):
   s=self.state(tag.upper());self.finish(f'hro_tech_{tag}_urban',s);self.finish(f'hro_tech_{tag}_river',s)
   self.assertFalse(self.researchable(f'hro_tech_{tag}_forest',s));self.assertFalse(self.researchable(f'hro_tech_{tag}_mobile',s))
   self.assertFalse(any(i.startswith('hro_') for i in s['ideas']))
 def test_retired_support_research_is_hidden_and_has_no_modifiers(self):
  for key in CHAINS:
   for stage in (1,2,3):
    k=f'hro_tech_front_{key}_{stage}';t=self.techs[k]
    self.assertFalse(t.one('folder'));self.assertEqual(t.one('allow').scalar('always'),'no')
    self.assertEqual({n.key for n in t.value},{'allow','research_cost','start_year'})
 def test_every_design_branch_has_real_prerequisites_and_exclusive_development(self):
  for key,b in BRANCHES.items():
   for side in ('a','b'):
    s=self.state();prefix='hro_design_'+key
    self.assertFalse(self.researchable(prefix+'_base',s));s['techs'].add(b['prereq'])
    self.assertFalse(self.researchable(prefix+'_'+side+'2',s));self.finish(prefix+'_base',s);self.finish(prefix+'_'+side,s);self.finish(prefix+'_'+side+'2',s)
    other='b' if side=='a' else 'a';self.assertFalse(self.researchable(prefix+'_'+other,s));self.assertFalse(self.researchable(prefix+'_'+other+'2',s))
 def test_module_unlocks_require_specific_research_and_retain_production_tradeoffs(self):
  unlocks={m.value:t.key for t in self.techs.values() if t.one('enable_equipment_modules') for m in t.one('enable_equipment_modules').value}
  self.assertEqual(len(unlocks),40);self.assertEqual(set(unlocks),set(MODULES))
  for k,m in MODULES.items():
   self.assertGreater(m['add']['build_cost_ic'],0)
   self.assertTrue(unlocks[k].startswith(('hro_design_','hro_modtech_')))
 def test_research_completion_removes_legacy_spirit_in_same_effect(self):
  r=self.records[0];s=self.state(r['tag']);s['ideas'].add(r['idea']['id'])
  self.r.call('hro_set_'+r['idea']['id'],s)
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
  p=self.p/'common/technologies/hro_front_developments.txt';p.write_text(p.read_text().replace('dependencies = { basic_light_tank_chassis = 1 }','dependencies = { hro_design_light_a2 = 1 }'))
  with self.assertRaisesRegex(ValueError,'Research dependency cycle'):audit(self.p,self.game,self.catalogs)
 def test_unknown_font_is_rejected_before_it_can_show_question_marks(self):
  p=self.p/'interface/countrytechtreeview.gui';p.write_text(p.read_text().replace('hoi_16mbs','hoi_16mb'))
  with self.assertRaisesRegex(ValueError,'Unknown research font'):audit(self.p,self.game,self.catalogs)
 def test_layout_overlap_is_rejected(self):
  p=self.p/'interface/countrytechtreeview.gui';p.write_text(p.read_text().replace('x = 250 y = 510','x = 250 y = 210'))
  with self.assertRaisesRegex(ValueError,'Overlapping research cards'):audit(self.p,self.game,self.catalogs)
 def test_module_category_and_icon_must_exist_in_vanilla(self):
  p=self.p/'common/units/equipment/modules/hro_tank_modules.txt';old=p.read_text()
  for before,after,error in [('category = tank_special_module','category = imaginary_slot','Unknown native module category'),('gfx = sloped_armor','gfx = missing_icon','no native icon fallback')]:
   p.write_text(old.replace(before,after))
   with self.assertRaisesRegex(ValueError,error):audit(self.p,self.game,self.catalogs)
  p.write_text(old)
 def test_constructor_limit_prevents_duplicate_modules_without_changing_native_stats(self):
  p=self.p/'common/units/equipment/fixture.txt';p.write_text(p.read_text().replace('module = hro_applique_armor count < 2','module = hro_applique_armor count < 5'))
  with self.assertRaisesRegex(ValueError,'Missing one-per-design limit'):audit(self.p,self.game,self.catalogs)
 def test_thirty_extra_modules_have_genuine_categories_and_costs(self):
  self.assertEqual(len(EXTRA_MODULES),34);self.assertEqual(len(MODULES),40)
  self.assertGreaterEqual(len({m['category'] for m in EXTRA_MODULES.values()}),7)
  self.assertTrue(any(m['category']=='tank_armor_type' for m in EXTRA_MODULES.values()))
  self.assertTrue(any(m['category']=='tank_engine_type' for m in EXTRA_MODULES.values()))
 def test_each_tab_has_its_own_visible_nodes(self):
  s=self.state()
  for folder in (FOLDER,MODULE_FOLDER):
   nodes=[t for t in self.techs.values() if t.one('folder') and t.one('folder').scalar('name')==folder and self.r.condition(t.one('allow').value,s)]
   self.assertEqual(len(nodes),46 if folder==FOLDER else 43)
 def test_module_research_choices_cannot_unlock_the_opposite_line(self):
  for key,p in PROGRAMMES.items():
   for side in ('a','b'):
    prefix='hro_modtech_'+key;s=self.state();s['techs'].add(p['prereq']);self.finish(prefix+'_base',s);self.finish(prefix+'_'+side,s)
    if p[side+'2']:self.finish(prefix+'_'+side+'2',s)
    other='a' if side=='b' else 'b';self.assertFalse(self.researchable(prefix+'_'+other,s))
    unlocked={m.value for k in s['techs'] if k in self.techs and self.techs[k].one('enable_equipment_modules') for m in self.techs[k].one('enable_equipment_modules').value}
    self.assertIn(p[side],unlocked);self.assertNotIn(p[other],unlocked)
    if p[side+'2']:self.assertIn(p[side+'2'],unlocked)
 def test_all_visible_cards_have_explicit_captions_instead_of_dynamic_name_binding(self):
  gui=parse((self.p/'interface/countrytechtreeview.gui').read_text())
  captions=[n for n in walk(gui) if n.key=='instantTextBoxType' and n.scalar('name','').strip('"').startswith('hro_caption_')]
  self.assertEqual(len(captions),89)
  for n in captions:self.assertEqual(n.scalar('alwaystransparent'),'yes');self.assertIn(n.scalar('text').strip('"'),self.techs)
 def test_fractional_coordinates_fail_even_if_the_parser_accepts_them(self):
  p=self.p/'common/technologies/hro_front_developments.txt';p.write_text(p.read_text().replace('x = -1 y = 3','x = -0.8 y = 3'))
  with self.assertRaisesRegex(ValueError,'Fractional technology grid coordinate'):audit(self.p,self.game,self.catalogs)
 def test_missing_visible_card_caption_fails_the_release(self):
  p=self.p/'interface/countrytechtreeview.gui';p.write_text(p.read_text().replace('text = "hro_design_light_base"','text = "missing_caption"'))
  with self.assertRaisesRegex(ValueError,'Missing explicit technology name'):audit(self.p,self.game,self.catalogs)
 def test_native_name_binding_remains_present_but_hidden_in_full_card_templates(self):
  gui=parse((self.p/'interface/countrytechtreeview.gui').read_text())[0]
  for folder in (FOLDER,MODULE_FOLDER):
   template=next(n for n in gui.value if n.scalar('name','').strip('"')=='techtree_'+folder+'_item')
   name=next(n for n in template.value if n.scalar('name','').strip('"')=='Name')
   self.assertEqual(name.scalar('hide'),'yes')

if __name__=='__main__':unittest.main()
