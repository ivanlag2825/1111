"""Thirty original constructor modules and nine mutually exclusive programmes."""
FOLDER='hro_module_folder'
MODULES={}
def module(key,ru,en,category,gfx,add,mult,reason,reason_en,extras=''):
 MODULES['hro_'+key]=dict(ru=ru,en=en,category=category,gfx=gfx,dlc='By Blood Alone' if category.startswith(('plane_','fighter_')) else 'No Step Back',add=add,mult=mult,reason=reason,reason_en=reason_en,extras=extras)
# Four alternatives/upgrades per long programme; two per short programme.
module('face_hardened','Цементированные листы','Face-Hardened Plates','tank_armor_type','tank_cast_armor',{'build_cost_ic':2,'defense':3,'breakthrough':2,'reliability':-.04},{'armor_value':.42},'Твёрдый поверхностный слой усиливает защиту, но усложняет изготовление и ремонт.','A hard surface improves protection but complicates manufacture and repair.')
module('homogeneous','Гомогенная сварная броня','Homogeneous Welded Armour','tank_armor_type','tank_welded_armor',{'build_cost_ic':1.5,'defense':2,'breakthrough':3,'reliability':.05},{'armor_value':.32},'Однородные листы и технологичные соединения облегчают обслуживание при умеренной защите.','Uniform plates and practical joints simplify maintenance with moderate protection.')
module('spaced_screens','Разнесённые экраны','Spaced Armour Screens','tank_special_module','armor_skirts',{'build_cost_ic':1.5,'reliability':-.03},{'armor_value':.16,'maximum_speed':-.04},'Дополнительные экраны повышают эффективную защиту, добавляя массу.','Extra screens improve effective protection but add weight.')
module('reinforced_plate','Усиленный лобовой пакет','Reinforced Frontal Package','tank_special_module','sloped_armor',{'build_cost_ic':2.5,'defense':3},{'armor_value':.24,'maximum_speed':-.08},'Утолщение фронтальной зоны повышает защиту ценой темпа и цены.','Thicker frontal protection trades speed and cost for armour.')
module('long_travel','Длинноходная подвеска','Long-Travel Suspension','tank_suspension_type','tank_christie_suspension',{'build_cost_ic':1.5,'reliability':-.03},{'maximum_speed':.25},'Ходовая для быстрых маршей требует более тщательного ухода.','A fast-march running gear requires closer maintenance.')
module('rugged_torsion','Усиленные торсионы','Reinforced Torsion Bars','tank_suspension_type','tank_torsion_bar_suspension',{'build_cost_ic':1.8,'reliability':.20},{'maximum_speed':-.04},'Запас прочности снижает технические отказы ценой массы.','Structural reserve reduces mechanical failures at a cost in weight.')
module('field_tracks','Сменные траки и катки','Replaceable Tracks and Wheels','tank_special_module','easy_maintenance',{'build_cost_ic':1.2,'reliability':.08},{'maximum_speed':.04,'build_cost_ic':.04},'Сменные элементы ходовой упрощают полевой ремонт, усложняя комплектацию.','Replaceable running-gear parts aid field repair but complicate manufacture.')
module('wide_tracks','Широкие гусеницы','Wide Tracks','tank_special_module','dozer_blade',{'build_cost_ic':1.5,'reliability':.05},{'maximum_speed':.06,'fuel_consumption':.05},'Уменьшенное давление на грунт улучшает подвижность ценой расхода топлива.','Lower ground pressure improves mobility at a cost in fuel.')
module('boosted_petrol','Форсированный бензиновый','Boosted Petrol Engine','tank_engine_type','tank_gasoline_engine',{'build_cost_ic':2,'fuel_consumption':2.5,'maximum_speed':.5,'reliability':-.08},{'maximum_speed':.25},'Форсировка даёт темп, но нагружает двигатель и снабжение.','Boosting improves tempo but strains the engine and supply.')
module('economy_diesel','Экономичный дизель','Economical Diesel','tank_engine_type','tank_diesel_engine',{'build_cost_ic':2,'fuel_consumption':1.6,'reliability':.20},{'maximum_speed':-.03},'Умеренный режим работы экономит топливо и повышает надёжность.','Moderate output saves fuel and improves reliability.')
module('improved_cooling','Усиленное охлаждение','Improved Cooling','tank_special_module','easy_maintenance',{'build_cost_ic':1.5,'reliability':.10},{'maximum_speed':.05,'build_cost_ic':.03},'Радиаторы позволяют дольше сохранять рабочий режим двигателя.','Better cooling sustains engine output for longer.')
module('fuel_metering','Точная подача топлива','Precision Fuel Metering','tank_special_module','expanded_fuel_tank',{'build_cost_ic':1.8},{'fuel_consumption':-.12,'maximum_speed':-.03},'Регулировка смеси экономит топливо ценой пиковой мощности.','Mixture regulation saves fuel at a cost in peak output.')
module('spall_liner','Противоосколочный подбой','Spall Liner','tank_special_module','wet_ammo_storage',{'build_cost_ic':1.5,'defense':3,'reliability':.04},{'build_cost_ic':.04},'Внутренняя защита снижает последствия повреждений, усложняя корпус.','Internal protection limits damage consequences but complicates the hull.')
module('fire_suppression','Автоматическое пожаротушение','Automatic Fire Suppression','tank_special_module','wet_ammo_storage',{'build_cost_ic':2,'reliability':.10},{'maximum_speed':-.02},'Противопожарное оснащение повышает эксплуатационную живучесть и массу.','Fire protection improves operational survival but adds weight.')
module('roof_armor','Усиленная крыша','Reinforced Roof Armour','tank_special_module','armor_skirts',{'build_cost_ic':1.7,'defense':4},{'armor_value':.12,'maximum_speed':-.04},'Дополнительное прикрытие сверху повышает защиту ценой массы.','Extra overhead protection trades weight for defence.')
module('separated_stowage','Секционированная укладка','Compartmented Stowage','tank_special_module','extra_ammo_storage',{'build_cost_ic':1.8,'reliability':.12},{'soft_attack':-.03,'hard_attack':-.03},'Безопасное размещение запасов снижает доступный темп подачи боеприпасов.','Safer stowage reduces the immediate ammunition feed rate.')
module('supercharged_motor','Мотор с нагнетателем','Supercharged Engine','plane_engine_type','engine_3_1x',{'build_cost_ic':18,'thrust':27,'fuel_consumption':.20},{'maximum_speed':.32},'Высотный наддув даёт мощность и требует больше топлива.','Altitude boosting provides power and demands more fuel.')
module('cruise_motor','Мотор крейсерского режима','Cruise-Tuned Engine','plane_engine_type','engine_3_1x',{'build_cost_ic':17,'thrust':24,'fuel_consumption':.13},{'maximum_speed':.24,'air_range':.08},'Экономичный режим расширяет радиус ценой скорости.','Economical tuning extends range at a cost in speed.')
module('emergency_boost','Система аварийного форсажа','Emergency Boost System','plane_special_module_small','engine_3_1x',{'build_cost_ic':2,'weight':1},{'maximum_speed':.08,'fuel_consumption':.12,'air_range':-.05},'Кратковременный избыток мощности повышает скорость ценой топлива.','Short bursts of excess power trade fuel for speed.')
module('aero_cowling','Обтекаемый капот','Streamlined Cowling','plane_special_module_small','non_strategic_materials_small',{'build_cost_ic':1.8,'weight':1},{'maximum_speed':.05,'air_range':.05},'Снижение сопротивления требует более сложного изготовления.','Reduced drag requires more elaborate manufacture.')
module('light_cockpit','Облегчённая бронекабина','Light Armoured Cockpit','plane_special_module_small','armor_plate_small',{'build_cost_ic':1.5,'weight':1,'air_defence':3},{'air_agility':-.02},'Локальная защита сохраняет часть подвижности, но не даёт полной защиты.','Local protection retains mobility without providing full coverage.')
module('sealed_cells','Протектированные топливные ячейки','Self-Sealing Fuel Cells','plane_special_module_small','self_sealing_fuel_tanks_small',{'build_cost_ic':2,'weight':1,'air_defence':5},{'air_range':-.05},'Защита баков уменьшает потери от повреждений, сокращая полезный запас топлива.','Protected tanks limit damage losses but reduce usable fuel space.')
module('armored_oil','Бронированный маслорадиатор','Armoured Oil Cooler','plane_special_module_small','armor_plate_small',{'build_cost_ic':2,'weight':2,'air_defence':6},{'maximum_speed':-.03},'Защита уязвимого узла повышает живучесть ценой массы и сопротивления.','Protecting a vulnerable component adds weight and drag.')
module('drop_tank_system','Усиленная система подвесных баков','Improved Drop-Tank System','plane_special_module_small','drop_tanks',{'build_cost_ic':2,'weight':1},{'air_range':.30,'air_agility':-.04},'Дополнительный запас топлива расширяет радиус, пока подвески ухудшают манёвр.','Extra fuel extends range while external fittings hinder manoeuvring.')
module('high_velocity_75','Длинноствольная 75-мм','Long-Barrel 75 mm','tank_medium_main_armament','tank_medium_cannon_2',{'build_cost_ic':5,'soft_attack':25,'hard_attack':26,'ap_attack':100,'breakthrough':3,'maximum_speed':-.3,'reliability':-.12},{},'Длинный ствол и бронебойные боеприпасы повышают борьбу с бронёй ценой универсальности.','A long barrel and armour-piercing ammunition favour anti-armour fire.',extras='allow_equipment_type = anti_tank build_cost_resources = { tungsten = 1 steel = 2 }')
module('support_75','75-мм орудие поддержки','75 mm Support Gun','tank_medium_main_armament','tank_medium_cannon',{'build_cost_ic':4,'soft_attack':36,'hard_attack':13,'ap_attack':55,'breakthrough':5,'reliability':-.06},{},'Фугасный снаряд и скорострельность приоритетны перед бронепробитием.','Explosive shells and rate of fire take priority over penetration.',extras='allow_equipment_type = anti_tank build_cost_resources = { steel = 2 }')
module('rapid_mg_pack','Скорострельная пулемётная батарея','Rapid-Fire MG Battery','fighter_weapon','heavy_mg_4x',{'build_cost_ic':4,'weight':4,'air_attack':17},{'air_agility':.02},'Лёгкая батарея сохраняет манёвр ценой силы попадания.','A lighter battery retains manoeuvrability at a cost in hitting power.',extras='add_equipment_type = { fighter heavy_fighter } allow_mission_type = { air_superiority interception }')
module('cannon_pack','Спаренная 20-мм батарея','Twin 20 mm Battery','fighter_weapon','aircraft_cannon_1_2x',{'build_cost_ic':6,'weight':7,'air_attack':25},{'air_agility':-.05},'Тяжёлая батарея повышает огневую мощь, нагружая планер.','A heavy battery increases firepower but burdens the airframe.',extras='add_equipment_type = { fighter heavy_fighter } allow_mission_type = { air_superiority interception }')
module('field_tools','Бортовой ремонтный комплект','Onboard Repair Tools','tank_special_module','easy_maintenance',{'build_cost_ic':1,'reliability':.08},{'maximum_speed':-.02},'Комплект инструмента сокращает простои, занимая объём машины.','Onboard tools reduce downtime but occupy vehicle space.')
module('extended_fuel','Маршевый регулятор двигателя','March Engine Governor','tank_special_module','expanded_fuel_tank',{'build_cost_ic':1.5,'reliability':-.03},{'fuel_consumption':-.08,'maximum_speed':-.03},'Ограничение пиковых оборотов экономит топливо, снижая максимальную скорость.','Limiting peak engine revolutions saves fuel and reduces top speed.')
module('long_88','Длинноствольная 88-мм','Long-Barrel 88 mm','tank_medium_main_armament','tank_medium_cannon_2',{'build_cost_ic':7,'soft_attack':32,'hard_attack':38,'ap_attack':140,'breakthrough':4,'maximum_speed':-.4,'reliability':-.14},{},'Длинный ствол увеличивает пробитие; тяжёлый боекомплект замедляет машину.','A long barrel improves penetration; heavy ammunition slows the vehicle.',extras='allow_equipment_type = anti_tank build_cost_resources = { tungsten = 2 steel = 2 }')
module('support_105','105-мм штурмовое орудие','105 mm Assault Gun','tank_medium_main_armament','tank_medium_cannon',{'build_cost_ic':6.5,'soft_attack':55,'hard_attack':18,'ap_attack':65,'breakthrough':8,'maximum_speed':-.4,'reliability':-.10},{},'Мощный фугасный снаряд поддерживает штурм; бронепробитие вторично.','A powerful explosive shell supports assaults; penetration is secondary.',extras='allow_equipment_type = anti_tank build_cost_resources = { tungsten = 1 steel = 2 }')
module('precision_88','88-мм: прицельный бронебойный огонь','88 mm Precision AP Fire','tank_medium_main_armament','tank_medium_cannon_2',{'build_cost_ic':8.5,'soft_attack':36,'hard_attack':48,'ap_attack':165,'breakthrough':5,'maximum_speed':-.5,'reliability':-.16},{},'Согласованные прицелы и бронебойные боеприпасы усиливают поражение тяжёлой брони.','Matched sights and armour-piercing ammunition improve heavy-armour defeat.',extras='allow_equipment_type = anti_tank build_cost_resources = { tungsten = 2 steel = 3 }')
module('blast_105','105-мм: усиленный фугас','105 mm Heavy HE','tank_medium_main_armament','tank_medium_cannon',{'build_cost_ic':8,'soft_attack':70,'hard_attack':22,'ap_attack':80,'breakthrough':10,'maximum_speed':-.6,'reliability':-.14},{},'Усиленная фугасная программа увеличивает огневую мощь ценой массы, производства и надёжности.','Heavy HE ammunition raises firepower at a cost in mass, production and reliability.',extras='allow_equipment_type = anti_tank build_cost_resources = { tungsten = 1 steel = 3 }')
assert len(MODULES)==34

def programme(ru,en,prereq,icon,a,b,a2=None,b2=None):return dict(ru=ru,en=en,prereq=prereq,icon=icon,a=a,b=b,a2=a2,b2=b2)
PROGRAMMES={
 'armor':programme('Бронекорпуса','Armour Construction','basic_medium_tank_chassis','basic_heavy_tank_chassis','hro_face_hardened','hro_homogeneous','hro_spaced_screens','hro_reinforced_plate'),
 'suspension':programme('Ходовая часть','Running Gear','basic_light_tank_chassis','basic_light_tank_chassis','hro_long_travel','hro_rugged_torsion','hro_field_tracks','hro_wide_tracks'),
 'engine':programme('Танковые двигатели','Tank Engines','basic_medium_tank_chassis','basic_medium_tank_chassis','hro_boosted_petrol','hro_economy_diesel','hro_improved_cooling','hro_fuel_metering'),
 'protection':programme('Живучесть танка','Tank Survival','basic_medium_tank_chassis','basic_heavy_tank_chassis','hro_spall_liner','hro_fire_suppression','hro_roof_armor','hro_separated_stowage'),
 'airengine':programme('Авиационные моторы','Aero Engines','basic_small_airframe','fighter1','hro_supercharged_motor','hro_cruise_motor','hro_emergency_boost','hro_aero_cowling'),
 'airsurvival':programme('Живучесть самолёта','Aircraft Survival','basic_small_airframe','CAS1','hro_light_cockpit','hro_sealed_cells','hro_armored_oil','hro_drop_tank_system'),
 'cannon':programme('Танковое вооружение','Tank Armament','basic_medium_tank_chassis','basic_medium_tank_chassis','hro_high_velocity_75','hro_support_75','hro_long_88','hro_support_105'),
 'airgun':programme('Авиационное вооружение','Aircraft Armament','basic_small_airframe','fighter1','hro_rapid_mg_pack','hro_cannon_pack'),
 'service':programme('Походное оснащение','March Equipment','basic_light_tank_chassis','tech_logistics_company','hro_field_tools','hro_extended_fuel'),
}

def definitions():
 result=[]
 for key,p in PROGRAMMES.items():
  prefix='hro_modtech_'+key
  result.append(dict(id=prefix+'_base',year=1936,pos=(0,0),parent=p['prereq'],children=(prefix+'_a',prefix+'_b'),modules=(),ru=p['ru'],en=p['en'],icon=p['icon'],row=key))
  for side,x in [('a',-1),('b',1)]:
   m=MODULES[p[side]];other='b' if side=='a' else 'a';child=prefix+'_'+side+'2' if p[side+'2'] else None
   result.append(dict(id=prefix+'_'+side,year=1938,pos=(x,3),parent=prefix+'_base',children=(child,) if child else (),xor=prefix+'_'+other,modules=(p[side],),ru=m['ru'],en=m['en'],icon=p['icon'],row=key))
   if child:
    m=MODULES[p[side+'2']]
    result.append(dict(id=child,year=1940,pos=(x,6),parent=prefix+'_'+side,children=(),modules=(p[side+'2'],),ru=m['ru'],en=m['en'],icon=p['icon'],row=key))
 # Four new technologies extend the two existing 75-mm choices.
 for side,module in [('a','hro_precision_88'),('b','hro_blast_105')]:
  parent=next(t for t in result if t['id']=='hro_modtech_cannon_'+side+'2');parent['year']=1939;child='hro_modtech_cannon_'+side+'3';parent['children']=(child,)
  m=MODULES[module];result.append(dict(id=child,year=1940,pos=(-1 if side=='a' else 1,9),parent=parent['id'],children=(),modules=(module,),ru=m['ru'],en=m['en'],icon='basic_medium_tank_chassis',row='cannon'))
 return result

def generate(put,text,format_stats):
 from generate_frontier import script
 techs=[];roots=[];icons={};unlocks={}
 text(FOLDER,'Конструкторские программы','Constructor Programmes')
 text(FOLDER+'_desc','Броня, двигатели, вооружение и оснащение. Выберите одну линию каждого проекта.','Armour, engines, weapons and equipment. Choose one line per programme.')
 for index,(key,p) in enumerate(PROGRAMMES.items()):
  roots.append(('hro_modtech_'+key+'_base',250,360+index*320))
  text('hro_mod_row_'+key,p['ru'].upper(),p['en'].upper())
 for t in definitions():
  x,y=t['pos'];identity=t['id'];mods=' '.join(t['modules']);paths=' '.join('path = { leads_to_tech = '+k+' research_cost_coeff = 1 }' for k in t['children'])
  xor='xor = { '+t['xor']+' }' if t.get('xor') else ''
  techs.append(f'{identity} = {{ allow_branch = {{ hro_supported_country = yes }} allow = {{ hro_supported_country = yes }} research_cost = { {1936:.4,1938:.55,1939:.7,1940:.7}[t["year"]]} start_year = {t["year"]} folder = {{ name = {FOLDER} position = {{ x = {x} y = {y} }} }} dependencies = {{ {t["parent"]} = 1 }} {paths} {xor} categories = {{ hro_front_research }} '+('enable_equipment_modules = { '+mods+' }' if mods else '')+' }')
  text(identity,t['ru'],t['en'])
  desc_ru='Основы программы: открывает выбор двух несовместимых направлений. Само по себе не даёт боевых бонусов.';desc_en='Programme foundations: opens two mutually exclusive paths. Does not itself grant combat bonuses.'
  if t['modules']:
   m=MODULES[t['modules'][0]];desc_ru=m['reason']+' Открывает модуль «'+m['ru']+'». Плоские прибавки: '+format_stats(m['add'],'russian',False)+'. '+('Процентные модификаторы: '+format_stats(m['mult'],'russian')+'. ' if m['mult'] else '')+'Требуется установка в конструкторе.';desc_en=m['reason_en']+' Unlocks '+m['en']+'. Flat additions: '+format_stats(m['add'],'english',False)+'. '+('Percentage modifiers: '+format_stats(m['mult'],'english')+'. ' if m['mult'] else '')+'Install it in the designer.'
  text(identity+'_desc',desc_ru,desc_en)
  icons[identity]=t['icon']
  for m in t['modules']:unlocks[m]=identity
 return techs,roots,icons,unlocks


def preview(output):
 from pathlib import Path
 from html import escape
 import textwrap
 out=['<svg xmlns="http://www.w3.org/2000/svg" width="1460" height="3200" viewBox="0 0 1460 3200">','<rect width="1460" height="3200" fill="#171c20"/>']
 def text(x,y,value,size=15):out.append(f'<text x="{x}" y="{y}" fill="#eee9d8" font-family="DejaVu Sans, sans-serif" font-size="{size}">{escape(value)}</text>')
 def card(x,y,name,year):
  out.append(f'<rect x="{x}" y="{y}" width="183" height="96" rx="7" fill="#343a3b" stroke="#b5a06b" stroke-width="2"/>')
  for i,line in enumerate(textwrap.wrap(name,18)[:2]):text(x+7,y+23+i*20,line)
  text(x+7,y+80,str(year),14)
 def line(x,y,xx,yy):out.append(f'<path d="M{x},{y} L{xx},{yy}" fill="none" stroke="#c2ae70" stroke-width="2"/>')
 text(30,45,'КОНСТРУКТОРСКИЕ ПРОГРАММЫ',24)
 text(30,80,'Схема размещения, не скриншот игры. Каждая ветка открывает новые модули.',16)
 for x,title in [(194,'1936 — ПРОГРАММА'),(494,'1938 — ВЫБОР'),(794,'1940 — РАЗВИТИЕ')]:text(x,235,title)
 for i,(key,p) in enumerate(PROGRAMMES.items()):
  y=360+i*320-7
  for j,title in enumerate(textwrap.wrap(p['ru'].upper(),15)):text(20,y+35+j*22,title)
  card(194,y,p['ru'],1936)
  for side,delta in [('a',-100),('b',100)]:
   m=MODULES[p[side]];card(494,y+delta,m['ru'],1938);line(380,y+48,490,y+delta+48)
   if p[side+'2']:
    cap=MODULES[p[side+'2']];card(794,y+delta,cap['ru'],1939 if key=='cannon' else 1940);line(680,y+delta+48,790,y+delta+48)
    if key=='cannon':
     final=MODULES['hro_precision_88' if side=='a' else 'hro_blast_105'];card(1094,y+delta,final['ru'],1940);line(980,y+delta+48,1090,y+delta+48)
  text(555,y+53,'ИЛИ')
 out.append('</svg>');path=Path(output)/'preview/module_programmes.svg';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('\n'.join(out))
