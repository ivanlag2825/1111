"""Original widescreen art; keep the vanilla background registry and UI intact."""
from pathlib import Path
import hashlib,json,re,shutil,struct
from clausewitz import parse
ASSETS=Path(__file__).resolve().parents[1]/'assets/loading_screens'
SCENES={'blitz':('Танковый прорыв','Armoured Breakthrough'),'winter':('Зимнее наступление','Winter Offensive'),'airwar':('Битва над фронтом','Battle above the Front')}

def registry(game):
 path=Path(game)/'common/frontend/backgrounds/base_backgrounds.txt'
 if not path.is_file():raise ValueError('Loading art needs supplied common/frontend/backgrounds/base_backgrounds.txt')
 names=[n.key for n in parse(path.read_text(encoding='utf-8-sig'))]
 if not names or any(not re.fullmatch('load_[A-Za-z0-9_]+',n) for n in names):raise ValueError('Unexpected vanilla loading-background key')
 return names,hashlib.sha256(path.read_bytes()).hexdigest()

def generate(output,game):
 root=Path(output);names,sha=registry(game);scenes=tuple(SCENES);mapping={n:scenes[i%len(scenes)] for i,n in enumerate(names)}
 mapping.update({'hro_load_'+k:k for k in scenes})
 for name,scene in mapping.items():
  for suffix in ('','_small'):
   path=root/'gfx/loadingscreens'/(name+suffix+'.dds');path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ASSETS/(scene+suffix+'.dds'),path)
 sprites=[]
 for scene in scenes:
  sprites.append(f'spriteType = {{ name = "GFX_hro_load_{scene}_small" texturefile = "gfx/loadingscreens/hro_load_{scene}_small.dds" }}')
 sprites.append('corneredTileSpriteType = { name = "GFX_hro_loading_background" texturefile = "gfx/loadingscreens/hro_load_blitz.dds" borderSize = { x = 0 y = 0 } size = { x = 1920 y = 1080 } tilingCenter = no effectFile = "gfx/FX/buttonstate.shader" }')
 def put(path,value,bom=False):
  p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(value+'\n',encoding='utf-8-sig' if bom else 'utf-8')
 put('interface/hro_loading_screens.gfx','spriteTypes = { '+' '.join(sprites)+' }')
 put('common/frontend/backgrounds/hro_painted_backgrounds.txt','\n'.join('hro_load_'+k+' = { gfx = GFX_hro_loading_background }' for k in scenes))
 for lang,index in [('russian',0),('english',1)]:
  put(f'localisation/{lang}/hro_loading_screens_l_{lang}.yml','l_'+lang+':\n'+''.join(f' hro_load_{k}:0 {json.dumps(v[index],ensure_ascii=False)}\n' for k,v in SCENES.items()),True)
 report=dict(paintings=list(scenes),native_backgrounds_retextured=len(names),own_backgrounds=3,native_registry_sha256=sha,full_size=[1920,1080],thumbnail_size=[192,108],dds_format='DXT1',bindings=mapping,vanilla_registry_replaced=False,gameplay_changed=False,runtime_verified=False)
 report['audit']=audit(root,game,report)
 return report

def audit(output,game,report):
 root=Path(output);names,sha=registry(game);errors=[]
 if report['native_registry_sha256']!=sha:errors.append('Native background registry differs')
 if (root/'common/frontend/backgrounds/base_backgrounds.txt').exists():errors.append('Native background registry must not be overridden')
 if not set(names).issubset(report['bindings']):errors.append('DLC/default loading artwork is not covered')
 for name,scene in report['bindings'].items():
  for suffix,size in [('',(1920,1080)),('_small',(192,108))]:
   path=root/'gfx/loadingscreens'/(name+suffix+'.dds')
   if not path.is_file():errors.append('Missing loading art: '+str(path));continue
   raw=path.read_bytes();w,h=size
   if len(raw)!=128+w*h//2 or raw[:4]!=b'DDS ' or raw[84:88]!=b'DXT1' or struct.unpack_from('<II',raw,12)!=(h,w):errors.append('Invalid loading DDS: '+name+suffix)
   if raw!=(ASSETS/(scene+suffix+'.dds')).read_bytes():errors.append('Loading texture does not match painting: '+name+suffix)
 manifest=root/'interface/hro_loading_screens.gfx'
 if not manifest.is_file():errors.append('Missing background sprite manifest')
 else:
  sprites={n.scalar('name','').strip('"'):n for top in parse(manifest.read_text()) for n in top.value}
  for k in SCENES:
   if 'GFX_hro_load_'+k+'_small' not in sprites:errors.append('Missing selectable-background thumbnail: '+k)
 if errors:raise ValueError('\n'.join(errors))
 return dict(native_keys_checked=len(names),dds_checked=len(report['bindings'])*2,vanilla_ui_preserved=True,runtime_verified=False)
