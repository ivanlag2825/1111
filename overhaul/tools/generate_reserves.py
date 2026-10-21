"""One-shot coal expansion and German replacement reserves; safe on 0.6 saves."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from clausewitz import parse

COAL={'GER':{51:250,67:150,65:100,66:100},'SOV':{227:200,578:200,569:200,572:100,881:100}}
MANPOWER=1000000
IDEA='hro_idea_ger_expanded_replacement_reserve'


def validate_geography(game):
    states={}
    for p in (Path(game)/'history/states').glob('*.txt'):
        state=next((n for n in parse(p.read_text(encoding='utf-8-sig')) if n.key=='state'),None)
        if state:states[int(state.scalar('id'))]=state
    for tag,regions in COAL.items():
        for identity in regions:
            state=states.get(identity)
            if state is None or state.one('history').scalar('owner')!=tag or not any(float(r.scalar('coal','0'))>0 for r in state.all('resources')):
                raise ValueError(f'Coal expansion does not match supplied map: {tag}/{identity}')
    return {tag:sum(regions.values()) for tag,regions in COAL.items()}


def generate(output):
    output=Path(output)
    def put(name,value,bom=False):
        p=output/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(value+'\n',encoding='utf-8-sig' if bom else 'utf-8')
    effects=[]
    for tag,regions in COAL.items():
        additions=[]
        for state,amount in regions.items():
            flag=f'hro_reserves_coal_{tag.lower()}_{state}_done'
            additions.append(f'''if = {{ limit = {{ NOT = {{ has_country_flag = {flag} }} {state} = {{ is_owned_by = ROOT is_fully_controlled_by = ROOT }} }}
                {state} = {{ add_resource = {{ type = coal amount = {amount} }} }} set_country_flag = {flag}
            }}''')
        if tag=='GER':additions.append(f'''if = {{ limit = {{ NOT = {{ has_country_flag = hro_reserves_ger_manpower_done }} }}
                add_manpower = {MANPOWER} set_country_flag = hro_reserves_ger_manpower_done
            }}
            if = {{ limit = {{ NOT = {{ has_idea = {IDEA} }} }} add_ideas = {IDEA} }}''')
        effects.append(f'''hro_reserves_{tag.lower()}_apply = {{
            if = {{ limit = {{ original_tag = {tag} }} {' '.join(additions)} }}
        }}''')
    put('common/scripted_effects/hro_reserves_effects.txt','\n'.join(effects))
    put('common/ideas/hro_reserves_ideas.txt',f'''ideas = {{ country = {{ {IDEA} = {{
        picture = generic_army allowed = {{ original_tag = GER }} removal_cost = -1
        modifier = {{ conscription = 0.02 }}
    }} }} }}''')
    put('common/on_actions/hro_reserves_on_actions.txt','''on_actions = {
        on_daily = { effect = {
            if = { limit = { original_tag = GER } hro_reserves_ger_apply = yes }
            else_if = { limit = { original_tag = SOV } hro_reserves_sov_apply = yes }
        } }
    }''')
    ru={IDEA:'Расширенный резерв пополнений',IDEA+'_desc':'Призывное население +2 процентных пункта. При первом применении программы Германия получает 1 000 000 доступных людских ресурсов. Загрузка сохранения и повторная проверка не выдают их снова.'}
    en={IDEA:'Expanded Replacement Reserve',IDEA+'_desc':'Recruitable population +2 percentage points. The first application grants Germany 1,000,000 available manpower. Reloading or reconciling does not grant it again.'}
    for language,loc in [('russian',ru),('english',en)]:
        put(f'localisation/{language}/hro_reserves_l_{language}.yml',f'l_{language}:\n'+''.join(f' {k}:0 {json.dumps(v,ensure_ascii=False)}\n' for k,v in loc.items()),True)
    return {'base_coal_added':{tag:sum(regions.values()) for tag,regions in COAL.items()},'coal_states':COAL,
            'german_one_time_manpower':MANPOWER,'german_recruitable_population_points':2,'repeat_rewards':False}
