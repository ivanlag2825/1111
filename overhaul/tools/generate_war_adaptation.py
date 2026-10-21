#!/usr/bin/env python3
"""Bounded Eastern Front crisis phases, winter costs and earned reforms."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[2] / 'tools')]
from effect_presentation import present_effects

SOV_PENALTIES = ('hro_idea_war_sov_surprise', 'hro_idea_war_sov_prepared_shock',
                 'hro_idea_war_sov_recovery_strain', 'hro_idea_war_sov_dislocated_fronts',
                 'hro_idea_war_sov_prepared_fronts', 'hro_idea_war_sov_prepared_regrouping')
GER_PENALTIES = ('hro_idea_war_ger_first_winter', 'hro_idea_war_ger_prepared_winter',
                 'hro_idea_war_ger_later_winter', 'hro_idea_war_ger_adapted_winter')
SOV_LEARNED = 'hro_idea_war_sov_battle_hardened'
SOV_DAYS = 240
WINTER_DAYS = 90


def winter_trigger():
    return 'OR = {\n' + '\n'.join(
        f'    AND = {{ date > {year}.10.31 date < {year + 1}.4.1 }}'
        for year in range(1935, 1947)) + '\n}'


def _remove(identities):
    return ' '.join(f'if = {{ limit = {{ has_idea = {i} }} remove_ideas = {i} }}' for i in identities)


def _select(identities, desired):
    return _remove([i for i in identities if i != desired]) + f' if = {{ limit = {{ NOT = {{ has_idea = {desired} }} }} add_ideas = {desired} }}'


def generate(output: Path):
    output=Path(output);loc={'russian':{},'english':{}}
    def put(name,value,bom=False):
        path=output/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(value,encoding='utf-8-sig' if bom else 'utf-8')
    def text(key,ru,en):loc['russian'][key],loc['english'][key]=ru,en
    records=[]
    def idea(identity,ru,en,mods,dr,de):records.append((identity,ru,en,dr,de,mods))
    idea(SOV_PENALTIES[0],'Срыв приграничного развёртывания','Disrupted Frontier Deployment',
         {'army_org_factor':-.35,'army_org_regain':-.45,'planning_speed':-.60,'industrial_capacity_factory':-.35,'supply_consumption_factor':.40,'army_speed_factor':-.15},
         'Первая ступень кризиса: первые 45 действительных дней оборонительной войны с Германией. Затем автоматически сменяется меньшими ограничениями. Подготовка округов смягчает каждую ступень; родные штрафы DLC действуют отдельно.',
         'The first 45 actual days of defensive war with Germany. Automatically replaced by milder phases. District preparation mitigates each phase; native DLC penalties remain separate.')
    idea(SOV_PENALTIES[1],'Подготовленное отражение вторжения','Prepared Response to Invasion',
         {'army_org_factor':-.22,'army_org_regain':-.30,'planning_speed':-.40,'industrial_capacity_factory':-.25,'supply_consumption_factor':.25,'army_speed_factor':-.05},
         'Подготовленные округа смягчают первые 45 дней, но не отменяют кризис. После 45 и 120 военных дней ограничения автоматически уменьшаются.',
         'Prepared districts mitigate the first 45 days without removing the crisis. Restrictions soften automatically after 45 and 120 war days.')
    idea(SOV_PENALTIES[2],'Стратегическая перегруппировка','Strategic Regrouping',
         {'army_org_factor':-.12,'army_org_regain':-.15,'planning_speed':-.20,'industrial_capacity_factory':-.12,'supply_consumption_factor':.15},
         'Дни 120–239 войны: острый кризис ослаб, но восстановление фронтов ещё требует времени. На 240-й день отрицательная ступень сменяется положительным опытом; завершённая реформа даст более сильный результат.',
         'War days 120–239: the acute crisis has eased. At day 240 restrictions become positive experience; the completed reform earns a stronger result.')
    idea(SOV_PENALTIES[3],'Расстроенные фронты','Dislocated Fronts',
         {'army_org_factor':-.25,'army_org_regain':-.30,'planning_speed':-.40,'industrial_capacity_factory':-.25,'supply_consumption_factor':.30,'army_speed_factor':-.10},
         'Дни 45–119 войны: первая катастрофа преодолена, управление ещё нарушено. В 120 дней начинается стратегическая перегруппировка.',
         'War days 45–119: the initial catastrophe has passed, but command remains disrupted. Strategic regrouping starts at day 120.')
    idea(SOV_PENALTIES[4],'Фронты подготовленных округов','Prepared District Fronts',
         {'army_org_factor':-.15,'army_org_regain':-.20,'planning_speed':-.25,'industrial_capacity_factory':-.18,'supply_consumption_factor':.18},
         'Смягчённая подготовкой вторая ступень кризиса: дни 45–119 войны.',
         'The prepared second phase of the crisis: war days 45–119.')
    idea(SOV_PENALTIES[5],'Плановая перегруппировка фронтов','Orderly Front Regrouping',
         {'army_org_factor':-.05,'army_org_regain':-.08,'planning_speed':-.10,'industrial_capacity_factory':-.05,'supply_consumption_factor':.08},
         'Подготовка округов смягчает остаточные ограничения дней 120–239. Срок опыта не сокращается.',
         'Prepared districts mitigate the remaining restrictions of war days 120–239 without skipping the experience requirement.')
    idea(SOV_LEARNED,'Закалённые фронты','Battle-Hardened Fronts',
         {'army_defence_factor':.10,'army_org_regain':.15,'planning_speed':.10,'industrial_capacity_factory':.08,'supply_consumption_factor':-.05},
         'После 240 действительных дней войны новые штрафы вторжения автоматически сменились преимуществами. «Отчёты фронтов вместо сводок» заменяют этот опыт полной реформой; две положительные ступени не складываются.',
         'After 240 actual war days the new invasion penalties automatically become advantages. Front Feedback replaces this tier with the full reform; the two positive tiers never stack.')
    idea('hro_idea_war_sov_adapted','Фронты научились воевать','Fronts That Have Learned to Fight',
         {'army_attack_factor':.25,'army_defence_factor':.20,'army_org_factor':.15,'army_org_regain':.40,'planning_speed':.50,'max_planning_factor':.35,'industrial_capacity_factory':.20,'supply_consumption_factor':-.10},
         'Завершённая командная реформа и 240 действительных дней войны с Германией превращают кризис в крупное постоянное преимущество. Заменяет все новые штрафы вторжения и ранний положительный опыт. Чистки и ограничения DLC снимаются настоящими игровыми реформами.',
         'The completed command reform and 240 actual war days turn the crisis into a major permanent advantage. Replaces invasion penalties and the earlier positive tier. Native purges and restrictions retain their own removal rules.')
    idea(GER_PENALTIES[0],'Первый неподготовленный зимний фронт','First Unprepared Winter Front',
         {'supply_consumption_factor':.50,'winter_attrition_factor':1.25,'army_org_regain':-.45,'army_speed_factor':-.25,'planning_speed':-.45,'army_org_factor':-.15,'army_attack_factor':-.15},
         'Тяжёлый кризис первой зимы войны с СССР, ноябрь–март. Подготовка смягчает его; полная логистическая реформа требует 90 действительных зимних дней войны. Наступательное окно первого удара зимой не действует.',
         'Severe first-winter crisis during November–March at war with the USSR. Preparation mitigates it; full logistics reform needs 90 actual winter war days. The initial offensive window is inactive in winter.')
    idea(GER_PENALTIES[1],'Зимний фронт с подготовленными службами','Winter Front with Prepared Services',
         {'supply_consumption_factor':.25,'winter_attrition_factor':.65,'army_org_regain':-.25,'army_speed_factor':-.12,'planning_speed':-.25,'army_org_factor':-.08,'army_attack_factor':-.08},
         'Подготовка смягчила зимние ограничения, но не устранила их. После полной реформы и 90 зимних дней остаётся только малая сезонная нагрузка.',
         'Preparation mitigates winter restrictions without eliminating them. Full reform and 90 winter days leave only a smaller seasonal burden.')
    idea(GER_PENALTIES[2],'Нерешённые зимние ограничения','Unresolved Winter Constraints',
         {'supply_consumption_factor':.35,'winter_attrition_factor':.85,'army_org_regain':-.30,'army_speed_factor':-.18,'planning_speed':-.30,'army_org_factor':-.10,'army_attack_factor':-.10},
         'Следующие зимы всё ещё тяжело нагружают неподготовленную армию. Весной сезонный штраф снимается, накопленный зимний опыт сохраняется.',
         'Later winters still burden an unprepared army. Spring removes the seasonal penalty; accumulated experience is retained.')
    idea(GER_PENALTIES[3],'Цена зимних операций','Cost of Winter Operations',
         {'supply_consumption_factor':.10,'winter_attrition_factor':.25,'army_speed_factor':-.05,'planning_speed':-.10},
         'Остаточная сезонная нагрузка уже адаптированной армии. Действует лишь зимой при активной войне с СССР; постоянные преимущества освоенной логистики сохраняются.',
         'Residual seasonal costs for an adapted army, only in winter during an active war with the USSR. The permanent benefits of mastered logistics remain.')
    idea('hro_idea_war_ger_adapted','Освоенная война в холодном климате','Mastered Cold-Climate Warfare',
         {'winter_attrition_factor':-.40,'acclimatization_cold_climate_gain_factor':1.0,'supply_consumption_factor':-.10,'army_org_regain':.15},
         'Логистическая реформа проверена 90 действительными зимними днями войны. Тяжёлые кризисы заменяются преимуществами, однако зимой остаётся меньшая сезонная нагрузка. Обычные холод, снег и местность игры сохраняются.',
         'The logistics reform has been tested by 90 actual winter war days. Severe crises become advantages with smaller seasonal costs. Normal cold, snow and terrain effects remain.')
    definitions=[]
    for identity,ru,en,dr,de,mods in records:
        clock=('hro_war_sov_war_days',SOV_DAYS) if '_sov_' in identity else ('hro_war_ger_winter_days',WINTER_DAYS)
        dr+=f' Военный опыт: [?{clock[0]}|0]/{clock[1]}; мир приостанавливает отсчёт.'
        de+=f' War experience: [?{clock[0]}|0]/{clock[1]}; peace pauses the count.'
        text(identity,ru,en);text(identity+'_desc',dr,de)
        tag='SOV' if '_sov_' in identity else 'GER'
        values=' '.join(f'{k} = {v:g}' for k,v in mods.items())
        definitions.append(f'{identity} = {{ picture = generic_army allowed = {{ original_tag = {tag} }} removal_cost = -1 modifier = {{ {values} }} }}')
    put('common/ideas/hro_war_ideas.txt','ideas = { country = {\n'+'\n'.join(definitions)+'\n} }\n')
    put('common/scripted_triggers/hro_war_triggers.txt','''hro_war_eastern_war = {
    date < 1947.1.1 has_capitulated = no
    OR = {
        AND = { original_tag = SOV any_enemy_country = { original_tag = GER has_capitulated = no } }
        AND = { original_tag = GER any_enemy_country = { original_tag = SOV has_capitulated = no } }
    }
}
hro_war_sov_defending = {
    original_tag = SOV
    any_enemy_country = { original_tag = GER has_capitulated = no has_offensive_war_with = PREV }
}
hro_war_ger_attacking = {
    original_tag = GER
    any_enemy_country = { original_tag = SOV has_capitulated = no has_defensive_war_with = PREV }
}
hro_war_winter_season = {
'''+winter_trigger()+'\n}\n')
    def sov_phase(unprepared,prepared):
        return f'if = {{ limit = {{ has_country_flag = hro_war_sov_prepared }} {_select(SOV_PENALTIES,prepared)} }} else = {{ {_select(SOV_PENALTIES,unprepared)} }}'
    effects=f'''hro_war_sov_reorganize_fronts = {{
    if = {{ limit = {{ original_tag = SOV }} set_country_flag = hro_war_sov_prepared hro_war_sov_sync_penalty = yes }}
}}
hro_war_sov_complete_adaptation = {{
    if = {{ limit = {{ original_tag = SOV }} set_country_flag = hro_war_sov_reform_authorized hro_war_sov_apply_reform = yes hro_war_sov_sync_penalty = yes }}
}}
hro_war_sov_apply_reform = {{
    if = {{ limit = {{ original_tag = SOV hro_war_eastern_war = yes
        has_country_flag = hro_war_sov_reform_authorized has_country_flag = hro_war_sov_started
        check_variable = {{ hro_war_sov_war_days > 239 }} NOT = {{ has_country_flag = hro_war_sov_adapted }} }}
        set_country_flag = hro_war_sov_adapted
        {_remove(SOV_PENALTIES+(SOV_LEARNED,))}
        add_ideas = hro_idea_war_sov_adapted country_event = {{ id = hro.303 days = 1 }}
    }}
}}
hro_war_sov_sync_penalty = {{
    if = {{ limit = {{ hro_war_eastern_war = yes has_country_flag = hro_war_sov_surprised NOT = {{ has_country_flag = hro_war_sov_adapted }} }}
        if = {{ limit = {{ check_variable = {{ hro_war_sov_war_days < 45 }} }} {sov_phase(SOV_PENALTIES[0],SOV_PENALTIES[1])} }}
        else_if = {{ limit = {{ check_variable = {{ hro_war_sov_war_days < 120 }} }} {sov_phase(SOV_PENALTIES[3],SOV_PENALTIES[4])} }}
        else_if = {{ limit = {{ check_variable = {{ hro_war_sov_war_days < 240 }} }} {sov_phase(SOV_PENALTIES[2],SOV_PENALTIES[5])} }}
        else = {{ {_remove(SOV_PENALTIES)} }}
    }} else = {{ {_remove(SOV_PENALTIES)} }}
    if = {{ limit = {{ original_tag = SOV hro_war_eastern_war = yes check_variable = {{ hro_war_sov_war_days > 239 }}
        NOT = {{ has_country_flag = hro_war_sov_adapted }} NOT = {{ has_idea = {SOV_LEARNED} }} }} add_ideas = {SOV_LEARNED} }}
}}
hro_war_sov_tick = {{
    if = {{ limit = {{ hro_war_eastern_war = yes NOT = {{ has_country_flag = hro_war_sov_started }} }}
        set_country_flag = hro_war_sov_started set_variable = {{ hro_war_sov_war_days = 0 }}
        set_country_flag = hro_war_sov_acute_phase
        if = {{ limit = {{ hro_war_sov_defending = yes }} set_country_flag = hro_war_sov_surprised country_event = {{ id = hro.301 days = 1 }} }}
    }} else_if = {{ limit = {{ hro_war_eastern_war = yes check_variable = {{ hro_war_sov_war_days < 240 }} }} add_to_variable = {{ hro_war_sov_war_days = 1 }} }}
    if = {{ limit = {{ hro_war_eastern_war = yes check_variable = {{ hro_war_sov_war_days > 44 }}
        has_country_flag = hro_war_sov_surprised NOT = {{ has_country_flag = hro_war_sov_phase_two }} }}
        set_country_flag = hro_war_sov_phase_two country_event = {{ id = hro.305 days = 1 }} }}
    if = {{ limit = {{ hro_war_eastern_war = yes check_variable = {{ hro_war_sov_war_days > 119 }} }}
        clr_country_flag = hro_war_sov_acute_phase
        if = {{ limit = {{ has_country_flag = hro_war_sov_surprised NOT = {{ has_country_flag = hro_war_sov_phase_three }} }}
            set_country_flag = hro_war_sov_phase_three country_event = {{ id = hro.306 days = 1 }} }}
    }}
    hro_war_sov_apply_reform = yes hro_war_sov_sync_penalty = yes
}}
hro_war_ger_prepare_winter = {{
    if = {{ limit = {{ original_tag = GER }} set_country_flag = hro_war_ger_prepared hro_war_ger_sync_penalty = yes }}
}}
hro_war_ger_complete_winter_adaptation = {{
    if = {{ limit = {{ original_tag = GER }} set_country_flag = hro_war_ger_reform_authorized hro_war_ger_apply_reform = yes hro_war_ger_sync_penalty = yes }}
}}
hro_war_ger_apply_reform = {{
    if = {{ limit = {{ original_tag = GER hro_war_eastern_war = yes
        has_country_flag = hro_war_ger_reform_authorized has_country_flag = hro_war_ger_first_winter
        check_variable = {{ hro_war_ger_winter_days > 89 }} NOT = {{ has_country_flag = hro_war_ger_adapted }} }}
        set_country_flag = hro_war_ger_adapted {_remove(GER_PENALTIES)}
        add_ideas = hro_idea_war_ger_adapted country_event = {{ id = hro.304 days = 1 }}
    }}
}}
hro_war_ger_sync_penalty = {{
    if = {{ limit = {{ hro_war_eastern_war = yes hro_war_winter_season = yes }}
        if = {{ limit = {{ has_country_flag = hro_war_ger_adapted }} {_select(GER_PENALTIES,GER_PENALTIES[3])} }}
        else_if = {{ limit = {{ has_country_flag = hro_war_ger_prepared }} {_select(GER_PENALTIES,GER_PENALTIES[1])} }}
        else_if = {{ limit = {{ has_country_flag = hro_war_ger_first_winter_active }} {_select(GER_PENALTIES,GER_PENALTIES[0])} }}
        else = {{ {_select(GER_PENALTIES,GER_PENALTIES[2])} }}
    }} else = {{ {_remove(GER_PENALTIES)} }}
}}
hro_war_ger_tick = {{
    if = {{ limit = {{ hro_war_eastern_war = yes hro_war_winter_season = yes NOT = {{ has_country_flag = hro_war_ger_first_winter }} }}
        set_country_flag = hro_war_ger_first_winter set_variable = {{ hro_war_ger_winter_days = 0 }}
        set_country_flag = hro_war_ger_first_winter_active country_event = {{ id = hro.302 days = 1 }}
    }} else_if = {{ limit = {{ hro_war_eastern_war = yes hro_war_winter_season = yes check_variable = {{ hro_war_ger_winter_days < 90 }} }}
        add_to_variable = {{ hro_war_ger_winter_days = 1 }} }}
    if = {{ limit = {{ OR = {{ NOT = {{ hro_war_eastern_war = yes }} NOT = {{ hro_war_winter_season = yes }} }} }} clr_country_flag = hro_war_ger_first_winter_active }}
    hro_war_ger_apply_reform = yes hro_war_ger_sync_penalty = yes
}}
'''
    presentations={
        'hro_war_sov_reorganize_fronts':('Подготовка округов: смягчает каждую ступень кризиса дней 0–239 первой оборонительной войны с Германией. До войны запоминается, отсутствующие идеи не снимает. С 240 дней действует положительный опыт; полная реформа усиливает его.',
            'District preparation mitigates every crisis phase of days 0–239 of the first defensive war with Germany. Recorded before war; absent ideas are untouched. Positive experience begins at day 240; full reform improves it.',None),
        'hro_war_sov_complete_adaptation':('Разрешает полную военную адаптацию после 240 действительных дней войны с Германией. До этого срок опыта сохраняется. Указанная положительная идея заменяет новые штрафы и ранний положительный опыт, не складываясь с ним.',
            'Authorises full adaptation after 240 actual war days with Germany. Does not skip the timer. The displayed positive idea replaces the new penalties and earlier positive experience without stacking.', 'hro_idea_war_sov_adapted'),
        'hro_war_ger_prepare_winter':('Подготовка зимних служб: смягчает тяжёлые сезонные ограничения. Заранее выполненная подготовка запоминается. Полная адаптация требует логистической реформы и 90 зимних дней войны с СССР.',
            'Winter preparation mitigates severe seasonal restrictions and is remembered before war. Full adaptation needs logistics reform and 90 actual winter war days against the USSR.',None),
        'hro_war_ger_complete_winter_adaptation':('Разрешает положительную зимнюю адаптацию после 90 действительных зимних дней войны с СССР. Тяжёлые кризисы заменяются преимуществами; остаётся меньшая сезонная нагрузка. Мир и тёплые месяцы срок не сокращают.',
            'Authorises positive winter adaptation after 90 actual winter war days against the USSR. Severe crises become advantages with smaller seasonal costs. Peace and warm months do not advance the clock.', 'hro_idea_war_ger_adapted')}
    visible={}
    for name,(ru,en,card) in presentations.items():
        key=name+'_tt';text(key,ru,en)
        visible[name]='custom_effect_tooltip = '+key+(' show_ideas_tooltip = '+card if card else '')
    put('common/scripted_effects/hro_war_effects.txt',present_effects(effects,visible))
    put('common/on_actions/hro_war_on_actions.txt','''on_actions = {
    on_daily = { effect = {
        if = { limit = { original_tag = SOV } hro_war_sov_tick = yes }
        else_if = { limit = { original_tag = GER } hro_war_ger_tick = yes }
    } }
}
''')
    messages=[
        (301,'Развёртывание сорвано','Deployment Disrupted','Дни 0–44: тяжёлый кризис. После 45 и 120 военных дней он ослабевает, а в 240 дней превращается в положительный опыт. Подготовка округов смягчает каждую ступень, отчёты фронтов закрепляют полную реформу.','Days 0–44 bring severe crisis. It softens at war days 45 and 120 and becomes positive experience at day 240. District preparation mitigates each phase; Front Feedback authorises full reform.'),
        (302,'Восточный фронт вступает в зиму','Winter Reaches the Eastern Front','Ноябрь–март: резко растут износ и расход снабжения, падает темп операций. Моторный парк смягчает кризис; континентальная логистика и 90 зимних дней открывают полную адаптацию.','November–March sharply increases attrition and supply costs while slowing operations. Transport preparation mitigates the crisis; continental logistics and 90 winter days earn full adaptation.'),
        (303,'Управление фронтами перестроено','Front Command Reorganised','Реформа и 240 военных дней превратили кризис в преимущества атаки, защиты, организации, планирования, выпуска и тыла. Родные ограничения DLC продолжают действовать по своим правилам.','Reform and 240 war days have turned crisis into advantages in attack, defence, organisation, planning, production and supply. Native DLC restrictions retain their own rules.'),
        (304,'Система зимнего обеспечения освоена','Winter Support Mastered','Реформа подтверждена 90 зимними днями войны. Крупные штрафы заменены преимуществами. Зимой остаётся малая нагрузка; холод, снег и местность действуют по обычным правилам.','Reform has been tested by 90 winter war days. Major penalties become advantages. Smaller seasonal costs remain; normal cold, snow and terrain rules still apply.'),
        (305,'Фронты пережили первый удар','Fronts Survive the First Blow','Пройдено 45 действительных дней войны. Первая ступень кризиса автоматически заменена более слабой; подготовка округов продолжает помогать.','45 actual war days have passed. The initial crisis has automatically become a milder phase; district preparation continues to help.'),
        (306,'Стратегическая перегруппировка','Strategic Regrouping','Пройдено 120 военных дней. Кризис ослаб ещё раз. В 240 дней накопленный опыт станет преимуществом, а завершённая командная реформа даст полную положительную ступень.','120 war days have passed and crisis has softened again. At 240 days experience becomes an advantage; completed command reform grants the full positive tier.')]
    events=['add_namespace = hro']
    for index,ru,en,dr,de in messages:
        identity=f'hro.{index}';text(identity+'.t',ru,en);text(identity+'.d',dr,de);text(identity+'.a','Принять новую обстановку.','Acknowledge the new situation.')
        events.append(f'country_event = {{ id = {identity} title = {identity}.t desc = {identity}.d is_triggered_only = yes fire_only_once = yes option = {{ name = {identity}.a }} }}')
    put('events/hro_war_events.txt','\n'.join(events)+'\n')
    for language,entries in loc.items():put(f'localisation/{language}/hro_war_l_{language}.yml',f'l_{language}:\n'+''.join(f' {k}:0 {json.dumps(v,ensure_ascii=False)}\n' for k,v in entries.items()),True)
    permanent={('SOV' if '_sov_' in i else 'GER'):mods for i,ru,en,dr,de,mods in records if i.endswith('_adapted')}
    return {'ideas':len(records),'events':len(messages),'soviet_shock_days':SOV_DAYS,'soviet_phase_boundaries':[45,120,240],
            'soviet_automatic_positive':SOV_LEARNED,'german_winter_experience_days':WINTER_DAYS,
            'adapted_winter_retains_seasonal_costs':True,'duration_clock':'actual daily war counters; peace and German warm seasons pause experience',
            'winter_season':'November through March','winter_years':[1936,1946],'reforms_authorized_before_eligibility':True,
            'surprise_requires_defending':True,'native_penalties_removed':False,'daily_scope':'country, filtered by original_tag','permanent_rewards':permanent}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path)
    print(json.dumps(generate(p.parse_args().output),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
