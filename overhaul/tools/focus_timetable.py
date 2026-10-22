"""Schedule one compatible German route with a single focus slot and date gates.

This proves nominal calendar feasibility, not satisfaction of engine political,
war-support, army-size, DLC/event or industrial conditions.
"""
from datetime import datetime, timedelta
import argparse,json
from pathlib import Path
from campaign_routes import review_route,_load,_groups

START=datetime(1936,1,1)
NEVER=datetime(2100,1,1)
POLITICAL_STARTS={
 'GER_anschluss':'1938.1.20',
 'GER_demand_sudetenland':'1938.8.1',
 'GER_first_vienna_award':'1938.10.1',
 'GER_fate_of_czechoslovakia':'1939.1.20',
 'GER_molotov_ribbentrop_pact':'1939.6.1',
 'GER_danzig_or_war':'1939.7.1',
}
POLITICAL_DEADLINES={
 'GER_anschluss':'1938.4.1','GER_demand_sudetenland':'1938.10.15',
 'GER_first_vienna_award':'1938.12.1','GER_fate_of_czechoslovakia':'1939.4.15',
 'GER_molotov_ribbentrop_pact':'1939.8.31','GER_danzig_or_war':'1939.9.1',
}
CORE_GOALS=[
 'hro_ger_rationalized_designs','hro_ger_warfactory_clusters',
 'hro_ger_decentralized_arsenals','hro_ger_operational_command_system',
 'hro_ger_mature_air_operations','hro_ger_mature_maritime_programme',
 'hro_ger_dora_programme','GER_danzig_or_war',
 'GER_demand_sudetenland','GER_first_vienna_award',
 'GER_fate_of_czechoslovakia','GER_molotov_ribbentrop_pact',
]
NEW_GOALS=['hro_ger_elite_panzer_crews','hro_ger_blitzkrieg_air_coordination','hro_ger_tooling_audit']

def day(s):return datetime.strptime(s.replace('-','.'),'%Y.%m.%d')

def date_floor(nodes):
 """Earliest day implied by AND/OR date gates, with historical rules enabled.

 Unknown non-calendar conditions are treated as potentially satisfiable and
 explicitly excluded from the proof. Upper-date limits are audited separately.
 """
 def one(n):
  if n.key=='OR':return min((one(c) for c in n.value),default=START)
  if n.key=='AND':return date_floor(n.value)
  if n.key=='has_game_rule':return NEVER if n.scalar('option')=='HRO_OPEN' else START
  if n.key=='always':return START if n.value=='yes' else NEVER
  if n.key=='date' and n.op in ('>','>=','='):
   return day(n.value)+(timedelta(days=1) if n.op=='>' else timedelta())
  return START
 return max((one(n) for n in nodes),default=START)

def schedule(mod_dir,goals,deadline='1941.6.22',political_starts=None):
 route=review_route(Path(mod_dir),goals,historical=True,deadline=deadline)
 focuses,_,_=_load(Path(mod_dir));groups={i:_groups(f) for i,f in focuses.items()}
 pending={p['id']:p for p in route['plan']};selected=set(pending);done=set();when=START;rows=[];idle=0
 releases={i:date_floor(focuses[i].one('available').value) if focuses[i].one('available') else START for i in pending}
 for i,s in (POLITICAL_STARTS if political_starts is None else political_starts).items():
  if i in releases:releases[i]=max(releases[i],day(s))
 ancestors={}
 def ancestry(i,seen=None):
  seen=set() if seen is None else seen
  if i in seen:return seen
  seen.add(i)
  for group in groups.get(i,[]):
   for parent in group:
    if parent in selected:ancestry(parent,seen)
  return seen
 targets={i:day('1941.6.22') for i in goals}
 for i in POLITICAL_STARTS:
  if i in selected:targets[i]=day(POLITICAL_DEADLINES[i])
 for i in ('hro_ger_rationalized_designs',):
  if i in selected:targets[i]=day('1938.1.1')
 for i in ('hro_ger_warfactory_clusters','hro_ger_decentralized_arsenals'):
  if i in selected:targets[i]=day('1940.1.1')
 ancestors={i:ancestry(i) for i in targets}
 priority={i:min((t for goal,t in targets.items() if i in ancestors[goal]),default=day(deadline)) for i in pending}
 while pending:
  ready=[i for i in pending if all(any(p in done for p in g) for g in groups.get(i,[]))]
  if not ready:raise ValueError('No valid completion order')
  available=[i for i in ready if releases[i]<=when]
  if not available:
   nxt=min(releases[i] for i in ready);idle+=(nxt-when).total_seconds()/86400;when=nxt;continue
  identity=min(available,key=lambda i:(priority[i],releases[i],i))
  cost=pending.pop(identity)['workdays'];finish=when+timedelta(days=cost)
  rows.append(dict(id=identity,start=when.isoformat(),finish=finish.isoformat(),workdays=cost,release=releases[identity].date().isoformat()))
  done.add(identity);when=finish
 # Check all raw upper bounds conservatively. OR-specific alternatives may
 # waive them, but no route is labelled feasible if an upper bound is missed.
 upper=[]
 from clausewitz import walk
 for row in rows:
  f=focuses[row['id']];a=f.one('available')
  if a:
   for n in walk(a.value):
    if n.key=='date' and n.op=='<' and day(n.value)<=datetime.fromisoformat(row['finish']):upper.append(row['id'])
 missed=[i for i,t in targets.items() if datetime.fromisoformat(next(x['finish'] for x in rows if x['id']==i))>t]
 result=dict(route=route,completed=when.isoformat(),focus_days=route['workdays']['total'],idle_days=idle,
             spare_days=(day(deadline)-when).total_seconds()/86400,
             feasible=when<=day(deadline) and not upper and not missed,upper_date_violations=sorted(set(upper)),missed_target_deadlines=missed,
             schedule=rows,targets={i:next(x['finish'] for x in rows if x['id']==i) for i in goals},
             political_start_assumptions=POLITICAL_STARTS if political_starts is None else political_starts,
             engine_verified=False,checks='single focus slot, full nominal duration, compatible AND/OR prerequisites, mutual exclusions, lower date gates, conservative upper date audit',
             limitations='Political events, army size, war support, DLC visibility, industry and war availability must be satisfied by the player. No focus speed bonus, bypass or saved focus progress is assumed. This is one reproducible route, not an optimum.')
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mod-dir',required=True,type=Path);p.add_argument('--core-only',action='store_true');p.add_argument('--output',type=Path)
 a=p.parse_args();r=schedule(a.mod_dir,CORE_GOALS+([] if a.core_only else NEW_GOALS));value=json.dumps(r,ensure_ascii=False,indent=2)+'\n'
 if a.output:a.output.write_text(value)
 else:print(value)
