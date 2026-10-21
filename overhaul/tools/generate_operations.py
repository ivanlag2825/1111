"""Costed Eastern-front operations, repairable sabotage and voluntary war councils.

Daily flag ages, rather than delayed events, own all campaign deadlines.
"""
import json
from pathlib import Path

TARGETS={
 'GER':[(195,3151,'Ленинград','Leningrad'),(219,6380,'Москва','Moscow'),(202,525,'Киев','Kyiv'),(206,11370,'Минск','Minsk'),(217,3529,'Сталинград','Stalingrad'),(221,418,'Харьков','Kharkiv')],
 'SOV':[(195,3151,'Ленинград','Leningrad'),(219,6380,'Москва','Moscow'),(202,525,'Киев','Kyiv'),(206,11370,'Минск','Minsk'),(221,418,'Харьков','Kharkiv'),(64,6521,'Берлин','Berlin')]}
MODS={
 'preparing':('Подготовка крупной операции','Preparing a Major Operation',{'industrial_capacity_factory':-.08,'planning_speed':.35}),
 'assault':('Сосредоточенный удар','Concentrated Offensive',{'army_attack_factor':.30,'army_speed_factor':.15,'planning_speed':.40,'army_org_regain':.20,'supply_consumption_factor':-.10}),
 'exhaustion':('Истощение наступления','Offensive Exhaustion',{'army_org_factor':-.10,'army_org_regain':-.25,'army_speed_factor':-.15,'supply_consumption_factor':.25,'attrition':.10}),
 'exhaustion_2':('Истощение наступления: вторая неделя','Offensive Exhaustion: Week Two',{'army_org_factor':-.15,'army_org_regain':-.35,'army_speed_factor':-.20,'supply_consumption_factor':.40,'attrition':.15,'army_attack_factor':-.10}),
 'exhaustion_3':('Истощение наступления: третья неделя','Offensive Exhaustion: Week Three',{'army_org_factor':-.20,'army_org_regain':-.45,'army_speed_factor':-.25,'supply_consumption_factor':.55,'attrition':.20,'army_attack_factor':-.20}),
 'exhaustion_4':('Наступление на пределе возможностей','Offensive at Breaking Point',{'army_org_factor':-.25,'army_org_regain':-.55,'army_speed_factor':-.30,'supply_consumption_factor':.70,'attrition':.25,'army_attack_factor':-.30}),
 'rest':('Перегруппировка армии','Army Regrouping',{'army_attack_factor':-.15,'army_org_regain':.30,'industrial_capacity_factory':-.05,'supply_consumption_factor':.30}),
 'security':('Охрана военных объектов','Military Site Security',{'industry_repair_factor':.30}),
 'council_attack':('Выполнен наступательный замысел','Offensive Objective Achieved',{'army_attack_factor':.15,'planning_speed':.25}),
 'council_hold':('Устойчивость обороны','Proven Defensive Resilience',{'army_defence_factor':.20,'army_org_regain':.25}),
 'council_failure':('Срыв задачи командования','Command Objective Failed',{'stability_factor':-.05,'planning_speed':-.10})}

def flag(name,days=None):
 return 'set_country_flag = '+(f'{{ flag = hro_ops_{name} value = 1 days = {days} }}' if days else 'hro_ops_'+name)
def has(name):return 'has_country_flag = hro_ops_'+name
def no(name):return 'NOT = { '+has(name)+' }'
def idea(name,days):return f'add_timed_idea = {{ idea = hro_ops_idea_{name} days = {days} }}'
def clear(name):return 'clr_country_flag = hro_ops_'+name
def enemy(vp):return f'any_enemy_country = {{ controls_province = {vp} }}'
def owns(vp):return f'controls_province = {vp}'

def validate_geography(game):
 from clausewitz import parse
 states={}
 for p in (Path(game)/'history/states').glob('*.txt'):
  node=next((n for n in parse(p.read_text(encoding='utf-8-sig')) if n.key=='state'),None)
  if node:states[int(node.scalar('id'))]=node
 for targets in TARGETS.values():
  for state,vp,*_ in targets:
   node=states.get(state)
   if node is None or not any(str(vp) in [v.value for v in points.value] for points in node.one('history').all('victory_points')):
    raise ValueError(f'Operation target does not match supplied map: {state}/{vp}')
 return True


def generate(output):
 output=Path(output);loc={'russian':{},'english':{}};effects=[];decisions=[];categories={'hro_ops_category':[],'hro_ops_rear_category':[],'hro_ops_council_category':[]}
 def put(path,value,bom=False):
  p=output/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(value+'\n',encoding='utf-8-sig' if bom else 'utf-8')
 def text(key,ru,en,desc_ru='',desc_en=''):
  for lang,name,desc in [('russian',ru,desc_ru),('english',en,desc_en)]:
   loc[lang][key]=name
   if desc:loc[lang][key+'_desc']=desc
 def decision(key,ru,en,cost,available,body,desc_ru,desc_en,visible=''):
  key='hro_ops_'+key;text(key,ru,en,desc_ru,desc_en)
  category = 'hro_ops_rear_category' if key.startswith(('hro_ops_sabotage_', 'hro_ops_status_sabotage_')) or key == 'hro_ops_security' else 'hro_ops_council_category' if key.startswith(('hro_ops_council_', 'hro_ops_status_council_')) else 'hro_ops_category'
  categories[category].append(key)
  decisions.append(f'''{key} = {{ icon = generic_army cost = {cost} visible = {{ {visible} }}
   available = {{ hro_war_eastern_war = yes {available} }}
   complete_effect = {{ {body} }} ai_will_do = {{ factor = 0 }} }}''')
 text('hro_ops_rear_category','Штаб: действия в тылу','Headquarters: Rear Area Operations','Диверсии перенесены в разведывательное агентство. Здесь доступна охрана объектов.','Sabotage is now launched through the intelligence agency. Site security remains available here.')
 text('hro_ops_council_category','Штаб: военные совещания','Headquarters: War Councils','Добровольные задачи на захват или удержание города. Отдельный общий слот и срок между совещаниями.','Voluntary capture or hold objectives. One shared council slot and acceptance cooldown.')
 text('hro_ops_category','Штаб: крупные операции','Headquarters: Major Operations',
 'Операции усиливают всю армию страны. Цель города задаётся отдельно. Истощение наступления нельзя снять новой операцией. Совещания добровольные; задания показаны отдельными решениями.',
 'Operations strengthen the national army; city objectives are separate. New operations cannot clear exhaustion. Councils are voluntary; tasks appear as separate decisions.')
 ideas=[]
 for key,(ru,en,mods) in MODS.items():
  text('hro_ops_idea_'+key,ru,en, 'Эффекты действуют на всю страну в течение указанного срока. Подробности и срок — в решении штаба.', 'Effects apply nationally for the stated duration. See the headquarters decision for timing and details.')
  if key.startswith('exhaustion'):
   from decision_details import describe
   for language in loc:
    loc[language]['hro_ops_idea_'+key+'_desc'] = describe(mods,language) + ('. Сохраняется до завершения перегруппировки; ступени заменяют друг друга.' if language=='russian' else '. Remains until regrouping completes; tiers replace each other.')
  ideas.append(f'hro_ops_idea_{key} = {{ picture = generic_army allowed = {{ OR = {{ original_tag = GER original_tag = SOV }} }} removal_cost = -1 modifier = {{ '+ ' '.join(f'{k} = {v}' for k,v in mods.items())+' } }')
 for tag,targets in TARGETS.items():
  for state,vp,ru,en in targets:
   stem=f'{tag.lower()}_{state}';vis=f'original_tag = {tag}'
   pending='prep_'+stem;ready='ready_'+stem
   decision('prepare_'+stem,'Подготовить операцию: '+ru,'Prepare Operation: '+en,90,
    ' '.join(no(x) for x in ['preparing','ready','active','cooldown','rest','exhaustion'])+' '+enemy(vp),
    flag(pending)+' set_variable = { hro_ops_preparation_days = 0 } '+flag('preparing',35)+' '+idea('preparing',35),
    '35 дней за 90 ПВ: военный выпуск −8%, планирование +35%. Затем 45 дней, чтобы запустить операцию ещё за 30 ПВ. Запуск даёт на 14 дней атаку +30%, скорость +15%, восстановление организации +20%, планирование +40%, расход снабжения −10% всей армии страны. Затем четыре ступени истощения: первая сразу, последующие каждые 7 дней. Штрафы растут до атаки −30%, организации −25%, восстановления −55%, скорости −30%, снабжения +70%, истощения +25%. Снимаются завершённой перегруппировкой. Один общий слот операций.',
    '35 preparation days for 90 PP: factory output −8%, planning +35%. Then 45 days to launch for another 30 PP. Launch grants national attack +30%, speed +15%, organisation recovery +20%, planning +40%, supply use −10% for 14 days. Four exhaustion tiers follow: the first immediately, then upgrades every 7 days, capped at attack −30%, organisation −25%, recovery −55%, speed −30%, supply use +70%, attrition +25%. Regrouping is required to clear them. One shared operation slot.',vis)
   decision('status_prep_'+stem,'Подготовка: '+ru,'Preparing: '+en,0,'always = no','',
    'Прошло [?hro_ops_preparation_days|0] из 35 дней. После подготовки появится решение о запуске.',
    '[?hro_ops_preparation_days|0] of 35 days elapsed. A launch decision appears after preparation.',vis+' '+has(pending))
   effects.append(f'''if = {{ limit = {{ {has(pending)} {no('preparing')} }}
    {clear(pending)} if = {{ limit = {{ {enemy(vp)} }} {flag('ready',45)} {flag(ready,45)} }} }}''')
   decision('launch_'+stem,'Начать операцию: '+ru,'Launch Operation: '+en,30,
    has('ready')+' '+has(ready)+' '+enemy(vp),
    clear('ready')+' '+clear(ready)+' '+flag('active',14)+' '+flag('assault_started')+' '+flag('cooldown',90)+' '+idea('assault',14),
    'На 14 дней: атака +30%, скорость +15%, восстановление организации +20%, планирование +40%, расход снабжения −10%. Затем четыре ступени истощения: первая сразу, последующие каждые 7 дней. Максимум: атака −30%, организация −25%, восстановление −55%, скорость −30%, снабжение +70%, истощение +25%. Без перегруппировки не снимаются. Повторный запуск не раньше 90 дней. Бонус действует на всю армию страны.',
    '14 days: attack +30%, speed +15%, organisation recovery +20%, planning +40%, supply use −10%. Four exhaustion tiers follow: the first immediately, then upgrades every 7 days, capped at attack −30%, organisation −25%, recovery −55%, speed −30%, supply use +70%, attrition +25%. Regrouping is required to clear them. 90-day launch cooldown. Bonuses affect the national army.',vis+' '+has(ready))
   for mode,duration in [('attack',75),('hold',60)]:
    task=f'council_{mode}_{stem}';condition=enemy(vp)
    # Defensive targets must border enemy-controlled territory, not simply a country at war.
    if mode=='hold':condition=owns(vp)+f' {state} = {{ any_neighbor_state = {{ controller = {{ has_war_with = ROOT }} }} }}'
    decision(task,('Совещание: взять ' if mode=='attack' else 'Совещание: удержать ')+ru,
     ('Council: Capture ' if mode=='attack' else 'Council: Hold ')+en,25,
     no('council_busy')+' '+no('council_cooldown')+' '+condition,
     flag('council_busy')+' '+flag('council_cooldown',90)+' '+flag(task)+f' set_variable = {{ hro_ops_council_days = 0 }}',
     f'Добровольная задача на {duration} дней. Награда: 80 ПВ, 50 опыта армии и 45 дней усиления '+('атаки +15%, планирования +25%.' if mode=='attack' else 'защиты +20%, восстановления организации +25%.')+' Провал: 30 дней стабильности −5%, планирования −10%. Повторное совещание через 90 дней.',
     f'Voluntary {duration}-day objective. Reward: 80 PP, 50 army XP and 45 days of '+('attack +15%, planning +25%.' if mode=='attack' else 'defence +20%, organisation recovery +25%.')+' Failure: stability −5%, planning −10% for 30 days. 90-day council cooldown.',vis)
    expired=f'check_variable = {{ hro_ops_council_days > {duration-1} }}'
    success=owns(vp) if mode=='attack' else owns(vp)+' '+expired
    failure=expired if mode=='attack' else 'NOT = { '+owns(vp)+' }'
    effects.append(f'''if = {{ limit = {{ {has(task)} }}
      if = {{ limit = {{ {success} }} {clear(task)} {clear('council_busy')} add_political_power = 80 army_experience = 50 {idea('council_'+mode,45)} }}
      else_if = {{ limit = {{ {failure} }} {clear(task)} {clear('council_busy')} {idea('council_failure',30)} }} }}''')
    decision('status_'+task,('Задача: взять ' if mode=='attack' else 'Задача: удержать ')+ru,
     ('Objective: Capture ' if mode=='attack' else 'Objective: Hold ')+en,0,'always = no','',
     f'Прошло дней: [?hro_ops_council_days|0]. Срок: {duration} дней. Потеря удерживаемого города проваливает задачу при ближайшей ежедневной проверке.',
     f'Elapsed days: [?hro_ops_council_days|0]. Deadline: {duration} days. Losing a defended city fails its objective at the next daily check.',vis+' '+has(task))
 decision('rest','Остановить наступление и перегруппироваться','Halt Offensive and Regroup',40,
  no('rest')+' OR = { '+has('active')+' '+has('exhaustion')+' }',
  clear('active')+' '+clear('assault_started')+' remove_ideas = hro_ops_idea_assault '+flag('rest',21)+' '+flag('rest_pending')+' '+idea('rest',21),
  '21 день: атака −15%, восстановление организации +30%, выпуск −5%, расход снабжения +30%. Текущая ступень истощения сохраняется до завершения, но больше не растёт; штрафы складываются с издержками перегруппировки. Затем истощение снимается. Срок запрета новой операции сохраняется.',
  '21 days: attack −15%, organisation recovery +30%, output −5%, supply use +30%. Existing exhaustion remains until completion, but stops escalating; its penalties stack with regrouping costs. Clears exhaustion on completion. Operation cooldown remains.')
 decision('security','Усилить охрану военных объектов','Strengthen Military Site Security',60,no('security'),flag('security',90)+' '+idea('security',90),
  'На 90 дней: ремонт +30%, урон диверсий этого мода уменьшается вдвое.',
  '90 days: repair +30%; halves damage from this mod’s sabotage.')
 fatigue_keys = ['exhaustion','exhaustion_2','exhaustion_3','exhaustion_4']
 fatigue_ids = ['hro_ops_idea_'+key for key in fatigue_keys]
 from generate_war_adaptation import _select, _remove
 fatigue_select = f"if = {{ limit = {{ check_variable = {{ hro_ops_exhaustion_days > 20 }} }} {_select(fatigue_ids,fatigue_ids[3])} }}"
 for threshold,tier in [(13,2),(6,1)]:
  fatigue_select += f" else_if = {{ limit = {{ check_variable = {{ hro_ops_exhaustion_days > {threshold} }} }} {_select(fatigue_ids,fatigue_ids[tier])} }}"
 fatigue_select += f" else = {{ {_select(fatigue_ids,fatigue_ids[0])} }}"
 effects.insert(0,f'''if = {{ limit = {{ {has('preparing')} }} add_to_variable = {{ hro_ops_preparation_days = 1 }} }}
 if = {{ limit = {{ {has('council_busy')} }} add_to_variable = {{ hro_ops_council_days = 1 }} }}
 if = {{ limit = {{ {has('exhaustion')} {has('exhaustion_initialized')} {no('rest')} }} add_to_variable = {{ hro_ops_exhaustion_days = 1 }} }}
 if = {{ limit = {{ {has('active')} has_country_flag = {{ flag = hro_ops_active days > 13 }} }} {clear('active')} remove_ideas = hro_ops_idea_assault }}
 if = {{ limit = {{ {has('assault_started')} {no('active')} }} {clear('assault_started')} {flag('exhaustion')} }}
 if = {{ limit = {{ {has('exhaustion')} {no('exhaustion_initialized')} }}
  {flag('exhaustion')} {flag('exhaustion_initialized')} set_variable = {{ hro_ops_exhaustion_days = 0 }} {_remove(fatigue_ids)}
 }}
 if = {{ limit = {{ {has('rest_pending')} {no('rest')} }} {clear('rest_pending')} {clear('exhaustion')} {clear('exhaustion_initialized')} {_remove(fatigue_ids)} }}
 if = {{ limit = {{ {has('exhaustion')} }} {fatigue_select} }}''')
 decision('exhaustion_status','Истощение наступления: состояние','Offensive Exhaustion: Status',0,'always = no','',
  'Дней истощения: [?hro_ops_exhaustion_days|0]. Ступени меняются через 7, 14 и 21 день истощения, максимум четвёртая. Во время перегруппировки рост остановлен. Штрафы сохраняются до завершения 21-дневной перегруппировки.',
  'Exhaustion days: [?hro_ops_exhaustion_days|0]. Tier upgrades after 7, 14 and 21 exhaustion days, capped at tier four. Regrouping freezes escalation; penalties remain until regrouping completes after 21 days.',has('exhaustion'))
 from decision_details import describe
 for language in loc:
  table = '\n'.join((f'Ступень {i}: ' if language=='russian' else f'Tier {i}: ') + describe(MODS[key][2],language) for i,key in enumerate(fatigue_keys,1))
  loc[language]['hro_ops_exhaustion_status_desc'] += '\n\n' + table
 # Clear pending work on peace, capitulation or the end of the supported campaign.
 all_flags=['preparing','ready','active','assault_started','exhaustion','rest','rest_pending','council_busy','sabotage_busy','sabotage_wait','exhaustion_initialized']
 for tag,targets in TARGETS.items():
  for state,*_ in targets:
   stem=f'{tag.lower()}_{state}'
   all_flags += ['prep_'+stem,'ready_'+stem,'council_attack_'+stem,'council_hold_'+stem]+[f'sabotage_{stem}_{b}' for b in ['air_base','infrastructure']]
 cleanup=' '.join(clear(f) for f in all_flags)+' '+' '.join('remove_ideas = hro_ops_idea_'+k for k in MODS if k!='security')
 legacy = ' '.join(clear(f'sabotage_{tag.lower()}_{state}_{b}') for tag,targets in TARGETS.items() for state,*_ in targets for b in ['air_base','infrastructure']) + ' ' + ' '.join(clear(f) for f in ['sabotage_busy','sabotage_wait','sabotage_cooldown'])
 put('common/scripted_effects/hro_operations_effects.txt','hro_ops_daily = { '+legacy+' if = { limit = { hro_war_eastern_war = yes } '+'\n'.join(effects)+' } else = { '+cleanup+' } }')
 put('common/on_actions/hro_operations_on_actions.txt','on_actions = { on_daily = { effect = { if = { limit = { OR = { original_tag = GER original_tag = SOV } } hro_ops_daily = yes } } } }')
 put('common/ideas/hro_operations_ideas.txt','ideas = { country = { '+'\n'.join(ideas)+' } }')
 put('common/decisions/categories/hro_operations_categories.txt','\n'.join(key+' = { icon = generic_army allowed = { OR = { original_tag = GER original_tag = SOV } } visible = { has_war = yes } }' for key in categories))
 by_id={script.split()[0]:script for script in decisions}
 put('common/decisions/hro_operations.txt','\n'.join(key+' = { '+'\n'.join(by_id[identity] for identity in ids)+' }' for key,ids in categories.items()))
 for lang,entries in loc.items():put(f'localisation/{lang}/hro_operations_l_{lang}.yml','l_'+lang+':\n'+''.join(f' {k}:0 {json.dumps(v,ensure_ascii=False)}\n' for k,v in entries.items()),True)
 return {'operation_preparation_days':35,'launch_window_days':45,'assault_days':14,'exhaustion_tiers':4,'exhaustion_step_days':7,'exhaustion_requires_regrouping':True,'regrouping_supply_consumption':.30,'operation_cooldown_days':90,'rest_days':21,'council_attack_days':75,'council_hold_days':60,'decisions':len(decisions),'national_operation_bonuses':True,'sabotage_in_agency':True,'legacy_sabotage_decisions':False}
