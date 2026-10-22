"""National spirits must resolve to owned visible sprites and valid DDS files."""
from pathlib import Path
import importlib.util,json,struct,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'overhaul/tools')]
from clausewitz import parse,walk
from spirit_lifecycle import author_spirit_assets,audit_spirit_assets
from generate_war_adaptation import generate as war_generate
from generate_emergency import generate as city_generate
from generate_offensive import generate as offensive_generate
from generate_gameplay import generate as programmes_generate
from generate_reserves import generate as reserves_generate
from generate_operations import generate as operations_generate
from generate_allied_aid import generate as aid_generate
from generate_last_chance import generate as last_generate
from generate_campaign_balance import generate as balance_generate
from generate_mefo_relief import generate as mefo_generate
spec=importlib.util.spec_from_file_location('spirit_asset_builder',ROOT/'overhaul/tools/build_overhaul.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)


class SpiritAssetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        builder.author_country_content(self.root,builder.read_catalogs(ROOT/'overhaul/data'),{'GER':0,'SOV':0})
        war_generate(self.root);city_generate(self.root);offensive_generate(self.root);programmes_generate(self.root)
        reserves_generate(self.root);operations_generate(self.root);aid_generate(self.root);last_generate(self.root);balance_generate(self.root);mefo_generate(self.root)
    def modifiers(self):
        result={}
        for p in (self.root/'common/ideas').glob('hro*.txt'):
            for n in walk(parse(p.read_text(encoding='utf-8-sig'))):
                if n.key and n.key.startswith('hro_') and n.one('modifier'):
                    result[n.key]=[(m.key,m.value) for m in n.one('modifier').value]
        return result
    def test_all_292_spirits_are_visible_self_contained_and_keep_their_modifiers(self):
        before=self.modifiers();summary=author_spirit_assets(self.root)
        self.assertEqual(summary['visible_spirits'],292)
        self.assertEqual(audit_spirit_assets(self.root),[])
        self.assertEqual(self.modifiers(),before)
    def test_owned_dds_headers_include_real_pixels_and_alpha(self):
        author_spirit_assets(self.root)
        paths=list((self.root/'gfx/interface/ideas').glob('*.dds'));self.assertEqual(len(paths),4)
        for p in paths:
            data=p.read_bytes();self.assertEqual(data[:4],b'DDS ')
            self.assertEqual(struct.unpack_from('<II',data,12),(64,64))
            self.assertEqual(len(data),128+64*64*4)
            self.assertEqual(struct.unpack_from('<I',data,104)[0],0xff000000)
            self.assertIn(255,data[131::4]);self.assertIn(0,data[131::4])
    def test_missing_or_invalid_sprite_assets_fail_the_release_audit(self):
        author_spirit_assets(self.root)
        path=self.root/'gfx/interface/ideas/hro_spirit_army.dds';data=path.read_bytes();path.unlink()
        self.assertTrue(any('Missing national-spirit texture' in e for e in audit_spirit_assets(self.root)))
        path.write_bytes(data[:64])
        self.assertTrue(any('Invalid national-spirit DDS' in e for e in audit_spirit_assets(self.root)))
    def test_timed_country_flags_have_an_explicit_positive_value(self):
        count=0
        for p in (self.root/'common/scripted_effects').glob('*.txt'):
            for n in walk(parse(p.read_text())):
                if n.key=='set_country_flag' and isinstance(n.value,list) and n.scalar('days'):
                    self.assertEqual(n.scalar('value'),'1',str(p));count+=1
        self.assertGreater(count,4)


if __name__=='__main__':unittest.main()
