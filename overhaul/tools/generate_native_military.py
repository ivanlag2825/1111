"""Tailored native GER military rewards with bounded permanent families.

Old completed focuses reconcile permanent reforms only. Timed preparation and
research are issued solely on a new first completion, never replayed by sync.
"""
from collections import Counter
from pathlib import Path
import json
from decision_details import describe
ROOT=Path(__file__).resolve().parents[1]
WINDOWS={
 'army':{'army_org_regain':.10,'planning_speed':.10},
 'air':{'experience_gain_air_factor':.20,'air_fuel_consumption_factor':-.05},
 'navy':{'naval_coordination':.10,'navy_fuel_consumption_factor':-.05}}
TITLES={'army':('Армейский цикл подготовки','Army Training Cycle'),'air':('Программа подготовки лётчиков','Pilot Training Programme'),'navy':('Учения боевых эскадр','Combat Squadron Exercises')}
DAYS=120

def records():return json.loads((ROOT/'data/german_native_rewards.json').read_text())

def generate(output,catalogues=None):
 output=Path(output);entries=records();c=next(c for c in catalogues if c['tag']=='GER') if catalogues else json.loads((ROOT/'data/ger.json').read_text())
 ideas_by_id={i['id']:i for i in c['ideas']};native={p['id']:p for p in c['native_patches']};effects=[];sync=[];ideas=[];loc={'russian':{},'english':{}}
 if len(entries)!=len({r['focus'] for r in entries}):raise ValueError('Duplicate native military reward')
 def put(path,text,bom=False):
  p=output/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text+'\n',encoding='utf-8-sig' if bom else 'utf-8')
 for branch,mods in WINDOWS.items():
  identity='hro_native_training_'+branch
  ideas.append(f'{identity} = {{ picture = generic_army allowed = {{ original_tag = GER }} removal_cost = -1 modifier = {{ '+' '.join(f'{k} = {v:g}' for k,v in mods.items())+' } }')
  for lang,n in [('russian',0),('english',1)]:
   loc[lang][identity]=TITLES[branch][n]
   loc[lang][identity+'_desc']=describe(mods,lang)+(f'. На{DAYS}дней после завершения ванильного фокуса этой военной ветки. Следующий фокус обновляет срок одного духа, а не складывает его. Загрузка сохранения срок не обновляет.' if n==0 else f'. For{DAYS}days after completing a native focus in this branch. The next focus refreshes one spirit rather than stacking it. Loading does not refresh the timer.')
 for record in entries:
  focus,idea,effect=record['focus'],record['idea'],record['effect'];tier=ideas_by_id.get(idea)
  if tier is None or effect+' = yes' not in native[focus].get('extra_reward',''):raise ValueError('Unattached native military reward: '+focus)
  branch=record['branch'];flag='hro_native_issued_'+focus;training='hro_native_training_'+branch;tooltip=effect+'_tt'
  for lang,n,suffix in [('russian',0,'ru'),('english',1,'en')]:
   loc[lang][effect]=('Дополнительная подготовка: ' if n==0 else 'Additional training: ')+tier['name_'+suffix]
   loc[lang][tooltip]=(f'Дополнение мода: {tier["name_"+suffix]}. {tier["desc_"+suffix]} Дополнительно один50%-ный профильный исследовательский бонус и «{TITLES[branch][n]}» на{DAYS}дней: '+describe(WINDOWS[branch],lang)+'. Если постоянная реформа уже сильнее, она сохраняется. Повторная выдача исследований и обновление срока доступны только при первом новом завершении, не при загрузке.' if n==0 else f'Mod reward: {tier["name_"+suffix]}. {tier["desc_"+suffix]} Also one50%matching research bonus and {TITLES[branch][n]} for{DAYS}days: '+describe(WINDOWS[branch],lang)+'. Stronger permanent reforms remain. Research and timed preparation are granted only on the first new completion, not on load.')
  effects.append(f'''{effect} = {{
   custom_effect_tooltip = {tooltip}
   hidden_effect = {{ if = {{ limit = {{ original_tag = GER NOT = {{ has_country_flag = {flag} }} }}
    set_country_flag = {flag}
    hro_set_{idea} = yes
    add_timed_idea = {{ idea = {training} days = {DAYS} }}
    add_tech_bonus = {{ name = {effect} bonus = 0.5 uses = 1 category = {record['tech']} }}
   }} }}
  }}''')
  sync.append(f'if = {{ limit = {{ has_completed_focus = {focus} }} hro_set_{idea} = yes }}')
 effects.append('hro_native_military_sync = { if = { limit = { original_tag = GER } '+' '.join(sync)+' } }')
 put('common/scripted_effects/hro_native_military_effects.txt','\n'.join(effects))
 put('common/ideas/hro_native_military_ideas.txt','ideas = { country = { '+'\n'.join(ideas)+' } }')
 put('common/on_actions/hro_native_military_on_actions.txt','on_actions = { on_daily = { effect = { hro_native_military_sync = yes } } }')
 for lang,entries_loc in loc.items():put(f'localisation/{lang}/hro_native_military_l_{lang}.yml','l_'+lang+':\n'+''.join(f' {k}:0 {json.dumps(v,ensure_ascii=False)}\n' for k,v in entries_loc.items()),True)
 return {'native_focuses':len(entries),'branches':dict(Counter(e['branch'] for e in entries)),'permanent_families':len({ideas_by_id[e['idea']]['family'] for e in entries}),'permanent_ideas':len([i for i in c['ideas'] if '_native_' in i['id']]),'training_days':DAYS,'training_modifiers':WINDOWS,'save_reconciliation':'permanent reforms only; no research or timer replay','global_army_attack_or_defence_added':False}
