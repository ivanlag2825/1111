"""Visible, slot-based front research and atomic migration of technical spirits.

The vanilla GUI is patched losslessly at build time. No vanilla game files are
stored in the source repository. Historical doctrine/crisis spirits stay ideas.
"""
from pathlib import Path
import hashlib,json
from clausewitz import parse,walk,edit
from generate_frontier import script,SCHOOLS
from decision_details import describe
import generate_design_schools as design
import generate_terrain_schools as terrain

FOLDER='hro_front_folder'
MODULE_FOLDER='hro_module_folder'
FOLDERS=(FOLDER,MODULE_FOLDER)
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
 identity=record['idea']['id'];tech=record['tech']
 return f'''hro_set_{identity} = {{
 custom_effect_tooltip = {tech}_focus_tt
 hidden_effect = {{ if = {{ limit = {{ original_tag = {record['tag']} }}
  if = {{ limit = {{ NOT = {{ has_tech = {tech} }} }} set_technology = {{ {tech} = 1 popup = no }} }}
  if = {{ limit = {{ has_idea = {identity} }} remove_ideas = {identity} }}
 }} }}
}}'''


def generate(output,game,catalogs):
 output=Path(output);game=Path(game);loc={'russian':{},'english':{}};techs=[];roots=[];sprite_requests={};migration=[]
 def put(path,text,bom=False):
  p=output/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text+'\n',encoding='utf-8-sig' if bom else 'utf-8')
 def text(k,ru,en):
  if ru is not None:loc['russian'][k]=ru
  if en is not None:loc['english'][k]=en
 text(FOLDER,'Школы боя и техники','Combat and Design Schools')
 text(FOLDER+'_desc','Школы боя и специализации танковых и авиационных частей. Технологии изучаются в обычных слотах.','Combat schools and armour/air specialisations. Technologies use normal research slots.')
 text('hro_front_research','Фронтовые разработки','Front Developments')
 text('hro_module_heading','КОНСТРУКТОРСКИЕ ПРОГРАММЫ','CONSTRUCTOR PROGRAMMES')
 text('hro_module_help','Каждая строка открывает выбор модулей. Выберите одну линию и установите изученные модули в конструкторе.','Each row offers module choices. Choose one line and install researched modules in the designer.')
 text('hro_research_heading','ШКОЛЫ БОЯ И ТЕХНИКИ','COMBAT AND DESIGN SCHOOLS')
 text('hro_research_help','Сверху выберите школы боя. Ниже каждая строка: основы, одна из двух специализаций, её развитие.','Choose combat schools above. Each row below: foundations, one of two specialisations, its development.')
 text('hro_research_schools','ШКОЛЫ БОЯ — ВЫБЕРИТЕ ОДНУ В КАЖДОЙ ПАРЕ','COMBAT SCHOOLS — CHOOSE ONE IN EACH PAIR')
 text('hro_research_support','ТАНКОВЫЕ И АВИАЦИОННЫЕ ШКОЛЫ','ARMOUR AND AIR SCHOOLS')
 text('hro_research_pair_1','ГОРОД ИЛИ ЛЕС','URBAN OR FOREST')
 text('hro_research_pair_2','РЕКИ ИЛИ МАРШИ','RIVERS OR MARCHES')
 text('hro_research_stage_1','1936: ОСНОВЫ','1936: FOUNDATIONS')
 text('hro_research_stage_2','1938: ВЫБОР','1938: CHOICE')
 text('hro_research_stage_3','1940: РАЗВИТИЕ','1940: DEVELOPMENT')
 # Country-specific old school IDs are retained so already researched schools survive.
 for tag in ('ger','sov'):
  for index,key in enumerate(SCHOOLS):
   identity=f'hro_tech_{tag}_{key}'
   roots.append((identity,*{'urban':(250,210),'forest':(250,510),'river':(250,850),'mobile':(850,850)}[key]))
   sprite_requests[identity]={'urban':'tech_engineers','forest':'tech_mountaineers','river':'tech_engineers2','mobile':'tech_logistics_company'}[key]
 terrain_techs,terrain_roots,terrain_icons=terrain.generate(output,put,text)
 techs.extend(terrain_techs);roots.extend(terrain_roots);sprite_requests.update(terrain_icons)
 # Retired support research keeps IDs solely for loading old saves. No
 # modifiers, folders or paths survive; these nodes cannot be researched anew.
 for key in CHAINS:
  for stage in (1,2,3):
   identity=f'hro_tech_front_{key}_{stage}'
   techs.append(f'{identity} = {{ allow = {{ always = no }} research_cost = 1 start_year = 1938 }}')
   text(identity,'Архивная программа обеспечения','Retired Support Programme')
   text(identity+'_desc','Исследование удалено при переработке вкладки. Новых бонусов не даёт.','Retired when the research tab was redesigned. Provides no bonuses.')
 new_techs,new_roots,new_icons,unlocks=design.generate(output,put,text)
 limits=design.module_limits(output,game)
 techs.extend(new_techs);roots.extend(new_roots);sprite_requests.update(new_icons)
 # Preserve twelve focus reforms as hidden technologies, not research nodes.
 records=converted(catalogs)
 source_path=output/'common/scripted_effects/hro_country_progression.txt';source=source_path.read_text();defs={n.key:n for n in parse(source)};patches=[]
 for record in records:
  idea=record['idea'];identity=idea['id'];tech=record['tech'];tag=record['tag']
  # Existing focus reforms use hidden technology effects, keeping the tab clean.
  techs.append(f'''{tech} = {{ allow = {{ always = no }}
   research_cost = 1.2 start_year = {record['year']}
   {script(idea['modifiers'])}
   on_research_complete = {{ if = {{ limit = {{ has_idea = {identity} }} remove_ideas = {identity} }} }}
  }}''')
  for lang,suffix in [('russian','ru'),('english','en')]:
   loc[lang][tech]=idea['name_'+suffix]
   loc[lang][tech+'_desc']=describe(idea['modifiers'],lang)+(' Постоянная техническая реформа от фокуса. Применяется один раз без отдельного национального духа.' if lang=='russian' else 'Permanent technical reform granted by a focus. Applies once without a separate national spirit.')
   loc[lang][tech+'_bonus']=loc[lang][tech]
   loc[lang][tech+'_focus_tt']=('Постоянная техническая реформа: '+idea['name_ru']+'. '+describe(idea['modifiers'],'russian')+'. Применяется один раз, без отдельного национального духа.' if lang=='russian' else 'Permanent technical reform: '+idea['name_en']+'. '+describe(idea['modifiers'],'english')+'. Applies once without a separate national spirit.')
  node=defs['hro_set_'+identity];patches.append((node.start,node.end,replacement_setter(record)))
  for focus in next(c for c in catalogs if c['tag']==tag)['focuses']:
   if 'hro_set_'+identity in focus.get('reward',''):
    migration.append(f'if = {{ limit = {{ original_tag = {tag} has_completed_focus = {focus["id"]} }} hro_set_{identity} = yes }}')
  migration.append(f'''if = {{ limit = {{ original_tag = {tag} has_idea = {identity} }}
   if = {{ limit = {{ NOT = {{ has_tech = {tech} }} }} set_technology = {{ {tech} = 1 popup = no }} }}
   remove_ideas = {identity} set_country_flag = {tech}_bonus_issued
  }}''')
 source_path.write_text(edit(source,patches))
 put('common/technologies/hro_front_developments.txt','technologies = {\n'+'\n'.join(techs)+'\n}')
 put('common/technology_tags/hro_front_research.txt',f'technology_categories = {{ hro_front_research }}\ntechnology_folders = {{ {FOLDER} = {{ ledger = army available = {{ hro_supported_country = yes }} }} {MODULE_FOLDER} = {{ ledger = army available = {{ hro_supported_country = yes }} }} }}')
 put('common/scripted_effects/hro_research_migration.txt','hro_research_migrate = {\n'+'\n'.join(migration)+'\n}')
 put('common/on_actions/hro_research_on_actions.txt','on_actions = { on_daily = { effect = { hro_research_migrate = yes } } }')
 ui=author_ui(output,game,roots,sprite_requests)
 from illustration_assets import research_assets
 ui["owned_illustration_bindings"]=research_assets(output)
 design.preview(output)
 design.programmes.preview(output)
 for lang,entries in loc.items():put(f'localisation/{lang}/hro_research_l_{lang}.yml',f'l_{lang}:\n'+''.join(f' {k}:0 {json.dumps(v,ensure_ascii=False)}\n' for k,v in entries.items()),True)
 return dict(technologies=124,visible_technologies=100,visible_per_country=89,maximum_researched_per_country=52,schools=22,design_schools=7,design_technologies=35,designer_modules=40,new_module_programmes=9,module_programme_technologies=43,new_designer_modules=34,retired_support_technologies=12,hidden_focus_reforms=12,removed_active_spirits_per_country=6,base_days=[55,71.5,88],school_base_days=110,research_slots=True,school_focus_auto_grant=False,ui=ui,module_unlocks=unlocks,constructor_limit_files=limits,runtime_verified=False)


def layout(techs,roots):
 result={}
 def place(identity,root_x,root_y):
  t=techs[identity];f=t.one('folder');pos=f.one('position')
  result[identity]=(f.scalar('name'),root_x+float(pos.scalar('y'))*100-56,root_y+float(pos.scalar('x'))*100-7)
  for path in t.all('path'):place(path.scalar('leads_to_tech'),root_x,root_y)
 for identity,x,y in roots:place(identity,x,y)
 return result


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
 techs={n.key:n for p in (output/'common/technologies').glob('hro*.txt') for r in parse(p.read_text()) for n in r.value}
 placements=layout(techs,roots)
 captions={FOLDER:[],MODULE_FOLDER:[]};seen=set()
 for identity,(folder,x,y) in placements.items():
  # The two countries share school names and screen positions.
  canonical=identity.replace('hro_tech_sov_','hro_tech_ger_')
  if (folder,x,y,canonical) in seen:continue
  seen.add((folder,x,y,canonical))
  captions[folder].append(f'instantTextBoxType = {{ name = "hro_caption_{identity}" position = {{ x = {x+6:g} y = {y+4:g} }} font = "hoi_16mbs" text = "{identity}" maxWidth = 169 maxHeight = 32 format = center alwaystransparent = yes }}')
 main=[label('hro_research_heading',30,20),label('hro_research_help',30,65,font='hoi_16mbs',height=42),label('hro_research_schools',30,120),label('hro_research_pair_1',30,170,150,font='hoi_16mbs'),label('hro_research_pair_2',30,800,150,font='hoi_16mbs'),label('hro_research_support',30,1350)]
 for i,key in enumerate(design.BRANCHES):main.append(label('hro_design_row_'+key,20,1530+i*320,170,font='hoi_16mbs'))
 for index,x in enumerate((190,490,790),1):main.append(label('hro_research_stage_'+str(index),x,1400,260,font='hoi_16mbs'))
 module=[label('hro_module_heading',30,20),label('hro_module_help',30,65,font='hoi_16mbs',height=54)]
 for i,key in enumerate(design.programmes.PROGRAMMES):module.append(label('hro_mod_row_'+key,20,340+i*320,170,font='hoi_16mbs'))
 for index,x in enumerate((190,490,790),1):module.append(label('hro_research_stage_'+str(index),x,215,260,font='hoi_16mbs'))
 panels=[];tabs_added=[]
 for folder,content,height,index in [(FOLDER,main,3750,0),(MODULE_FOLDER,module,3200,1)]:
  for identity,x,y in roots:
   if techs[identity].one('folder').scalar('name')==folder:content.append(f'gridboxtype = {{ name = "{identity}_tree" position = {{ x = {x} y = {y} }} slotsize = {{ width = 100 height = 100 }} format = "LEFT" }}')
  rows=[(1550+i*320) for i in range(len(design.BRANCHES))] if folder==FOLDER else [(360+i*320) for i in range(len(design.programmes.PROGRAMMES))]
  bands=[f'containerWindowType = {{ name = "hro_band_{index}_{i}" position = {{ x = 10 y = {row-120} }} size = {{ width = {1390 if folder==MODULE_FOLDER else 1090} height = 310 }} background = {{ name = "Background" quadTextureSprite = "GFX_tiled_research_bg" }} }}' for i,row in enumerate(rows)]
  content=bands+content
  content.extend(captions[folder])
  panels.append(f'''containerWindowType = {{ name = "{folder}" position = {{ x = 0 y = 47 }} size = {{ width = 100%% height = 100%% }}
   margin = {{ top = 13 left = 13 bottom = 24 right = 25 }} drag_scroll = {{ left middle }}
   verticalScrollbar = "right_vertical_slider" horizontalScrollbar = "bottom_horizontal_slider" scroll_wheel_factor = 40
   background = {{ name = "Background" quadTextureSprite = "GFX_tiled_window_2b_border" }}
   containerWindowType = {{ name = "hro_extent_{index}" position = {{ x = 0 y = 0 }} size = {{ width = {1460 if folder==MODULE_FOLDER else 1160} height = {height} min = {{ width = 100%% height = 100%% }} }} clipping = no }}
   {' '.join(content)}
  }}''')
  tabs_added.append(f'buttonType = {{ name = "{folder}_tab" position = {{ x = {823+index*89} y = 0 }} quadTextureSprite = "'+('GFX_armour_folder_tab' if index==0 else 'GFX_techtree_engineering_tab')+f'" frame = 1 clicksound = ui_research_tab_support pdx_tooltip = "{folder}" }}')
 panel='\n'.join(panels);tab='\n'.join(tabs_added)
 # Vanilla naming conventions let the engine bind research nodes and their
 # researched/current/available states to these templates.
 templates=[]
 for folder,size in [(folder,size) for folder in FOLDERS for size in ('item','small_item')]:
  node=named(root.value,'techtree_support_folder_'+size)
  fragment=source[node.start:node.end].replace('techtree_support_folder_'+size,'techtree_'+folder+'_'+size)
  # Both templates use the actual Cyrillic-capable vanilla font. Full
  # cards retain native research-state and bonus bindings.
  fragment=fragment.replace('"hoi_20bs"','"hoi_16mbs"')
  if size=='item':
   parsed=parse(fragment)[0];changes=[]
   for child in parsed.value:
    if child.scalar('name','').strip('"')=='Name':
     changes.append((child.value_end-1,child.value_end-1,' hide = yes '))
     if field:=child.one('position'):changes.append((field.start,field.end,'position = { x = -10000 y = -10000 }'))
     else:changes.append((child.value_end-1,child.value_end-1,' position = { x = -10000 y = -10000 } '))
    if child.scalar('name','').strip('"')=='Icon':
     if field:=child.one('centerposition'):changes.append((field.start,field.end,'centerposition = no'))
     else:changes.append((child.value_end-1,child.value_end-1,' centerposition = no '))
     if field:=child.one('spriteType'):changes.append((field.start,field.end,'spriteType = "GFX_hro_research_placeholder"'))
     else:changes.append((child.value_end-1,child.value_end-1,' spriteType = "GFX_hro_research_placeholder" '))
     if field:=child.one('position'):changes.append((field.start,field.end,'position = { x = 42 y = 36 }'))

   fragment=edit(fragment,changes)
  templates.append(fragment)
 patches=[(tabs.value_end-1,tabs.value_end-1,tab),(window.value_end-1,window.value_end-1,panel),(root.value_end-1,root.value_end-1,'\n'.join(templates))]
 final=edit(source,patches);parse(final)
 (output/'interface').mkdir(exist_ok=True);(output/'interface/countrytechtreeview.gui').write_text(final,encoding='utf-8')
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
 return dict(explicit_name_captions=sum(len(v) for v in captions.values()),integer_grid_coordinates=True,folders=list(FOLDERS),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),folder=FOLDER,root_grids=len(roots),sprite_aliases=len(icons),vanilla_gui_preserved_outside_insertions=True)


def audit_interface_encoding(output):
 errors=[]
 for p in (Path(output)/'interface').rglob('*'):
  if p.is_file() and p.suffix.lower() in ('.gui','.gfx'):
   data=p.read_bytes()
   if data.startswith((b'\xef\xbb\xbf',b'\xff\xfe',b'\xfe\xff')):
    errors.append('Interface file has unsupported BOM: '+str(p.relative_to(output)))
 return errors


def audit(output,game,catalogs,schema_dir=None):
 """Validate graph, names, GUI bindings, inherited modifiers and migration.
 Game-engine rendering remains a separate, manual verification step.
 """
 output=Path(output);records=converted(catalogs);errors=audit_interface_encoding(output)
 techs={n.key:n for p in (output/'common/technologies').glob('hro*.txt') for r in parse(p.read_text()) for n in r.value}
 gui=parse((output/'interface/countrytechtreeview.gui').read_text(encoding='utf-8-sig'))
 names={n.scalar('name','').strip('"') for n in walk(gui) if isinstance(n.value,list)}
 targets={n.value for t in techs.values() for n in walk(t.value) if n.key=='leads_to_tech'}
 for k,t in techs.items():
  if t.one('folder') and t.one('folder').scalar('name') not in FOLDERS:errors.append('Missing research folder: '+k)
  if t.one('folder') and k not in targets and k+'_tree' not in names:errors.append('Missing root grid: '+k)
  if not t.one('folder') and (t.one('allow') is None or t.one('allow').scalar('always')!='no'):errors.append('Legacy technology became researchable: '+k)
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
  if any(n.key=='add_ideas' for n in walk(node.value)):errors.append('Focus restores a separate technical spirit: '+identity)
  if not any(n.key==record['tech'] and n.value=='1' for n in walk(node.value)):errors.append('Missing hidden focus reform: '+identity)
 for path in (output/'common/scripted_effects').glob('hro*.txt'):
  for n in walk(parse(path.read_text())):
   if n.key=='set_technology':
    for child in n.value:
     if child.key and child.key.startswith('hro_tech_') and child.key not in techs:errors.append('Unknown technology: '+child.key)
 # Research categories are identifiers from the actual game, not free text.
 categories=set()
 for base in (Path(game),output):
  for p in (base/'common/technology_tags').glob('*.txt'):
   for block in parse(p.read_text(encoding='utf-8-sig')):
    if block.key=='technology_categories':categories.update(n.value for n in block.value if isinstance(n.value,str))
 if not categories:errors.append('Missing vanilla research category definitions')
 for p in output.rglob('*.txt'):
  if not p.relative_to(output).parts[0] in ('common','events'):continue
  for n in walk(parse(p.read_text(encoding='utf-8-sig'))):
   if n.key=='add_tech_bonus':
    for category in n.all('category'):
     if category.value not in categories:errors.append('Unknown research category: '+str(category.value))
 # Exact preservation of vanilla GUI structure after removing our additions.
 def signature(nodes):
  result=[]
  for n in nodes:
   if isinstance(n.value,list) and n.scalar('name','').strip('"') in {v for f in FOLDERS for v in (f,f+'_tab','techtree_'+f+'_item','techtree_'+f+'_small_item')}:continue
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
  stats=set(re.findall(r'alias\[(?:unit_stat|air_stat):([A-Za-z_][A-Za-z0-9_]*)\]',schema))
  modifiers=set(re.findall(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:country|army|aggressive|defensive|naval|air|state|intelligence_agency)\s*$',schema,re.M))
  modifiers.update('production_speed_'+b+'_factor' for b in ('bunker','coastal_bunker'))
  meta={'allow','allow_branch','xor','research_cost','start_year','folder','categories','force_use_small_tech_layout','ai_will_do','dependencies','path','on_research_complete','enable_equipment_modules'}
  for k,t in techs.items():
   for n in t.value:
    if n.key in meta:continue
    if isinstance(n.value,str):
     if n.key not in modifiers:errors.append('Unknown research modifier: '+str(n.key))
     float(n.value)
    elif n.key not in units:errors.append('Unknown research unit: '+str(n.key))
    else:
     for stat in n.value:
      if stat.key in ('urban','forest','river','fort','mountain','hills'):
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
  if techs[k].one('folder') and 'GFX_'+k+'_medium' not in sprite_names:errors.append('Missing research sprite: '+k)
 # Validate owned pixels, not just sprite names: missing DDS files otherwise
 # render as empty cards although the script references look correct.
 import struct
 from illustration_assets import research_bindings
 bindings=research_bindings()
 for node in walk(parse((output/'interface/hro_research_icons.gfx').read_text())):
  if node.key!='spriteType':continue
  relative=node.scalar('texturefile','').strip('"');asset=(output/relative).resolve()
  if not relative.startswith('gfx/interface/hro_research/') or not asset.is_relative_to(output.resolve()) or not asset.is_file():
   errors.append('Missing owned research texture: '+relative);continue
  identity=node.scalar('name','').strip('"').removeprefix('GFX_').removesuffix('_medium')
  if identity in bindings and asset.name!=bindings[identity]+'.dds':errors.append('Research illustration does not match technology: '+identity)
  raw=asset.read_bytes()
  if len(raw)!=128+96*44*4 or raw[:4]!=b'DDS ' or struct.unpack_from('<II',raw,12)!=(44,96):errors.append('Invalid owned research DDS: '+relative)
 # Only Cyrillic-capable, actually defined fonts are allowed in our UI.
 font_source=Path(game)/'interface/core.gfx'
 fonts={};cyrillic=set()
 if not font_source.is_file():errors.append('Missing native font definitions: interface/core.gfx')
 else:
  for n in walk(parse(font_source.read_text(encoding='utf-8-sig'))):
   if n.key in ('bitmapfont','bitmapfont_override'):
    name=n.scalar('name','').strip('"');fonts[name]=n
    if any('cryllic' in str(v.value).lower() or 'cyrillic' in str(v.value).lower() for v in walk(n.value)):cyrillic.add(name)
 owned=[n for n in walk(gui) if isinstance(n.value,list) and n.scalar('name','').strip('"') in {v for f in FOLDERS for v in (f,'techtree_'+f+'_item','techtree_'+f+'_small_item')}]
 for container in owned:
  for n in walk(container.value):
   if n.key=='font':
    name=n.value.strip('"')
    if name not in fonts:errors.append('Unknown research font: '+name)
    elif name not in cyrillic:errors.append('Research font has no Cyrillic fallback: '+name)
 # Simulate declared native grid coordinates to catch overlapping cards.
 grids={n.scalar('name','').strip('"')[:-5]:n for n in walk(gui) if n.key=='gridboxtype' and n.scalar('name','').strip('"').endswith('_tree')}
 placements={}
 def place(k,root):
  t=techs[k];position=t.one('folder').one('position');grid=grids[root].one('position')
  xy=(float(grid.scalar('x'))+float(position.scalar('y'))*100-56,float(grid.scalar('y'))+float(position.scalar('x'))*100-7)
  placements[k]=(t.one('folder').scalar('name'),*xy)
  for path in t.all('path'):place(path.scalar('leads_to_tech'),root)
 for k,t in techs.items():
  if t.one('folder') and k not in targets and k in grids:place(k,k)
 for tag in ('ger','sov'):
  boxes=[(k,xy) for k,xy in placements.items() if not k.startswith('hro_tech_'+('sov' if tag=='ger' else 'ger')+'_')]
  for i,(k,(f,x,y)) in enumerate(boxes):
   for other,(ff,xx,yy) in boxes[i+1:]:
    if f==ff and abs(x-xx)<183 and abs(y-yy)<96:errors.append('Overlapping research cards: '+k+' / '+other)
 for k,t in techs.items():
  if folder:=t.one('folder'):
   for v in folder.one('position').value:
    if float(v.value)!=int(float(v.value)):errors.append('Fractional technology grid coordinate: '+k)
 captions={n.scalar('text','').strip('"'):n for n in walk(gui) if n.key=='instantTextBoxType' and n.scalar('name','').strip('"').startswith('hro_caption_')}
 for k,(f,x,y) in placements.items():
  canonical=k.replace('hro_tech_sov_','hro_tech_ger_')
  c=captions.get(k,captions.get(canonical))
  if c is None:errors.append('Missing explicit technology name: '+k)
  elif float(c.one('position').scalar('x'))!=x+6 or float(c.one('position').scalar('y'))!=y+4:errors.append('Technology caption does not align: '+k)
 module_report=design.audit(output,game,schema_dir)
 if errors:raise ValueError('\n'.join(errors))
 return dict(technologies=len(techs),converted_modifiers_exact=True,root_bindings_checked=True,exclusive_schools_checked=True,school_focuses_do_not_grant_technologies=True,interface_bom_free=True,research_bonus_categories_checked_against_game=True,cyrillic_fonts_checked=True,card_layout_checked=True,modules=module_report)
