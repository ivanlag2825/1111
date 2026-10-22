"""Consumer-goods relief and bounded growth for MEFO and conquest economy."""
from pathlib import Path
import json
from generate_war_adaptation import _select,_remove
RELIEF={1:{'consumer_goods_factor':-.20,'consumer_goods_expected_value':-.02},2:{'consumer_goods_factor':-.35,'consumer_goods_expected_value':-.03},3:{'consumer_goods_factor':-.50,'consumer_goods_expected_value':-.04}}
ACTIVE='original_tag = GER OR = { has_dynamic_modifier = { modifier = GER_economy_of_conquest_modifier } AND = { NOT = { has_idea = GER_mefo_bills_ended } OR = { has_dynamic_modifier = { modifier = GER_mefo_bills_modifier } has_idea = GER_mefo_bills } } }'
CAPS={1:(.25,.01),2:(.10,.005),3:(0,0)}
def generate(output):
 output=Path(output);ids=['hro_mefo_relief_'+str(i) for i in RELIEF];ideas=[];loc={'russian':{},'english':{}}
 def put(path,s,bom=False):
  p=output/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s+'\n',encoding='utf-8-sig' if bom else 'utf-8')
 for tier,mods in RELIEF.items():
  key=ids[tier-1];ideas.append(f'{key} = {{ picture = generic_army allowed = {{ original_tag = GER }} removal_cost = -1 modifier = {{ '+' '.join(f'{k} = {v:g}' for k,v in mods.items())+' } }')
  for lang,n in [('russian',0),('english',1)]:
   loc[lang][key]=('MEFO и экономика завоевания: послабление ' if n==0 else 'MEFO and Conquest Economy Relief ')+str(tier)
 # Clamp only harmful positive values. Native reductions remain untouched;
 # original payment, debt and decision effects are retained by the base tree.
 caps=[]
 for tier,(load,growth) in CAPS.items():
  caps.append(f'''hro_mefo_bound_{tier} = {{
   if = {{ limit = {{ check_variable = {{ GER_industrial_consumer_goods_factor > {load:g} }} }} set_variable = {{ GER_industrial_consumer_goods_factor = {load:g} }} }}
   if = {{ limit = {{ check_variable = {{ GER_monthly_consumer_goods_increase > {growth:g} }} }} set_variable = {{ GER_monthly_consumer_goods_increase = {growth:g} }} }}
  }}''')
  for lang in loc:
   ru=(f'Пока действуют MEFO или «Экономика завоевания»: множитель потребительских товаров {RELIEF[tier]["consumer_goods_factor"]*100:+g}%, ожидаемая доля {RELIEF[tier]["consumer_goods_expected_value"]*100:+g} п.п. Ежедневно ограничивает положительную нагрузку экономического духа до {load*100:g}%, месячный рост до {growth*100:g} п.п. Отрицательные значения не ухудшаются. Ступень 1 сразу, 2 после «Единых комплектов поставок», 3 после «Арсенала затяжной войны». Один дух, без сложения. Законы и прочие модификаторы всё ещё влияют на итоговое число фабрик.')
   en=(f'While MEFO or Economy of Conquest is active: consumer goods factor {RELIEF[tier]["consumer_goods_factor"]*100:+g}%, expected share {RELIEF[tier]["consumer_goods_expected_value"]*100:+g} pp. Daily positive economic burden cap {load*100:g}%; monthly growth cap {growth*100:g} pp. Negative values are not increased. Tier 1 immediately, tier 2 after Supplier Standards, tier 3 after Arsenal. One non-stacking tier. Laws and other modifiers still affect actual factories.')
   loc[lang][ids[tier-1]+'_desc']=ru if lang=='russian' else en
   if tier>1:loc[lang][f'hro_mefo_stage{tier}_tt']=loc[lang][ids[tier-1]+'_desc']
 effect='\n'.join(caps)+f'''\nhro_mefo_relief_daily = {{
 if = {{ limit = {{ {ACTIVE} }}
  if = {{ limit = {{ has_completed_focus = hro_ger_mature_procurement }} {_select(ids,ids[2])} hro_mefo_bound_3 = yes }}
  else_if = {{ limit = {{ has_completed_focus = hro_ger_supplier_standards }} {_select(ids,ids[1])} hro_mefo_bound_2 = yes }}
  else = {{ {_select(ids,ids[0])} hro_mefo_bound_1 = yes }}
 }} else = {{ {_remove(ids)} }}
 }}'''
 put('common/ideas/hro_mefo_relief_ideas.txt','ideas = { country = { '+'\n'.join(ideas)+' } }')
 put('common/scripted_effects/hro_mefo_relief_effects.txt',effect)
 put('common/on_actions/hro_mefo_relief_on_actions.txt','on_actions = { on_daily = { effect = { hro_mefo_relief_daily = yes } } }')
 for lang,entries in loc.items():put(f'localisation/{lang}/hro_mefo_relief_l_{lang}.yml','l_'+lang+':\n'+''.join(f' {k}:0 {json.dumps(v,ensure_ascii=False)}\n' for k,v in entries.items()),True)
 return {'stages':RELIEF,'active_systems':['GER_mefo_bills_modifier','GER_economy_of_conquest_modifier','GER_mefo_bills'], 'positive_burden_and_monthly_growth_caps':CAPS,'native_variables_unchanged':False,'one_stage_at_a_time':True}
