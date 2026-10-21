#!/usr/bin/env python3
"""Finite German first-offensive and one-shot Soviet-city capture rewards."""
import json,sys
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parent),str(Path(__file__).resolve().parents[2]/'tools')]
from generate_emergency import records
from generate_war_adaptation import _remove,_select

LAUNCH_IDEAS=('hro_idea_off_ger_breakthrough','hro_idea_off_ger_pursuit')
CITY_IDEAS=tuple(f'hro_idea_off_ger_city_momentum_{n}' for n in range(1,4))
CAPTURE_REWARDS={'minsk':(60,40),'kiev':(80,50),'leningrad':(100,60),'moscow':(150,75),'stalingrad':(100,60),'kharkov':(90,50)}


def generate(output):
    output=Path(output);loc={'russian':{},'english':{}}
    def put(name,value,bom=False):
        p=output/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(value+'\n',encoding='utf-8-sig' if bom else 'utf-8')
    def text(key,ru,en):loc['russian'][key],loc['english'][key]=ru,en
    ideas=[]
    def idea(identity,ru,en,mods,dr,de):
        text(identity,ru,en);text(identity+'_desc',dr,de)
        body=' '.join(f'{k} = {v:g}' for k,v in mods.items())
        ideas.append(f'{identity} = {{ picture = generic_army allowed = {{ original_tag = GER }} removal_cost = -1 modifier = {{ {body} }} }}')
    idea(LAUNCH_IDEAS[0],'Первый удар Восточной кампании','Opening Blow of the Eastern Campaign',
         {'army_attack_factor':.35,'army_speed_factor':.20,'planning_speed':.30,'army_org_regain':.20,'supply_consumption_factor':-.10},
         'Первые 60 действительных дней первой наступательной войны Германии против СССР. Затем сменяется меньшим темпом преследования до 120-го дня. В ноябре–марте не действует; дни войны продолжают расходовать окно. Мир приостанавливает военный счётчик, повторная война его не сбрасывает.',
         'The first 60 actual days of Germany’s first offensive war against the USSR. A milder pursuit tier lasts until day 120. Inactive in November–March while war days continue consuming the window. Peace pauses the clock; rewar does not reset it.')
    idea(LAUNCH_IDEAS[1],'Развитие первоначального прорыва','Exploiting the Initial Breakthrough',
         {'army_attack_factor':.20,'army_speed_factor':.10,'planning_speed':.20,'army_org_regain':.10,'supply_consumption_factor':-.05},
         'Дни 60–119 первой наступательной войны против СССР. После 120 военных дней первоначальное преимущество заканчивается. Зимой не действует.',
         'Days 60–119 of the first offensive war against the USSR. Initial advantages end after 120 war days and are inactive in winter.')
    for tier,values in enumerate(((.10,.05,.10,.20),(.15,.10,.15,.30),(.20,.15,.20,.40)),1):
        attack,defence,recovery,planning=values
        idea(CITY_IDEAS[tier-1],f'Оперативный успех на Востоке: {tier}',f'Eastern Operational Success: {tier}',
             {'army_attack_factor':attack,'army_defence_factor':defence,'army_org_regain':recovery,'planning_speed':planning},
             'Захват ключевых советских городов открыл 120-дневное окно оперативного преимущества. Действует одна ступень. Следующий город повышает ступень без продления текущего окна; повторный захват уже учтённого города награду не даёт. Мир и капитуляция снимают временные преимущества.',
             'Capturing key Soviet cities opens a 120-day operational window. Only one tier applies. Another city upgrades without refreshing it; recapturing an already rewarded city grants nothing. Peace and capitulation remove temporary advantages.')
    events=['add_namespace = hro']
    def event(index,ru,en,dr,de):
        key=f'hro.{index}';text(key+'.t',ru,en);text(key+'.d',dr,de);text(key+'.a','Использовать преимущество.','Exploit the advantage.')
        events.append(f'country_event = {{ id = {key} title = {key}.t desc = {key}.d is_triggered_only = yes fire_only_once = yes option = {{ name = {key}.a }} }}')
    event(601,'Первый удар на Востоке','The Opening Blow in the East',
          'Началась первая наступательная кампания против СССР. Первые 60 военных дней дают крупное преимущество, затем до 120-го дня действует меньший бонус. Зима приостанавливает действие бонуса, но не расход военного времени.',
          'The first offensive campaign against the USSR has begun. The first 60 war days grant a major advantage, with a smaller tier until day 120. Winter suppresses the bonus without stopping war-time consumption.')
    effects=[];city_checks=[]
    for index,city in enumerate(records(),1):
        key=city['key'];name='hro_off_ger_'+key+'_capture';pp,xp=CAPTURE_REWARDS[key]
        body=f'''if = {{ limit = {{ original_tag = GER hro_war_eastern_war = yes controls_province = {city['province']}
            any_enemy_country = {{ original_tag = SOV has_country_flag = hro_city_{key}_lost }}
            NOT = {{ has_country_flag = hro_off_ger_{key}_awarded }} }}
            set_country_flag = hro_off_ger_{key}_awarded
            add_to_variable = {{ hro_off_ger_cities = 1 }}
            add_political_power = {pp} army_experience = {xp}
            add_tech_bonus = {{ name = {name} bonus = 1 uses = 2 category = {city['tech']} }}
            if = {{ limit = {{ NOT = {{ has_country_flag = hro_off_ger_city_window }} }} set_country_flag = {{ flag = hro_off_ger_city_window days = 120 }} }}
            country_event = {{ id = hro.{610+index} days = 1 }}
        }}'''
        effects.append(name+' = {\n'+body+'\n}')
        city_checks.append(name+' = yes')
        text(name, 'Военный опыт: '+city['ru'], 'Campaign Lessons: '+city['en'])
        event(610+index,city['ru']+': оперативный успех',city['en']+': Operational Success',
              f"Город под нашим контролем. Один раз получено {pp} ПВ, {xp} армейского опыта, два 100% профильных исследовательских бонуса и ступень 120-дневного оперативного преимущества. Повторная сдача и захват награду не обновляют.",
              f"The city is under our control. One-time rewards: {pp} PP, {xp} army experience, two 100% research bonuses and a tier of 120-day operational advantage. Losing and recapturing it cannot renew the reward.")
    effects.append(f'''hro_off_ger_sync = {{
        if = {{ limit = {{ original_tag = GER hro_war_eastern_war = yes has_country_flag = hro_off_ger_launch_authorized NOT = {{ hro_war_winter_season = yes }} }}
            if = {{ limit = {{ check_variable = {{ hro_off_ger_campaign_days < 60 }} }} {_select(LAUNCH_IDEAS,LAUNCH_IDEAS[0])} }}
            else_if = {{ limit = {{ check_variable = {{ hro_off_ger_campaign_days < 120 }} }} {_select(LAUNCH_IDEAS,LAUNCH_IDEAS[1])} }}
            else = {{ {_remove(LAUNCH_IDEAS)} }}
        }} else = {{ {_remove(LAUNCH_IDEAS)} }}
        if = {{ limit = {{ original_tag = GER hro_war_eastern_war = yes has_country_flag = hro_off_ger_city_window }}
            if = {{ limit = {{ check_variable = {{ hro_off_ger_cities > 2 }} }} {_select(CITY_IDEAS,CITY_IDEAS[2])} }}
            else_if = {{ limit = {{ check_variable = {{ hro_off_ger_cities > 1 }} }} {_select(CITY_IDEAS,CITY_IDEAS[1])} }}
            else = {{ {_select(CITY_IDEAS,CITY_IDEAS[0])} }}
        }} else = {{ {_remove(CITY_IDEAS)} }}
    }}
    hro_off_ger_tick = {{
        if = {{ limit = {{ NOT = {{ has_country_flag = hro_off_ger_initialized }} }}
            set_country_flag = hro_off_ger_initialized set_variable = {{ hro_off_ger_cities = 0 }} set_variable = {{ hro_off_ger_campaign_days = 0 }} }}
        if = {{ limit = {{ hro_war_eastern_war = yes NOT = {{ has_country_flag = hro_off_ger_started }} }}
            set_country_flag = hro_off_ger_started
            if = {{ limit = {{ hro_war_ger_attacking = yes }} set_country_flag = hro_off_ger_launch_authorized country_event = {{ id = hro.601 days = 1 }} }}
        }} else_if = {{ limit = {{ hro_war_eastern_war = yes check_variable = {{ hro_off_ger_campaign_days < 120 }} }} add_to_variable = {{ hro_off_ger_campaign_days = 1 }} }}
        {' '.join(city_checks)}
        hro_off_ger_sync = yes
    }}''')
    put('common/ideas/hro_offensive_ideas.txt','ideas = { country = {\n'+'\n'.join(ideas)+'\n} }')
    put('common/scripted_effects/hro_offensive_effects.txt','\n'.join(effects))
    put('common/on_actions/hro_offensive_on_actions.txt','on_actions = { on_daily = { effect = { if = { limit = { original_tag = GER } hro_off_ger_tick = yes } } } }')
    put('events/hro_offensive_events.txt','\n'.join(events))
    for language,entries in loc.items():put(f'localisation/{language}/hro_offensive_l_{language}.yml',f'l_{language}:\n'+''.join(f' {k}:0 {json.dumps(v,ensure_ascii=False)}\n' for k,v in entries.items()),True)
    return {'ideas':len(ideas),'events':len(events)-1,'initial_offensive_days':[60,120],'only_first_german_offensive':True,
            'winter_suppresses_launch':True,'city_window_days':120,'cities':len(records()),'one_reward_per_city':True,
            'city_rewards':{key:{'political_power':pp,'army_experience':xp,'research_uses':2} for key,(pp,xp) in CAPTURE_REWARDS.items()}}
