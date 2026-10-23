"""Background coverage, native registry preservation and DDS corruption checks."""
from pathlib import Path
import sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'overhaul/tools')]
from generate_loading_screens import generate,audit
class LoadingTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);base=Path(self.temp.name);self.game=base/'game';self.mod=base/'mod';p=self.game/'common/frontend/backgrounds/base_backgrounds.txt';p.parent.mkdir(parents=True);p.write_text('load_1 = {} load_5 = {} load_nsb = { dlc_allowed = "No Step Back" }');self.native=p;self.before=p.read_bytes()
 def test_every_default_and_dlc_key_has_a_full_image_and_thumbnail(self):
  r=generate(self.mod,self.game);self.assertEqual(r['native_backgrounds_retextured'],3);self.assertEqual(r['own_backgrounds'],5);self.assertEqual(r['audit']['dds_checked'],16);self.assertEqual(self.native.read_bytes(),self.before);self.assertFalse((self.mod/'common/frontend/backgrounds/base_backgrounds.txt').exists())
 def test_missing_or_wrong_size_texture_stops_art_audit(self):
  r=generate(self.mod,self.game);p=self.mod/'gfx/loadingscreens/load_nsb.dds';raw=p.read_bytes();p.unlink()
  with self.assertRaisesRegex(ValueError,'Missing loading art'):audit(self.mod,self.game,r)
  p.write_bytes(raw[:128])
  with self.assertRaisesRegex(ValueError,'Invalid loading DDS'):audit(self.mod,self.game,r)
 def test_missing_game_registry_stops_generation(self):
  self.native.unlink()
  with self.assertRaisesRegex(ValueError,'needs supplied'):generate(self.mod,self.game)
 def test_visual_update_preserves_existing_gameplay_files(self):
  p=self.mod/'common/scripted_effects/sentinel.txt';p.parent.mkdir(parents=True);p.write_bytes(b'keep = { army_experience = 5 }');generate(self.mod,self.game);self.assertEqual(p.read_bytes(),b'keep = { army_experience = 5 }');self.assertFalse((self.mod/'interface/countrytechtreeview.gui').exists())
if __name__=='__main__':unittest.main()
