"""Finite Eastern-front phases: opening advantage, recovery, mature Soviet war."""
from pathlib import Path
import json
from decision_details import describe
from generate_war_adaptation import _select,_remove
PHASES={
 'GER':{
  'opening':{'army_attack_factor':.20,'army_defence_factor':.15,'army_org_factor':.10,'army_org_regain':.15,'planning_speed':.20,'supply_consumption_factor':-.05},
  'parity':{'army_attack_factor':.15,'army_defence_factor':.25,'army_org_factor':.10,'army_org_regain':.20,'planning_speed':.10},
  'mature':{'industrial_capacity_factory':-.05,'supply_consumption_factor':.05,'attrition':.05}},
 'SOV':{
  'opening':{'army_defence_factor':-.10,'army_attack_factor':-.05,'army_org_regain':-.15},
  'parity':{'army_defence_factor':-.30,'army_org_factor':-.05,'army_org_regain':-.55,'industrial_capacity_factory':-.05},
  'mature':{'army_attack_factor':.05,'army_defence_factor':.05,'industrial_capacity_factory':.05}}}
NAMES={
 'GER':{'opening':('Подготовленная Восточная кампания','Prepared Eastern Campaign'),'parity':('Стабилизация Восточного фронта','Stabilising the Eastern Front'),'mature':('Нагрузка затяжной войны','Burden of a Prolonged War')},
 'SOV':{'opening':('Армия переходного периода','Army in Transition'),'parity':('Освоение современной войны','Learning Modern Warfare'),'mature':('Зрелая военная система','Mature War System')}}
OPENING='OR = { date < 1942.1.1 check_variable = { hro_balance_war_days < 180 } }'
PARITY='OR = { date < 1943.1.1 check_variable = { hro_balance_war_days < 540 } }'

def identity(tag,phase):return 'hro_balance_'+tag.lower()+'_'+phase

def generate(output):
 output=Path(output);ideas=[];effects=[];loc={'russian':{},'english':{}}
 def put(path,s,bom=False):
  p=output/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s+'\n',encoding='utf-8-sig' if bom else 'utf-8')
 for tag,phases in PHASES.items():
  ids=[identity(tag,k) for k in phases]
  for phase,mods in phases.items():
   key=identity(tag,phase)
   ideas.append(f'{key} = {{ picture = generic_army allowed = {{ original_tag = {tag} }} removal_cost = -1 modifier = {{ '+' '.join(f'{k} = {v:g}' for k,v in mods.items())+' } }')
   for lang,n in [('russian',0),('english',1)]:
    loc[lang][key]=NAMES[tag][phase][n]
    rule=('Начальная фаза: до1942года или первых180военных дней. Средняя: до1943года или540военных дней. Зрелая: с1943года и после540военных дней. Действует ровно один этап, в мире и после капитуляции снимается; повторная война не сбрасывает опыт. ' if n==0 else 'Opening: before1942 or180war days. Recovery: before1943 or540war days. Mature: from1943 after540war days. Exactly one phase is active. Peace/capitulation removes the spirits without resetting experience. ')
    loc[lang][key+'_desc']=rule+describe(mods,lang)+('. Дней войны: [?hro_balance_war_days|0].' if n==0 else '. War days: [?hro_balance_war_days|0].')
  effects.append(f'''if = {{ limit = {{ original_tag = {tag} }}
   if = {{ limit = {{ hro_war_eastern_war = yes }}
    if = {{ limit = {{ {OPENING} }} {_select(ids,ids[0])} }}
    else_if = {{ limit = {{ {PARITY} }} {_select(ids,ids[1])} }}
    else = {{ {_select(ids,ids[2])} }}
   }} else = {{ {_remove(ids)} }}
  }}''')
 # Reuse saved Soviet count on update. After a capped old counter, infer ongoing-war age
 # from the old 1.0.0-free historical date only up to the phase boundaries; no rewards.
 initialize='''if = { limit = { NOT = { has_country_flag = hro_balance_initialized } }
  set_country_flag = hro_balance_initialized set_country_flag = { flag = hro_balance_day_checked value = 1 days = 1 } set_variable = { hro_balance_war_days = 0 }
  if = { limit = { original_tag = SOV has_country_flag = hro_war_sov_started }
   set_variable = { hro_balance_war_days = hro_war_sov_war_days }
  }
  if = { limit = { original_tag = GER has_country_flag = hro_off_ger_started }
   set_variable = { hro_balance_war_days = hro_off_ger_campaign_days }
  }
  if = { limit = { NOT = { date < 1942.1.1 } check_variable = { hro_balance_war_days > 119 } check_variable = { hro_balance_war_days < 180 } }
   set_variable = { hro_balance_war_days = 180 }
  }
  if = { limit = { NOT = { date < 1943.1.1 } check_variable = { hro_balance_war_days > 119 } }
   set_variable = { hro_balance_war_days = 540 }
  }
 }'''
 # Initialize on first actual war, not in 1936: old saves can carry capped counters.
 daily=f'''hro_campaign_balance_daily = {{
 if = {{ limit = {{ hro_war_eastern_war = yes }}
  {initialize}
  if = {{ limit = {{ NOT = {{ has_country_flag = hro_balance_day_checked }} }}
   set_country_flag = {{ flag = hro_balance_day_checked value = 1 days = 1 }}
   if = {{ limit = {{ check_variable = {{ hro_balance_war_days < 540 }} }} add_to_variable = {{ hro_balance_war_days = 1 }} }}
  }}
 }}
 {' '.join(effects)}
 }}'''
 put('common/ideas/hro_campaign_balance_ideas.txt','ideas = { country = { '+'\n'.join(ideas)+' } }')
 put('common/scripted_effects/hro_campaign_balance_effects.txt',daily)
 put('common/on_actions/hro_campaign_balance_on_actions.txt','on_actions = { on_daily = { effect = { hro_campaign_balance_daily = yes } } }')
 for lang,entries in loc.items():put(f'localisation/{lang}/hro_campaign_balance_l_{lang}.yml','l_'+lang+':\n'+''.join(f' {k}:0 {json.dumps(v,ensure_ascii=False)}\n' for k,v in entries.items()),True)
 return {'phases':PHASES,'opening_min_war_days':180,'mature_min_war_days':540,'calendar_limits':[1942,1943],'old_save_phase_inferred':True,'one_phase_per_country':True,'runtime_verified':False}
