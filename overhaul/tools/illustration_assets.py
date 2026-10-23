"""Ship original painted illustration assets, with deterministic thematic bindings."""
from pathlib import Path
import shutil,json
from clausewitz import parse,edit
ASSETS=Path(__file__).resolve().parents[1]/'assets/illustrations'
# Ordered specific phrases win over broad categories. Every generated idea and
# visible technology receives an owned texture, independent of vanilla sprites.
THEMES=[('czech','light'),('renault','trucks'),('neubaufahrzeug','heavy'),('axis_blitz','map'),('mainila_crisis','winter'),('mainila_agreement','tent'),
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
# Exact per-module bindings prevent petrol and diesel engines, armour and fire
# extinguishers from receiving the same generic row picture.
COMPONENTS=Path(__file__).resolve().parents[1]/'assets/research_components'
MODULE_ART=dict(zip('command_radio applique_armor optical_rangefinder protected_rack gyro_sight cockpit_armor face_hardened homogeneous spaced_screens reinforced_plate long_travel rugged_torsion field_tracks wide_tracks boosted_petrol economy_diesel improved_cooling fuel_metering spall_liner fire_suppression roof_armor separated_stowage supercharged_motor cruise_motor emergency_boost aero_cowling light_cockpit sealed_cells armored_oil drop_tank_system high_velocity_75 support_75 rapid_mg_pack cannon_pack field_tools extended_fuel long_88 support_105 precision_88 blast_105'.split(),'radio frontal rangefinder stowage gyro cockpit cemented welded screens frontal christie torsion spare_tracks wide_tracks petrol diesel radiator injection liner extinguisher roof stowage radial inline supercharger cowling cockpit sealed_fuel oil drop_tank gun75 howitzer75 mg cannons tools regulator gun88 howitzer105 ap_shells he_shells'.split()))
def research_bindings():
 from generate_module_programmes import definitions as programmes
 from generate_design_schools import definitions as designs
 roots={'armor':'tank_blueprint','suspension':'tools','engine':'tank_blueprint','protection':'shield_medium','airengine':'air_blueprint','airsurvival':'armored_cas','cannon':'sight','airgun':'belt','service':'truck'}
 bindings={t['id']:MODULE_ART[t['modules'][0].removeprefix('hro_')] if t['modules'] else roots[t['row']] for t in programmes()}
 art={'light':['tank_blueprint','scout_light','radio_light','compass','radio'],'medium':['tank_blueprint','flag_medium','shield_medium','stabilizer','frontal'],'heavy':['tank_blueprint','heavy_gun','heavy_tools','gun88','welded'],'spg':['tank_blueprint','spg_fire','spg_march','howitzer105','regulator'],'td':['tank_blueprint','td_ambush','td_sight','ap_shells','rangefinder'],'fighter':['air_blueprint','dogfight','interceptor','gyro','supercharger'],'cas':['air_blueprint','dive_bomber','armored_cas','he_shells','cockpit']}
 for t in designs():
  suffix=t['id'].split('_')[-1];bindings[t['id']]=art[t['branch']][['base','a','b','a2','b2'].index(suffix)]
 school={'urban':'terrain_city','urban_assault':'terrain_assault','urban_defence':'terrain_defence','forest':'terrain_forest','forest_ambush':'terrain_ambush','forest_rangers':'terrain_rangers','river':'pontoon','mobile':'truck','mountain':'terrain_mountain','mountain_assault':'terrain_climb','mountain_supply':'terrain_mule'}
 for tag in ('ger','sov'):
  for key,name in school.items():bindings[f'hro_tech_{tag}_{key}']=name
 return bindings

def research_assets(root):
 root=Path(root);sprites=[];bindings=research_bindings();used={}
 for path in sorted((root/'common/technologies').glob('hro*.txt')):
  for block in parse(path.read_text()):
   for tech in block.value:
    if not tech.one('folder'):continue
    name=bindings[tech.key];relative=f'gfx/interface/hro_research/{name}.dds';target=root/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(COMPONENTS/f'{name}.dds',target)
    sprites.append(f'spriteType = {{ name = "GFX_{tech.key}_medium" texturefile = "{relative}" }}');used[tech.key]=name
 sprites.append('spriteType = { name = "GFX_hro_research_placeholder" texturefile = "gfx/interface/hro_research/tank_blueprint.dds" }')
 (root/'interface/hro_research_icons.gfx').write_text('spriteTypes = {\n'+'\n'.join(sprites)+'\n}\n')
 return used
