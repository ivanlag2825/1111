"""One country-scoped dispatcher plus a saved event heartbeat.

Only the assembled build is consolidated. Individual generators retain their
isolated hooks for unit tests; no shipped system relies on competing on_daily
entries. The one-day guard coalesces the country hook and event callback.
"""
from pathlib import Path
from clausewitz import parse

REPEATABLE={'hro.800','hro.810','hro.811'}


def generate(output):
 output=Path(output);hooks={'on_daily':[],'on_monthly':[],'on_startup':[]}
 for path in sorted((output/'common/on_actions').glob('hro*.txt')):
  source=path.read_text()
  for top in parse(source):
   for hook in top.value:
    if hook.key not in hooks:raise ValueError('Unmerged HRO hook: '+hook.key)
    effect=hook.one('effect')
    if effect:hooks[hook.key].append(source[effect.value_start+1:effect.value_end-1])
  path.unlink()
 def put(path,value):
  p=output/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(value+'\n')
 daily='\n'.join(hooks['on_daily'])
 put('common/scripted_effects/hro_runtime_effects.txt',f'''hro_runtime_tick = {{
  if = {{ limit = {{ OR = {{ original_tag = GER original_tag = SOV }} NOT = {{ has_country_flag = hro_runtime_checked }} }}
   set_country_flag = {{ flag = hro_runtime_checked value = 1 days = 1 }}
   {daily}
  }}
 }}
 hro_runtime_seed = {{
  if = {{ limit = {{ OR = {{ original_tag = GER original_tag = SOV }} date < 1947.1.1 NOT = {{ has_country_flag = hro_runtime_queued }} }}
   set_country_flag = {{ flag = hro_runtime_queued value = 1 days = 2 }}
   country_event = {{ id = hro.800 days = 1 }}
  }}
 }}''')
 startup='\n'.join(hooks['on_startup'])
 monthly='\n'.join(hooks['on_monthly'])
 put('common/on_actions/hro_zz_runtime.txt',f'''on_actions = {{
  on_startup = {{ effect = {{ {startup} every_country = {{ limit = {{ OR = {{ original_tag = GER original_tag = SOV }} }} hro_runtime_seed = yes }} }} }}
  on_daily_GER = {{ effect = {{ hro_runtime_tick = yes hro_runtime_seed = yes }} }}
  on_daily_SOV = {{ effect = {{ hro_runtime_tick = yes hro_runtime_seed = yes }} }}
  on_monthly = {{ effect = {{ {monthly} }} }}
 }}''')
 events=['add_namespace = hro']
 for identity,body in [('hro.800','clr_country_flag = hro_runtime_queued hro_runtime_tick = yes hro_runtime_seed = yes'),
                       ('hro.810','hro_ops_begin_exhaustion = yes'),('hro.811','hro_ops_finish_rest = yes')]:
  events.append(f'country_event = {{ id = {identity} hidden = yes is_triggered_only = yes immediate = {{ {body} }} option = {{ name = hro_runtime_hidden }} }}')
 put('events/hro_runtime_events.txt','\n'.join(events))
 for lang,title in [('russian','Служебная проверка'),('english','Lifecycle check')]:
  path=output/f'localisation/{lang}/hro_runtime_l_{lang}.yml';path.parent.mkdir(parents=True,exist_ok=True)
  path.write_text(f'l_{lang}:\n hro_runtime_hidden:0 "{title}"\n',encoding='utf-8-sig')
 return {'country_hooks':['on_daily_GER','on_daily_SOV'],'saved_daily_event':'hro.800','duplicate_guard_days':1,'direct_assault_transition_days':14,'profile_assault_transition_days':{'decisive':14,'sequential':21},'direct_regrouping_completion_days':21,'merged_daily_sources':len(hooks['on_daily'])}
