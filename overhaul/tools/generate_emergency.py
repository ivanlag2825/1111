#!/usr/bin/env python3
"""One-shot city-loss crises and finite Soviet counter-mobilisation.

City victory-point control, rather than state controller, determines loss.
Only one shock tier, comeback tier and rebuilding tier can be active.
"""
from collections import defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from clausewitz import parse, walk
from effect_presentation import present_effects
from spirit_lifecycle import timed_selection
from decision_details import describe


def records():
    return json.loads((ROOT / 'overhaul/data/cities.json').read_text())


def validate_geography(game):
    states = {}
    for path in (Path(game) / 'history/states').glob('*.txt'):
        state = next((n for n in parse(path.read_text(encoding='utf-8-sig')) if n.key == 'state'), None)
        if state:
            states[int(state.scalar('id'))] = state
    for city in records():
        state = states.get(city['state'])
        if state is None:
            raise ValueError('Missing city state: ' + city['key'])
        provinces = {int(n.value) for n in state.one('provinces').value}
        points = [p.value for p in state.one('history').all('victory_points')]
        if city['province'] not in provinces or not any(int(p[0].value) == city['province'] and float(p[1].value) >= 10 for p in points):
            raise ValueError('City victory point does not match supplied map: ' + city['key'])
    return {c['key']: {'state': c['state'], 'province': c['province']} for c in records()}


def generate(output):
    output = Path(output)
    loc = {'russian': {}, 'english': {}}
    def put(path, value, bom=False):
        target = output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value + '\n', encoding='utf-8-sig' if bom else 'utf-8')
    def text(key, ru, en):
        loc['russian'][key], loc['english'][key] = ru, en
    def remove(ids):
        return ' '.join('remove_ideas = ' + identity for identity in ids)
    ideas = []
    groups = defaultdict(list)
    def idea(identity, family, ru, en, mods, desc_ru, desc_en):
        groups[family].append(identity)
        text(identity, ru, en);text(identity + '_desc', desc_ru, desc_en)
        values = ' '.join(f'{k} = {v:g}' for k, v in mods.items())
        ideas.append(f'{identity} = {{ picture = generic_army allowed = {{ original_tag = SOV }} removal_cost = -1 modifier = {{ {values} }} }}')
    for tier, mods in enumerate((
        {'army_org_factor':-.10,'army_org_regain':-.20,'industrial_capacity_factory':-.12,'supply_consumption_factor':.15},
        {'army_org_factor':-.18,'army_org_regain':-.30,'industrial_capacity_factory':-.22,'supply_consumption_factor':.25},
        {'army_org_factor':-.25,'army_org_regain':-.40,'industrial_capacity_factory':-.30,'supply_consumption_factor':.35}), 1):
        idea(f'hro_idea_city_crisis_{tier}', 'crisis', f'Кризис отступления: ступень {tier}', f'Retreat Crisis: Tier {tier}', mods,
             'Потеря ключевых городов нарушила управление и выпуск. Действует одна ступень, максимум третья. Контрмеры, освобождение города или 90 фактических дней войны ослабляют кризис; в мире и после капитуляции дух снимается.',
             'Lost cities disrupt command and production. Only one tier applies, up to tier three. Countermeasures, liberation or 90 actual war days reduce the crisis; peace and capitulation remove it.')
    for tier, mods in enumerate((
        {'army_defence_factor':.08,'army_org_regain':.15,'training_time_army_factor':-.10,'land_reinforce_rate':.02,'industrial_capacity_factory':.05},
        {'army_defence_factor':.25,'army_org_regain':.35,'training_time_army_factor':-.25,'industrial_capacity_factory':.15,'land_reinforce_rate':.05,'army_org_factor':.08},
        {'army_defence_factor':.40,'army_org_regain':.50,'training_time_army_factor':-.35,'industrial_capacity_factory':.25,'land_reinforce_rate':.08,'army_org_factor':.15}), 1):
        idea(f'hro_idea_city_mobilization_{tier}', 'mobilization', f'Вторая мобилизация: ступень {tier}', f'Second Mobilisation: Tier {tier}', mods,
             'Оплаченные и завершённые контрмеры усиливают мобилизацию. Действует одна ступень. Окно 240 дней начинается с первой контрмеры; новые ступени внутри окна не продлевают его. Повторная потеря одного города наград не даёт.',
             'Paid, completed countermeasures strengthen mobilisation. Only one tier applies. A 240-day window starts with the first response; upgrades do not refresh it. Losing the same city again grants no rewards.')
    for tier in range(1,4):
        idea(f'hro_idea_city_rebuilding_{tier}', 'rebuilding', f'Восстановление освобождённых городов: {tier}', f'Liberated City Reconstruction: {tier}',
             {'industry_repair_factor':.25*tier,'production_speed_buildings_factor':.05*tier},
             'Освобождение даёт конечное окно восстановления на 180 дней. Ступени заменяют друг друга. Не восстанавливает заводы и территорию мгновенно.',
             'Liberation grants a finite 180-day rebuilding window. Tiers replace one another. Factories and territory are not restored instantly.')
    idea('hro_idea_city_response_working','working','Чрезвычайное развёртывание резервов','Emergency Reserve Deployment',
         {'industrial_capacity_factory':-.06,'political_power_gain':-.20},
         'Издержки текущей чрезвычайной программы. Результат приходит после её срока; отмена не возвращает ПВ.',
         'Costs of the current emergency programme. Results arrive after its full duration; cancellation refunds no PP.')
    idea('hro_idea_city_liberation_offensive','offensive','Окно освободительного наступления','Liberation Offensive Window',
         {'army_attack_factor':.25,'army_speed_factor':.15,'army_org_regain':.25},
         'Одно 180-дневное окно после возвращения важного города и завершения фокуса. +25% атаки, +15% скорости, +25% восстановления организации. Не обновляется повторным захватом города.',
         'One 180-day window after liberating a major city and completing its focus. +25% attack, +15% speed, +25% organisation recovery. Repeated recaptures cannot refresh it.')

    text('hro_city_responses','Ставка: кризисы и контрмеры','Stavka: Crises and Countermeasures')
    text('hro_city_responses_desc','Падение города создаёт кризис. Одна чрезвычайная программа выполняется за раз. Награда за каждый город выдаётся один раз: решением или соответствующим фокусом. Подготовка расходует политическую власть и временно отвлекает производство.',
         'A fallen city creates a crisis. One emergency programme can run at a time. Each city reward is granted once, through a decision or its focus. Preparation costs political power and temporarily diverts production.')
    text('hro_city_reward_preview', 'После полного завершения: следующая ступень второй мобилизации при текущем числе ответов. Окно — 240 дней от первого ответа; повышение ступени не продлевает срок. При завершении ступень пересчитывается.',
         'On full completion: next Second Mobilisation tier based on current responses. A 240-day window begins with the first response; upgrades do not refresh it. The tier is recalculated on completion.')
    mobilisation = {node.key: {m.key:float(m.value) for m in node.one('modifier').value}
                    for script in ideas for node in parse(script)}
    working = mobilisation['hro_idea_city_response_working']
    tier_ru = ' '.join(f"Ступень {tier}: " + describe(mobilisation[f'hro_idea_city_mobilization_{tier}'], 'russian') + '.' for tier in range(1,4))
    tier_en = ' '.join(f"Tier {tier}: " + describe(mobilisation[f'hro_idea_city_mobilization_{tier}'], 'english') + '.' for tier in range(1,4))
    text('hro_city_mobilization_details',
         'Во время подготовки: ' + describe(working, 'russian') + '. После завершения повышается одна общая ступень второй мобилизации. ' + tier_ru + ' Ступени заменяют друг друга, не складываются. Окно 240 дней начинается с первой контрмеры и не продлевается. Подсказка ниже показывает следующую ступень при текущем числе ответов.',
         'During preparation: ' + describe(working, 'english') + '. Completion upgrades one shared mobilisation tier. ' + tier_en + ' Tiers replace each other without stacking. The 240-day window begins with the first response and is never extended. The tooltip below previews the next tier using current responses.')
    opening = 'OR = { date < 1942.1.1 check_variable = { hro_balance_war_days < 180 } }'
    parity = 'OR = { date < 1943.1.1 check_variable = { hro_balance_war_days < 540 } }'
    rule_ru = ' До1942года или180военных дней — максимум первая ступень; до1943года или540дней — максимум вторая. Дата и опыт не продлевают240-дневное окно.'
    rule_en = ' Before1942 or180war days: tier1maximum; before1943 or540days: tier2maximum. Unlocking a phase never extends the240-day window.'
    for lang in loc:
        for key in list(loc[lang]):
            if key in ('hro_city_mobilization_details','hro_city_reward_preview') or key.startswith('hro_idea_city_mobilization_') and key.endswith('_desc'):
                loc[lang][key] += rule_ru if lang=='russian' else rule_en
    effects=[];decisions=[];events=['add_namespace = hro'];daily=[]
    def notification(identity, ru, en, dr, de):
        text(identity+'.t',ru,en);text(identity+'.d',dr,de);text(identity+'.a','К исполнению.','Proceed.')
        events.append(f'country_event = {{ id = {identity} title = {identity}.t desc = {identity}.d is_triggered_only = yes fire_only_once = yes immediate = {{ hro_city_sync = yes }} option = {{ name = {identity}.a hro_city_sync = yes }} }}')

    for index, city in enumerate(records(), 1):
        k=city['key'];p=f'hro_city_{k}';vp=city['province'];state=city['factory_state'];n=city['factories']
        response=f'{p}_response'
        text(response,'Контрмеры: '+city['ru'],'Countermeasures: '+city['en'])
        text(response+'_desc', f"Цена {city['cost']} ПВ, срок {city['days']} дней. После завершения: {n} новых военных заводов на востоке, {city['manpower']} людских ресурсов, два 100% исследовательских бонуса и ступень второй мобилизации. Награда общая с фокусом этого города, не выдаётся повторно. При недоступной области вместо очереди предприятий — дополнительные исследования. Это новые мощности, исходная эвакуация не дублируется.",
             f"Cost {city['cost']} PP; duration {city['days']} days. Completion: {n} new eastern military factories, {city['manpower']} manpower, two 100% research bonuses and a mobilisation tier. Shared with this city's focus, never awarded twice. Unavailable factory capacity grants extra research instead. These are new facilities, not duplicated evacuation.")
        for language in loc:
            loc[language][response+'_desc'] += '\n\n' + loc[language]['hro_city_mobilization_details']
        notification(f'hro.{500+index}', city['ru']+': стратегический кризис',city['en']+': Strategic Crisis',
                     'Противник контролирует город. Появляется национальный дух «Кризис отступления»: одна из трёх общих ступеней по тяжести потерь. Решение или городской фокус дают контрмеры и положительный дух «Вторая мобилизация». Мир и капитуляция снимают временные военные духи; повторная потеря не создаёт наград.',
                     'The enemy controls the city. The Retreat Crisis national spirit applies one of three shared tiers. A regional decision or focus grants countermeasures and the positive Second Mobilisation spirit. Peace and capitulation remove temporary war spirits; repeated losses grant nothing.')
        notification(f'hro.{510+index}',city['ru']+': освобождение',city['en']+': Liberation',
                     'Город вновь под нашим контролем. Его вклад в кризис снят, открыто ограниченное окно восстановления. Прежний выпуск и повреждённые предприятия восстанавливаются по обычным правилам игры.',
                     'The city is under our control again. Its crisis contribution is removed and a finite rebuilding window opens. Production and damaged factories recover under normal game rules.')
        cancel=f'{p}_cancel';finish=f'{p}_finish'
        effects.append(f'''{cancel} = {{
    if = {{ limit = {{ has_country_flag = {p}_active }}
        clr_country_flag = {p}_active clr_country_flag = hro_city_response_busy
        remove_ideas = hro_idea_city_response_working
    }}
}}
{finish} = {{
    if = {{ limit = {{ original_tag = SOV hro_war_eastern_war = yes has_country_flag = {p}_lost NOT = {{ has_country_flag = {p}_responded }} }}
        {cancel} = yes
        set_country_flag = {p}_responded
        add_to_variable = {{ hro_city_responses_completed = 1 }}
        add_manpower = {city['manpower']}
        add_tech_bonus = {{ name = {response} bonus = 1 uses = 2 category = {city['tech']} }}
        if = {{ limit = {{ {state} = {{ is_owned_by = ROOT is_fully_controlled_by = ROOT }} }}
            {state} = {{ add_extra_state_shared_building_slots = {n}
                if = {{ limit = {{ free_building_slots = {{ building = arms_factory size > {n-1} include_locked = yes }} }}
                    add_building_construction = {{ type = arms_factory level = {n} instant_build = yes }}
                }} else = {{ ROOT = {{ add_tech_bonus = {{ name = {response} bonus = 1 uses = 2 category = industry }} }} }}
            }}
        }} else = {{ add_tech_bonus = {{ name = {response} bonus = 1 uses = 2 category = industry }} }}
        if = {{ limit = {{ NOT = {{ has_country_flag = hro_city_mobilization_active }} }}
            set_country_flag = {{ flag = hro_city_mobilization_active value = 1 days = 240 }}
        }}
        hro_city_sync = yes
    }}
}}''')
        decisions.append(f'''{response} = {{
    icon = generic_army cost = {city['cost']} days_remove = {city['days']}
    visible = {{ original_tag = SOV has_country_flag = {p}_lost NOT = {{ has_country_flag = {p}_responded }} }}
    available = {{ hro_war_eastern_war = yes NOT = {{ has_country_flag = hro_city_response_busy }} }}
    complete_effect = {{ set_country_flag = hro_city_response_busy set_country_flag = {p}_active add_ideas = hro_idea_city_response_working
        custom_effect_tooltip = hro_city_reward_preview
        if = {{ limit = {{ {opening} }} show_ideas_tooltip = hro_idea_city_mobilization_1 }}
        else_if = {{ limit = {{ check_variable = {{ hro_city_responses_completed > 1 }} NOT = {{ {parity} }} }} show_ideas_tooltip = hro_idea_city_mobilization_3 }}
        else_if = {{ limit = {{ check_variable = {{ hro_city_responses_completed > 0 }} }} show_ideas_tooltip = hro_idea_city_mobilization_2 }}
        else = {{ show_ideas_tooltip = hro_idea_city_mobilization_1 }}
    }}
    cancel_trigger = {{ OR = {{ NOT = {{ hro_war_eastern_war = yes }} NOT = {{ has_country_flag = {p}_active }} has_country_flag = {p}_responded }} }}
    cancel_effect = {{ {cancel} = yes }}
    remove_effect = {{ if = {{ limit = {{ has_country_flag = {p}_active hro_war_eastern_war = yes }} {finish} = yes }} else = {{ {cancel} = yes }} }}
    ai_will_do = {{ factor = 2 }}
}}''')
        daily.append(f'''
    if = {{ limit = {{ controls_province = {vp} }} set_country_flag = {p}_seen }}
    if = {{ limit = {{ hro_war_eastern_war = yes has_country_flag = {p}_seen NOT = {{ has_country_flag = {p}_lost }}
        NOT = {{ controls_province = {vp} }} any_enemy_country = {{ controls_province = {vp} }} }}
        set_country_flag = {p}_lost set_variable = {{ {p}_days = 0 }}
        country_event = {{ id = hro.{500+index} days = 1 }}
    }}
    else_if = {{ limit = {{ hro_war_eastern_war = yes has_country_flag = {p}_lost check_variable = {{ {p}_days < 90 }} }}
        add_to_variable = {{ {p}_days = 1 }}
    }}
    if = {{ limit = {{ hro_war_eastern_war = yes has_country_flag = {p}_lost controls_province = {vp} NOT = {{ has_country_flag = {p}_liberated }} }}
        set_country_flag = {p}_liberated add_to_variable = {{ hro_city_liberated_total = 1 }}
        if = {{ limit = {{ NOT = {{ has_country_flag = hro_city_rebuilding_active }} }} set_country_flag = {{ flag = hro_city_rebuilding_active value = 1 days = 180 }} }}
        country_event = {{ id = hro.{510+index} days = 1 }}
    }}
    if = {{ limit = {{ has_country_flag = {p}_active NOT = {{ hro_war_eastern_war = yes }} }} {cancel} = yes }}''')

    def select(family, tier):
        desired=groups[family][tier-1]
        if family in ('mobilization', 'rebuilding'):
            flag,days = ('hro_city_mobilization_active',240) if family == 'mobilization' else ('hro_city_rebuilding_active',180)
            return timed_selection(groups[family],desired,flag,days)
        return remove([i for i in groups[family] if i != desired])+f' if = {{ limit = {{ NOT = {{ has_idea = {desired} }} }} add_ideas = {desired} }}'
    unresolved=[]
    for city in records():
        p='hro_city_'+city['key'];unresolved.append(f'''if = {{ limit = {{ has_country_flag = {p}_lost NOT = {{ has_country_flag = {p}_responded }}
            NOT = {{ controls_province = {city['province']} }} any_enemy_country = {{ controls_province = {city['province']} }}
            check_variable = {{ {p}_days < 90 }} }} add_to_variable = {{ hro_city_unresolved = {city.get("weight",1)} }} }}''')
    init_city_vars = ' '.join(f'set_variable = {{ hro_city_{c["key"]}_days = 0 }}' for c in records())
    effects.append('''hro_city_orderly_mobilization = {
    if = { limit = { original_tag = SOV hro_war_eastern_war = yes NOT = { has_country_flag = hro_city_orderly_awarded } }
        set_country_flag = hro_city_orderly_awarded
        add_manpower = 120000
        if = { limit = { NOT = { has_country_flag = hro_city_mobilization_active } }
            set_country_flag = { flag = hro_city_mobilization_active value = 1 days = 240 }
        }
        hro_city_sync = yes
    }
}
hro_city_start_liberation_offensive = {
    if = { limit = { original_tag = SOV hro_war_eastern_war = yes check_variable = { hro_city_liberated_total > 0 }
        NOT = { has_country_flag = hro_city_offensive_awarded } }
        set_country_flag = hro_city_offensive_awarded
        add_timed_idea = { idea = hro_idea_city_liberation_offensive days = 180 }
    }
}
hro_city_sync = {
    set_variable = { hro_city_unresolved = 0 }
    if = { limit = { hro_war_eastern_war = yes }
'''+'\n'.join(unresolved)+f'''
        if = {{ limit = {{ check_variable = {{ hro_city_unresolved > 2 }} }} {select('crisis',3)} }}
        else_if = {{ limit = {{ check_variable = {{ hro_city_unresolved > 1 }} }} {select('crisis',2)} }}
        else_if = {{ limit = {{ check_variable = {{ hro_city_unresolved > 0 }} }} {select('crisis',1)} }}
        else = {{ {remove(groups['crisis'])} }}
        if = {{ limit = {{ has_country_flag = hro_city_mobilization_active }}
            if = {{ limit = {{ {opening} }} {select('mobilization',1)} }}
            else_if = {{ limit = {{ check_variable = {{ hro_city_responses_completed > 2 }} NOT = {{ {parity} }} }} {select('mobilization',3)} }}
            else_if = {{ limit = {{ check_variable = {{ hro_city_responses_completed > 1 }} }} {select('mobilization',2)} }}
            else = {{ {select('mobilization',1)} }}
        }} else = {{ {remove(groups['mobilization'])} }}
        if = {{ limit = {{ has_country_flag = hro_city_rebuilding_active }}
            if = {{ limit = {{ check_variable = {{ hro_city_liberated_total > 2 }} }} {select('rebuilding',3)} }}
            else_if = {{ limit = {{ check_variable = {{ hro_city_liberated_total > 1 }} }} {select('rebuilding',2)} }}
            else = {{ {select('rebuilding',1)} }}
        }} else = {{ {remove(groups['rebuilding'])} }}
    }} else = {{ {remove(groups['crisis']+groups['mobilization']+groups['rebuilding']+groups['offensive'])} }}
}}
hro_city_tick = {{
    if = {{ limit = {{ NOT = {{ has_country_flag = hro_city_initialized }} }}
        set_country_flag = hro_city_initialized
        set_variable = {{ hro_city_responses_completed = 0 }}
        set_variable = {{ hro_city_liberated_total = 0 }}
        {init_city_vars}
    }}
'''+'\n'.join(daily)+'''
    hro_city_sync = yes
}''')
    put('common/ideas/hro_city_ideas.txt','ideas = { country = {\n'+'\n'.join(ideas)+'\n} }')
    presentations = {}
    for city in records():
        name = 'hro_city_' + city['key'] + '_finish'; key = name + '_tt'
        text(key,
             f"Первый ответ на потерю города {city['ru']}: {city['manpower']} людских ресурсов, {city['factories']} новых военных заводов на востоке при доступной мощности и два 100% профильных исследовательских бонуса. Усиливает конечную мобилизационную волну. При недоступной мощности — промышленные исследования. Награда общая с решением; второй раз не выдаётся. Уже полученные сильные ступени не понижаются.",
             f"First response to the loss of {city['en']}: {city['manpower']} manpower, {city['factories']} new eastern military factories where capacity permits and two 100% research bonuses. Advances the finite mobilisation wave. Unavailable capacity grants industry research. Shared with the decision, never awarded twice; higher tiers are preserved.")
        presentations[name] = 'custom_effect_tooltip = ' + key
    for name,ru,en in (
        ('hro_city_orderly_mobilization','Один раз в действительной войне с Германией: 120 000 людских ресурсов и конечная мобилизационная волна даже без потери городов. Уже полученная более сильная ступень сохраняется, действующее окно не продлевается.',
         'Once during an active war with Germany: 120,000 manpower and a finite mobilisation wave without losing cities. Existing higher tiers are preserved and an active window is not refreshed.'),
        ('hro_city_start_liberation_offensive','После первого освобождения крупного города: одно 180-дневное наступательное окно, атака +25%, скорость +15%, восстановление организации +25%. Требуется действительная война с Германией; повторная награда недоступна.',
         'After the first major-city liberation: one 180-day offensive window, attack +25%, speed +15%, organisation recovery +25%. Requires active war with Germany and cannot be awarded twice.')):
        text(name+'_tt',ru,en); presentations[name] = 'custom_effect_tooltip = ' + name + '_tt'
    put('common/scripted_effects/hro_city_effects.txt',present_effects('\n'.join(effects), presentations))
    put('common/on_actions/hro_city_on_actions.txt','on_actions = { on_daily = { effect = { if = { limit = { original_tag = SOV } hro_city_tick = yes } } } }')
    put('common/decisions/categories/hro_city_categories.txt','hro_city_responses = { icon = generic_army allowed = { original_tag = SOV } visible = { original_tag = SOV } visible_when_empty = no }')
    put('common/decisions/hro_city_responses.txt','hro_city_responses = {\n'+'\n'.join(decisions)+'\n}')
    put('events/hro_city_events.txt','\n'.join(events))
    for language, entries in loc.items():
        put(f'localisation/{language}/hro_city_l_{language}.yml',f'l_{language}:\n'+''.join(f' {k}:0 {json.dumps(v,ensure_ascii=False)}\n' for k,v in entries.items()),True)
    return {'cities':len(records()),'decisions':len(decisions),'events':len(events)-1,'ideas':len(ideas),
            'max_crisis_tier':3,'crisis_war_days':90,'mobilization_window_days':240,'phase_caps':{'opening':1,'parity':2,'mature':3},'one_response_per_city':True,
            'recapture_rewards_once':True,'victory_point_control':True,'native_evacuation_duplicated':False}
