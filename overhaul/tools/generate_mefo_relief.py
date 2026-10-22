"""Conditional consumer-goods relief while native MEFO bills remain active."""
from pathlib import Path
import json
from generate_war_adaptation import _select,_remove
RELIEF={1:{'consumer_goods_factor':-.20,'consumer_goods_expected_value':-.02},2:{'consumer_goods_factor':-.35,'consumer_goods_expected_value':-.03},3:{'consumer_goods_factor':-.50,'consumer_goods_expected_value':-.04}}
ACTIVE='original_tag = GER NOT = { has_idea = GER_mefo_bills_ended } OR = { has_dynamic_modifier = { modifier = GER_mefo_bills_modifier } has_idea = GER_mefo_bills }'
def generate(output):
 output=Path(output);ids=['hro_mefo_relief_'+str(i) for i in RELIEF];ideas=[];loc={'russian':{},'english':{}}
 def put(path,s,bom=False):
  p=output/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s+'\n',encoding='utf-8-sig' if bom else 'utf-8')
 for tier,mods in RELIEF.items():
  key=ids[tier-1];ideas.append(f'{key} = {{ picture = generic_army allowed = {{ original_tag = GER }} removal_cost = -1 modifier = {{ '+' '.join(f'{k} = {v:g}' for k,v in mods.items())+' } }')
  for lang,n in [('russian',0),('english',1)]:
   loc[lang][key]=('Обслуживание векселей MEFO: ' if n==0 else 'MEFO Debt Relief: ')+str(tier)
   loc[lang][key+'_desc']=(f'Пока действуют исходные векселя MEFO: множитель фабрик на потребительские товары {mods["consumer_goods_factor"]*100:+g}%, ожидаемая доля потребительских товаров {mods["consumer_goods_expected_value"]*100:+g}п.п. Ступень1сразу; ступень2после «Стандартов военных поставщиков»; ступень3после «Арсенала затяжной войны». Действует один дух; предыдущая ступень заменяется. После окончания MEFO послабление снимается. Исходные долг, рост обязательств, решения и выплаты сохраняются. Это не обещание уменьшить конечное число занятых фабрик ровно на указанный процент: действуют законы, другие модификаторы и минимум игры.' if n==0 else f'While native MEFO bills are active: consumer-goods factor {mods["consumer_goods_factor"]*100:+g}%, expected consumer-goods share {mods["consumer_goods_expected_value"]*100:+g}percentage points. Tier1immediately; tier2after Supplier Standards; tier3after Arsenal for a Prolonged War. Exactly one tier; relief ends when MEFO ends. Native debt, growth, decisions and payments remain. Actual factory savings depend on laws, other modifiers and the engine minimum.')
 for lang in loc:
  for tier in (2,3):
   mods=RELIEF[tier]
   loc[lang][f'hro_mefo_stage{tier}_tt']=(f'Если продолжают действовать MEFO, со следующей ежедневной проверки: ступень{tier}, множитель потребительских товаров{mods["consumer_goods_factor"]*100:+g}%, ожидаемая доля{mods["consumer_goods_expected_value"]*100:+g}п.п. Заменяет предыдущую ступень, после окончания MEFO снимается.' if lang=='russian' else f'If MEFO is still active, from the next daily check: relief tier{tier}, consumer-goods factor{mods["consumer_goods_factor"]*100:+g}%, expected share{mods["consumer_goods_expected_value"]*100:+g}pp. Replaces the earlier tier and ends with MEFO.')
 effect=f'''hro_mefo_relief_daily = {{
 if = {{ limit = {{ {ACTIVE} }}
  if = {{ limit = {{ has_completed_focus = hro_ger_mature_procurement }} {_select(ids,ids[2])} }}
  else_if = {{ limit = {{ has_completed_focus = hro_ger_supplier_standards }} {_select(ids,ids[1])} }}
  else = {{ {_select(ids,ids[0])} }}
 }} else = {{ {_remove(ids)} }}
 }}'''
 put('common/ideas/hro_mefo_relief_ideas.txt','ideas = { country = { '+'\n'.join(ideas)+' } }')
 put('common/scripted_effects/hro_mefo_relief_effects.txt',effect)
 put('common/on_actions/hro_mefo_relief_on_actions.txt','on_actions = { on_daily = { effect = { hro_mefo_relief_daily = yes } } }')
 for lang,entries in loc.items():put(f'localisation/{lang}/hro_mefo_relief_l_{lang}.yml','l_'+lang+':\n'+''.join(f' {k}:0 {json.dumps(v,ensure_ascii=False)}\n' for k,v in entries.items()),True)
 return {'stages':RELIEF,'only_while_native_mefo_active':True,'native_variables_unchanged':True,'one_stage_at_a_time':True}
