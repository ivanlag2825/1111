"""One-shot emergency recruitment after two simultaneous enemy-held city losses."""
from itertools import combinations
from pathlib import Path
import json
CITIES={'SOV':[(219,6380,'Москва','Moscow'),(195,3151,'Ленинград','Leningrad'),(202,525,'Киев','Kyiv'),(217,3529,'Сталинград','Stalingrad')],
        'GER':[(64,6521,'Берлин','Berlin'),(58,9347,'Гамбург','Hamburg'),(4,11666,'Вена','Vienna'),(52,692,'Мюнхен','Munich')]}
MODIFIERS={'training_time_army_factor':-.90,'minimum_training_level':-.19,'conscription':.05,'stability_factor':-.30,'war_support_factor':-.40,'industrial_capacity_factory':-.80}
DAYS=182

def validate_geography(game):
 from clausewitz import parse
 states={}
 for p in (Path(game)/'history/states').glob('*.txt'):
  n=next((n for n in parse(p.read_text(encoding='utf-8-sig')) if n.key=='state'),None)
  if n:states[int(n.scalar('id'))]=n
 for cities in CITIES.values():
  for state,vp,*_ in cities:
   if state not in states or not any(n.value[0].value==str(vp) and float(n.value[1].value)>=10 for n in states[state].one('history').all('victory_points')):raise ValueError(f'Invalid last-chance city: {state}/{vp}')
 return True

def generate(output):
 output=Path(output);loc={'russian':{},'english':{}};decisions=[];ideas=[];triggers=[];effects=[];daily=[]
 def put(path,text,bom=False):
  p=output/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text+'\n',encoding='utf-8-sig' if bom else 'utf-8')
 for tag,cities in CITIES.items():
  stem='hro_last_chance_'+tag.lower();idea=stem+'_idea';eligible=stem+'_eligible';used=stem+'_used';grant=stem+'_grant';losses=[]
  for state,vp,*_ in cities:
   seen=stem+'_held_'+str(vp)
   daily.append(f'if = {{ limit = {{ original_tag = {tag} controls_province = {vp} }} set_country_flag = {seen} }}')
   losses.append(f'AND = {{ OR = {{ has_country_flag = {seen} {state} = {{ is_owned_by = ROOT }} }} any_enemy_country = {{ controls_province = {vp} }} }}')
  pairs=' '.join('AND = { '+a+' '+b+' }' for a,b in combinations(losses,2))
  condition=f'original_tag = {tag} has_war = yes has_capitulated = no NOT = {{ has_country_flag = {used} }} OR = {{ {pairs} }}'
  triggers.append(f'{eligible} = {{ {condition} }}')
  effects.append(f'{grant} = {{ if = {{ limit = {{ {eligible} = yes }} set_country_flag = {used} add_timed_idea = {{ idea = {idea} days = {DAYS} }} }} }}')
  ideas.append(f'{idea} = {{ picture = generic_army allowed = {{ original_tag = {tag} }} removal_cost = -1 modifier = {{ '+ ' '.join(f'{k} = {v:g}' for k,v in MODIFIERS.items())+' } }')
  decisions.append(f'{stem} = {{ icon = generic_army allowed = {{ original_tag = {tag} }} visible = {{ has_war = yes NOT = {{ has_country_flag = {used} }} }} available = {{ {eligible} = yes }} cost = 0 fire_only_once = yes complete_effect = {{ {grant} = yes }} ai_will_do = {{ factor = 0 }} }}')
  for lang,n in [('russian',2),('english',3)]:
   title='Агония правительства: последний шанс' if n==2 else 'Government Agony: The Last Chance'
   names=', '.join(c[n] for c in cities)
   desc=(f'Один раз за кампанию, бесплатно. Не капитулировавшая страна воюет; враг одновременно контролирует любые два города: {names}. Город должен ранее находиться под нашим контролем или принадлежать нам; передача союзнику не считается. На {DAYS} дня: время обучения армии −90%, минимальная подготовка для развёртывания −19 процентных пунктов (с базовых 20% до 1%), военнообязанное население +5 процентных пунктов, стабильность −30%, поддержка войны −40%, объём заводского производства −80%. Все эффекты действуют вместе и истекают вместе. Другие модификаторы обучения и порога подготовки продолжают складываться. Потеря городов не выдаёт дух автоматически: нужно принять решение. Повторное применение невозможно.' if n==2 else f'Once per campaign, free. While at war and not capitulated, enemies must simultaneously hold any two of: {names}. Cities must previously have been controlled or still be owned by us; allied handovers do not count. For {DAYS} days: army training time −90%, minimum deployment training −19 percentage points (base 20% becomes 1%), recruitable population +5 percentage points, stability −30%, war support −40%, factory output −80%. All effects expire together. Other modifiers still stack. Activate the decision to receive the spirit; it is not automatic and cannot be repeated.')
   loc[lang].update({stem:title,stem+'_desc':desc,idea:title,idea+'_desc':desc,'hro_last_chance_category':'Чрезвычайная мобилизация' if n==2 else 'Emergency Mobilisation','hro_last_chance_category_desc':'Последние резервы ценой глубокого кризиса производства и общества.' if n==2 else 'Last reserves at a severe industrial and social cost.'})
 put('common/ideas/hro_last_chance_ideas.txt','ideas = { country = { '+'\n'.join(ideas)+' } }')
 put('common/decisions/categories/hro_last_chance_categories.txt','hro_last_chance_category = { icon = generic_army allowed = { OR = { original_tag = GER original_tag = SOV } } }')
 put('common/decisions/hro_last_chance.txt','hro_last_chance_category = { '+'\n'.join(decisions)+' }')
 put('common/scripted_triggers/hro_last_chance_triggers.txt','\n'.join(triggers))
 put('common/scripted_effects/hro_last_chance_effects.txt','\n'.join(effects)+'\nhro_last_chance_daily = { '+' '.join(daily)+' }')
 put('common/on_actions/hro_last_chance_on_actions.txt','on_actions = { on_daily = { effect = { hro_last_chance_daily = yes } } }')
 for lang,entries in loc.items():put(f'localisation/{lang}/hro_last_chance_l_{lang}.yml','l_'+lang+':\n'+''.join(f' {k}:0 {json.dumps(v,ensure_ascii=False)}\n' for k,v in entries.items()),True)
 return {'duration_days':DAYS,'one_time':True,'cities':CITIES,'modifiers':MODIFIERS,'simultaneous_enemy_losses':2,'base_training_level':.20,'minimum_training_level_delta':-.19,'runtime_verified':False}
