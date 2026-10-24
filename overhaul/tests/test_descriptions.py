"""Narrative must cover UI entities while preserving mechanical text and scripts."""
from pathlib import Path
import json,sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'overhaul/tools')]
import generate_descriptions as g

class DescriptionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.mod=self.root/'mod';(self.root/'data').mkdir();(self.root/'data/narrative_native.json').write_text('{}');self.catalogs=[{'focuses':[{'id':'hro_test_staff'}],'native_patches':[]}]
  self.put('common/ideas/test.txt','ideas = { country = { hro_test_repair = { modifier = { army_org_regain = 0.15 } } } }')
  self.put('common/technologies/test.txt','technologies = { hro_test_forest = { research_cost = 1 } }')
  self.put('common/units/equipment/modules/test.txt','equipment_modules = { hro_test_wide_tracks = { category = tank_suspension_type } }')
  self.put('common/decisions/test.txt','hro_test_ops_category = { hro_test_ops_rest = { cost = 50 complete_effect = { army_experience = 1 } } }')
  self.put('common/decisions/categories/test.txt','hro_test_ops_category = { icon = generic_army }')
  self.put('events/test.txt','add_namespace = hro country_event = { id = hro.950 title = hro.950.t desc = hro.950.d option = { name = hro.950.a } }')
  values={'hro_test_staff':'Staff college','hro_test_staff_desc':'Existing catalogue narrative explaining why the staff college matters. Exact reward: +15%. Preparation and effects remain unchanged.','hro_test_repair':'Repair service','hro_test_repair_desc':'Organisation recovery: +15%. Lasts 21 days.','hro_test_forest':'Forest school','hro_test_forest_desc':'Forest attack +10%.','hro_test_wide_tracks':'Wide tracks','hro_test_wide_tracks_desc':'Module stats remain visible in designer.','hro_test_ops_rest':'Regroup','hro_test_ops_rest_desc':'21 days; supply consumption +30%.','hro_test_ops_category':'Operations','hro_test_ops_category_desc':'Prepare and launch an offensive.','hro.950.t':'Multi-turreted shadow','hro.950.d':'Five experimental vehicles, not a mass-produced heavy tank.','hro.950.a':'Continue'}
  for lang in ('russian','english'):self.put(f'localisation/{lang}/test_l_{lang}.yml','l_'+lang+':\n'+''.join(' '+k+':0 '+json.dumps(v)+'\n' for k,v in values.items()),True)
  self.old=g.read(self.mod);self.before={p.relative_to(self.mod):p.read_bytes() for p in self.mod.rglob('*.txt')}
 def put(self,path,text,bom=False):
  p=self.mod/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8-sig' if bom else 'utf-8')
 def build(self):
  with patch.object(g,'ROOT',self.root):return g.generate(self.mod,self.catalogs)
 def test_every_entity_gets_context_but_effect_values_and_script_bytes_remain(self):
  report=self.build();self.assertEqual(report['entity_counts'],{'focuses':1,'ideas':1,'research':1,'modules':1,'decisions':1,'decision_categories':1,'events':1});new=g.read(self.mod)
  for path,data in self.before.items():self.assertEqual((self.mod/path).read_bytes(),data)
  for lang in ('russian','english'):
   for key in report['keys']:
    self.assertIn(self.old[lang][key][0],new[lang][key][0])
   self.assertEqual(new[lang]['hro_test_staff_desc'][0],self.old[lang]['hro_test_staff_desc'][0])
  self.assertTrue((self.mod/'docs/ENCYCLOPEDIA_RU.md').is_file())
 def test_context_must_explain_a_specific_subject(self):
  with self.assertRaisesRegex(ValueError,'Missing narrative subject'):g.context('hro_unknown','Unknown')
 def test_native_override_adds_no_duplicate_key_and_keeps_old_reward(self):
  (self.root/'data/narrative_native.json').write_text(json.dumps({'hro_test_repair':{'ru':'Плановые ремонтные службы сохраняют исправность техники и возвращают повреждённые машины в части.','en':'Planned repair services retain serviceability and return damaged vehicles to their units.'}}));self.build();data=g.read(self.mod);self.assertEqual(sum(k=='hro_test_repair_desc' for k in data['russian']),1);self.assertIn('Organisation recovery: +15%.',data['russian']['hro_test_repair_desc'][0])
 def test_dynamic_game_localisation_and_colours_survive_typographic_cleanup(self):
  self.assertEqual(g.normalize('$stage1$ [GER.GetModel2] §Yна14дней§!'),'$stage1$ [GER.GetModel2] §Yна 14 дней§!')
 def test_bad_localisation_encoding_or_missing_description_cannot_pass(self):
  report=self.build();p=self.mod/'localisation/russian/test_l_russian.yml';p.write_text(p.read_text(encoding='utf-8-sig').replace('Forest attack +10%.','???'),encoding='utf-8-sig')
  with self.assertRaisesRegex(ValueError,'Broken text'):g.audit(self.mod,report)
 def test_explanations_distinguish_mutually_exclusive_specialisations(self):
  for left,right in [('hro_tech_ger_urban_assault','hro_tech_ger_urban_defence'),('hro_design_fighter_a','hro_design_fighter_b'),('hro_face_hardened','hro_homogeneous'),('hro_ger_specialize_decisive','hro_ger_specialize_sequential')]:self.assertNotEqual(g.context(left)[1],g.context(right)[1])
if __name__=='__main__':unittest.main()
