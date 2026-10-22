"""Native agency operations with guarded in-flight sabotage waves.

ROOT is the actor. Native callbacks enter an operation scope, so explicitly
return to ROOT before touching country flags. Each actor has one shared slot;
targets are the actual opposing GER/SOV country, never global event targets.
"""
import json
from pathlib import Path
from clausewitz import parse

MISSIONS = {
 'air': {'ru':'Разгром аэродромной сети','en':'Disrupt the Airfield Network','days':60,'network':60,'risk':.30,
         'equipment':{'infantry_equipment':600,'support_equipment':150},'factories':4,'preparation':35,
         'damage':{'air_base':6},'picture':'army'},
 'logistics': {'ru':'Парализовать военную логистику','en':'Cripple Military Logistics','days':75,'network':70,'risk':.35,
         'equipment':{'infantry_equipment':800,'support_equipment':200,'motorized_equipment':100},'factories':5,'preparation':45,
         'damage':{'infrastructure':3,'rail_way':5,'supply_node':1},'picture':'industry'},
}
PRIORITIES={'SOV':[195,219,202,206,217,221,227,572], 'GER':[64,51,67,65,66,60]}
WAVE_DAYS=(15,35)
COOLDOWN=150


def flag(name):return 'hro_agency_'+name

def generate(output):
 output=Path(output);loc={'russian':{},'english':{}};effects=[];operations=[];daily=[]
 def put(path,value,bom=False):
  p=output/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(value+'\n',encoding='utf-8-sig' if bom else 'utf-8')
 def text(key,ru,en):loc['russian'][key]=ru;loc['english'][key]=en
 def setflag(name,days=None):return 'set_country_flag = '+(f'{{ flag = {flag(name)} value = 1 days = {days} }}' if days else flag(name))
 def has(name):return 'has_country_flag = '+flag(name)
 def clear(name):return 'clr_country_flag = '+flag(name)
 def no(name):return 'NOT = { '+has(name)+' }'
 text('hro_agency_requirements','Нужны агентство, война Германии с СССР, два агента, сеть и ресурсы подготовки. Для каждой миссии — 150 дней кулдауна после завершения; подготовка кулдаун не включает.',
      'Requires an agency, the German-Soviet war, two operatives, a network and preparation resources. Each mission has its own 150-day cooldown after completion.')
 for phase,ru,en,dr,de in [
  ('infiltration','Проникновение диверсионных групп','Infiltrate Sabotage Teams','Группы проникают в тыл и выбирают объекты. Первая волна — после 15 дней выполнения.', 'Teams infiltrate rear areas and identify sites. The first wave occurs after 15 execution days.'),
  ('demolition','Согласованные подрывы','Coordinated Demolitions','На 35-й день начинается вторая волна ударов. Повреждённые объекты противник может ремонтировать.', 'The second wave occurs on execution day 35. The enemy can repair damaged sites.'),
  ('exfiltration','Завершающий удар и отход','Final Strike and Extraction','Последняя волна наносится при завершении операции. Группы выходят из района действий.', 'The final wave hits on operation completion. Teams withdraw from the area.')]:
  key='hro_agency_phase_'+phase
  text(key+'_name',ru,en);text(key+'_desc',dr,de);text(key+'_outcome',ru+': этап завершён.',en+': phase completed.')
 phases=[]
 for phase in ('infiltration','demolition','exfiltration'):
  key='hro_agency_phase_'+phase
  phases.append(f'{key} = {{ name = {key}_name desc = {key}_desc outcome = {key}_outcome icon = GFX_hro_agency_air picture = GFX_hro_agency_logistics }}')
 for kind,m in MISSIONS.items():
  identity='hro_operation_'+kind
  text(identity+'_name',m['ru'],m['en'])
  damage_ru='авиабазам до 6 уровней' if kind=='air' else 'инфраструктуре до 3 уровней, железным дорогам до 5, узлам снабжения до 1'
  damage_en='up to 6 air base levels' if kind=='air' else 'up to 3 infrastructure, 5 railway and 1 supply hub levels'
  equipment_ru=', '.join({'infantry_equipment':'пехотного снаряжения','support_equipment':'дополнительного оснащения','motorized_equipment':'грузовиков'}[k]+f': {v}' for k,v in m['equipment'].items())
  desc_ru=(f"Два агента, разведсеть {m['network']}%. Ресурсы подготовки: {equipment_ru}; гражданские фабрики: {m['factories']} на {m['preparation']} дней. Базовое выполнение — {m['days']} дней; навыки и модификаторы могут изменить срок и цену. Три волны: на 15-й, 35-й день выполнения и при завершении. Каждая волна поражает до шести разных областей противника, приоритет — крупные военные центры. Урон в каждой области: {damage_ru}. Между волнами область может стать целью снова. Всё ремонтируется; охрана объектов уменьшает урон вдвое. Действует только по реально контролируемым противником объектам. При отмене будущие волны прекращаются; уже нанесённый урон сохраняется. Риск для агентов обрабатывается игрой. 150 дней после завершения этой миссии.")
  desc_en=(f"Two operatives, {m['network']}% network. Base execution: {m['days']} days. Preparation uses equipment and {m['factories']} civilian factories for {m['preparation']} days; skills may modify costs and duration. Three waves on execution days 15, 35 and completion. Each wave hits up to six distinct enemy-controlled states: {damage_en} per state. Major centres are prioritised. States may be hit again in later waves. All damage is repairable; site security halves damage. Cancellation stops future waves, but does not undo damage. Native operation risk applies. 150-day cooldown after completion.")
  text(identity+'_desc',desc_ru,desc_en)
  text(identity+'_reward',f'Три волны, до 6 областей в каждой: {damage_ru} на область. Урон ремонтируемый, охрана снижает его вдвое. Нет мгновенного урона при выборе или подготовке.',
       f'Three waves, up to 6 states each: {damage_en} per state. Repairable damage; site security halves it. No damage on selection or during resource preparation.')
  actor_check='OR = { AND = { original_tag = GER FROM = { original_tag = SOV } } AND = { original_tag = SOV FROM = { original_tag = GER } } }'
  base_requirements='hro_war_eastern_war = yes has_intelligence_agency = yes '+actor_check
  available=base_requirements+' OR = { '+no(kind+'_cooldown')+' '+has('ger_'+kind+'_planned')+' '+has('sov_'+kind+'_planned')+' }'
  callback=lambda action:'ROOT = { '+ ' '.join(f'if = {{ limit = {{ original_tag = {tag} }} hro_agency_{tag.lower()}_{kind}_{action} = yes }}' for tag in ('GER','SOV'))+' }'
  phases_script=' '.join('phases = { hro_agency_phase_'+phase+' = { base = 1 } }' for phase in ('infiltration','demolition','exfiltration'))
  resources=' '.join(f'{k} = {v}' for k,v in m['equipment'].items())
  operations.append(f'''{identity} = {{
   name = {identity}_name desc = {identity}_desc icon = GFX_hro_agency_{kind} map_icon = GFX_hro_agency_{kind}
   priority = 90 days = {m['days']} operatives = 2 network_strength = {m['network']} risk_chance = {m['risk']} danger_level = 2 experience = 0.1
   scale_cost_independent_of_target = yes
   allowed = {{ OR = {{ original_tag = GER original_tag = SOV }} }}
   operation_target = {{ targets = {{ GER SOV }} }}
   visible = {{ {actor_check} }}
   available = {{ {available} }}
   requirements = {{ custom_trigger_tooltip = {{ tooltip = hro_agency_requirements {base_requirements} }} }}
   equipment = {{ {resources} civilian_factories = {{ amount = {m['factories']} days = {m['preparation']} }} }}
   {phases_script}
   on_start = {{ {callback('start')} }}
   outcome_potential = {{ ROOT = {{ custom_effect_tooltip = {identity}_reward }} }}
   outcome_execute = {{ {callback('finish')} }}
   ai_will_do = {{ factor = 0 }}
  }}''')
  for actor,target in [('GER','SOV'),('SOV','GER')]:
   stem=f'{actor.lower()}_{kind}';active=stem+'_active';planned=stem+'_planned';counter='hro_agency_'+stem+'_days'
   cleanup=' '.join(clear(name) for name in [active,planned])
   effects.append(f'''hro_agency_{stem}_start = {{
    hro_runtime_seed = yes
    if = {{ limit = {{ original_tag = {actor} hro_war_eastern_war = yes {no(planned)} {no(active)} {no(kind+'_cooldown')} }}
     {setflag(planned)} set_variable = {{ {counter} = 0 }}
     {' '.join(clear(stem+'_wave_'+str(i)) for i in (1,2,3))}
    }}
   }}''')
   target_valid=f'{target} = {{ has_war_with = ROOT has_capitulated = no }}'
   eligible=('air_base > 0' if kind=='air' else 'OR = { rail_way > 0 supply_node > 0 infrastructure > 2 }')
   protected=f'{target} = {{ has_country_flag = hro_ops_security }}'
   def strike(multiplier):
    return ' '.join(f'if = {{ limit = {{ {building} > 0 }} damage_building = {{ type = {building} damage = {amount*multiplier:g} }} }}' for building,amount in m['damage'].items())
   hitflag='hro_agency_'+kind+'_recent_hit'
   reset=f'{target} = {{ every_controlled_state = {{ clr_state_flag = {hitflag} }} }}'
   attack=f'''{target} = {{ random_controlled_state = {{
     prioritize = {{ {' '.join(map(str,PRIORITIES[target]))} }}
     limit = {{ is_fully_controlled_by = PREV {eligible} NOT = {{ has_state_flag = {hitflag} }} }}
     set_state_flag = {{ flag = {hitflag} value = 1 days = 1 }}
     if = {{ limit = {{ {protected} }} {strike(.5)} }} else = {{ {strike(1)} }}
   }} }}'''
   for wave in (1,2,3):
    marker=stem+'_wave_'+str(wave)
    effects.append(f'''hro_agency_{stem}_wave_{wave} = {{
     if = {{ limit = {{ original_tag = {actor} hro_war_eastern_war = yes OR = {{ {has(active)} {has(planned)} }} {no(marker)} {target_valid} }}
      {setflag(marker)} {reset} {attack} {attack} {attack} {attack} {attack} {attack}
     }}
    }}''')
   effects.append(f'''hro_agency_{stem}_finish = {{
    if = {{ limit = {{ original_tag = {actor} OR = {{ {has(active)} {has(planned)} }} }}
     hro_agency_{stem}_wave_1 = yes hro_agency_{stem}_wave_2 = yes hro_agency_{stem}_wave_3 = yes
     {setflag(kind+'_cooldown',COOLDOWN)} {cleanup}
    }}
   }}''')
   daily.append(f'''if = {{ limit = {{ original_tag = {actor} OR = {{ {has(active)} {has(planned)} }} }}
    if = {{ limit = {{ NOT = {{ hro_war_eastern_war = yes {target_valid} }} }} {cleanup} }}
    else_if = {{ limit = {{ is_running_operation = {{ target = {target} operation = {identity} }} has_finished_collecting_for_operation = {{ target = {target} operation = {identity} }} }}
     if = {{ limit = {{ {no(active)} }} {setflag(active)} }}
     add_to_variable = {{ {counter} = 1 }}
     if = {{ limit = {{ check_variable = {{ {counter} > 14 }} }} hro_agency_{stem}_wave_1 = yes }}
     if = {{ limit = {{ check_variable = {{ {counter} > 34 }} }} hro_agency_{stem}_wave_2 = yes }}
    }} else_if = {{ limit = {{ {has(active)} }} {setflag(kind+'_cooldown',COOLDOWN)} {cleanup} }}
   }}''')
 put('common/operations/hro_agency_operations.txt','\n'.join(operations))
 put('common/operation_phases/hro_agency_phases.txt','\n'.join(phases))
 migration=' '.join(f'if = {{ limit = {{ original_tag = {actor} has_country_flag = hro_agency_{actor.lower()}_{kind}_active NOT = {{ has_country_flag = hro_agency_{actor.lower()}_{kind}_planned }} }} set_country_flag = hro_agency_{actor.lower()}_{kind}_planned clr_country_flag = hro_agency_{actor.lower()}_{kind}_active }}' for actor in ('GER','SOV') for kind in MISSIONS)
 put('common/scripted_effects/hro_agency_effects.txt','\n'.join(effects)+'\nhro_agency_daily = { if = { limit = { NOT = { has_country_flag = hro_agency_lifecycle_081 } } set_country_flag = hro_agency_lifecycle_081 clr_country_flag = hro_agency_busy clr_country_flag = hro_agency_cooldown '+migration+' } '+' '.join(daily)+' }')
 put('common/on_actions/hro_agency_on_actions.txt','on_actions = { on_daily = { effect = { if = { limit = { OR = { original_tag = GER original_tag = SOV } } hro_agency_daily = yes } } } }')
 put('interface/hro_agency_icons.gfx','spriteTypes = { spriteType = { name = "GFX_hro_agency_air" texturefile = "gfx/interface/ideas/hro_spirit_army.dds" } spriteType = { name = "GFX_hro_agency_logistics" texturefile = "gfx/interface/ideas/hro_spirit_industry.dds" } }')
 for lang,entries in loc.items():put(f'localisation/{lang}/hro_agency_l_{lang}.yml','l_'+lang+':\n'+''.join(f' {k}:0 {json.dumps(v,ensure_ascii=False)}\n' for k,v in entries.items()),True)
 return {'native_operations':len(MISSIONS),'native_phases':len(phases),'agents':2,'waves':3,'first_waves_execution_days':list(WAVE_DAYS),'final_wave':'native outcome_execute','states_per_wave':6,'completion_cooldown_days':COOLDOWN,'preparation_does_not_lock_execution':True,'missions':MISSIONS,'repairable_damage':True,'risk_handled_by_engine':True,'ai_enabled':False}


def audit_operations(output):
 """Audit native operation/phase references and owned presentation resources."""
 from clausewitz import walk
 output=Path(output);path=output/'common/operations/hro_agency_operations.txt'
 if not path.exists():return []  # Synthetic validator fixtures need no agency content.
 errors=[];operations={n.key:n for n in parse(path.read_text())}
 phases_path=output/'common/operation_phases/hro_agency_phases.txt'
 phases={n.key:n for n in parse(phases_path.read_text())} if phases_path.exists() else {}
 sprites={}
 for p in (output/'interface').glob('*.gfx'):
  for top in parse(p.read_text()):
   for node in top.all('spriteType'):
    sprites[str(node.scalar('name')).strip('"')]=str(node.scalar('texturefile')).strip('"')
 for key,operation in operations.items():
  for field in ('name','desc','days','operatives','network_strength','risk_chance','equipment','available','requirements','on_start','outcome_execute','outcome_potential'):
   if operation.one(field) is None:errors.append(f'Agency operation missing {field}: {key}')
  if operation.one('on_start') and operation.one('on_start').one('ROOT') is None:errors.append(f'Agency start must enter actor ROOT: {key}')
  if operation.one('outcome_execute') and operation.one('outcome_execute').one('ROOT') is None:errors.append(f'Agency outcome must enter actor ROOT: {key}')
  if len(operation.all('phases'))!=3:errors.append(f'Agency operation needs three phases: {key}')
  for node in operation.all('phases'):
   for phase in node.value:
    if phase.key not in phases:errors.append(f'Unknown agency phase: {phase.key}')
  for node in walk(operation.value):
   if node.key in ('icon','map_icon'):
    if node.value not in sprites or not (output/sprites.get(node.value,'missing')).is_file():errors.append(f'Missing agency sprite: {node.value}')
 for key,phase in phases.items():
  for field in ('name','desc','outcome','icon','picture'):
   if phase.one(field) is None:errors.append(f'Agency phase missing {field}: {key}')
  for field in ('icon','picture'):
   if phase.scalar(field) not in sprites or not (output/sprites.get(phase.scalar(field),'missing')).is_file():errors.append(f'Missing agency phase sprite: {key}/{field}')
 for p in (output/'common').rglob('hro*.txt'):
  for node in walk(parse(p.read_text())):
   if node.key=='is_running_operation' and node.scalar('operation','').startswith('hro_') and node.scalar('operation') not in operations:errors.append(f'Unknown agency operation reference: {node.scalar("operation")}')
 return errors
