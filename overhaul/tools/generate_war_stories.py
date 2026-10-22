"""Conditional war stories, one railway prototype and a bounded recon blackout."""
from pathlib import Path
import json,re
from generate_war_adaptation import _select,_remove
from effect_presentation import present_effects
RECON_IDS=['hro_story_recon_blind','hro_story_recon_recovering','hro_story_recon_restored']
MODIFIERS={
 RECON_IDS[0]:{'recon_factor':-1.0,'army_intel_factor':-1.0,'intel_from_combat_factor':-1.0},
 RECON_IDS[1]:{'recon_factor':-.50,'army_intel_factor':-.50,'intel_from_combat_factor':-.50},
 RECON_IDS[2]:{'recon_factor':.10,'army_intel_factor':.10},
 'hro_story_dora_trials':{'industrial_capacity_factory':-.03},
 'hro_story_kolobanov_ambush':{'army_armor_defence_factor':.10,'recon_factor_while_entrenched':.15},
 'hro_story_kolobanov_cadres':{'experience_loss_factor':-.10,'army_org_regain':.10},
 'hro_story_hot_tea':{'army_org_regain':.05,'supply_consumption_factor':-.05},
 'hro_story_fort_builders':{'production_speed_bunker_factor':.50,'production_speed_coastal_bunker_factor':.40,'industrial_capacity_factory':-.03},
 'hro_story_combat_recon':{'recon_factor':.15,'intel_from_combat_factor':.25},
 'hro_story_captured_maps':{'army_intel_factor':.15,'recon_factor':.10}}
NAMES={
 RECON_IDS[0]:('Штаб без сводок','Headquarters Without Reports'),RECON_IDS[1]:('Обрывочные донесения фронтов','Fragmented Front Reports'),RECON_IDS[2]:('Сводки, которым можно верить','Reports We Can Trust'),
 'hro_story_dora_trials':('Полигонные испытания «Доры»','Dora Proving-Ground Trials'),
 'hro_story_kolobanov_ambush':('Урок танковой засады','Lessons of a Tank Ambush'),'hro_story_kolobanov_cadres':('Сохранённые экипажи','Preserved Crews'),
 'hro_story_hot_tea':('Горячий чай на холодном фронте','Hot Tea on a Cold Front'),
 'hro_story_fort_builders':('Ускоренный инженерный подряд','Accelerated Engineer Contracts'),
 'hro_story_combat_recon':('Разведка боем','Reconnaissance in Force'),'hro_story_captured_maps':('Охота за фронтовыми сводками','Hunting Front Reports')}
DESCS={
 RECON_IDS[0]:('Первые21день оборонительной войны с Германией: разведка−100%, армейские разведданные−100%, данные из боёв−100%. Это модификаторы, не жёсткое обнуление всех источников агентства. Подготовка не пропускает первые21день.','First21days of defensive war with Germany: reconnaissance, army intelligence and combat intel−100%. These are modifiers, not a hard zero of every agency source. The initial21days cannot be skipped.'),
 RECON_IDS[1]:('Дни21–59первой оборонительной войны: разведка, армейские данные и сведения из боёв−50%. Фокус восстановления может завершить эту стадию раньше; после60дней она исчезает сама.','War days21–59: reconnaissance, army and combat intel−50%. The recovery focus can end this stage early; it automatically ends at day60.'),
 RECON_IDS[2]:('После реформы связи и первых21военных дней: разведка+10%, армейские разведданные+10%. В мире и после капитуляции снимается, разрешение реформы сохраняется.','After the reform and21war days: reconnaissance and army intelligence+10%. Removed in peace/capitulation; reform authorisation remains.'),
 'hro_story_dora_trials':('90дней: выпуск военных заводов−3%. Проект требует испытаний и железнодорожной подготовки. Один прототип выдаётся отдельно и не повторяется при загрузке.','90days: military factory output−3%. Trials and railway preparation have costs; the separate prototype is never replayed on load.'),
 'hro_story_kolobanov_ambush':('180дней: защита бронетанковых частей+10%, разведка при окапывании+15%. Один из двух взаимоисключающих уроков события.','180days: armour defence+10%, entrenched reconnaissance+15%. One of two mutually exclusive event lessons.'),
 'hro_story_kolobanov_cadres':('180дней: потери опытных бойцов−10%, восстановление организации+10%. Альтернатива школе засады.','180days: experience losses−10%, organisation recovery+10%. Alternative to the ambush lesson.'),
 'hro_story_hot_tea':('30дней: восстановление организации+5%, расход снабжения−5%. Маленькая история о большой службе тыла; одно событие на страну.','30days: organisation recovery+5%, supply use−5%. A small story about the supply service; once per country.'),
 'hro_story_fort_builders':('120дней: строительство сухопутных укреплений+50%, береговых+40%, выпуск военных заводов−3%. Заводы и строительные очереди всё ещё нужны.','120days: land fort construction+50%, coastal forts+40%, military output−3%. Factories and construction queues are still required.'),
 'hro_story_combat_recon':('90дней: разведка+15%, сведения из боёв+25%. Это не открывает полностью позиции противника.','90days: reconnaissance+15%, combat intel+25%. This does not fully reveal enemy positions.'),
 'hro_story_captured_maps':('90дней: армейские разведданные+15%, разведка+10%.','90days: army intelligence+15%, reconnaissance+10%.')}

def validate_geography(game):
 from clausewitz import parse
 found={}
 for p in (Path(game)/'history/states').glob('*.txt'):
  s=next((n for n in parse(p.read_text(encoding='utf-8-sig')) if n.key=='state'),None)
  if s and s.scalar('id') in ('64','195'):
   found[int(s.scalar('id'))]={int(x.value[0].value) for x in s.one('history').all('victory_points')}
 if 6521 not in found.get(64,set()) or 3151 not in found.get(195,set()):raise ValueError('Story VP geography differs: Berlin/Leningrad')
 return True

def generate(output):
 output=Path(output);loc={'russian':{},'english':{}};effects=[];events=['add_namespace = hro'];decisions=[]
 def put(path,s,bom=False):
  p=output/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s+'\n',encoding='utf-8-sig' if bom else 'utf-8')
 def tidy(value):
  value=re.sub(r'(?<=[A-Za-zА-Яа-яЁё])(?=\d)|(?<=\d)(?=[A-Za-zА-Яа-яЁё])',' ',value)
  value=re.sub(r'(?<=[A-Za-z])(?=[А-Яа-яЁё])|(?<=[А-Яа-яЁё])(?=[A-Za-z])|(?<=%)(?=[А-Яа-яЁёA-Za-z])',' ',value)
  return value.replace('3 Dmodel','3D model').replace('3 D','3D')
 def text(key,ru,en):loc['russian'][key]=tidy(ru);loc['english'][key]=tidy(en)
 idea_defs=[]
 for key,mods in MODIFIERS.items():
  owner='SOV' if key in RECON_IDS or 'kolobanov' in key or key=='hro_story_combat_recon' else 'GER' if key in ('hro_story_dora_trials','hro_story_captured_maps') else None
  allowed='original_tag = '+owner if owner else 'OR = { original_tag = GER original_tag = SOV }'
  idea_defs.append(f'{key} = {{ picture = generic_army allowed = {{ {allowed} }} removal_cost = -1 modifier = {{ '+' '.join(f'{k} = {v:g}' for k,v in mods.items())+' } }')
  text(key,*NAMES[key]);text(key+'_desc',*DESCS[key])
 text('hro_story_projects','Инженеры, разведка и фронтовые истории','Engineers, Intelligence and War Stories')
 text('hro_story_projects_desc','Ограниченные программы с ценой, сроком и ясным результатом.','Limited programmes with explicit costs, durations and rewards.')
 text('hro_story_dora_tt','Один раз: технология железнодорожных орудий и прототип «Дора» в контролируемом Берлине; обстрел+15%. Испытания: выпуск военных заводов−3%на90дней. Если Берлин временно недоступен, прототип ожидает восстановления контроля.','Once: railway gun technology and a Dora prototype in controlled Berlin, bombardment+15%. Trials cost−3%military output for90days. If Berlin is unavailable the prototype waits for control to return.')
 text('hro_story_recon_tt','После21военного дня завершает восстановление разведки и открывает+10%разведки/армейских данных в продолжающейся войне. До21дня провал сохраняется.','After21war days, completes recovery and enables+10%reconnaissance/army intel during the war. It cannot skip the initial21days.')
 effects.append('''hro_story_dora_deliver = {
 if = { limit = { original_tag = GER has_capitulated = no has_country_flag = hro_story_dora_pending NOT = { has_country_flag = hro_story_dora_delivered } controls_province = 6521 }
  clr_country_flag = hro_story_dora_pending set_country_flag = hro_story_dora_delivered
  create_railway_gun = { equipment = railway_gun_equipment_1 name = "Dora" location = 6521 }
 }
}
hro_story_dora_complete = {
 custom_effect_tooltip = hro_story_dora_tt
 hidden_effect = { if = { limit = { original_tag = GER NOT = { has_country_flag = hro_story_dora_awarded } }
  set_country_flag = hro_story_dora_awarded set_country_flag = hro_story_dora_pending
  if = { limit = { NOT = { has_tech = railway_gun } } set_technology = { railway_gun = 1 popup = no } }
  hro_set_hro_idea_ger_story_dora = yes
  add_timed_idea = { idea = hro_story_dora_trials days = 90 }
  hro_story_dora_deliver = yes
  country_event = { id = hro.910 days = 1 }
 } }
}
hro_story_recon_reform = {
 custom_effect_tooltip = hro_story_recon_tt
 hidden_effect = { if = { limit = { original_tag = SOV }
  set_country_flag = hro_story_recon_prepared hro_story_recon_sync = yes
 } }
}
hro_story_recon_sync = {
 if = { limit = { original_tag = SOV hro_war_eastern_war = yes }
  if = { limit = { has_country_flag = hro_war_sov_surprised check_variable = { hro_war_sov_war_days < 21 } }
'''+_select(RECON_IDS,RECON_IDS[0])+'''
  } else_if = { limit = { has_country_flag = hro_war_sov_surprised NOT = { has_country_flag = hro_story_recon_prepared } check_variable = { hro_war_sov_war_days < 60 } }
'''+_select(RECON_IDS,RECON_IDS[1])+'''
  } else_if = { limit = { has_country_flag = hro_story_recon_prepared check_variable = { hro_war_sov_war_days > 20 } }
'''+_select(RECON_IDS,RECON_IDS[2])+'''
  } else = { '''+_remove(RECON_IDS)+''' }
 } else = { '''+_remove(RECON_IDS)+''' }
}''')
 eligible='original_tag = SOV hro_war_eastern_war = yes hro_war_sov_defending = yes controls_province = 3151 date > 1941.8.19 check_variable = { hro_war_sov_war_days > 44 } check_variable = { hro_war_sov_war_days < 180 }'
 for choice,idea,tech in [('ambush','hro_story_kolobanov_ambush','armor'),('cadres','hro_story_kolobanov_cadres','support_tech')]:
  key='hro_story_kolobanov_'+choice+'_reward';text(key,NAMES[idea][0],NAMES[idea][1])
  effects.append(f'''{key} = {{
   if = {{ limit = {{ {eligible} NOT = {{ has_country_flag = hro_story_kolobanov_chosen }} }}
    set_country_flag = hro_story_kolobanov_chosen add_timed_idea = {{ idea = {idea} days = 180 }}
    army_experience = 35 add_tech_bonus = {{ name = {key} bonus = 0.5 uses = 1 category = {tech} }}
   }}
  }}''')
 for tag in ('ger','sov'):
  effects.append(f'''hro_story_tea_{tag}_reward = {{
   if = {{ limit = {{ original_tag = {tag.upper()} hro_war_eastern_war = yes NOT = {{ has_country_flag = hro_story_tea_{tag}_chosen }} }}
    set_country_flag = hro_story_tea_{tag}_chosen add_timed_idea = {{ idea = hro_story_hot_tea days = 30 }}
   }}
  }}''')
 def event(identity,ru,en,dr,de,options):
  text(identity+'.t',ru,en);text(identity+'.d',dr,de);out=[]
  for index,(r,e,body) in enumerate(options):
   key=identity+'.'+chr(97+index);text(key,r,e);out.append('option = { name = '+key+' '+body+' }')
  events.append(f'country_event = {{ id = {identity} title = {identity}.t desc = {identity}.d is_triggered_only = yes fire_only_once = yes '+' '.join(out)+' }')
 event('hro.910','Сколько платформ нужно одной пушке?','How Many Wagons Does One Gun Need?',
 'Орудие ещё не выстрелило, а железнодорожный штаб уже запросил отдельное расписание. «Дора» — дорогой опыт осадной артиллерии: огромная мощь требует путей, расчёта и снабжения. Историческая справка: сверхтяжёлые80-см орудия программыGustav/Doraсоздавались для борьбы с укреплениями; одно применялось под Севастополем в1942году. В игре прототип использует стандартное железнодорожное орудие.',
 'The gun has not fired yet, but railway headquarters already wants its own timetable. Dora is an expensive siege experiment: firepower needs tracks, crews and supplies. Historical note: the80-cm Gustav/Dora programme targeted fortifications; one gun was used at Sevastopol in1942. The game prototype uses the standard railway gun.',
 [('Короткий ответ: много.','Short answer: a lot.','')])
 event('hro.911','Товарищ, где противник?','Comrade, Where Is the Enemy?',
 'Телефон молчит, радиограмма запоздала, а на карте соседний полк всё ещё находится там, откуда он ушёл вчера. Командирам нужны проверенные сведения, а не ещё один красивый карандаш. Первые21военный день действуют−100%модификаторы фронтовой разведки; затем начинается восстановление. Фокус «Вернуть глаза фронту» способен ускорить его после первоначального провала.',
 'The telephone is silent, the radio report is late and yesterday’s map still shows yesterday’s regiment. Commanders need verified reports. The first21war days apply−100%reconnaissance modifiers, followed by recovery. Give the Front Its Eyes Back can accelerate recovery after the initial blackout.',
 [('Для начала найдите карту.','Find the map first.','')])
 event('hro.912','Экипаж Колобанова: урок засады','Kolobanov’s Crew: An Ambush Lesson',
 'На Ленинградском направлении в учебные материалы попадает донесение о тяжёлом танке, который встретил колонну из подготовленной засады. Исторический эпизод связан с экипажем Зиновия Колобанова под Красногвардейском в августе1941; в советском донесении заявлено22подбитых танка. Обсудить можно не только счёт машин: наблюдение, выбор позиции и сохранение экипажа важнее красивой цифры. Выберите один урок на180дней; при продолжающейся оборонительной войне и удержании Ленинграда также35опыта армии и один50%-ный профильный исследовательский бонус.',
 'A Leningrad-front report describes a heavy tank engaging a column from a prepared ambush. The historical episode concerns Zinoviy Kolobanov’s crew near Krasnogvardeysk inAugust1941; Soviet reporting claimed22enemy tanks. Observation, position selection and crew survival matter beyond the score. Choose one180-day lesson; while the defensive war continues and Leningrad is held, also gain35 army XP and one50%matching research bonus.',
 [('Открыть школу танковой засады.','Teach the ambush.','hro_story_kolobanov_ambush_reward = yes'),('Главная ценность — экипаж.','The crew comes first.','hro_story_kolobanov_cadres_reward = yes')])
 for tag,ev in [('ger','hro.913'),('sov','hro.914')]:
  event(ev,'Где горячий чай, там и штаб' if tag=='ger' else 'Самовар по штатному расписанию','Headquarters Follows the Hot Tea' if tag=='ger' else 'A Samovar on the Establishment List',
   'Интендант требует акт на лишний термос. Механик предлагает сначала выдать чай тем, кто ночью меняет гусеницу. На этот раз бюрократия подождёт. Если война продолжается: на30дней восстановление организации+5%, расход снабжения−5%. Событие одноразовое.',
   'The quartermaster wants a form for the extra thermos. The mechanic suggests serving the people changing tracks at night first. Paperwork can wait. If the war continues: organisation recovery+5%, supply use−5%for30days. Once only.',
   [('Внести самовар в штат.','Put the samovar on the establishment.','hro_story_tea_'+tag+'_reward = yes')])
 configs=[
 ('ger_fort_builders','GER','hro_ger_modular_fortifications','hro_story_fort_builders',60,120,'Инженерный подряд: бетон по расписанию','Engineer Contracts: Concrete on Schedule',False),
 ('sov_fort_builders','SOV','hro_sov_modular_fortification_lines','hro_story_fort_builders',60,120,'Стройбат: сборные огневые точки','Construction Troops: Prefabricated Positions',False),
 ('sov_combat_recon','SOV','hro_sov_front_recon_rebuild','hro_story_combat_recon',50,90,'Разведка боем','Reconnaissance in Force',True),
 ('ger_captured_maps','GER','hro_ger_dummy_positions','hro_story_captured_maps',50,90,'Охота за советскими сводками','Hunt Soviet Reports',True)]
 for key,tag,focus,idea,cost,duration,ru,en,war in configs:
  decision='hro_story_'+key;cooldown=decision+'_cooldown';extra=' hro_war_eastern_war = yes' if war else ''
  if key=='ger_captured_maps':extra+=' has_intelligence_agency = yes'
  condition=f'original_tag = {tag} has_capitulated = no has_completed_focus = {focus} NOT = {{ has_country_flag = {cooldown} }}'+extra
  text(cooldown,'Перерыв между программами','Programme cooldown')
  text(decision,ru,en);text(decision+'_desc',f'{cost}ПВ. После принятия на{duration}дней: '+DESCS[idea][0]+f' Повторный запуск через180дней от принятия; требует профильного фокуса.'+(' Нужна продолжающаяся война Германии с СССР.' if war else ''),f'{cost}PP. For{duration}days after activation: '+DESCS[idea][1]+' Repeat after180days from activation; requires the matching focus.'+(' Requires an ongoing GER-SOVwar.' if war else ''))
  effect=decision+'_activate';effects.append(f'{effect} = {{ if = {{ limit = {{ {condition} }} set_country_flag = {{ flag = {cooldown} value = 1 days = 180 }} add_timed_idea = {{ idea = {idea} days = {duration} }} }} }}')
  decisions.append(f'{decision} = {{ icon = generic_army cost = {cost} visible = {{ original_tag = {tag} has_completed_focus = {focus} }} available = {{ {condition} }} complete_effect = {{ {effect} = yes }} ai_will_do = {{ factor = 0 }} }}')
 tea=[]
 for tag,focus,eventid in [('GER','hro_ger_field_kitchens','hro.913'),('SOV','hro_sov_field_workshops','hro.914')]:
  tea.append(f'if = {{ limit = {{ original_tag = {tag} hro_war_eastern_war = yes hro_war_winter_season = yes has_completed_focus = {focus} NOT = {{ has_country_flag = hro_story_tea_{tag.lower()}_seen }} }} set_country_flag = hro_story_tea_{tag.lower()}_seen country_event = {{ id = {eventid} days = 1 }} }}')
 effects.append(f'''hro_war_stories_daily = {{
 hro_story_dora_deliver = yes hro_story_recon_sync = yes
 if = {{ limit = {{ original_tag = SOV hro_war_eastern_war = yes has_country_flag = hro_war_sov_surprised check_variable = {{ hro_war_sov_war_days < 21 }} NOT = {{ has_country_flag = hro_story_map_seen }} }} set_country_flag = hro_story_map_seen country_event = {{ id = hro.911 days = 1 }} }}
 if = {{ limit = {{ {eligible} NOT = {{ has_country_flag = hro_story_kolobanov_seen }} }} set_country_flag = hro_story_kolobanov_seen country_event = {{ id = hro.912 days = 1 }} }}
 {' '.join(tea)}
 if = {{ limit = {{ NOT = {{ hro_war_eastern_war = yes }} }} {_remove(['hro_story_kolobanov_ambush','hro_story_kolobanov_cadres','hro_story_hot_tea','hro_story_combat_recon','hro_story_captured_maps'])} }}
 }}''')
 put('common/ideas/hro_war_stories_ideas.txt','ideas = { country = { '+'\n'.join(idea_defs)+' } }')
 presentations={}
 for choice,idea in [('ambush','hro_story_kolobanov_ambush'),('cadres','hro_story_kolobanov_cadres')]:
  key='hro_story_kolobanov_'+choice+'_reward';tooltip=key+'_tt'
  text(tooltip,'При продолжающейся оборонительной войне, удержании Ленинграда и отсутствии ранее выбранного урока: '+DESCS[idea][0]+' Дополнительно35опыта армии и один50%-ный профильный исследовательский бонус.','While the defensive war continues, Leningrad is held and no lesson has been selected: '+DESCS[idea][1]+' Also35armyXPand one50%matching research bonus.')
  presentations[key]='custom_effect_tooltip = '+tooltip+' show_ideas_tooltip = '+idea
 for tag in ('ger','sov'):
  key='hro_story_tea_'+tag+'_reward';tooltip=key+'_tt';text(tooltip,'Один раз в продолжающейся войне: '+DESCS['hro_story_hot_tea'][0],'Once during the ongoing war: '+DESCS['hro_story_hot_tea'][1]);presentations[key]='custom_effect_tooltip = '+tooltip+' show_ideas_tooltip = hro_story_hot_tea'
 put('common/scripted_effects/hro_war_stories_effects.txt',present_effects('\n'.join(effects),presentations))
 put('common/on_actions/hro_zz_war_stories_on_actions.txt','on_actions = { on_daily = { effect = { hro_war_stories_daily = yes } } }')
 put('events/hro_war_stories_events.txt','\n'.join(events))
 put('common/decisions/categories/hro_war_stories_categories.txt','hro_story_projects = { icon = generic_army allowed = { OR = { original_tag = GER original_tag = SOV } } }')
 put('common/decisions/hro_war_stories.txt','hro_story_projects = { '+'\n'.join(decisions)+' }')
 for lang,entries in loc.items():put(f'localisation/{lang}/hro_war_stories_l_{lang}.yml','l_'+lang+':\n'+''.join(f' {k}:0 {json.dumps(v,ensure_ascii=False)}\n' for k,v in entries.items()),True)
 return {'focuses':8,'events':5,'decisions':4,'runtime_ideas':len(MODIFIERS),'blackout_days':21,'automatic_recovery_day':60,'recon_minimum_days_not_skippable':True,'one_dora_prototype':True,'kolobanov_choice_days':180,'kolobanov_requires_leningrad':True,'jokes_have_small_finite_rewards':True,'runtime_verified':False}
