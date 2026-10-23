"""Ship original painted illustration assets, with deterministic thematic bindings."""
from pathlib import Path
import shutil,json
from clausewitz import parse,edit
ASSETS=Path(__file__).resolve().parents[1]/'assets/illustrations'
# Ordered specific phrases win over broad categories. Every generated idea and
# visible technology receives an owned texture, independent of vanilla sprites.
THEMES=[
 ('last_chance','mobilisation'),('kolobanov','heavy'),('hot_tea','supply'),('kitchens','supply'),('captured_maps','map'),('panzer','medium'),
 ('balance','map'),('preparing','blueprint'),('assault','rifles'),('rest','hospital'),('security','binoculars'),('council','tent'),
 ('replacement','training'),('breakthrough','medium'),('pursuit','trucks'),('city_momentum','urban'),
 ('contract','blueprint'),('tooling','lathe'),('spares','tools'),('dockyard','dockyard'),('signals','radio'),('signal','radio'),('transport','trucks'),('escort','convoy'),
 ('reserve_cycle','training'),('civil_defence','bunker'),('commercial','blueprint'),('civilian','factory'),('workshop','lathe'),('component','gears'),('shipyard','dockyard'),('truck','trucks'),
 ('diplomacy','tent'),('war_','rifles'),('elastic','map'),('exploitation','medium'),('strategic_reserves','supply'),('specialize','map'),('motorized','trucks'),('firepower','artillery'),
 ('native_special','mountain'),('bomber','bomber'),('surface','battleship'),('shipbuilding','dockyard'),('science','blueprint'),('decoys','medium'),
 ('administration','blueprint'),('plan_defence','bunker'),('plan_balanced','map'),('officer','tent'),('guards','medals'),('fire_control','artillery'),('warehouses','supply'),
 ('modernization','assembly'),('equipment_catalogue','blueprint'),('hold_city','urban'),('save_cadres','veteran'),('ambush','forest'),
 ('mountain supply','mountain_fort'),('mountain','mountain'),('urban defence','bunker'),('urban','urban'),('forest','forest'),('river','river'),
 ('winter','winter'),('exhaustion','exhausted'),('regroup','supply'),('crisis','burning'),('shock','shattered'),('surprise','shattered'),('dislocated','exhausted'),
 ('rebuilding','recovery'),('liberation','victory'),('mobiliz','mobilisation'),('adapted','veteran'),('battle_hardened','veteran'),
 ('dora','dora'),('coal','coal'),('mefo','blueprint'),('factory','factory'),('industry','assembly'),('production','lathe'),('industrial','factory'),
 ('armor','plates'),('armour','plates'),('heavy','heavy'),('medium','medium'),('light','light'),('spg','spg'),('td','td'),('tank','medium'),('blitzkrieg','medium'),
 ('fighter','fighter'),('cas','cas'),('airgun','cannon'),('airengine','engine'),('airsurvival','cockpit'),('air','airfield'),
 ('suspension','tools'),('engine','engine'),('protection','shield'),('cannon','cannon'),('service','trucks'),
 ('artillery','artillery'),('fort','bunker'),('engineer','tools'),('radio','radio'),('recon','binoculars'),('intelligence','binoculars'),
 ('submarine','submarine'),('raiding','submarine'),('navy','battleship'),('naval','anchor'),('sea','convoy'),
 ('rail','railway'),('logistic','trucks'),('depot','supply'),('supply','supply'),('fuel','fuel'),('repair','tools'),
 ('staff','map'),('command','tent'),('training','training'),('elite','medals'),('veteran','veteran'),('infantry','rifles'),('army','helmet'),('planning','map'),('operation','map'),('offensive','map'),('reform','blueprint'),('working','gears'),('front','map'),('aid','supply'),('recovery','recovery'),('state','mobilisation')]
def motif(identity):
 value=identity.lower().replace('_',' ')
 for pattern,name in THEMES:
  if pattern.replace('_',' ') in value:return name
 return 'medals'
def copy_asset(root,name,size,relative):
 target=Path(root)/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ASSETS/f'{name}_{size}.dds',target)
def research_assets(root):
 root=Path(root);sprites=[];bindings={}
 for path in sorted((root/'common/technologies').glob('hro*.txt')):
  for block in parse(path.read_text()):
   for tech in block.value:
    if not tech.one('folder'):continue
    name=motif(tech.key);relative=f'gfx/interface/hro_research/{name}.dds';copy_asset(root,name,128,relative)
    sprites.append(f'spriteType = {{ name = "GFX_{tech.key}_medium" texturefile = "{relative}" }}');bindings[tech.key]=name
 (root/'interface/hro_research_icons.gfx').write_text('spriteTypes = {\n'+'\n'.join(sprites)+'\n}\n')
 return bindings
