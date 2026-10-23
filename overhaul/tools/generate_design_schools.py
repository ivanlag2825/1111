"""Original armour/air school choices and designer modules, using vanilla IDs."""
from pathlib import Path
import json
from clausewitz import parse,walk,edit
from generate_frontier import script

# Every row is independent; its two specialisations are mutually exclusive.
# Base, specialisation and capstone effects are incremental, not full totals.
def choice(ru,en,stats,capru,capen,capstats,reason,reason_en,modules=(),capmodules=()):
 return dict(ru=ru,en=en,stats=stats,capru=capru,capen=capen,capstats=capstats,reason=reason,reason_en=reason_en,modules=modules,capmodules=capmodules)
BRANCHES={
 'light':dict(ru='Лёгкие танки',en='Light Tanks',units=('light_armor',),prereq='basic_light_tank_chassis',icon='basic_light_tank_chassis',base={'breakthrough':.03},
  a=choice('Крейсерский рейд','Cruiser Raids',{'maximum_speed':.10,'breakthrough':.05,'armor_value':-.05},'Рейдовые эшелоны','Raiding Echelons',{'maximum_speed':.05,'breakthrough':.05,'fuel_consumption_factor':.05},'Облегчение защиты и маршевые тренировки дают скорость; глубокий рейд требует больше топлива.','Lighter protection and march training improve speed; deep raids need more fuel.'),
  b=choice('Поддержка пехоты','Infantry Support',{'soft_attack':.10,'defense':.05,'maximum_speed':-.05},'Штурмовые звенья','Assault Sections',{'soft_attack':.05,'defense':.05,'supply_consumption_factor':.03},'Тесная работа с пехотой улучшает огонь и защиту, но снижает темп и увеличивает снабжение.','Infantry cooperation improves firepower and defence but lowers tempo and increases supply demand.')),
 'medium':dict(ru='Средние танки',en='Medium Tanks',units=('medium_armor',),prereq='basic_medium_tank_chassis',icon='basic_medium_tank_chassis',base={'breakthrough':.03},
  a=choice('Маневренная группа','Manoeuvre Groups',{'maximum_speed':.08,'breakthrough':.10,'armor_value':-.05},'Управляемый прорыв','Coordinated Breakthrough',{'maximum_speed':.04,'breakthrough':.05,'fuel_consumption_factor':.05},'Радиосвязь и быстрые перестроения помогают развивать прорыв; защита уступает подвижности.','Radio coordination and rapid regrouping exploit breakthroughs, favouring mobility over protection.',modules=('hro_command_radio',)),
  b=choice('Лобовое превосходство','Frontal Superiority',{'armor_value':.10,'soft_attack':.08,'maximum_speed':-.05},'Огневой кулак','Armoured Firepower',{'armor_value':.05,'soft_attack':.04,'maximum_speed':-.02},'Защита и работа экипажа против полевых позиций повышают огонь ценой скорости.','Protection and crew drills against field positions increase firepower at a cost in speed.')),
 'heavy':dict(ru='Тяжёлые танки',en='Heavy Tanks',units=('heavy_armor',),prereq='basic_heavy_tank_chassis',icon='basic_heavy_tank_chassis',base={'armor_value':.03},
  a=choice('Танк прорыва','Breakthrough Tanks',{'breakthrough':.15,'soft_attack':.10,'maximum_speed':-.05},'Пролом обороны','Breach the Defences',{'breakthrough':.08,'soft_attack':.05,'fuel_consumption_factor':.05},'Тяжёлые машины сосредотачивают огонь и подавляют позиции; масса снижает скорость и увеличивает расход топлива.','Heavy vehicles concentrate fire against positions; their weight reduces speed and increases fuel demand.'),
  b=choice('Подвижная крепость','Mobile Fortresses',{'armor_value':.15,'defense':.10,'maximum_speed':-.08},'Броневой заслон','Armoured Barrier',{'armor_value':.08,'defense':.05,'supply_consumption_factor':.05},'Приоритет выживания и прикрытия флангов требует усиленной защиты и более тяжёлого снабжения.','Survival and flank protection demand stronger armour and heavier logistical support.',modules=('hro_applique_armor',))),
 'spg':dict(ru='Самоходная артиллерия',en='Self-Propelled Artillery',units=('light_sp_artillery_brigade','medium_sp_artillery_brigade','heavy_sp_artillery_brigade'),prereq='basic_medium_tank_chassis',icon='basic_medium_tank_chassis',base={'soft_attack':.03},
  a=choice('Штурмовая батарея','Assault Batteries',{'soft_attack':.15,'breakthrough':.05,'maximum_speed':-.05},'Орудия сопровождения','Assault Gun Groups',{'soft_attack':.08,'breakthrough':.03,'supply_consumption_factor':.05},'Прицельная поддержка переднего края усиливает огонь по пехоте, но требует больше боеприпасов.','Direct frontline support improves anti-infantry fire but consumes more ammunition.'),
  b=choice('Кочующий огонь','Shoot and Scoot',{'maximum_speed':.10,'defense':.10,'soft_attack':-.05},'Подвижные батареи','Mobile Batteries',{'maximum_speed':.05,'defense':.05,'fuel_consumption_factor':.05},'Частая смена позиций сохраняет батареи, но сокращает время огня и повышает расход топлива.','Frequent displacement protects batteries but reduces firing time and increases fuel use.')),
 'td':dict(ru='Противотанковые САУ',en='Tank Destroyers',units=('light_tank_destroyer_brigade','medium_tank_destroyer_brigade','heavy_tank_destroyer_brigade'),prereq='basic_medium_tank_chassis',icon='basic_heavy_tank_chassis',base={'ap_attack':.03},
  a=choice('Дальняя засада','Long-Range Ambush',{'hard_attack':.15,'ap_attack':.10,'soft_attack':-.05},'Прицельное поражение','Precision Tank Killing',{'hard_attack':.08,'ap_attack':.05,'maximum_speed':-.03},'Выбор позиции и дальномер помогают поражать броню; узкая специализация ослабляет борьбу с пехотой.','Position selection and rangefinding defeat armour; specialisation reduces anti-infantry effectiveness.',modules=('hro_optical_rangefinder',)),
  b=choice('Подвижный резерв ПТО','Mobile AT Reserve',{'maximum_speed':.10,'hard_attack':.08,'armor_value':-.05},'Охотничьи группы','Tank Hunter Groups',{'maximum_speed':.05,'hard_attack':.04,'fuel_consumption_factor':.05},'Быстрая переброска закрывает прорывы; облегчение машины снижает защиту.','Rapid movement closes breakthroughs; lighter vehicles sacrifice protection.',modules=('hro_protected_rack',))),
 'fighter':dict(ru='Истребители',en='Fighters',units=('fighter',),prereq='basic_small_airframe',icon='fighter1',base={'air_attack':.03},
  a=choice('Маневренный бой','Dogfighting',{'air_agility':.10,'maximum_speed':.05,'air_attack':-.05},'Школа воздушного боя','Advanced Dogfighting',{'air_agility':.05,'maximum_speed':.03,'air_range':-.03},'Облегчение вооружения и пилотаж улучшают манёвр ценой огневой мощи и дальности.','Lighter armament and pilot drills improve manoeuvrability at a cost in firepower and range.',capmodules=('hro_gyro_sight',)),
  b=choice('Высотный перехват','Altitude Interception',{'air_attack':.15,'air_range':.05,'air_agility':-.05},'Перехват эшелонами','Layered Interception',{'air_attack':.08,'air_range':.05,'air_agility':-.03},'Плотность огня и запас дальности помогают перехвату; дополнительное оснащение затрудняет манёвр.','Firepower and range support interception; additional equipment hinders manoeuvrability.')),
 'cas':dict(ru='Штурмовики',en='Close Air Support',units=('cas',),prereq='basic_small_airframe',icon='CAS1',base={'air_ground_attack':.03},
  a=choice('Удар по переднему краю','Frontline Strikes',{'air_ground_attack':.15,'air_defence':-.05},'Точное сопровождение','Precision Support',{'air_ground_attack':.08,'air_agility':-.03},'Сосредоточение на прицельном ударе повышает урон наземным целям, оставляя меньше возможностей для самозащиты.','Concentrating on accurate strikes increases ground damage but leaves fewer resources for self-defence.'),
  b=choice('Защищённый штурмовик','Protected Attack Aircraft',{'air_defence':.15,'air_range':-.05},'Возвращение экипажей','Bring the Crews Home',{'air_defence':.08,'air_ground_attack':.03,'maximum_speed':-.03},'Защита экипажа и жизненно важных узлов повышает живучесть ценой массы, скорости и дальности.','Protecting crews and vital components improves survival at a cost in weight, speed and range.',modules=('hro_cockpit_armor',))),
}
MODULES={
 'hro_command_radio':dict(ru='Командная радиосеть',en='Command Radio Network',category='tank_radio_module',gfx='tank_radio_2',dlc='No Step Back',add={'build_cost_ic':2,'breakthrough':2},mult={'breakthrough':.35,'defense':.30},reason='Настройка частот и связь экипажей улучшают управление прорывом; оснащение повышает стоимость.',reason_en='Frequency coordination and crew communication improve breakthrough control; equipment increases cost.'),
 'hro_applique_armor':dict(ru='Комплект навесной защиты',en='Applique Armour Kit',category='tank_special_module',gfx='sloped_armor',dlc='No Step Back',add={'build_cost_ic':2,'reliability':-.05},mult={'armor_value':.15,'maximum_speed':-.05},reason='Дополнительные броневые элементы усиливают защиту, но перегружают ходовую.',reason_en='Additional plates improve protection but strain the running gear.'),
 'hro_optical_rangefinder':dict(ru='Оптический дальномер',en='Optical Rangefinder',category='tank_special_module',gfx='stabilizer',dlc='No Step Back',add={'build_cost_ic':1.5,'ap_attack':5,'hard_attack':3},mult={'soft_attack':-.03},reason='Приборы и укладка для бронебойных боеприпасов улучшают огонь по броне ценой универсальности.',reason_en='Sighting equipment and armour-piercing ammunition arrangements improve anti-armour fire at a cost in versatility.'),
 'hro_protected_rack':dict(ru='Защищённая боеукладка',en='Protected Ammunition Racks',category='tank_special_module',gfx='wet_ammo_storage',dlc='No Step Back',add={'build_cost_ic':1.5,'reliability':.08},mult={'build_cost_ic':.05},reason='Разделение и защита укладки снижают потери от технических отказов, усложняя производство.',reason_en='Separated, protected storage improves reliability but complicates manufacture.'),
 'hro_gyro_sight':dict(ru='Гироскопический прицел',en='Gyroscopic Gunsight',category='plane_special_module_small',gfx='armor_plate_small',dlc='By Blood Alone',add={'build_cost_ic':1.5,'weight':1,'air_attack':2},mult={'air_agility':-.02},reason='Поправка на упреждение повышает результативность огня; прибор добавляет массу.',reason_en='Lead calculation improves fire effectiveness; the instrument adds weight.'),
 'hro_cockpit_armor':dict(ru='Защита кабины и маслосистемы',en='Cockpit and Oil-System Protection',category='plane_special_module_small',gfx='armor_plate_small',dlc='By Blood Alone',add={'build_cost_ic':2,'weight':2,'air_defence':5},mult={'air_range':-.05},reason='Прикрытие жизненно важных узлов повышает живучесть ценой массы и дальности.',reason_en='Protecting vital components improves survival at a cost in weight and range.'),
}
STAT_NAMES={
 'breakthrough':('Прорыв','Breakthrough'),'maximum_speed':('Скорость','Speed'),'armor_value':('Броня','Armour'),
 'soft_attack':('Противопехотная атака','Soft attack'),'hard_attack':('Противотанковая атака','Hard attack'),
 'ap_attack':('Бронепробитие','Piercing'),'defense':('Защита','Defence'),'fuel_consumption_factor':('Расход топлива','Fuel consumption'),
 'supply_consumption_factor':('Расход припасов','Supply consumption'),'air_attack':('Воздушная атака','Air attack'),
 'air_agility':('Манёвренность','Agility'),'air_range':('Дальность','Range'),'air_defence':('Воздушная защита','Air defence'),
 'air_ground_attack':('Атака наземных целей','Ground attack'),'build_cost_ic':('Стоимость производства','Production cost'),
 'reliability':('Надёжность','Reliability'),'weight':('Масса','Weight'),
}

def describe_stats(stats,lang,percentage=True):
 return '; '.join(STAT_NAMES[k][lang=='english']+': '+format(v*100 if percentage or k=='reliability' else v,'+g')+('%' if percentage else (' п.п.' if lang=='russian' else ' pp') if k=='reliability' else '') for k,v in stats.items())

def definitions():
 result=[]
 for key,b in BRANCHES.items():
  prefix='hro_design_'+key
  result.append(dict(id=prefix+'_base',branch=key,year=1938,pos=(0,0),parents=(b['prereq'],),children=(prefix+'_a',prefix+'_b'),stats=b['base'],ru={'light':'Школа лёгких танков','medium':'Школа средних танков','heavy':'Школа тяжёлых танков','spg':'Школа САУ','td':'Школа ПТ-САУ','fighter':'Школа истребителей','cas':'Школа штурмовиков'}[key],en=b['en']+': Foundations',reason='Испытания и обучение экипажей создают основу специализированной школы.',reason_en='Trials and crew training establish the foundation of a specialised school.',modules=()))
  for side,x in [('a',-.8),('b',.8)]:
   c=b[side];other='b' if side=='a' else 'a'
   result.append(dict(id=prefix+'_'+side,branch=key,year=1940,pos=(x,3.4),parents=(prefix+'_base',),children=(prefix+'_'+side+'2',),xor=prefix+'_'+other,stats=c['stats'],ru=c['ru'],en=c['en'],reason=c['reason'],reason_en=c['reason_en'],modules=c['modules']))
   result.append(dict(id=prefix+'_'+side+'2',branch=key,year=1943,pos=(x,6.8),parents=(prefix+'_'+side,),children=(),stats=c['capstats'],ru=c['capru'],en=c['capen'],reason=c['reason'],reason_en=c['reason_en'],modules=c['capmodules']))
 return result


def generate(output,put,text):
 techs=[];roots=[];icons={};unlocks={}
 for index,(key,b) in enumerate(BRANCHES.items()):
  roots.append(('hro_design_'+key+'_base',250,680+index*270))
  text('hro_design_row_'+key,b['ru'].upper(),b['en'].upper())
 for t in definitions():
  b=BRANCHES[t['branch']];identity=t['id'];x,y=t['pos']
  units={u:t['stats'] for u in b['units']}
  paths=' '.join(f'path = {{ leads_to_tech = {k} research_cost_coeff = 1 }}' for k in t['children'])
  xor=f'xor = {{ {t["xor"]} }}' if t.get('xor') else ''
  modules='enable_equipment_modules = { '+' '.join(t['modules'])+' }' if t['modules'] else ''
  for m in t['modules']:
   if m in unlocks:raise ValueError('Module is unlocked by two choices: '+m)
   unlocks[m]=identity
  techs.append(f'''{identity} = {{ allow_branch = {{ hro_supported_country = yes }} allow = {{ hro_supported_country = yes }}
   research_cost = { {1938: .8,1940:1,1943:1.2}[t['year']]} start_year = {t['year']}
   folder = {{ name = hro_front_folder position = {{ x = {x} y = {y} }} }}
   dependencies = {{ {' '.join(k+' = 1' for k in t['parents'])} }} {paths} {xor}
   categories = {{ hro_front_research {'air_equipment' if t['branch'] in ('fighter','cas') else 'armor'} }}
   ai_will_do = {{ factor = 1 }} {script(units)} {modules}
  }}''')
  names_ru=[MODULES[m]['ru'] for m in t['modules']];names_en=[MODULES[m]['en'] for m in t['modules']]
  suffix_ru=' Дополнительно открывает модули: '+', '.join(names_ru)+'.' if names_ru else ''
  suffix_en=' Also unlocks modules: '+', '.join(names_en)+'.' if names_en else ''
  text(identity,t['ru'],t['en'])
  text(identity+'_desc',t['reason']+' '+describe_stats(t['stats'],'russian')+'. Прибавки ступеней складываются. Эффект относится только к указанному типу батальона или авиакрыла; это не общий бонус всей армии.'+suffix_ru,t['reason_en']+' '+describe_stats(t['stats'],'english')+'. Stage increments stack. Effects apply only to the listed battalion or wing type, not the whole army.'+suffix_en)
  icons[identity]=b['icon']
 assert set(unlocks)==set(MODULES)
 for dlc,filename in [('No Step Back','tank'),('By Blood Alone','air')]:
  modules=[]
  for k,m in MODULES.items():
   if m['dlc']!=dlc:continue
   modules.append(f'{k} = {{ abbreviation = "HRO" category = {m["category"]} gfx = {m["gfx"]} sfx = sfx_ui_sd_module_turret xp_cost = 2 add_stats = {{ {script(m["add"])} }} multiply_stats = {{ {script(m["mult"])} }} }}')
   text(k,m['ru'],m['en'])
   text(k+'_desc',m['reason']+' '+describe_stats(m['add'],'russian',False)+'. Процентные модификаторы: '+describe_stats(m['mult'],'russian')+'. Устанавливается вручную в конструкторе; исследование не меняет готовые проекты.',m['reason_en']+' '+describe_stats(m['add'],'english',False)+'. Percentage modifiers: '+describe_stats(m['mult'],'english')+'. Install manually in the designer; research does not change existing designs.')
  put(f'common/units/equipment/modules/hro_{filename}_modules.txt','equipment_modules = { limit = { has_dlc = "'+dlc+'" }\n'+'\n'.join(modules)+'\n}')
 return techs,roots,icons,unlocks


def audit(output,game,schema_dir=None):
 """Validate native constructor categories, gfx fallbacks, stats and unlocks."""
 output=Path(output);game=Path(game);errors=[];native={};icons=set();slots=set()
 for p in (game/'common/units/equipment/modules').glob('*.txt'):
  for root in parse(p.read_text(encoding='utf-8-sig')):
   if root.key=='equipment_modules':native.update({n.key:n for n in root.value if n.key!='limit'})
 categories={n.scalar('category') for n in native.values()}
 for p in (game/'common/units/equipment').glob('*.txt'):
  for n in walk(parse(p.read_text(encoding='utf-8-sig'))):
   if n.key=='allowed_module_categories':
    slots.update(v.value for v in n.value if isinstance(v.value,str))
 for filename in ('tank_modules_icons.gfx','plane_modules_icons.gfx'):
  p=game/'interface'/filename
  if p.is_file():
   for n in walk(parse(p.read_text(encoding='utf-8-sig'))):
    if n.key and n.key.lower()=='spritetype':icons.add(n.scalar('name','').strip('"'))
 modules={n.key:n for p in (output/'common/units/equipment/modules').glob('hro*.txt') for r in parse(p.read_text()) for n in r.value if n.key!='limit'}
 if set(modules)!=set(MODULES):errors.append('Designer module manifest differs')
 techs={n.key:n for p in (output/'common/technologies').glob('hro*.txt') for r in parse(p.read_text()) for n in r.value}
 unlocked={}
 for k,t in techs.items():
  if enable:=t.one('enable_equipment_modules'):
   for m in enable.value:
    if m.value not in modules:errors.append('Unknown unlocked module: '+str(m.value))
    if m.value in unlocked:errors.append('Module unlocked twice: '+str(m.value))
    unlocked[m.value]=k
 if set(unlocked)!=set(modules):errors.append('A designer module has no research unlock')
 for k,m in modules.items():
  if m.scalar('category') not in categories:errors.append('Unknown native module category: '+str(m.scalar('category')))
  if m.scalar('category') not in slots:errors.append('Module category has no native constructor slot: '+str(m.scalar('category')))
  if 'GFX_EMI_'+m.scalar('gfx','') not in icons:errors.append('Module has no native icon fallback: '+k)
  add=m.one('add_stats');mult=m.one('multiply_stats')
  if add is None or float(add.scalar('build_cost_ic','0'))<=0:errors.append('New module must have positive production cost: '+k)
  for block in (add,mult):
   for stat in block.value:float(stat.value)
 if schema_dir:
  import re
  schema='\n'.join(p.read_text(encoding='utf-8-sig') for p in (Path(schema_dir)/'Config').rglob('*.cwt'))
  stats=set(re.findall(r'alias\[(?:unit_stat|air_stat|naval_stat):([A-Za-z_][A-Za-z0-9_]*)\]',schema))|{'weight','build_cost_ic','reliability','air_defence'}
  for k,m in modules.items():
   for block in ('add_stats','multiply_stats'):
    for stat in m.one(block).value:
     if stat.key not in stats:errors.append('Unknown module stat: '+k+'/'+stat.key)
 if errors:raise ValueError('\n'.join(errors))
 return dict(modules=len(modules),unique_research_unlocks=len(unlocked),native_categories_and_slots_checked=True,native_icon_fallbacks_checked=True,limits=audit_limits(output,game))


def module_limits(output,game):
 """Insert one-per-design limits into native archetypes with matching slots.
 Remove these exact blocks and every original token must remain identical.
 """
 output=Path(output);game=Path(game);patched={}
 for p in (game/'common/units/equipment').glob('*.txt'):
  source=p.read_text(encoding='utf-8-sig');changes=[];identities=[]
  for root in parse(source):
   if root.key!='equipments':continue
   for item in root.value:
    slots=[n for n in item.all('module_slots') if isinstance(n.value,list)]
    if not slots:continue
    categories={v.value for slot in slots for n in walk(slot.value) if n.key=='allowed_module_categories' for v in n.value if isinstance(v.value,str)}
    applicable=[k for k,m in MODULES.items() if m['category'] in categories]
    if not applicable:continue
    blocks=' '.join(f'module_count_limit = {{ module = {k} count < 2 }}' for k in applicable)
    changes.append((item.value_end-1,item.value_end-1,' '+blocks+' '));identities.append(item.key)
  if changes:
   target=output/'common/units/equipment'/p.name;target.parent.mkdir(parents=True,exist_ok=True)
   target.write_text(edit(source,changes));patched[p.name]=identities
 return patched


def audit_limits(output,game):
 output=Path(output);game=Path(game);count=0;files=0
 def signature(nodes):
  return [(n.key,n.op,signature(n.value) if isinstance(n.value,list) else n.value) for n in nodes if not (n.key=='module_count_limit' and n.scalar('module') in MODULES)]
 for p in (output/'common/units/equipment').glob('*.txt'):
  original=game/'common/units/equipment'/p.name
  if not original.is_file():raise ValueError('Unknown constructor base: '+p.name)
  actual=parse(p.read_text());native=parse(original.read_text(encoding='utf-8-sig'))
  if signature(actual)!=signature(native):raise ValueError('Native constructor changed beyond module limits: '+p.name)
  for root in actual:
   if root.key!='equipments':continue
   for item in root.value:
    slots=[n for n in item.all('module_slots') if isinstance(n.value,list)]
    if not slots:continue
    categories={v.value for slot in slots for n in walk(slot.value) if n.key=='allowed_module_categories' for v in n.value if isinstance(v.value,str)}
    for k,m in MODULES.items():
     if m['category'] not in categories:continue
     limits=[n for n in item.all('module_count_limit') if n.scalar('module')==k]
     if len(limits)!=1 or limits[0].one('count').op!='<' or limits[0].scalar('count')!='2':raise ValueError('Missing one-per-design limit: '+item.key+'/'+k)
     count+=1
  files+=1
 if not files:raise ValueError('No constructor limits were emitted')
 return dict(native_files=files,one_per_design_limits=count,all_original_fields_preserved=True)


def preview(output):
 """Standalone layout diagram based on the exact emitted grid coordinates.
 This is a review diagram, never represented as an in-game screenshot.
 """
 from html import escape
 import textwrap
 output=Path(output);items=['<svg xmlns="http://www.w3.org/2000/svg" width="1160" height="2500" viewBox="0 0 1160 2500">','<rect width="1160" height="2500" fill="#171c20"/>','<defs><marker id="arrow" markerWidth="9" markerHeight="9" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#c2ae70"/></marker></defs>']
 def text(x,y,value,size=17,color='#e9e6d8'):
  items.append(f'<text x="{x}" y="{y}" fill="{color}" font-family="DejaVu Sans, sans-serif" font-size="{size}">{escape(value)}</text>')
 def card(x,y,name,year):
  items.append(f'<rect x="{x}" y="{y}" width="183" height="96" rx="7" fill="#343a3b" stroke="#b5a06b" stroke-width="2"/>')
  for i,line in enumerate(textwrap.wrap(name,width=18)[:2]):text(x+9,y+24+i*21,line,15)
  text(x+9,y+80,str(year),14,'#d4bb75')
 def arrow(x,y,xx,yy):items.append(f'<path d="M{x},{y} L{xx},{yy}" fill="none" stroke="#c2ae70" stroke-width="2" marker-end="url(#arrow)"/>')
 text(30,40,'ШКОЛЫ БОЯ И ТЕХНИКИ',24)
 text(30,80,'Схема расположения из файлов мода; это не снимок игрового интерфейса.',16)
 text(30,140,'ШКОЛЫ БОЯ: ОДИН ВЫБОР В КАЖДОЙ ПАРЕ',20)
 for x,y,name in [(194,203,'Штурм городов'),(534,203,'Лесная война'),(194,363,'Форсирование рек'),(534,363,'Дальние марши')]:card(x,y,name,'Выбор школы')
 text(407,260,'ИЛИ',17,'#d59081');text(407,420,'ИЛИ',17,'#d59081')
 text(30,535,'РАЗВИТИЕ ТЕХНИКИ',22)
 for x,title in [(194,'1938 — ОСНОВЫ'),(534,'1940 — ВЫБОР'),(874,'1943 — РАЗВИТИЕ')]:text(x,580,title,16)
 lookup={t['id']:t for t in definitions()}
 for index,(key,b) in enumerate(BRANCHES.items()):
  y=680+index*270-7;prefix='hro_design_'+key
  for i,line in enumerate(textwrap.wrap(b['ru'].upper(),width=15)):text(20,y+35+i*22,line,15)
  card(194,y,lookup[prefix+'_base']['ru'],1938)
  for side,offset in [('a',-80),('b',80)]:
   t=lookup[prefix+'_'+side];cap=lookup[prefix+'_'+side+'2']
   card(534,y+offset,t['ru'],1940);card(874,y+offset,cap['ru'],1943)
   arrow(382,y+48,526,y+offset+48);arrow(722,y+offset+48,866,y+offset+48)
  text(600,y+52,'ИЛИ',15,'#d59081')
 items.append('</svg>');p=output/'preview/research.svg';p.parent.mkdir(parents=True,exist_ok=True);p.write_text('\n'.join(items))
