"""Visible, slot-based front research and atomic migration of technical spirits.

The vanilla GUI is patched losslessly at build time. No vanilla game files are
stored in the source repository. Historical doctrine/crisis spirits stay ideas.
"""
from pathlib import Path
import hashlib,json
from clausewitz import parse,walk,edit
from generate_frontier import script,SCHOOLS
from decision_details import describe

FOLDER='hro_front_folder'
# Single-tier, permanent, technical reforms only. Modifier dictionaries remain
# authoritative in the catalogs, and are copied exactly into technologies.
CONVERT = {
 'GER': [('radio_network_1',1939),('assault_engineers_1',1941),('strategic_reserves_1',1939),
         ('story_fortifications',1938),('story_decoys',1941),('story_kitchens',1940)],
 'SOV': [('fire_control_1',1942),('engineers_1',1942),('radio_network_1',1942),
         ('reserve_warehouses_1',1942),('story_fortifications',1939),('story_workshops',1942)],
}
CHAINS = {
 'maintenance': ('Обслуживание техники','Equipment Maintenance',
                 {'maintenance_company':{'reliability_factor':.05}}, {'attrition':-.03},'tech_maintenance_company'),
 'evacuation': ('Эвакуация раненых','Casualty Evacuation',
                {'field_hospital':{'casualty_trickleback':.05}}, {'experience_loss_factor':-.03},'tech_field_hospital'),
 'winter': ('Зимнее оснащение','Winter Equipment',{}, {'winter_attrition_factor':-.05},'tech_mountaineers'),
 'logistics': ('Полевое снабжение','Field Supply',
               {'logistics_company':{'supply_consumption_factor':-.03,'fuel_consumption_factor':-.03}}, {},'tech_logistics_company'),
}
YEARS=(1938,1941,1943)


def converted(catalogs):
 result=[]
 for c in catalogs:
  lookup={i['id']:i for i in c['ideas']}
  for suffix,year in CONVERT[c['tag']]:
   idea=lookup['hro_idea_'+c['tag'].lower()+'_'+suffix]
   assert not idea.get('initial') and not idea.get('equipment_bonus')
   assert len([i for i in c['ideas'] if i['family']==idea['family']])==1
   result.append(dict(idea=idea,tag=c['tag'],year=year,tech=idea['id'].replace('hro_idea_','hro_tech_reform_')))
 return result


def replacement_setter(record):
 identity=record['idea']['id'];tech=record['tech'];flag=tech+'_bonus_issued'
 return f'''hro_set_{identity} = {{
 custom_effect_tooltip = {tech}_focus_tt
 hidden_effect = {{ if = {{ limit = {{ original_tag = {record['tag']} NOT = {{ has_country_flag = {flag} }} }}
  set_country_flag = {flag}
  if = {{ limit = {{ NOT = {{ has_tech = {tech} }} }} add_tech_bonus = {{ name = {tech}_bonus bonus = 1 uses = 1 technology = {tech} }} }}
 }} }}
}}'''


def generate(output,game,catalogs):
 output=Path(output);game=Path(game);loc={'russian':{},'english':{}};techs=[];roots=[];sprite_requests={};migration=[]
 def put(path,text,bom=False):
  p=output/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text+'\n',encoding='utf-8-sig' if bom else 'utf-8')
 def text(k,ru,en):loc['russian'][k]=ru;loc['english'][k]=en
 text(FOLDER,'Фронтовые разработки','Front Developments')
 text(FOLDER+'_desc','Школы боя, инженерные разработки и обеспечение войск. Технологии изучаются в обычных слотах.','Combat schools, engineering and army support. Technologies use normal research slots.')
 text('hro_front_research','Фронтовые разработки','Front Developments')
 text('hro_research_heading','ФРОНТОВЫЕ РАЗРАБОТКИ','FRONT DEVELOPMENTS')
 text('hro_research_help','Исследуйте в обычных слотах. Фокусы ускоряют разработку. Бонусы появляются после завершения исследования.','Use normal research slots. Focuses speed up development. Effects apply when research completes.')
 text('hro_research_schools','ШКОЛЫ БОЯ — ВЫБЕРИТЕ ОДНУ В КАЖДОЙ ПАРЕ','COMBAT SCHOOLS — CHOOSE ONE IN EACH PAIR')
 text('hro_research_support','ОБЕСПЕЧЕНИЕ ВОЙСК — ПОСЛЕДОВАТЕЛЬНЫЕ УЛУЧШЕНИЯ','ARMY SUPPORT — PROGRESSIVE IMPROVEMENTS')
 text('hro_research_reforms','НАЦИОНАЛЬНЫЕ ТЕХНИЧЕСКИЕ ПРОГРАММЫ','NATIONAL TECHNICAL PROGRAMMES')
 text('hro_research_reforms_help','Постоянные технические бонусы перенесены из национальных духов. Фокус даёт один целевой бонус +100% к скорости исследования.','Permanent technical bonuses replace national spirits. The matching focus gives one targeted +100% research speed bonus.')
 # Country-specific old school IDs are retained so already researched schools survive.
 for tag in ('ger','sov'):
  for index,key in enumerate(SCHOOLS):
   identity=f'hro_tech_{tag}_{key}'
   roots.append((identity,220+(index%2)*350,190+(index//2)*160))
   sprite_requests[identity]={'urban':'tech_engineers','forest':'tech_mountaineers','river':'tech_engineers2','mobile':'tech_logistics_company'}[key]
 # Four independent chains, additive increments (not replacement spirits).
 for row,(key,(ru,en,units,mods,icon)) in enumerate(CHAINS.items()):
  text('hro_research_row_'+key,ru,en)
  for index,year in enumerate(YEARS,1):
   identity=f'hro_tech_front_{key}_{index}'
   if index==1:roots.append((identity,350,610+row*150))
   next_path=f'path = {{ leads_to_tech = hro_tech_front_{key}_{index+1} research_cost_coeff = 1 }}' if index<3 else ''
   dependency=f'dependencies = {{ hro_tech_front_{key}_{index-1} = 1 }}' if index>1 else ''
   # The specialist support company must already be available; infantry winter
   # equipment is independent of mountain-troop research.
   if index==1 and key!='winter':dependency=f'dependencies = {{ {icon} = 1 }}'
   techs.append(f'''{identity} = {{ allow_branch = {{ hro_supported_country = yes }} allow = {{ hro_supported_country = yes }}
    research_cost = {(.8,1,1.2)[index-1]} start_year = {year}
    folder = {{ name = {FOLDER} position = {{ x = 0 y = {(index-1)*4} }} }}
    {next_path} {dependency} categories = {{ hro_front_research support_tech }}
    force_use_small_tech_layout = yes ai_will_do = {{ factor = 1 }}
    {script(units)} {script(mods)}
   }}''')
   details_ru={'maintenance':'Ремонтная рота: надёжность +5%. Общие потери от истощения −3%.',
    'evacuation':'Полевой госпиталь: возвращение потерь +5 процентных пунктов. Потери опыта бойцов −3%.',
    'winter':'Общие зимние потери от истощения −5%. Не снимает кризис первой зимы.',
    'logistics':'Рота снабжения: дополнительное снижение расхода припасов и топлива на 3%.'}[key]
   details_en={'maintenance':'Maintenance company: reliability +5%. Global attrition −3%.',
    'evacuation':'Field hospital: casualty trickleback +5 percentage points. Experience loss −3%.',
    'winter':'Global winter attrition −5%. Does not remove the first-winter crisis.',
    'logistics':'Logistics company: additional supply and fuel consumption reductions of 3%.'}[key]
   text(identity,f'{ru} {index}',f'{en} {index}')
   text(identity+'_desc',details_ru+f' Этап {year} года. Каждая ступень добавляет указанные эффекты; после трёх ступеней итог втрое больше. Бонусы рот действуют при наличии этих рот в дивизии.',details_en+f' {year} stage. Each level adds the stated effects; three levels total three times these effects. Company bonuses require that company in the division.')
   sprite_requests[identity]=icon
 # Convert twelve existing single-stage spirits into visible research.
 records=converted(catalogs)
 source_path=output/'common/scripted_effects/hro_country_progression.txt';source=source_path.read_text();defs={n.key:n for n in parse(source)};patches=[]
 for record in records:
  idea=record['idea'];identity=idea['id'];tech=record['tech'];tag=record['tag'];index=[r for r in records if r['tag']==tag].index(record)
  roots.append((tech,220+(index%3)*300,1370+(index//3)*170));sprite_requests[tech]='tech_engineers' if 'fortification' in identity or 'engineer' in identity else 'tech_signal_company' if 'radio' in identity or 'decoy' in identity else 'tech_logistics_company'
  techs.append(f'''{tech} = {{ allow_branch = {{ original_tag = {tag} }} allow = {{ original_tag = {tag} }}
   research_cost = 1.2 start_year = {record['year']} folder = {{ name = {FOLDER} position = {{ x = 0 y = 0 }} }}
   categories = {{ hro_front_research support_tech }} force_use_small_tech_layout = yes ai_will_do = {{ factor = 1 }}
   {script(idea['modifiers'])}
   on_research_complete = {{ if = {{ limit = {{ has_idea = {identity} }} remove_ideas = {identity} }} }}
  }}''')
  for lang,suffix in [('russian','ru'),('english','en')]:
   loc[lang][tech]=idea['name_'+suffix]
   loc[lang][tech+'_desc']=describe(idea['modifiers'],lang)+(' Постоянные эффекты технологии. Прежний национальный дух заменён исследованием; повторно бонусы не складываются.' if lang=='russian' else 'Permanent technology effects. This research replaces the former national spirit; bonuses do not stack twice.')
   loc[lang][tech+'_bonus']=loc[lang][tech]
   loc[lang][tech+'_focus_tt']=(f'Один бонус +100% к скорости исследования «{idea["name_ru"]}» во вкладке «Фронтовые разработки», если технология ещё не изучена. Постоянные эффекты появятся после завершения исследования.' if lang=='russian' else f'One +100% research speed bonus for {idea["name_en"]} in Front Developments, if not researched yet. Permanent effects begin when research completes.')
  node=defs['hro_set_'+identity];patches.append((node.start,node.end,replacement_setter(record)))
  migration.append(f'''if = {{ limit = {{ original_tag = {tag} has_idea = {identity} }}
   if = {{ limit = {{ NOT = {{ has_tech = {tech} }} }} set_technology = {{ {tech} = 1 popup = no }} }}
   remove_ideas = {identity} set_country_flag = {tech}_bonus_issued
  }}''')
 source_path.write_text(edit(source,patches))
 put('common/technologies/hro_front_developments.txt','technologies = {\n'+'\n'.join(techs)+'\n}')
 put('common/technology_tags/hro_front_research.txt',f'technology_categories = {{ hro_front_research }}\ntechnology_folders = {{ {FOLDER} = {{ ledger = army available = {{ hro_supported_country = yes }} }} }}')
 put('common/scripted_effects/hro_research_migration.txt','hro_research_migrate = {\n'+'\n'.join(migration)+'\n}')
 put('common/on_actions/hro_research_on_actions.txt','on_actions = { on_daily = { effect = { hro_research_migrate = yes } } }')
 ui=author_ui(output,game,roots,sprite_requests)
 for lang,entries in loc.items():put(f'localisation/{lang}/hro_research_l_{lang}.yml',f'l_{lang}:\n'+''.join(f' {k}:0 {json.dumps(v,ensure_ascii=False)}\n' for k,v in entries.items()),True)
 return dict(technologies=32,visible_per_country=22,schools=8,new_support_technologies=12,converted_spirits=12,removed_active_spirits_per_country=6,base_days=[88,110,132],school_base_days=110,reform_base_days=132,research_slots=True,school_focus_auto_grant=False,ui=ui,runtime_verified=False)


def author_ui(output,game,roots,icons):
 """Insert one tab, one scrollable folder and two item templates, preserving
 every byte outside insertions in the supplied version-specific vanilla GUI."""
 path=game/'interface/countrytechtreeview.gui'
 if not path.is_file():raise ValueError('Research needs uploaded interface/countrytechtreeview.gui')
 source=path.read_text(encoding='utf-8-sig');root=parse(source)[0]
 def named(nodes,name):return next(n for n in nodes if n.scalar('name','').strip('"')==name)
 window=named(root.value,'countrytechtreeview');tabs=named(window.value,'folder_tabs')
 def label(key,x,y,width=1000,font='hoi_20b',height=42):
  return f'instantTextBoxType = {{ name = "{key}" position = {{ x = {x} y = {y} }} font = "{font}" text = "{key}" maxWidth = {width} maxHeight = {height} format = left }}'
 content=[label('hro_research_heading',30,20),label('hro_research_help',30,60,font='hoi_16mb'),label('hro_research_schools',30,115),label('hro_research_support',30,495),label('hro_research_reforms',30,1230),label('hro_research_reforms_help',30,1270,font='hoi_16mb')]
 for i,key in enumerate(CHAINS):content.append(label('hro_research_row_'+key,30,625+i*150,265))
 for year,x in zip(YEARS,(350,630,910)):content.append(f'instantTextBoxType = {{ name = "year_{year}" position = {{ x = {x} y = 555 }} font = "hoi_20b" text = "{year}" maxWidth = 130 maxHeight = 30 }}')
 for identity,x,y in roots:content.append(f'gridboxtype = {{ name = "{identity}_tree" position = {{ x = {x} y = {y} }} slotsize = {{ width = 70 height = 70 }} format = "LEFT" }}')
 panel=f'''containerWindowType = {{ name = "{FOLDER}" position = {{ x = 0 y = 47 }} size = {{ width = 100%% height = 100%% }}
  margin = {{ top = 13 left = 13 bottom = 24 right = 25 }} drag_scroll = {{ left middle }}
  verticalScrollbar = "right_vertical_slider" horizontalScrollbar = "bottom_horizontal_slider" scroll_wheel_factor = 40
  background = {{ name = "Background" quadTextureSprite = "GFX_tiled_window_2b_border" }}
  containerWindowType = {{ name = "hro_extent" position = {{ x = 0 y = 0 }} size = {{ width = 1120 height = 1780 min = {{ width = 100%% height = 100%% }} }} clipping = no }}
  {' '.join(content)}
 }}'''
 tab=f'buttonType = {{ name = "{FOLDER}_tab" position = {{ x = 823 y = 0 }} quadTextureSprite = "GFX_support_folder_tab" frame = 1 clicksound = ui_research_tab_support pdx_tooltip = "{FOLDER}" }}'
 # Vanilla naming conventions let the engine bind research nodes and their
 # researched/current/available states to these templates.
 templates=[]
 for size in ('item','small_item'):
  node=named(root.value,'techtree_support_folder_'+size)
  fragment=source[node.start:node.end].replace('techtree_support_folder_'+size,'techtree_'+FOLDER+'_'+size)
  if size=='small_item':
   fragment=fragment[:-1]+'''instantTextBoxType = { name = "Name" position = { x = -65 y = 75 } font = "hoi_16mb" maxWidth = 200 maxHeight = 55 format = center } }'''
  templates.append(fragment)
 patches=[(tabs.value_end-1,tabs.value_end-1,tab),(window.value_end-1,window.value_end-1,panel),(root.value_end-1,root.value_end-1,'\n'.join(templates))]
 final=edit(source,patches);parse(final)
 (output/'interface').mkdir(exist_ok=True);(output/'interface/countrytechtreeview.gui').write_text(final,encoding='utf-8-sig')
 # Alias existing, shipped vanilla texture files by the new technology IDs.
 sprites={}
 for p in [game/'interface/Technologies.gfx']:
  for n in walk(parse(p.read_text(encoding='utf-8-sig'))):
   if n.key and n.key.lower()=='spritetype' and n.scalar('texturefile'):
    sprites[n.scalar('name','').strip('"')]=n.scalar('texturefile')
 definitions=[]
 for tech,icon in icons.items():
  name='GFX_'+icon+'_medium'
  if name not in sprites:raise ValueError('Vanilla research sprite missing: '+name)
  definitions.append(f'spriteType = {{ name = "GFX_{tech}_medium" texturefile = {sprites[name]} }}')
 (output/'interface/hro_research_icons.gfx').write_text('spriteTypes = {\n'+'\n'.join(definitions)+'\n}')
 return dict(source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),folder=FOLDER,root_grids=len(roots),sprite_aliases=len(icons),vanilla_gui_preserved_outside_insertions=True)


def audit(output,game,catalogs,schema_dir=None):
 """Validate graph, names, GUI bindings, inherited modifiers and migration.
 Game-engine rendering remains a separate, manual verification step.
 """
 output=Path(output);records=converted(catalogs);errors=[]
 techs={n.key:n for p in (output/'common/technologies').glob('hro*.txt') for r in parse(p.read_text()) for n in r.value}
 gui=parse((output/'interface/countrytechtreeview.gui').read_text(encoding='utf-8-sig'))
 names={n.scalar('name','').strip('"') for n in walk(gui) if isinstance(n.value,list)}
 targets={n.value for t in techs.values() for n in walk(t.value) if n.key=='leads_to_tech'}
 for k,t in techs.items():
  if not t.one('folder') or t.one('folder').scalar('name')!=FOLDER:errors.append('Missing research folder: '+k)
  if k not in targets and k+'_tree' not in names:errors.append('Missing root grid: '+k)
  if float(t.scalar('research_cost','0'))<=0:errors.append('Research must cost time: '+k)
  for n in walk(t.value):
   if n.key=='leads_to_tech' and n.value not in techs:errors.append('Missing path target: '+str(n.value))
  if t.one('xor'):
   for n in t.one('xor').value:
    if n.value not in techs or k not in {x.value for x in techs[n.value].one('xor').value}:errors.append('Asymmetric exclusion: '+k)
 for record in records:
  t=techs[record['tech']];actual={m.key:float(m.value) for m in t.value if m.key in record['idea']['modifiers']}
  if actual!=record['idea']['modifiers']:errors.append('Transferred modifiers differ: '+record['tech'])
 effects={n.key:n for p in (output/'common/scripted_effects').glob('hro*.txt') for n in parse(p.read_text())}
 for record in records:
  identity=record['idea']['id'];node=effects['hro_set_'+identity]
  if any(n.key in ('add_ideas','set_technology') for n in walk(node.value)):errors.append('Focus directly grants technical benefits: '+identity)
  if not any(n.key=='technology' and n.value==record['tech'] for n in walk(node.value)):errors.append('Missing targeted focus bonus: '+identity)
 for path in (output/'common/scripted_effects').glob('hro*.txt'):
  for n in walk(parse(path.read_text())):
   if n.key=='set_technology':
    for child in n.value:
     if child.key and child.key.startswith('hro_tech_') and child.key not in techs:errors.append('Unknown technology: '+child.key)
 # Exact preservation of vanilla GUI structure after removing our additions.
 def signature(nodes):
  result=[]
  for n in nodes:
   if isinstance(n.value,list) and n.scalar('name','').strip('"') in {FOLDER,FOLDER+'_tab','techtree_'+FOLDER+'_item','techtree_'+FOLDER+'_small_item'}:continue
   result.append((n.key,n.op,signature(n.value) if isinstance(n.value,list) else n.value))
  return result
 native=parse((Path(game)/'interface/countrytechtreeview.gui').read_text(encoding='utf-8-sig'))
 if signature(gui)!=signature(native):errors.append('Vanilla research GUI changed outside declared additions')
 native_techs={n.key for p in (Path(game)/'common/technologies').glob('*.txt') for r in parse(p.read_text(encoding='utf-8-sig')) if isinstance(r.value,list) for n in r.value}
 units={n.key for p in (Path(game)/'common/units').glob('*.txt') for r in parse(p.read_text(encoding='utf-8-sig')) if r.key=='sub_units' for n in r.value}
 if not units:errors.append('Missing vanilla unit definitions')
 edges={k:[] for k in techs}
 for k,t in techs.items():
  dependency=t.one('dependencies')
  if dependency:
   for dep in dependency.value:
    if dep.key not in native_techs|techs.keys():errors.append('Unknown prerequisite: '+str(dep.key))
    if dep.key in techs:edges[k].append(dep.key)
 def visit(k,seen,active):
  if k in active:raise ValueError('Research dependency cycle: '+k)
  if k in seen:return
  active.add(k)
  for target in edges[k]:visit(target,seen,active)
  active.remove(k);seen.add(k)
 seen=set()
 for k in techs:visit(k,seen,set())
 if schema_dir:
  import re
  schema='\n'.join(p.read_text(encoding='utf-8-sig') for p in (Path(schema_dir)/'Config').rglob('*.cwt'))
  stats=set(re.findall(r'alias\[unit_stat:([A-Za-z_][A-Za-z0-9_]*)\]',schema))
  modifiers=set(re.findall(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:country|army|aggressive|defensive|naval|air|state|intelligence_agency)\s*$',schema,re.M))
  modifiers.update('production_speed_'+b+'_factor' for b in ('bunker','coastal_bunker'))
  meta={'allow','allow_branch','xor','research_cost','start_year','folder','categories','force_use_small_tech_layout','ai_will_do','dependencies','path','on_research_complete'}
  for k,t in techs.items():
   for n in t.value:
    if n.key in meta:continue
    if isinstance(n.value,str):
     if n.key not in modifiers:errors.append('Unknown research modifier: '+str(n.key))
     float(n.value)
    elif n.key not in units:errors.append('Unknown research unit: '+str(n.key))
    else:
     for stat in n.value:
      if stat.key in ('urban','forest','river','fort'):
       if any(x.key not in ('attack','defence','movement') for x in stat.value):errors.append('Unknown terrain stat: '+str(stat.key))
      elif stat.key not in stats:errors.append('Unknown research unit stat: '+str(stat.key))
 for lang in ('russian','english'):
  import re
  loc='\n'.join(p.read_text(encoding='utf-8-sig') for p in (output/'localisation'/lang).glob('*.yml'))
  keys=set(re.findall(r'^\s*(\w+):',loc,re.M))
  for k in techs:
   if k not in keys or k+'_desc' not in keys:errors.append('Missing research localisation: '+lang+'/'+k)
 sprite_names={n.scalar('name','').strip('"') for n in walk(parse((output/'interface/hro_research_icons.gfx').read_text())) if isinstance(n.value,list)}
 for k in techs:
  if 'GFX_'+k+'_medium' not in sprite_names:errors.append('Missing research sprite: '+k)
 if errors:raise ValueError('\n'.join(errors))
 return dict(technologies=len(techs),converted_modifiers_exact=True,root_bindings_checked=True,exclusive_schools_checked=True,focuses_do_not_grant_technologies=True)
