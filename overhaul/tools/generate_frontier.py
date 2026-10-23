"""Front schools, finite industrial programmes and paid operational reserves.

Original implementation; schools use normal research slots since version 1.5.
Vanilla 1.19.3 supplies unit IDs and scripting examples; no RT56 assets are shipped.
"""
from pathlib import Path
import json
from decision_details import describe

ARMOUR = ('medium_tank_chassis','heavy_tank_chassis','medium_tank_destroyer_chassis','heavy_tank_destroyer_chassis')
AIR = ('small_plane_airframe','small_plane_cas_airframe')
SUPPLIES = ('infantry_equipment','artillery_equipment','motorized_equipment','support_equipment')
SCHOOLS = {
 'urban': ('Школа штурма городов','Urban Assault School',
   {'infantry':{'urban':{'attack':.20}},'engineer':{'urban':{'attack':.20},'fort':{'attack':.15}}},
   'Пехота: атака в городе +20%. Сапёры: атака в городе +20%, против укреплений +15%.',
   'Infantry: urban attack +20%. Engineers: urban attack +20%, fort attack +15%.'),
 'forest': ('Школа лесной войны','Forest Warfare School',
   {'infantry':{'forest':{'defence':.20,'movement':.15}}},
   'Пехота: защита в лесу +20%, передвижение в лесу +15%.',
   'Infantry: forest defence +20%, forest movement +15%.'),
 'river': ('Школа форсирования рек','River Crossing School',
   {'infantry':{'river':{'attack':.15}},'engineer':{'river':{'attack':.20,'movement':.15}}},
   'Пехота: атака через реку +15%. Сапёры: атака через реку +20%, передвижение через реки +15%.',
   'Infantry: river attack +15%. Engineers: river attack +20%, river movement +15%.'),
 'mobile': ('Школа дальних маршей','Long-Range March School',
   {'motorized':{'maximum_speed':.05},'mechanized':{'maximum_speed':.05},'logistics_company':{'supply_consumption_factor':-.10,'fuel_consumption_factor':-.10}},
   'Моторизованные и механизированные батальоны: скорость +5%. Рота снабжения: дополнительное снижение расхода припасов и топлива на 10%.',
   'Motorized and mechanized battalions: speed +5%. Logistics company: additional supply and fuel consumption reductions of 10%.'),
}
PROGRAMMES = {
 'armour': ('Приоритет бронетанкового производства','Armour Production Priority',
             {**{k:{'build_cost_ic':-.15} for k in ARMOUR},**{k:{'build_cost_ic':.10} for k in AIR}},
             'Средние и тяжёлые танки и ПТ-варианты: стоимость −15%; лёгкие истребители и штурмовики: стоимость +10%.',
             'Medium/heavy tanks and tank destroyers: cost −15%; small fighters and CAS: cost +10%.'),
 'air': ('Приоритет авиастроения','Aircraft Production Priority',
             {**{k:{'build_cost_ic':-.15} for k in AIR},**{k:{'build_cost_ic':.10} for k in ARMOUR}},
             'Лёгкие истребители и штурмовики: стоимость −15%; средние и тяжёлые танки и ПТ-варианты: стоимость +10%.',
             'Small fighters and CAS: cost −15%; medium/heavy tanks and tank destroyers: cost +10%.'),
 'supply': ('Вооружение массовой армии','Equipment for a Mass Army',
             {**{k:{'build_cost_ic':-.12} for k in SUPPLIES},**{k:{'build_cost_ic':.05} for k in ARMOUR+AIR}},
             'Пехотное оружие, буксируемая артиллерия, грузовики и оснащение: стоимость −12%; указанные танки и самолёты: стоимость +5%.',
             'Infantry weapons, towed artillery, trucks and support equipment: cost −12%; listed tanks and aircraft: cost +5%.'),
}
GER_ACTIONS = {
 'motor_march':('Маршевые маршруты танковых групп','Panzer Group March Routes',70,30,{'army_speed_factor':.15,'supply_consumption_factor':.20},{}),
 'fighter_sweep':('Свободная охота истребителей','Fighter Sweeps',80,45,{'air_fuel_consumption_factor':.20},{'small_plane_airframe':{'air_attack':.15}}),
 'cas_surge':('Штурмовики над направлением прорыва','CAS over the Breakthrough',80,45,{'air_cas_efficiency':.20,'air_fuel_consumption_factor':.25},{'small_plane_cas_airframe':{'air_ground_attack':.15}}),
 'supply_discipline':('Приоритет фронтовых перевозок','Front Transport Priority',65,45,{'supply_consumption_factor':-.15,'industrial_capacity_factory':-.05},{}),
 'repair_columns':('Дополнительные ремонтные колонны','Additional Repair Columns',65,60,{'attrition':-.10,'truck_attrition_factor':-.20,'industrial_capacity_factory':-.05},{}),
}
# Choices describe historical developments, not fictional victories in the save.
HISTORY = [
 dict(key='welding',tag='SOV',date='1942.1.1',name=('Автоматическая сварка бронекорпусов','Automatic Welding of Armour Hulls'),
      desc=('Разработки коллектива Е. О. Патона помогли внедрить автоматическую сварку при выпуске советских танков. В нашей программе нужно выбрать: внедрять новую технологию сейчас или временно направить специалистов в ремонтные службы.',
            'E. O. Paton’s team helped introduce automatic welding in Soviet tank production. Our programme must choose between adopting the process now and temporarily assigning specialists to repair services.'),
      options=[('Внедрить сварку на серийных линиях','Introduce Welding on Serial Lines',{'production_factory_efficiency_gain_factor':.15,'industrial_capacity_factory':.05},180),
               ('Усилить ремонтные службы','Reinforce Repair Services',{'attrition':-.10,'army_org_regain':.15},180)]),
 dict(key='locomotives',tag='GER',date='1942.9.1',name=('Программа военных паровозов','The War Locomotive Programme'),
      desc=('В 1942 году начался выпуск упрощённых военных паровозов серии 52. Стандартизация позволяет сосредоточить усилия на восстановлении путей или на эксплуатации существующей сети. Выбранная программа действует ограниченное время.',
            'Production of simplified Class 52 war locomotives began in 1942. Standardisation lets us prioritise railway reconstruction or use of the existing network. The chosen programme has a finite duration.'),
      options=[('Восстанавливать пути вслед за фронтом','Rebuild Railways Behind the Front',{'production_speed_rail_way_factor':.40,'industry_repair_factor':.20},180),
               ('Наладить оборот составов','Improve Train Turnaround',{'supply_consumption_factor':-.10,'army_fuel_consumption_factor':-.10},180)]),
 dict(key='donations',tag='SOV',date='1942.12.15',name=('Самолёты на народные средства','Aircraft Funded by Public Donations'),
      desc=('В декабре 1942 года пожертвование Ферапонта Головатого на боевой самолёт стало известным примером помощи фронту. Предлагается поддержать подготовку экипажей или организовать дополнительную смену на предприятиях. Готовые самолёты из воздуха не появляются.',
            'In December 1942, Ferapont Golovaty’s donation for a combat aircraft became a well-known example of civilian support. We can support aircrew training or arrange an additional factory shift. No aircraft are spawned.'),
      options=[('Подготовить экипажи для новых машин','Train Crews for the New Aircraft',{'experience_gain_air_factor':.30,'air_accidents_factor':-.15},120),
               ('Организовать дополнительную смену','Organise an Additional Shift',{'industrial_capacity_factory':.10,'stability_factor':-.05},120)]),
 dict(key='interceptors',tag='GER',date='1943.7.1',name=('Ответ на воздушное наступление','Responding to the Air Offensive'),
      desc=('Летом 1943 года налёты на Германию усилили значение радиолокационного наведения, перехвата и рассредоточения производства. Мы можем временно сосредоточить ресурсы на истребителях ПВО или на восстановлении предприятий. Событие не утверждает, что конкретный налёт уже произошёл в этой партии.',
            'The air offensive against Germany in summer 1943 highlighted radar guidance, interception and dispersed production. We can temporarily prioritise air-defence fighters or factory recovery. This does not assert that a particular raid happened in this campaign.'),
      options=[('Сосредоточиться на перехвате','Prioritise Interception',{'air_intercept_efficiency':.20,'air_fuel_consumption_factor':.15},180),
               ('Восстанавливать и рассредоточивать','Repair and Disperse',{'industry_repair_factor':.40,'production_speed_arms_factory_factor':.15},180)]),
]


def script(values):
 return ' '.join(f'{k} = {{ {script(v)} }}' if isinstance(v,dict) else f'{k} = {v if isinstance(v,str) else format(v,".9g")}' for k,v in values.items())


def generate(output):
 output=Path(output);loc={'russian':{},'english':{}};ideas=[];effects=[];decisions=[];techs=[];events=['add_namespace = hro'];daily=[]
 def put(path,value,bom=False):
  p=output/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(value+'\n',encoding='utf-8-sig' if bom else 'utf-8')
 def text(k,ru,en):loc['russian'][k]=ru;loc['english'][k]=en
 def idea(k,ru,en,mods,equipment=None,extra=('','')):
  text(k,ru,en)
  for lang in loc:
   loc[lang][k+'_desc']=describe(mods,lang)+('. ' if mods else '')+extra[lang=='english']
  eq='equipment_bonus = { '+' '.join(t+' = { instant = yes '+script(stats)+' }' for t,stats in (equipment or {}).items())+' }' if equipment else ''
  ideas.append(f'{k} = {{ picture = generic_army allowed = {{ hro_supported_country = yes }} removal_cost = -1 modifier = {{ {script(mods)} }} {eq} }}')
 def decision(k,names,desc,condition,effect,cost=0,visible='hro_supported_country = yes',extra=''):
  text(k,*names);text(k+'_desc',*desc)
  decisions.append(f'{k} = {{ icon = generic_army cost = {cost} visible = {{ {visible} }} available = {{ {condition} }} complete_effect = {{ {effect} }} ai_will_do = {{ factor = 0 }} {extra} }}')
 live='hro_supported_country = yes has_capitulated = no date < 1947.1.1'
 bureau='OR = { has_completed_focus = hro_ger_frontier_bureau has_completed_focus = hro_sov_frontier_bureau }'
 reserve_focus='OR = { has_completed_focus = hro_ger_operational_depots has_completed_focus = hro_sov_operational_depots }'
 text('hro_frontier','Фронтовые технологии и военные программы','Front Technologies and War Programmes')
 text('hro_frontier_desc','Школы изучаются во вкладке исследований «Школы боя и техники». Промышленный приоритет: 30 дней подготовки, 180 дней работы, затем 90 дней до нового запуска. Резерв наступления требует реального вооружения и топлива. Результаты и издержки указаны у каждого решения.',
      'Schools are researched in the Front Developments research tab. Industry priorities: 30 days of preparation, 180 days active, then 90 days until another start. Operational reserves consume real equipment and fuel. Each decision states its benefits and costs.')
 # Researchable schools. Focuses accelerate research; they never award it.
 for tag in ('GER','SOV'):
  for key,(ru,en,mods,dr,de) in SCHOOLS.items():
   identity=f'hro_tech_{tag.lower()}_{key}'
   opposite={'urban':'forest','forest':'urban','river':'mobile','mobile':'river'}[key]
   other=f'hro_tech_{tag.lower()}_{opposite}'
   year=1940 if tag=='GER' else (1943 if key=='urban' else 1942)
   text(identity,ru,en);text(identity+'_desc',dr+' Изучается в слоте исследований. Выбор школы взаимоисключающий.',de+' Researched in a research slot. School choices are mutually exclusive.')
   text(identity+'_bonus','Исследовательская программа: '+ru,'Research programme: '+en)
   techs.append(f'{identity} = {{ allow_branch = {{ original_tag = {tag} }} allow = {{ original_tag = {tag} }} xor = {{ {other} }} research_cost = 1 start_year = {year} folder = {{ name = hro_front_folder position = {{ x = 0 y = 0 }} }} categories = {{ hro_front_research support_tech }} ai_will_do = {{ factor = 1 }} {script(mods)} }}')
   effect=f'hro_frontier_grant_{tag.lower()}_{key}'
   effects.append(f'{effect} = {{ if = {{ limit = {{ original_tag = {tag} NOT = {{ has_country_flag = {identity}_bonus_issued }} }} set_country_flag = {identity}_bonus_issued army_experience = 25 if = {{ limit = {{ NOT = {{ has_tech = {identity} }} NOT = {{ has_tech = {other} }} }} add_tech_bonus = {{ name = {identity}_bonus bonus = 1 uses = 1 technology = {identity} }} }} }} }}')
 # Programme locks survive reloads. Completion also runs from daily dispatch if native decision removal is delayed.
 idea('hro_frontier_retooling','Переналадка предприятий','Factory Retooling',{'industrial_capacity_factory':-.10},extra=('30 дней. Затем начинает действовать выбранная программа.','30 days, followed by the chosen programme.'))
 for key,(ru,en,eq,dr,de) in PROGRAMMES.items():
  spirit='hro_frontier_industry_'+key;pending='hro_frontier_pending_'+key
  idea(spirit,ru,en,{'production_factory_efficiency_gain_factor':.15},eq,(dr+' Действует 180 дней.',de+' Active for 180 days.'))
  start='hro_frontier_begin_'+key;finish='hro_frontier_finish_'+key
  eligible=f'{live} {bureau} NOT = {{ has_country_flag = hro_frontier_industry_lock }}'
  effects.append(f'''{start} = {{ if = {{ limit = {{ {eligible} }}
   set_country_flag = {{ flag = hro_frontier_industry_lock value = 1 days = 300 }}
   set_country_flag = {pending}
   set_country_flag = {{ flag = hro_frontier_retooling_time value = 1 days = 30 }}
   add_ideas = hro_frontier_retooling
  }} }}
  {finish} = {{ if = {{ limit = {{ {live} has_country_flag = {pending} NOT = {{ has_country_flag = hro_frontier_retooling_time }} }}
   clr_country_flag = {pending} remove_ideas = hro_frontier_retooling
   add_timed_idea = {{ idea = {spirit} days = 180 }}
  }} }}''')
  decision('hro_frontier_programme_'+key,(ru,en),
   (f'100 ПВ. Подготовка 30 дней: выпуск военных заводов −10%. Затем на 180 дней: {dr} Рост эффективности производства +15%. Одна программа за раз; следующий запуск не ранее 300 дней после начала. Капитуляция или 1947 год отменяют программу без возврата цены.',
    f'100 PP. 30-day preparation: military output −10%. Then 180 days: {de} Production efficiency growth +15%. One programme at a time; another start is locked for 300 days. Capitulation or 1947 cancels without refund.'),
   eligible,start+' = yes',100,visible=bureau,extra=f'days_remove = 30 remove_effect = {{ {finish} = yes }}')
  daily.append(f'{finish} = yes')
 # Real stocks consumed exactly once at preparation; ready reserves cannot be stockpiled in parallel.
 equipment={'motorized_equipment':150,'support_equipment':300,'infantry_equipment':2000}
 stocks=' '.join(f'has_equipment = {{ {k} > {v-1} }}' for k,v in equipment.items())+' has_fuel > 4999'
 payment=' '.join(f'add_equipment_to_stockpile = {{ type = {k} amount = -{v} }}' for k,v in equipment.items())+' add_fuel = -5000'
 idea('hro_frontier_reserve_loading','Погрузка оперативного резерва','Loading the Operational Reserve',{'industrial_capacity_factory':-.05},extra=('21 день подготовки. Резерв готовится из переданного вооружения.','21-day preparation using committed equipment.'))
 idea('hro_frontier_reserve_tempo','Резерв введён в прорыв','Reserves Exploit the Breakthrough',{'army_speed_factor':.10,'army_org_regain':.20,'supply_consumption_factor':.15})
 idea('hro_frontier_reserve_relief','Смена передовых эшелонов','Relief of Forward Echelons',{'army_org_regain':.20,'supply_consumption_factor':-.10})
 reserve_ok=f'{live} {reserve_focus} {stocks} NOT = {{ has_country_flag = hro_frontier_reserve_lock }} NOT = {{ has_country_flag = hro_frontier_reserve_ready }} NOT = {{ has_country_flag = hro_frontier_reserve_pending }}'
 effects.append(f'''hro_frontier_load_reserve = {{ if = {{ limit = {{ {reserve_ok} }}
  {payment} set_country_flag = hro_frontier_reserve_pending
  set_country_flag = {{ flag = hro_frontier_reserve_time value = 1 days = 21 }}
  set_country_flag = {{ flag = hro_frontier_reserve_lock value = 1 days = 120 }}
  add_ideas = hro_frontier_reserve_loading
 }} }}
 hro_frontier_finish_reserve = {{ if = {{ limit = {{ {live} has_country_flag = hro_frontier_reserve_pending NOT = {{ has_country_flag = hro_frontier_reserve_time }} }}
  clr_country_flag = hro_frontier_reserve_pending remove_ideas = hro_frontier_reserve_loading
  set_country_flag = hro_frontier_reserve_ready
 }} }}''')
 daily.append('hro_frontier_finish_reserve = yes')
 decision('hro_frontier_prepare_reserve',('Подготовить оперативный резерв','Prepare an Operational Reserve'),
  ('50 ПВ, 150 грузовиков, 300 оснащения, 2000 пехотного оружия и 5000 топлива списываются при запуске. 21 день: выпуск военных заводов −5%. Затем один резерв хранится до использования. Новая подготовка — не ранее 120 дней от начала и после расходования старого резерва. Списание означает расход на подготовку и снабжение; возврата в запас нет.',
   '50 PP, 150 trucks, 300 support equipment, 2,000 infantry equipment and 5,000 fuel are consumed on activation. 21 days: military output −5%. One ready reserve persists until used. Another preparation requires 120 days since the start and consumption of the previous reserve. Equipment is spent on preparation and supply, never refunded.'),
  reserve_ok,'hro_frontier_load_reserve = yes',50,visible=reserve_focus,extra='days_remove = 21 remove_effect = { hro_frontier_finish_reserve = yes }')
 decision('hro_frontier_ready_status',('Оперативный резерв готов','Operational Reserve Ready'),('Доступен один резерв: выберите развитие прорыва или смену передовых эшелонов. Использование возможно только во время наступления или его истощения; перегруппировка блокирует применение.','One reserve is available: exploit a breakthrough or relieve forward echelons. Use during an operation or its exhaustion; regrouping blocks deployment.'),'always = no','',visible='has_country_flag = hro_frontier_reserve_ready')
 for key,ru,en in [('tempo','Ввести резерв в прорыв','Commit the Reserve to the Breakthrough'),('relief','Сменить передовые эшелоны','Relieve the Forward Echelons')]:
  effect='hro_frontier_deploy_'+key;spirit='hro_frontier_reserve_'+key
  eligible=f'{live} hro_war_eastern_war = yes has_country_flag = hro_frontier_reserve_ready OR = {{ has_country_flag = hro_ops_active has_country_flag = hro_ops_exhaustion }} NOT = {{ has_country_flag = hro_ops_rest }}'
  effects.append(f'{effect} = {{ if = {{ limit = {{ {eligible} }} clr_country_flag = hro_frontier_reserve_ready add_timed_idea = {{ idea = {spirit} days = 14 }} }} }}')
  decision(effect,(ru,en),('Расходует готовый резерв. На 14 дней: '+loc['russian'][spirit+'_desc']+'. Сроки наступления и истощения не сбрасываются; перегруппировка по-прежнему необходима.',
                          'Consumes the ready reserve. For 14 days: '+loc['english'][spirit+'_desc']+'. Operation and exhaustion clocks are not reset; regrouping remains necessary.'),eligible,effect+' = yes',visible='has_country_flag = hro_frontier_reserve_ready')
 # Additional requested German actions share one scarce command slot.
 for key,(ru,en,cost,days,mods,eq) in GER_ACTIONS.items():
  spirit='hro_frontier_ger_'+key;effect=spirit+'_activate'
  equipment_desc=(' Истребители с малым планером: воздушная атака +15%.',' Small-airframe fighters: air attack +15%.') if key=='fighter_sweep' else (' Штурмовики с малым планером: атака по наземным целям +15%.',' Small-airframe CAS: ground attack +15%.') if key=='cas_surge' else ('','')
  idea(spirit,ru,en,mods,eq,equipment_desc)
  gate='hro_ger_front_air_programme' if key in ('fighter_sweep','cas_surge') else 'hro_ger_motor_transport_standards'
  eligible=f'{live} original_tag = GER has_completed_focus = {gate} hro_war_eastern_war = yes NOT = {{ has_country_flag = hro_frontier_command_lock }}'
  effects.append(f'{effect} = {{ if = {{ limit = {{ {eligible} }} set_country_flag = {{ flag = hro_frontier_command_lock value = 1 days = 90 }} add_timed_idea = {{ idea = {spirit} days = {days} }} }} }}')
  decision(effect,(ru,en),(f'{cost} ПВ. На {days} дней: '+loc['russian'][spirit+'_desc']+' Все пять дополнительных штабных программ занимают один слот на 90 дней от запуска. Мир или капитуляция снимают боевой эффект; срок блокировки сохраняется.',
                         f'{cost} PP. For {days} days: '+loc['english'][spirit+'_desc']+' All five additional staff programmes share a 90-day lock from activation. Peace or capitulation removes combat benefits without resetting the lock.'),eligible,effect+' = yes',cost,visible=f'original_tag = GER has_completed_focus = {gate}')
 # Historical opportunities: one event/choice per historical opportunity, rechecked on click.
 history_ideas=[]
 for i,record in enumerate(HISTORY,930):
  k=record['key'];event=f'hro.{i}';tag=record['tag'];flag=f'hro_frontier_history_{k}'
  eligible=f'{live} original_tag = {tag} hro_war_eastern_war = yes {bureau} date > {record["date"]}'
  if tag=='SOV':eligible+=' check_variable = { hro_war_sov_war_days > 179 }'
  daily.append(f'if = {{ limit = {{ {eligible} NOT = {{ has_country_flag = {flag}_notified }} }} set_country_flag = {flag}_notified country_event = {{ id = {event} days = 1 }} }}')
  text(event+'.t',*record['name']);text(event+'.d',*record['desc']);opts=[]
  for j,(ru,en,mods,days) in enumerate(record['options']):
   spirit=f'{flag}_{j}';history_ideas.append(spirit);idea(spirit,ru,en,mods,extra=(f'{days} дней. Один из двух взаимоисключающих итогов исторического события.',f'{days} days. One of two mutually exclusive historical-event outcomes.'))
   text(event+f'.o{j}',ru,en)
   opts.append(f'option = {{ name = {event}.o{j} custom_effect_tooltip = {spirit}_desc hidden_effect = {{ if = {{ limit = {{ {eligible} NOT = {{ has_country_flag = {flag}_chosen }} }} set_country_flag = {flag}_chosen add_timed_idea = {{ idea = {spirit} days = {days} }} }} }} }}')
  events.append(f'country_event = {{ id = {event} title = {event}.t desc = {event}.d is_triggered_only = yes fire_only_once = yes '+' '.join(opts)+' }')
 # UI explains actual remaining lock timers; the engine exposes flag age via elapsed_days.
 for key,ru,en,flag,days in [('industry','Промышленный цикл занят','Industrial Cycle Locked','hro_frontier_industry_lock',300),('command','Штабная программа уже выбрана','Staff Programme Already Selected','hro_frontier_command_lock',90),('reserve','Резерв: срок повторной подготовки','Reserve Preparation Cooldown','hro_frontier_reserve_lock',120)]:
  decision('hro_frontier_lock_'+key,(ru,en),(f'Следующий запуск возможен через {days} дней после предыдущего.',f'Another start is available {days} days after the last.'),'always = no','',visible=f'has_country_flag = {flag}')
 # Finite benefits never revive on load or peace; only permanent technologies reconcile.
 combat_ideas=[f'hro_frontier_ger_{k}' for k in GER_ACTIONS]+['hro_frontier_reserve_tempo','hro_frontier_reserve_relief']+history_ideas
 clean_combat=' '.join('remove_ideas = '+i for i in combat_ideas)
 all_ideas=[i.split(' = ',1)[0] for i in ideas]
 cleanup=' '.join('remove_ideas = '+i for i in all_ideas)+' '+' '.join('clr_country_flag = '+f for f in ['hro_frontier_reserve_pending','hro_frontier_reserve_ready','hro_frontier_reserve_time','hro_frontier_retooling_time']+['hro_frontier_pending_'+k for k in PROGRAMMES])
 effects.append('hro_frontier_daily = { if = { limit = { '+live+' } '+'\n'.join(daily)+' if = { limit = { NOT = { hro_war_eastern_war = yes } } '+clean_combat+' } } else = { '+cleanup+' } }')
 put('common/technologies/hro_front_schools.txt','technologies = {\n'+'\n'.join(techs)+'\n}')
 put('common/ideas/hro_frontier_ideas.txt','ideas = { country = {\n'+'\n'.join(ideas)+'\n} }')
 put('common/scripted_effects/hro_frontier_effects.txt','\n'.join(effects))
 put('common/on_actions/hro_frontier.txt','on_actions = { on_daily = { effect = { if = { limit = { hro_supported_country = yes } hro_frontier_daily = yes } } } }')
 put('common/decisions/categories/hro_frontier.txt','hro_frontier = { icon = generic_army allowed = { hro_supported_country = yes } visible = { hro_supported_country = yes } visible_when_empty = no }')
 put('common/decisions/hro_frontier.txt','hro_frontier = {\n'+'\n'.join(decisions)+'\n}')
 put('events/hro_frontier_events.txt','\n'.join(events))
 for lang,entries in loc.items():put(f'localisation/{lang}/hro_frontier_l_{lang}.yml',f'l_{lang}:\n'+''.join(f' {k}:0 {json.dumps(v,ensure_ascii=False)}\n' for k,v in entries.items()),True)
 return dict(technologies=len(techs),focuses=12,decisions=len(decisions),ideas=len(ideas),events=len(HISTORY),school_limit_per_country=2,industrial_cycle=[30,180,90],reserve_preparation_days=21,reserve_cooldown_days=120,reserve_equipment=equipment,reserve_fuel=5000,reserve_combat_days=14,german_command_lock_days=90,technology_source='research slots in hro_front_folder; focus grants a single targeted speed bonus',runtime_verified=False)


def audit_technologies(output, game, schema_dir):
 """Check school unit IDs against supplied 1.19.3 and stats against CWTools."""
 import re
 from clausewitz import parse,walk
 units=set()
 for path in (Path(game)/'common/units').glob('*.txt'):
  for root in parse(path.read_text(encoding='utf-8-sig')):
   if root.key=='sub_units':units.update(n.key for n in root.value)
 if not units:raise ValueError('Front schools require the supplied vanilla common/units directory')
 schema_text='\n'.join(p.read_text(encoding='utf-8-sig') for p in (Path(schema_dir)/'Config').rglob('*.cwt')) if schema_dir else ''
 allowed_stats=set(re.findall(r'alias\[unit_stat:([A-Za-z_][A-Za-z0-9_]*)\]',schema_text))
 terrain={'urban','forest','river','fort'}
 meta={'allow','allow_branch','research_cost','start_year','xor','folder','categories','force_use_small_tech_layout','ai_will_do'}
 root=Path(output)
 techs=parse((root/'common/technologies/hro_front_schools.txt').read_text())[0].value
 known={t.key for t in techs}
 all_known={n.key for p in (root/'common/technologies').glob('hro*.txt') for r in parse(p.read_text()) for n in r.value}
 for tech in techs:
  assert tech.one('folder').scalar('name')=='hro_front_folder',tech.key
  assert tech.one('allow').scalar('original_tag') in ('GER','SOV'),tech.key
  for unit in tech.value:
   if unit.key in meta:continue
   if unit.key not in units:raise ValueError('School technology references missing unit: '+unit.key)
   for stat in unit.value:
    if stat.key in terrain:
     if any(v.key not in ('attack','defence','movement') for v in stat.value):raise ValueError('Invalid terrain stat: '+stat.key)
    elif schema_dir and stat.key not in allowed_stats:raise ValueError('Unknown school stat: '+stat.key)
    for value in (stat.value if isinstance(stat.value,list) else [stat]):
     if not isinstance(value.value,str):raise ValueError('Unexpected school stat nesting')
     float(value.value)
 references=0
 for path in (root/'common/scripted_effects').glob('hro*.txt'):
  for n in walk(parse(path.read_text())):
   if n.key=='set_technology':
    for child in n.value:
     if child.key and child.key.startswith('hro_tech_'):
      if child.key not in all_known:raise ValueError('Unknown school technology: '+child.key)
      if child.key in known:references+=1
 return dict(technologies=len(techs),grant_references=references,unit_ids_checked_against_uploaded_game=True,stats_checked_against_schema=bool(schema_dir))
