"""One-time, donor-validated assistance at the first Eastern-war observation."""
import json
from pathlib import Path

AID=[dict(actor='SOV',donor='MON',key='mongolian_horses',event='hro.820',
          ru='Монголия поставляет нам коней для армии',en='Mongolia Supplies Horses for Our Army',
          dr='Монгольские поставки лошадей помогают снабдить и пополнить кавалерийские части Красной армии. На 365 дней: атака кавалерии +20%. Бонус относится к кавалерии, не ко всей армии. Помощь выдаётся один раз.',
          de='Mongolian horse deliveries support Red Army cavalry. For 365 days: cavalry attack +20%, not a national army-wide attack bonus. This aid is granted once.',
          mods={'modifier_army_sub_unit_cavalry_attack_factor':.20}),
     dict(actor='GER',donor='ROM',key='romanian_fuel',event='hro.821',
          ru='Румыния помогает нам',en='Romania Helps Us',
          dr='Румынские поставки нефти поддерживают сухопутные операции. На 365 дней: расход топлива армией −20%. Расход топлива авиацией и флотом не меняется. Помощь выдаётся один раз.',
          de='Romanian oil deliveries support land operations. For 365 days: army fuel consumption −20%. Air and naval fuel consumption are unchanged. This aid is granted once.',
          mods={'army_fuel_consumption_factor':-.20})]


def generate(output):
 output=Path(output);ideas=[];effects=[];events=['add_namespace = hro'];loc={'russian':{},'english':{}}
 def put(path,text,bom=False):
  p=output/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text+'\n',encoding='utf-8-sig' if bom else 'utf-8')
 for a in AID:
  key='hro_aid_'+a['key'];idea=key+'_idea';issued=key+'_issued';seen=key+'_seen'
  valid=f"{a['donor']} = {{ exists = yes has_capitulated = no NOT = {{ has_war_with = ROOT }} }}"
  for lang,name,desc in [('russian',a['ru'],a['dr']),('english',a['en'],a['de'])]:
   loc[lang].update({idea:name,idea+'_desc':desc,a['event']+'.t':name,a['event']+'.d':desc,a['event']+'.a':'Принять помощь.' if lang=='russian' else 'Accept the assistance.'})
  ideas.append(f"{idea} = {{ picture = generic_army allowed = {{ original_tag = {a['actor']} }} removal_cost = -1 modifier = {{ "+' '.join(f'{k} = {v:g}' for k,v in a['mods'].items())+' } }')
  effects.append(f'''if = {{ limit = {{ original_tag = {a['actor']} hro_war_eastern_war = yes NOT = {{ has_country_flag = {seen} }} }}
   set_country_flag = {seen}
   if = {{ limit = {{ {valid} }} country_event = {{ id = {a['event']} days = 1 }} }}
  }}''')
  events.append(f'''country_event = {{ id = {a['event']} title = {a['event']}.t desc = {a['event']}.d is_triggered_only = yes fire_only_once = yes
   immediate = {{ if = {{ limit = {{ original_tag = {a['actor']} hro_war_eastern_war = yes {valid} NOT = {{ has_country_flag = {issued} }} }}
    set_country_flag = {issued} add_timed_idea = {{ idea = {idea} days = 365 }}
   }} }}
   option = {{ name = {a['event']}.a show_ideas_tooltip = {idea} }}
  }}''')
 put('common/ideas/hro_allied_aid_ideas.txt','ideas = { country = { '+'\n'.join(ideas)+' } }')
 put('common/scripted_effects/hro_allied_aid_effects.txt','hro_allied_aid_daily = { '+'\n'.join(effects)+' }')
 put('common/on_actions/hro_allied_aid_on_actions.txt','on_actions = { on_daily = { effect = { hro_allied_aid_daily = yes } } }')
 put('events/hro_allied_aid_events.txt','\n'.join(events))
 for lang,entries in loc.items():put(f'localisation/{lang}/hro_allied_aid_l_{lang}.yml','l_'+lang+':\n'+''.join(f' {k}:0 {json.dumps(v,ensure_ascii=False)}\n' for k,v in entries.items()),True)
 return {'duration_days':365,'one_time_per_country':True,'donor_exists_not_capitulated_not_enemy':True,'ideas':len(ideas),'aid':AID}
