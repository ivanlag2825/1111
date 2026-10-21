#!/usr/bin/env python3
"""Generate bounded Eastern Front shock, winter strain and learned reforms.

The four public effects record reforms even if their focus is completed before
the relevant war or winter. A country-scoped daily hook applies the earned
result once eligible. This module never edits native DLC penalties or units.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

SOV_PENALTIES = ('hro_idea_war_sov_surprise', 'hro_idea_war_sov_prepared_shock',
                 'hro_idea_war_sov_recovery_strain')
GER_PENALTIES = ('hro_idea_war_ger_first_winter', 'hro_idea_war_ger_prepared_winter',
                 'hro_idea_war_ger_later_winter')


def winter_trigger():
    """Explicit Nov–March windows avoid ambiguous/unsupported month indices."""
    return 'OR = {\n' + '\n'.join(
        f'    AND = {{ date > {year}.10.31 date < {year + 1}.4.1 }}'
        for year in range(1935, 1947)) + '\n}'


def _remove(identities):
    return ' '.join('remove_ideas = ' + identity for identity in identities)


def _select(identities, desired):
    return _remove([i for i in identities if i != desired]) + f'''\n
    if = {{ limit = {{ NOT = {{ has_idea = {desired} }} }} add_ideas = {desired} }}'''


def generate(output: Path):
    output = Path(output)
    loc = {'russian': {}, 'english': {}}

    def put(name, value, bom=False):
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding='utf-8-sig' if bom else 'utf-8')

    def text(key, ru, en):
        loc['russian'][key], loc['english'][key] = ru, en

    idea_records = [
        (SOV_PENALTIES[0], 'Срыв приграничного развёртывания', 'Disrupted Frontier Deployment',
         'Первые 120 дней первой войны с Германией, только если СССР вступил на обороняющейся стороне. Организация −25%, её восстановление −25%, планирование −35%, выпуск военных заводов −20%, потребление снабжения +25%. Подготовленные округа ослабляют этот кризис; после 120 дней остаётся меньшая нагрузка. Исходные ограничения Красной армии продолжают действовать отдельно.',
         'The first 120 days of the first war with Germany, only when the USSR entered on the defending side. Organisation −25%, recovery −25%, planning −35%, military factory output −20%, supply use +25%. Prepared districts mitigate the crisis; after 120 days it softens. Native Red Army restrictions remain separate.',
         {'army_org_factor': -.25, 'army_org_regain': -.25, 'planning_speed': -.35,
          'industrial_capacity_factory': -.20, 'supply_consumption_factor': .25}),
        (SOV_PENALTIES[1], 'Подготовленное отражение вторжения', 'Prepared Response to Invasion',
         'Подготовка округов сократила первоначальный кризис: организация −10%, восстановление −10%, планирование −15%, военный выпуск −10%, снабжение +10%. Остаток первых 120 дней всё ещё требует осторожной обороны.',
         'District preparation mitigates the initial crisis: organisation −10%, recovery −10%, planning −15%, military output −10%, supply use +10%. The remainder of the first 120 days still calls for a careful defence.',
         {'army_org_factor': -.10, 'army_org_regain': -.10, 'planning_speed': -.15,
          'industrial_capacity_factory': -.10, 'supply_consumption_factor': .10}),
        (SOV_PENALTIES[2], 'Перестройка фронтового управления', 'Rebuilding Front Administration',
         'Острый кризис закончился через 120 дней. Без подготовки округов или полной реформы остаются восстановление организации −15%, планирование −20% и снабжение +15%. Подготовка снимает этот остаток; полная военная адаптация превращает опыт в преимущество.',
         'The acute crisis ended after 120 days. Without district preparation or the full reform, organisation recovery remains −15%, planning −20% and supply use +15%. Preparation removes this residual strain; full adaptation turns experience into an advantage.',
         {'army_org_regain': -.15, 'planning_speed': -.20, 'supply_consumption_factor': .15}),
        ('hro_idea_war_sov_adapted', 'Фронты научились воевать', 'Fronts That Have Learned to Fight',
         'Новая система управления освоена после 120 дней войны с Германией: восстановление организации +25%, скорость планирования +35%, максимальный план +25%, военный выпуск +10%, потребление снабжения −10%. Заменяет все новые штрафы вторжения. Исходные чистки, реабилитация и уроки войны снимаются по своим правилам.',
         'The new command system matures after 120 days of war with Germany: organisation recovery +25%, planning speed +35%, maximum planning +25%, military output +10%, supply use −10%. Replaces all new invasion penalties. Native purges, rehabilitation and lessons of war retain their own rules.',
         {'army_org_regain': .25, 'planning_speed': .35, 'max_planning_factor': .25,
          'industrial_capacity_factory': .10, 'supply_consumption_factor': -.10}),
        (GER_PENALTIES[0], 'Первый неподготовленный зимний фронт', 'First Unprepared Winter Front',
         'Первая зима войны с СССР: снабжение +30%, зимнее истощение +75%, восстановление организации −25%, скорость армий −15%, планирование −30%. Действует только в ноябре–марте и только во время войны с СССР. Предварительная подготовка смягчает ограничения; освоенная континентальная логистика снимает их.',
         'The first winter at war with the USSR: supply use +30%, winter attrition +75%, organisation recovery −25%, army speed −15%, planning −30%. Active only in November–March and while at war with the USSR. Prior preparation mitigates the penalties; mastered continental logistics removes them.',
         {'supply_consumption_factor': .30, 'winter_attrition_factor': .75,
          'army_org_regain': -.25, 'army_speed_factor': -.15, 'planning_speed': -.30}),
        (GER_PENALTIES[1], 'Зимний фронт с подготовленными службами', 'Winter Front with Prepared Services',
         'Подготовка сократила зимние ограничения: снабжение +12%, зимнее истощение +25%, восстановление организации −10%, скорость армий −5%, планирование −10%. Зимняя перестройка снабжения окончательно заменяет эти издержки положительным результатом.',
         'Preparation mitigates winter strain: supply use +12%, winter attrition +25%, organisation recovery −10%, army speed −5%, planning −10%. The completed supply reform replaces these costs with a positive result.',
         {'supply_consumption_factor': .12, 'winter_attrition_factor': .25,
          'army_org_regain': -.10, 'army_speed_factor': -.05, 'planning_speed': -.10}),
        (GER_PENALTIES[2], 'Нерешённые зимние ограничения', 'Unresolved Winter Constraints',
         'В последующие зимы неподготовленная система всё ещё расходует больше снабжения (+18%), теряет больше от зимнего истощения (+40%) и медленнее восстанавливает организацию (−15%). Это более слабое повторение, а не новый первый кризис. Весной штраф исчезает.',
         'In later winters an unprepared system still uses more supply (+18%), suffers higher winter attrition (+40%) and recovers organisation more slowly (−15%). This is a milder recurrence, not another first-winter crisis. It ends in spring.',
         {'supply_consumption_factor': .18, 'winter_attrition_factor': .40, 'army_org_regain': -.15}),
        ('hro_idea_war_ger_adapted', 'Освоенная война в холодном климате', 'Mastered Cold-Climate Warfare',
         'Континентальная система снабжения проверена зимней войной: зимнее истощение −40%, скорость холодовой акклиматизации +100%, потребление снабжения −10%, восстановление организации +15%. Новые зимние штрафы HRO больше не применяются. Снег, холод и обычные правила местности игры сохраняются.',
         'Continental supply has been tested by winter warfare: winter attrition −40%, cold acclimatisation speed +100%, supply use −10%, organisation recovery +15%. The new HRO winter penalties no longer apply. Snow, cold and normal terrain rules remain in force.',
         {'winter_attrition_factor': -.40, 'acclimatization_cold_climate_gain_factor': 1.0,
          'supply_consumption_factor': -.10, 'army_org_regain': .15}),
    ]
    definitions = []
    for identity, ru, en, dr, de, modifiers in idea_records:
        if '_sov_' in identity:
            dr += ' Дни действительной войны с Германией: [?hro_war_sov_war_days|0]/120; мир приостанавливает отсчёт.'
            de += ' Actual days at war with Germany: [?hro_war_sov_war_days|0]/120; peace pauses the count.'
        else:
            dr += ' Зимний опыт войны с СССР: [?hro_war_ger_winter_days|0]/45 дней; мир и апрель–октябрь не учитываются.'
            de += ' Winter war experience against the USSR: [?hro_war_ger_winter_days|0]/45 days; peace and April–October do not count.'
        text(identity, ru, en)
        text(identity + '_desc', dr, de)
        tag = 'SOV' if '_sov_' in identity else 'GER'
        values = ' '.join(f'{key} = {value:g}' for key, value in modifiers.items())
        definitions.append(f'''{identity} = {{ picture = generic_army allowed = {{ original_tag = {tag} }} removal_cost = -1 modifier = {{ {values} }} }}''')
    put('common/ideas/hro_war_ideas.txt', 'ideas = { country = {\n' + '\n'.join(definitions) + '\n} }\n')

    put('common/scripted_triggers/hro_war_triggers.txt', '''hro_war_eastern_war = {
    date < 1947.1.1
    has_capitulated = no
    OR = {
        AND = { original_tag = SOV any_enemy_country = { original_tag = GER has_capitulated = no } }
        AND = { original_tag = GER any_enemy_country = { original_tag = SOV has_capitulated = no } }
    }
}
hro_war_sov_defending = {
    original_tag = SOV
    any_enemy_country = { original_tag = GER has_capitulated = no has_offensive_war_with = PREV }
}
hro_war_winter_season = {
''' + winter_trigger() + '\n}\n')

    effects = f'''# Public effects record completed reforms even before war/season eligibility.
hro_war_sov_reorganize_fronts = {{
    if = {{ limit = {{ original_tag = SOV }}
        set_country_flag = hro_war_sov_prepared
        hro_war_sov_sync_penalty = yes
    }}
}}
hro_war_sov_complete_adaptation = {{
    if = {{ limit = {{ original_tag = SOV }}
        set_country_flag = hro_war_sov_reform_authorized
        hro_war_sov_apply_reform = yes
        hro_war_sov_sync_penalty = yes
    }}
}}
hro_war_sov_apply_reform = {{
    if = {{ limit = {{
        original_tag = SOV hro_war_eastern_war = yes
        has_country_flag = hro_war_sov_reform_authorized
        has_country_flag = hro_war_sov_started
        NOT = {{ has_country_flag = hro_war_sov_acute_phase }}
        check_variable = {{ hro_war_sov_war_days > 119 }}
        NOT = {{ has_country_flag = hro_war_sov_adapted }}
    }}
        set_country_flag = hro_war_sov_adapted
        {_remove(SOV_PENALTIES)}
        add_ideas = hro_idea_war_sov_adapted
        country_event = {{ id = hro.303 days = 1 }}
    }}
}}
hro_war_sov_sync_penalty = {{
    if = {{ limit = {{ hro_war_eastern_war = yes has_country_flag = hro_war_sov_surprised NOT = {{ has_country_flag = hro_war_sov_adapted }} }}
        if = {{ limit = {{ has_country_flag = hro_war_sov_acute_phase }}
            if = {{ limit = {{ has_country_flag = hro_war_sov_prepared }}
                {_select(SOV_PENALTIES, SOV_PENALTIES[1])}
            }}
            else = {{ {_select(SOV_PENALTIES, SOV_PENALTIES[0])} }}
        }}
        else_if = {{ limit = {{ NOT = {{ has_country_flag = hro_war_sov_prepared }} }}
            {_select(SOV_PENALTIES, SOV_PENALTIES[2])}
        }}
        else = {{ {_remove(SOV_PENALTIES)} }}
    }}
    else = {{ {_remove(SOV_PENALTIES)} }}
}}
hro_war_sov_tick = {{
    if = {{ limit = {{ hro_war_eastern_war = yes NOT = {{ has_country_flag = hro_war_sov_started }} }}
        set_country_flag = hro_war_sov_started
        set_variable = {{ hro_war_sov_war_days = 0 }}
        set_country_flag = hro_war_sov_acute_phase
        if = {{ limit = {{ hro_war_sov_defending = yes }}
            set_country_flag = hro_war_sov_surprised
            country_event = {{ id = hro.301 days = 1 }}
        }}
    }}
    else_if = {{ limit = {{ hro_war_eastern_war = yes check_variable = {{ hro_war_sov_war_days < 120 }} }}
        add_to_variable = {{ hro_war_sov_war_days = 1 }}
    }}
    if = {{ limit = {{ hro_war_eastern_war = yes check_variable = {{ hro_war_sov_war_days > 119 }} }}
        clr_country_flag = hro_war_sov_acute_phase
    }}
    hro_war_sov_apply_reform = yes
    hro_war_sov_sync_penalty = yes
}}
hro_war_ger_prepare_winter = {{
    if = {{ limit = {{ original_tag = GER }}
        set_country_flag = hro_war_ger_prepared
        hro_war_ger_sync_penalty = yes
    }}
}}
hro_war_ger_complete_winter_adaptation = {{
    if = {{ limit = {{ original_tag = GER }}
        set_country_flag = hro_war_ger_reform_authorized
        hro_war_ger_apply_reform = yes
        hro_war_ger_sync_penalty = yes
    }}
}}
hro_war_ger_apply_reform = {{
    if = {{ limit = {{
        original_tag = GER hro_war_eastern_war = yes
        has_country_flag = hro_war_ger_reform_authorized
        has_country_flag = hro_war_ger_first_winter
        check_variable = {{ hro_war_ger_winter_days > 44 }}
        NOT = {{ has_country_flag = hro_war_ger_adapted }}
    }}
        set_country_flag = hro_war_ger_adapted
        {_remove(GER_PENALTIES)}
        add_ideas = hro_idea_war_ger_adapted
        country_event = {{ id = hro.304 days = 1 }}
    }}
}}
hro_war_ger_sync_penalty = {{
    if = {{ limit = {{ hro_war_eastern_war = yes hro_war_winter_season = yes NOT = {{ has_country_flag = hro_war_ger_adapted }} }}
        if = {{ limit = {{ has_country_flag = hro_war_ger_prepared }}
            {_select(GER_PENALTIES, GER_PENALTIES[1])}
        }}
        else_if = {{ limit = {{ has_country_flag = hro_war_ger_first_winter_active }}
            {_select(GER_PENALTIES, GER_PENALTIES[0])}
        }}
        else = {{ {_select(GER_PENALTIES, GER_PENALTIES[2])} }}
    }}
    else = {{ {_remove(GER_PENALTIES)} }}
}}
hro_war_ger_tick = {{
    if = {{ limit = {{ hro_war_eastern_war = yes hro_war_winter_season = yes NOT = {{ has_country_flag = hro_war_ger_first_winter }} }}
        set_country_flag = hro_war_ger_first_winter
        set_variable = {{ hro_war_ger_winter_days = 0 }}
        set_country_flag = hro_war_ger_first_winter_active
        country_event = {{ id = hro.302 days = 1 }}
    }}
    else_if = {{ limit = {{ hro_war_eastern_war = yes hro_war_winter_season = yes check_variable = {{ hro_war_ger_winter_days < 45 }} }}
        add_to_variable = {{ hro_war_ger_winter_days = 1 }}
    }}
    if = {{ limit = {{ OR = {{ NOT = {{ hro_war_eastern_war = yes }} NOT = {{ hro_war_winter_season = yes }} }} }}
        clr_country_flag = hro_war_ger_first_winter_active
    }}
    hro_war_ger_apply_reform = yes
    hro_war_ger_sync_penalty = yes
}}
'''
    put('common/scripted_effects/hro_war_effects.txt', effects)
    put('common/on_actions/hro_war_on_actions.txt', '''on_actions = {
    # on_daily already runs in each country. Never scope GER/SOV globally here.
    on_daily = { effect = {
        if = { limit = { original_tag = SOV } hro_war_sov_tick = yes }
        else_if = { limit = { original_tag = GER } hro_war_ger_tick = yes }
    } }
}
''')

    notifications = [
        (301, 'Развёртывание сорвано', 'Deployment Disrupted',
         'Война с Германией застала систему управления на обороняющейся стороне. Первые 120 дней действуют крупные ограничения, затем кризис автоматически ослабевает. «$hro_sov_campaign_preparedness$» готовит войска; «$hro_sov_front_feedback$» закрепляет реформу. Если эти этапы уже выполнены, подготовка учитывается сейчас, а полный результат включится после первых 120 дней.',
         'War with Germany has caught our command system on the defending side. Major restrictions last for the first 120 days, then soften automatically. $hro_sov_campaign_preparedness$ prepares the troops; $hro_sov_front_feedback$ authorises the full reform. If these stages were already completed, preparation applies now and the earned full result activates after the first 120 days.'),
        (302, 'Восточный фронт вступает в зиму', 'Winter Reaches the Eastern Front',
         'С ноября по март война с СССР требует зимнего обеспечения. Без подготовки первая зима серьёзно замедляет операции и увеличивает расход снабжения. «$hro_ger_motor_transport_standards$» смягчает кризис; «$hro_ger_sustained_supply$» превращает освоенный зимний опыт в постоянное преимущество. Заранее выполненная реформа сработает автоматически после 45 действительных зимних дней войны; мир и тёплые месяцы не приближают результат.',
         'From November through March, war with the USSR requires winter support. Without preparation, the first winter seriously slows operations and increases supply costs. $hro_ger_motor_transport_standards$ mitigates the crisis; $hro_ger_sustained_supply$ converts winter experience into a permanent advantage. A previously completed reform activates automatically after 45 actual winter days at war; peace and warm months do not advance the result.'),
        (303, 'Управление фронтами перестроено', 'Front Command Reorganised',
         'Завершённая реформа и первые 120 дней войны с Германией позволили закрепить новую практику. Новые штрафы вторжения сняты; восстановление организации, планирование, выпуск вооружений и снабжение получили постоянное улучшение. Исходные ограничения и реформы Красной армии продолжают действовать по своим правилам.',
         'The completed reform and the first 120 days of war with Germany have established a new practice. The new invasion penalties are removed; organisation recovery, planning, armaments output and supply receive permanent improvements. Native Red Army restrictions and reforms keep their own rules.'),
        (304, 'Система зимнего обеспечения освоена', 'Winter Support Mastered',
         'Существующая реформа снабжения подтверждена 45 зимними днями войны с СССР. Дополнительные зимние штрафы сняты. Холодовая подготовка ускорена, зимнее истощение сокращено, тыл расходует меньше снабжения. Обычные эффекты погоды и местности игры остаются.',
         'The completed supply reform has been tested by 45 winter days at war with the USSR. Additional winter penalties are removed. Cold acclimatisation accelerates, winter attrition falls and supply use improves. Normal game weather and terrain effects remain.'),
    ]
    events = ['add_namespace = hro']
    for index, ru, en, dr, de in notifications:
        identity = f'hro.{index}'
        text(identity + '.t', ru, en)
        text(identity + '.d', dr, de)
        text(identity + '.a', 'Принять новую обстановку.', 'Acknowledge the new situation.')
        events.append(f'''country_event = {{
    id = {identity} title = {identity}.t desc = {identity}.d
    is_triggered_only = yes fire_only_once = yes
    option = {{ name = {identity}.a }}
}}''')
    put('events/hro_war_events.txt', '\n'.join(events) + '\n')
    for language, entries in loc.items():
        put(f'localisation/{language}/hro_war_l_{language}.yml', f'l_{language}:\n' + ''.join(
            f' {key}:0 {json.dumps(value, ensure_ascii=False)}\n' for key, value in entries.items()), bom=True)
    permanent = {('SOV' if '_sov_' in identity else 'GER'): modifiers
                 for identity, ru, en, dr, de, modifiers in idea_records if identity.endswith('_adapted')}
    return {'ideas': len(idea_records), 'events': len(notifications), 'soviet_shock_days': 120,
            'german_winter_experience_days': 45,
            'duration_clock': 'bounded actual daily war counters; peace and German warm seasons do not advance',
            'winter_season': 'November through March', 'winter_years': [1936, 1946],
            'reforms_authorized_before_eligibility': True, 'surprise_requires_defending': True,
            'native_penalties_removed': False, 'daily_scope': 'country, filtered by original_tag',
            'permanent_rewards': permanent}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(generate(args.output), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
