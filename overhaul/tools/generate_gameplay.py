#!/usr/bin/env python3
"""Generate finite, costed HRO programmes and deterministic conditional crises.

This module owns programme content only. Native DLC systems, country-family
initialisation and focus-tree generation remain with the main builder.
"""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from decision_details import describe, experience


def _programme(tag, key, slot, branch, ru, en, goal_ru, goal_en, cost, days,
               mods, earliest=None, condition='', xp='', benefit_days=180,
               working=None):
    return dict(tag=tag, key=key, slot=slot, branch=branch, ru=ru, en=en,
                goal_ru=goal_ru, goal_en=goal_en, cost=cost, days=days,
                mods=mods, earliest=earliest, condition=condition, xp=xp,
                benefit_days=benefit_days, working=working)


def _catalogue():
    p = []
    def add(tag, key, slot, branch, ru, en, goal_ru, goal_en, cost, days,
            mods, **kwargs):
        p.append(_programme(tag, key, slot, branch, ru, en, goal_ru, goal_en,
                            cost, days, mods, **kwargs))

    add('GER', 'contract_audit', 'industry', 'industry',
        'Свести военные контракты', 'Consolidate Armaments Contracts',
        'Ускорить освоение серийного выпуска, выделив часть управленческих ресурсов.',
        'Improve serial-production learning while assigning administrative resources.',
        45, 90, {'production_factory_efficiency_gain_factor': .04, 'political_power_gain': -.03})
    add('GER', 'tooling_reserve', 'industry', 'industry',
        'Создать резерв оснастки', 'Establish a Tooling Reserve',
        'Облегчить запуск новых линий ценой части текущего выпуска.',
        'Improve new-line efficiency at the expense of current output.',
        55, 90, {'production_factory_start_efficiency_factor': .04, 'industrial_capacity_factory': -.01}, earliest='1937.1.1')
    add('GER', 'repair_workshops', 'industry', 'logistics',
        'Развернуть ремонтные мастерские', 'Expand Repair Workshops',
        'Направить работников на восстановление предприятий вместо нового строительства.',
        'Assign workers to industrial repairs rather than new construction.',
        50, 75, {'industry_repair_factor': .10, 'production_speed_buildings_factor': -.02}, condition='has_war = yes')
    add('GER', 'spares_standard', 'industry', 'industry',
        'Согласовать стандарты запчастей', 'Standardise Spare Parts',
        'Повысить устойчивость снабжения, пожертвовав частью производственной гибкости.',
        'Improve supply resilience at the expense of production flexibility.',
        60, 120, {'supply_consumption_factor': -.025, 'production_factory_efficiency_gain_factor': -.02}, earliest='1939.1.1')
    add('GER', 'aircraft_service', 'industry', 'air',
        'Перестроить обслуживание авиации', 'Reorganise Aircraft Servicing',
        'Сократить аварийность ценой расхода топлива на обслуживание и проверки.',
        'Reduce accidents while using more fuel for servicing and checks.',
        50, 90, {'air_accidents_factor': -.08, 'air_fuel_consumption_factor': .02}, xp='air_experience = 8')
    add('GER', 'dockyard_schedule', 'industry', 'navy',
        'Согласовать загрузку верфей', 'Coordinate Dockyard Schedules',
        'Увеличить выпуск верфей, перенаправив часть промышленного управления.',
        'Increase dockyard output by diverting industrial administration.',
        55, 120, {'industrial_capacity_dockyard': .04, 'industrial_capacity_factory': -.01}, earliest='1938.1.1')
    add('GER', 'staff_rotation', 'operations', 'army',
        'Провести ротацию штабных стажировок', 'Rotate Staff Internships',
        'Ускорить планирование и получить 10 армейского опыта после окончания стажировок.',
        'Improve planning and gain 10 army experience after the internships finish.',
        45, 90, {'planning_speed': .06, 'training_time_army_factor': .02}, xp='army_experience = 10')
    add('GER', 'signals_drill', 'operations', 'army',
        'Провести межштабное учение связи', 'Run an Inter-Headquarters Signals Exercise',
        'Немного повысить организацию ценой постоянной административной нагрузки.',
        'Modestly improve organisation at an ongoing administrative cost.',
        55, 90, {'army_org_factor': .02, 'political_power_gain': -.04}, earliest='1937.1.1')
    add('GER', 'transport_columns', 'operations', 'logistics',
        'Реорганизовать транспортные колонны', 'Reorganise Transport Columns',
        'Снизить потери грузовиков, выделив выпуск на запчасти.',
        'Reduce truck attrition by allocating production to spare parts.',
        50, 75, {'truck_attrition_factor': -.08, 'industrial_capacity_factory': -.01})
    add('GER', 'winter_service', 'operations', 'logistics',
        'Подготовить зимние службы', 'Prepare Winter Services',
        'Снизить зимнее истощение, выделив промышленные ресурсы на подготовку.',
        'Reduce winter attrition by allocating industrial resources to preparation.',
        55, 90, {'winter_attrition_factor': -.10, 'industrial_capacity_factory': -.015}, earliest='1939.6.1')
    add('GER', 'operational_review', 'operations', 'war',
        'Провести межвидовой разбор кампании', 'Review the Campaign Across Services',
        'Улучшить предельную подготовку планов и получить 15 армейского опыта.',
        'Improve maximum planning and gain 15 army experience.',
        65, 120, {'max_planning_factor': .04, 'planning_speed': -.02}, condition='has_war = yes', earliest='1939.9.1', xp='army_experience = 15')
    add('GER', 'fighter_coordination', 'operations', 'air',
        'Согласовать боевую подготовку лётчиков', 'Coordinate Operational Pilot Training',
        'Улучшить накопление авиационного опыта ценой дополнительного расхода топлива.',
        'Improve air experience gain at an additional fuel cost.',
        50, 90, {'experience_gain_air_factor': .08, 'air_fuel_consumption_factor': .025}, xp='air_experience = 8')
    add('GER', 'escort_drills', 'operations', 'navy',
        'Провести учения охранения', 'Conduct Escort Exercises',
        'Повысить эффективность охранения ценой расхода топлива.',
        'Improve escort efficiency at a fuel cost.',
        50, 90, {'convoy_escort_efficiency': .06, 'navy_fuel_consumption_factor': .025}, xp='navy_experience = 10')
    add('GER', 'reserve_cycle', 'operations', 'war',
        'Согласовать подготовку пополнений', 'Coordinate Replacement Training',
        'Ускорить подготовку пополнений ценой части текущего выпуска вооружений.',
        'Accelerate replacement training at the expense of current armaments output.',
        60, 120, {'training_time_army_factor': -.05, 'industrial_capacity_factory': -.02}, earliest='1942.1.1', condition='has_war = yes')
    add('GER', 'civil_defence', 'state', 'state',
        'Подготовить гражданские аварийные службы', 'Prepare Civilian Emergency Services',
        'Ускорить восстановление и укрепить устойчивость тыла ценой управления.',
        'Improve repair work and home-front resilience at an administrative cost.',
        50, 90, {'industry_repair_factor': .05, 'stability_factor': .015, 'political_power_gain': -.04})
    add('GER', 'commercial_office', 'state', 'diplomacy',
        'Согласовать работу внешнеторговых ведомств', 'Coordinate Foreign Trade Offices',
        'Уменьшить внутренние задержки производства; договоры и ресурсы не появляются автоматически.',
        'Reduce internal production delays; no treaties or resources are created automatically.',
        55, 90, {'production_factory_efficiency_gain_factor': .03, 'political_power_gain': -.04}, earliest='1937.1.1')
    add('GER', 'civilian_distribution', 'state', 'state',
        'Перераспределить снабжение гражданского тыла', 'Reallocate Civilian Home-Front Supplies',
        'Повысить стабильность ценой части военного выпуска.',
        'Improve stability at the expense of military output.',
        60, 90, {'stability_factor': .025, 'industrial_capacity_factory': -.02}, earliest='1941.1.1', condition='has_war = yes')
    add('GER', 'reconstruction_office', 'state', 'state',
        'Организовать мирную реконструкцию', 'Organise Peacetime Reconstruction',
        'Ускорить гражданское строительство и ремонт ценой военного выпуска. Требуется фактический мир.',
        'Accelerate civilian construction and repairs at the expense of military output. Requires actual peace.',
        65, 120, {'production_speed_industrial_complex_factor': .05, 'industry_repair_factor': .08, 'industrial_capacity_factory': -.025}, earliest='1944.1.1', condition='has_war = no', benefit_days=240)

    add('SOV', 'production_audit', 'industry', 'industry',
        'Проверить межзаводские производственные планы', 'Audit Inter-Factory Production Plans',
        'Ускорить освоение выпуска ценой расходов на производственное управление.',
        'Improve production learning at the cost of industrial administration.',
        45, 90, {'production_factory_efficiency_gain_factor': .04, 'political_power_gain': -.03})
    add('SOV', 'tooling_school', 'industry', 'industry',
        'Подготовить наладчиков новых линий', 'Train New-Line Tooling Specialists',
        'Облегчить запуск линий, временно отвлекая специалистов от текущего выпуска.',
        'Improve new-line efficiency while diverting specialists from current output.',
        55, 90, {'production_factory_start_efficiency_factor': .04, 'industrial_capacity_factory': -.01}, earliest='1937.1.1')
    add('SOV', 'commission_workshops', 'industry', 'logistics',
        'Согласовать восстановление оборудования', 'Coordinate Machinery Restoration',
        'Ускорить ремонт производственных мощностей вместо нового строительства. Это не перенос и не создание фабрик.',
        'Accelerate industrial repairs rather than new construction. No factories are moved or created.',
        50, 75, {'industry_repair_factor': .10, 'production_speed_buildings_factor': -.02}, condition='has_war = yes')
    add('SOV', 'component_standards', 'industry', 'industry',
        'Унифицировать межзаводские комплектующие', 'Standardise Inter-Factory Components',
        'Уменьшить нагрузку снабжения ценой производственной гибкости.',
        'Reduce supply demand at the expense of production flexibility.',
        60, 120, {'supply_consumption_factor': -.025, 'production_factory_efficiency_gain_factor': -.02}, earliest='1939.1.1')
    add('SOV', 'airfield_servicing', 'industry', 'air',
        'Подготовить аэродромные ремонтные службы', 'Train Airfield Maintenance Services',
        'Сократить аварийность ценой расхода топлива на проверки.',
        'Reduce accidents while using more fuel for checks.',
        50, 90, {'air_accidents_factor': -.08, 'air_fuel_consumption_factor': .02}, xp='air_experience = 8')
    add('SOV', 'shipyard_coordination', 'industry', 'navy',
        'Согласовать заказы судостроительных заводов', 'Coordinate Shipyard Orders',
        'Повысить выпуск верфей, ограничив часть сухопутных производственных ресурсов.',
        'Improve dockyard output while diverting some land-production resources.',
        55, 120, {'industrial_capacity_dockyard': .04, 'industrial_capacity_factory': -.01}, earliest='1938.1.1')
    add('SOV', 'staff_academy', 'operations', 'army',
        'Провести выпускную штабную практику', 'Conduct Advanced Staff Practice',
        'Ускорить планирование и получить 10 армейского опыта после завершения практики.',
        'Improve planning and gain 10 army experience after practice is completed.',
        45, 90, {'planning_speed': .06, 'training_time_army_factor': .02}, xp='army_experience = 10')
    add('SOV', 'signal_network', 'operations', 'army',
        'Проверить взаимодействие окружных штабов', 'Exercise Military District Signals',
        'Улучшить организацию армии ценой постоянных расходов на координацию.',
        'Improve army organisation at an ongoing coordination cost.',
        55, 90, {'army_org_factor': .02, 'political_power_gain': -.04}, earliest='1937.1.1')
    add('SOV', 'truck_maintenance', 'operations', 'logistics',
        'Перестроить техническое обслуживание автопарка', 'Reorganise Vehicle Maintenance',
        'Сократить потери грузовиков, выделив выпуск на запчасти.',
        'Reduce truck attrition by allocating production to spare parts.',
        50, 75, {'truck_attrition_factor': -.08, 'industrial_capacity_factory': -.01})
    add('SOV', 'winter_stores', 'operations', 'logistics',
        'Организовать зимнее материальное обеспечение', 'Organise Winter Material Support',
        'Снизить зимнее истощение ценой выделенного производственного ресурса.',
        'Reduce winter attrition by reserving industrial resources.',
        55, 90, {'winter_attrition_factor': -.10, 'industrial_capacity_factory': -.015}, earliest='1939.6.1')
    add('SOV', 'front_review', 'operations', 'war',
        'Провести фронтовой разбор операций', 'Review Front Operations',
        'Улучшить максимальную подготовку планов и получить 15 армейского опыта.',
        'Improve maximum planning and gain 15 army experience.',
        65, 120, {'max_planning_factor': .04, 'planning_speed': -.02}, condition='has_war = yes', earliest='1939.9.1', xp='army_experience = 15')
    add('SOV', 'pilot_training', 'operations', 'air',
        'Согласовать боевую подготовку авиации', 'Coordinate Operational Air Training',
        'Улучшить набор авиационного опыта ценой большего расхода топлива.',
        'Improve air experience gain at a higher fuel cost.',
        50, 90, {'experience_gain_air_factor': .08, 'air_fuel_consumption_factor': .025}, xp='air_experience = 8')
    add('SOV', 'convoy_training', 'operations', 'navy',
        'Отработать охранение морских перевозок', 'Exercise Maritime Convoy Escort',
        'Улучшить охранение ценой расхода топлива флотом.',
        'Improve escort efficiency at a naval fuel cost.',
        50, 90, {'convoy_escort_efficiency': .06, 'navy_fuel_consumption_factor': .025}, xp='navy_experience = 10')
    add('SOV', 'replacement_centres', 'operations', 'war',
        'Согласовать работу учебных запасных частей', 'Coordinate Replacement Training Units',
        'Сократить сроки подготовки пополнений ценой части военного выпуска.',
        'Reduce replacement training times at the expense of military output.',
        60, 120, {'training_time_army_factor': -.05, 'industrial_capacity_factory': -.02}, earliest='1942.1.1', condition='has_war = yes')
    add('SOV', 'urban_rescue', 'state', 'state',
        'Подготовить городские спасательные службы', 'Train Urban Rescue Services',
        'Ускорить восстановление и укрепить устойчивость тыла ценой управления.',
        'Improve repair work and home-front resilience at an administrative cost.',
        50, 90, {'industry_repair_factor': .05, 'stability_factor': .015, 'political_power_gain': -.04})
    add('SOV', 'foreign_supply_office', 'state', 'diplomacy',
        'Согласовать учёт внешних поставок', 'Coordinate Foreign Delivery Accounting',
        'Уменьшить внутренние задержки производства. Не создаёт ленд-лиз, технику или договоры.',
        'Reduce internal production delays. Creates no lend-lease, equipment or treaties.',
        55, 90, {'production_factory_efficiency_gain_factor': .03, 'political_power_gain': -.04}, earliest='1937.1.1')
    add('SOV', 'home_front_supplies', 'state', 'state',
        'Согласовать снабжение тыла', 'Coordinate Home-Front Supplies',
        'Повысить стабильность, сократив часть военного выпуска.',
        'Improve stability while reducing some military output.',
        60, 90, {'stability_factor': .025, 'industrial_capacity_factory': -.02}, earliest='1941.1.1', condition='has_war = yes')
    add('SOV', 'recovery_commission', 'state', 'state',
        'Подготовить мирное восстановление', 'Prepare Peacetime Recovery',
        'Ускорить гражданское строительство и ремонт ценой военного выпуска. Требуется действительный мир.',
        'Improve civilian construction and repairs at the expense of military output. Requires actual peace.',
        65, 120, {'production_speed_industrial_complex_factor': .05, 'industry_repair_factor': .08, 'industrial_capacity_factory': -.025}, earliest='1944.1.1', condition='has_war = no', benefit_days=240)
    return p


def _crises():
    """Mirrored cost/effect pairs keep human-opponent rules transparent."""
    return [
        dict(key='procurement', branch='industry', date='1936.7.1', cost=35, condition='num_of_military_factories > 15',
             ru='Пересечение военных заказов', en='Overlapping Armaments Orders',
             dr='Несогласованные заказы конкурируют за одну производственную цепочку. Можно оплатить согласование или принять временное замедление выпуска.',
             de='Uncoordinated orders compete for one production chain. Fund coordination or accept temporarily slower output.',
             good={'production_factory_efficiency_gain_factor': .03, 'political_power_gain': -.04}, bad={'industrial_capacity_factory': -.02}),
        dict(key='specialists', branch='industry', date='1937.6.1', cost=45, condition='num_of_military_factories > 30',
             ru='Нехватка производственных специалистов', en='Shortage of Production Specialists',
             dr='Расширение военного производства опережает подготовку специалистов. Оплата обучения ускорит освоение линий, но временно ограничит строительство.',
             de='Military production expands faster than specialist training. Fund training to improve line learning while temporarily limiting construction.',
             good={'production_factory_efficiency_gain_factor': .04, 'production_speed_buildings_factor': -.02}, bad={'production_factory_efficiency_gain_factor': -.05}),
        dict(key='staff_workload', branch='army', date='1938.1.1', cost=40, condition='num_of_military_factories > 15',
             ru='Перегрузка штабной подготовки', en='Overloaded Staff Training',
             dr='Новые задачи перегружают подготовку штабов. Дополнительный учебный цикл требует ресурсов и замедляет выпуск новых кадров на время программы.',
             de='New tasks overload staff preparation. An extra training cycle consumes resources and temporarily slows training throughput.',
             good={'planning_speed': .05, 'training_time_army_factor': .03}, bad={'planning_speed': -.05}),
        dict(key='transport', branch='logistics', date='1939.9.1', cost=50, condition='has_war = yes',
             ru='Транспорт работает на пределе', en='Transport Operating at Capacity',
             dr='Действительная война увеличивает нагрузку на перевозки. Приоритет запасным частям улучшит снабжение, но отнимет часть военного выпуска.',
             de='An actual war increases transport demand. Prioritising spare parts improves supply but diverts military output.',
             good={'supply_consumption_factor': -.03, 'industrial_capacity_factory': -.015}, bad={'supply_consumption_factor': .03}),
        dict(key='interservice', branch='war', date='1940.3.1', cost=45, condition='has_war = yes',
             ru='Несогласованные оперативные приоритеты', en='Conflicting Operational Priorities',
             dr='Ведомства требуют разных сроков и целей. Оплата координации повышает организацию, но требует постоянного административного внимания.',
             de='Services demand conflicting schedules and objectives. Fund coordination to improve organisation at an ongoing administrative cost.',
             good={'army_org_factor': .02, 'political_power_gain': -.05}, bad={'planning_speed': -.04, 'army_org_factor': -.01}),
        dict(key='continental_war', branch='logistics', date='1936.1.1', cost=55, condition='has_war_with = {enemy}',
             ru='Континентальная война: обеспечение фронта', en='Continental War: Supporting the Front',
             dr='Германия и СССР действительно воюют. Это состояние партии, а не автоматическое повторение исторической даты. Новая сеть обслуживания требует ресурсов; она не создаёт бесплатных поездов или складов.',
             de='Germany and the USSR are actually at war. This reflects the campaign rather than a scheduled historical invasion. Expanded servicing requires resources and creates no free trains or hubs.',
             good={'supply_consumption_factor': -.04, 'industrial_capacity_factory': -.02}, bad={'supply_consumption_factor': .04, 'planning_speed': -.02}),
        dict(key='winter_plans', branch='logistics', date='1941.9.1', cost=45, condition='has_war = yes',
             ru='Пересмотр зимнего обеспечения', en='Reviewing Winter Support',
             dr='Планирование зимнего обеспечения необходимо до наступления холодов. Выделенные ресурсы снижают зимние потери; отказ увеличивает нагрузку снабжения на ограниченный срок.',
             de='Winter support must be planned before cold weather arrives. Reserved resources reduce winter losses; refusal increases supply demand for a limited time.',
             good={'winter_attrition_factor': -.10, 'industrial_capacity_factory': -.015}, bad={'supply_consumption_factor': .025}),
        dict(key='air_protection', branch='air', date='1942.1.1', cost=50, condition='has_war = yes',
             ru='Воздушная угроза и аварийные службы', en='Air Threat and Emergency Services',
             dr='Война требует готовности к воздушной угрозе. Событие не утверждает, что конкретный город уже разрушен. Ремонтные резервы создаются за счёт текущего выпуска.',
             de='War requires preparation for air threats. This event does not assert that a particular city has been destroyed. Repair reserves divert resources from current output.',
             good={'industry_repair_factor': .10, 'industrial_capacity_factory': -.02}, bad={'industry_repair_factor': -.08}),
        dict(key='late_standardisation', branch='industry', date='1943.6.1', cost=60, condition='has_war = yes',
             ru='Пересмотр поздних военных серий', en='Reviewing Late-War Production Series',
             dr='Долгая война требует выбора между новыми образцами и стабильной серией. Оплаченная стандартизация поддержит выпуск ценой нового строительства; сохранение разрозненных заказов временно снижает эффективность.',
             de='A long war forces a choice between new models and stable series. Funded standardisation supports output at a construction cost; fragmented orders temporarily reduce efficiency.',
             good={'industrial_capacity_factory': .02, 'production_speed_buildings_factor': -.02}, bad={'production_factory_efficiency_gain_factor': -.05}),
        dict(key='demobilisation', branch='state', date='1945.1.1', cost=60, condition='has_war = no',
             ru='Мирная переналадка хозяйства', en='Peacetime Economic Conversion',
             dr='Страна действительно находится в мире. Переход к восстановлению требует перераспределить военные мощности; календарь не назначает победителя и не заключает мир за игроков.',
             de='The country is actually at peace. Recovery requires reallocating military capacity; the calendar neither declares a winner nor makes peace for the players.',
             good={'production_speed_industrial_complex_factor': .05, 'industry_repair_factor': .06, 'industrial_capacity_factory': -.025}, bad={'production_speed_buildings_factor': -.03}),
    ]


def generate(output: Path) -> dict:
    output = Path(output)
    localisations = {'russian': {}, 'english': {}}
    def loc(key, ru, en):
        if key in localisations['russian']:
            raise ValueError('Duplicate gameplay localisation: ' + key)
        localisations['russian'][key] = ru
        localisations['english'][key] = en
    def write(path, text, bom=False):
        target = output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text.strip() + '\n', encoding='utf-8-sig' if bom else 'utf-8')
    def modifiers(values):
        return ' '.join(f'{key} = {value:g}' for key, value in values.items())
    def flag(name):
        return 'has_country_flag = ' + name
    def unlock_flag(tag, branch):
        # The country catalogues expose staff preparation under this shared
        # interface; the visual focus branch itself is named "army".
        return 'hro_' + tag.lower() + '_' + ('staff' if branch == 'army' else branch) + '_unlocked'
    def valid_country(tag):
        return f'original_tag = {tag} has_country_flag = hro_initialized has_capitulated = no'
    def calendar(date):
        if not date:
            return ''
        return ('OR = { has_game_rule = { rule = HRO_PACING option = HRO_OPEN } '
                f'date > {date} }}')

    programmes = _catalogue()
    ideas, effects, categories, triggers = [], [], [], []
    decisions = {slot: [] for slot in ('industry', 'operations', 'state')}
    slot_names = {
        'industry': ('Промышленные программы', 'Industrial Programmes'),
        'operations': ('Оперативная подготовка', 'Operational Preparation'),
        'state': ('Управление и гражданский тыл', 'Administration and Civilian Support'),
    }
    work_mods = {
        'industry': {'industrial_capacity_factory': -.02, 'political_power_gain': -.03},
        'operations': {'training_time_army_factor': .06, 'industrial_capacity_factory': -.01},
        'state': {'production_speed_buildings_factor': -.02, 'political_power_gain': -.05},
    }
    idea_ids = []
    def idea(identity, ru, en, dr, de, values):
        idea_ids.append(identity)
        loc(identity, ru, en)
        loc(identity + '_desc', dr, de)
        ideas.append(f'''        {identity} = {{
            picture = generic_industry
            allowed = {{ OR = {{ original_tag = GER original_tag = SOV }} }}
            removal_cost = -1
            modifier = {{ {modifiers(values)} }}
        }}''')

    for slot, (ru, en) in slot_names.items():
        identity = 'hro_' + slot + '_programmes'
        loc(identity, ru, en)
        loc(identity + '_desc',
            'Одновременно выполняется одна программа этой категории. Политическая власть списывается при запуске; временные издержки действуют весь срок. Награда выдаётся только после полного завершения. Завершённая программа одноразовая; отмена не возвращает ПВ и не даёт наград. До окончания текущего результата следующая программа этой категории недоступна.',
            'Only one programme in this category can run at a time. Political power is paid on activation; temporary costs last throughout. Benefits arrive only after full completion. Each completed programme is one-shot; cancellation gives no refund or reward. Another programme in the category must wait until the current result expires.')
        categories.append(f'''{identity} = {{
    icon = generic_industry
    allowed = {{ OR = {{ original_tag = GER original_tag = SOV }} }}
    visible = {{ has_country_flag = hro_initialized }}
    visible_when_empty = no
}}''')
        triggers.append(f'''hro_can_start_{slot}_programme = {{
    OR = {{ original_tag = GER original_tag = SOV }}
    has_country_flag = hro_initialized
    has_capitulated = no
    NOT = {{ has_country_flag = hro_{slot}_programme_busy }}
    NOT = {{ has_country_flag = hro_{slot}_programme_result_active }}
}}''')

    # Named result flags have timed lifetimes: no separate fake resource counters.
    for p in programmes:
        tag, slot = p['tag'], p['slot']
        identity = 'hro_programme_' + tag.lower() + '_' + p['key']
        active, done = identity + '_active', identity + '_done'
        working, benefit = identity + '_working', identity + '_benefit'
        unlock = unlock_flag(tag, p['branch'])
        cancel, complete = identity + '_cancel', identity + '_complete'
        working_mods = p['working'] or work_mods[slot]
        loc(identity, p['ru'], p['en'])
        ru_desc = (p['goal_ru'] + f" Срок: {p['days']} дней; цена: {p['cost']} ПВ. "
                   f"Во время работы действует дух «{p['ru']}: выполнение» с издержками. "
                   f"После завершения — результат на {p['benefit_days']} дней. "
                   'Награда не выдаётся при запуске. Каждая программа завершается только один раз; отмена не возвращает затраты.')
        en_desc = (p['goal_en'] + f" Duration: {p['days']} days; cost: {p['cost']} PP. "
                   'The working national spirit applies costs throughout preparation. '
                   f"Completion grants a {p['benefit_days']}-day result. "
                   'There is no activation reward. Each programme can finish only once; cancellation refunds nothing.')
        ru_desc += '\n\n§YВо время подготовки:§! ' + describe(working_mods, 'russian') + '.'
        ru_desc += f"\n\n§YПосле завершения на {p['benefit_days']} дней:§! " + describe(p['mods'], 'russian') + '. ' + experience(p['xp'], 'russian')
        en_desc += '\n\n§YDuring preparation:§! ' + describe(working_mods, 'english') + '.'
        en_desc += f"\n\n§YOn completion for {p['benefit_days']} days:§! " + describe(p['mods'], 'english') + '. ' + experience(p['xp'], 'english')
        loc(identity + '_desc', ru_desc, en_desc)
        loc(identity + '_reward_preview', f"После {p['days']} дней подготовки: результат на {p['benefit_days']} дней. " + experience(p['xp'], 'russian'),
            f"After {p['days']} preparation days: result for {p['benefit_days']} days. " + experience(p['xp'], 'english'))
        idea(working, p['ru'] + ': выполнение', p['en'] + ': In Progress',
             'Издержки подготовки. При отмене или завершении дух удаляется; награда появляется только после полного срока.',
             'Preparation costs. Removed on cancellation or completion; benefits require the full programme duration.', working_mods)
        idea(benefit, p['ru'] + ': результат', p['en'] + ': Result',
             p['goal_ru'] + f" Результат действует {p['benefit_days']} дней; другие программы этой категории пока недоступны.",
             p['goal_en'] + f" The result lasts {p['benefit_days']} days; other programmes in this category remain unavailable.", p['mods'])
        effects.append(f'''{cancel} = {{
    remove_ideas = {working}
    if = {{
        limit = {{ has_country_flag = {active} }}
        clr_country_flag = {active}
        clr_country_flag = hro_{slot}_programme_busy
    }}
}}
{complete} = {{
    if = {{
        limit = {{ has_country_flag = {active} NOT = {{ has_country_flag = {done} }} }}
        {cancel} = yes
        set_country_flag = {done}
        set_country_flag = {{ flag = hro_{slot}_programme_result_active value = 1 days = {p['benefit_days']} }}
        add_timed_idea = {{ idea = {benefit} days = {p['benefit_days']} }}
        {p['xp']}
    }}
}}''')
        ongoing = valid_country(tag) + ' ' + flag(unlock) + ' ' + p['condition']
        decisions[slot].append(f'''    {identity} = {{
        icon = generic_industry
        cost = {p['cost']}
        days_remove = {p['days']}
        days_re_enable = {p['days'] + 30}
        cancel_if_not_visible = yes
        visible = {{ original_tag = {tag} has_country_flag = {unlock} NOT = {{ has_country_flag = {done} }} }}
        available = {{ hro_can_start_{slot}_programme = yes {calendar(p['earliest'])} {p['condition']} }}
        complete_effect = {{
            set_country_flag = hro_{slot}_programme_busy
            set_country_flag = {active}
            add_ideas = {working}
            custom_effect_tooltip = {identity}_reward_preview
            show_ideas_tooltip = {benefit}
        }}
        cancel_trigger = {{ NOT = {{ {ongoing} }} }}
        cancel_effect = {{ {cancel} = yes }}
        remove_effect = {{
            if = {{ limit = {{ {ongoing} }} {complete} = yes }}
            else = {{ {cancel} = yes }}
        }}
        ai_will_do = {{ factor = 1 modifier = {{ factor = 0 NOT = {{ has_political_power > {p['cost'] + 75} }} }} }}
    }}''')

    effects.append('hro_cancel_all_programmes = {\n' + '\n'.join(
        f'    if = {{ limit = {{ has_country_flag = hro_programme_{p["tag"].lower()}_{p["key"]}_active }} hro_programme_{p["tag"].lower()}_{p["key"]}_cancel = yes }}'
        for p in programmes) + '\n}')

    events, checks = ['add_namespace = hro'], {}
    for tag, base_id in (('GER', 100), ('SOV', 200)):
        checks[tag] = []
        for index, crisis in enumerate(_crises(), 1):
            event_id = f'hro.{base_id + index}'
            event_flag = f'hro_{tag.lower()}_crisis_{crisis["key"]}_sent'
            good = 'hro_programme_crisis_' + crisis['key'] + '_resolved'
            bad = 'hro_programme_crisis_' + crisis['key'] + '_unresolved'
            if tag == 'GER':
                idea(good, crisis['ru'] + ': оплаченная мера', crisis['en'] + ': Funded Response',
                     'Условная кризисная мера на 120 дней. Положительный результат сопровождается указанными издержками.',
                     'A conditional 120-day response. Its benefits carry the stated costs.', crisis['good'])
                idea(bad, crisis['ru'] + ': отсроченное решение', crisis['en'] + ': Deferred Response',
                     'Временное последствие отказа от финансирования; автоматически закончится через 90 дней.',
                     'A temporary consequence of declining funding; expires automatically after 90 days.', crisis['bad'])
            title_ru = ('Германия: ' if tag == 'GER' else 'СССР: ') + crisis['ru']
            title_en = ('Germany: ' if tag == 'GER' else 'USSR: ') + crisis['en']
            loc(event_id + '.t', title_ru, title_en)
            loc(event_id + '.d', crisis['dr'] + f" Мера стоит {crisis['cost']} ПВ и действует 120 дней; отказ приводит к 90-дневным указанным издержкам. Событие одноразовое и не вмешивается в паранойю, MEFO или исходные дипломатические цепочки.",
                crisis['de'] + f" The response costs {crisis['cost']} PP and lasts 120 days; refusal brings the stated 90-day costs. This event is one-shot and does not alter paranoia, MEFO or native diplomatic chains.")
            loc(event_id + '.a', 'Оплатить согласованную меру.', 'Fund the coordinated response.')
            loc(event_id + '.b', 'Принять временные издержки.', 'Accept the temporary costs.')
            condition = crisis['condition'].replace('{enemy}', 'SOV' if tag == 'GER' else 'GER')
            required = valid_country(tag) + ' has_country_flag = ' + unlock_flag(tag, crisis['branch']) + ' ' + condition
            events.append(f'''country_event = {{
    id = {event_id}
    title = {event_id}.t
    desc = {event_id}.d
    is_triggered_only = yes
    fire_only_once = yes
    trigger = {{ {required} }}
    option = {{
        name = {event_id}.a
        trigger = {{ has_political_power > {crisis['cost'] - 1} }}
        ai_chance = {{ factor = 1 modifier = {{ factor = 0 NOT = {{ has_political_power > {2 * crisis['cost']} }} }} }}
        add_political_power = -{crisis['cost']}
        add_timed_idea = {{ idea = {good} days = 120 }}
    }}
    option = {{
        name = {event_id}.b
        ai_chance = {{ factor = 1 modifier = {{ factor = 0 has_political_power > {2 * crisis['cost']} }} }}
        add_timed_idea = {{ idea = {bad} days = 90 }}
    }}
}}''')
            checks[tag].append(f'''    {'if' if index == 1 else 'else_if'} = {{
        limit = {{ date > {crisis['date']} NOT = {{ has_country_flag = {event_flag} }} {required} }}
        set_country_flag = {event_flag}
        country_event = {{ id = {event_id} days = 1 }}
    }}''')
        effects.append(f'hro_{tag.lower()}_check_programme_crises = {{\n' + '\n'.join(checks[tag]) + '\n}')

    write('common/decisions/categories/hro_categories.txt', '\n\n'.join(categories))
    write('common/decisions/hro_programmes.txt', '\n\n'.join(
        'hro_' + slot + '_programmes = {\n' + '\n'.join(values) + '\n}' for slot, values in decisions.items()))
    write('common/ideas/hro_programme_ideas.txt', 'ideas = {\n    country = {\n' + '\n'.join(ideas) + '\n    }\n}')
    write('common/scripted_triggers/hro_programme_triggers.txt', '\n\n'.join(triggers))
    write('common/scripted_effects/hro_programme_effects.txt', '\n\n'.join(effects))
    write('events/hro_programme_events.txt', '\n\n'.join(events))
    write('common/on_actions/hro_programme_on_actions.txt', '''on_actions = {
    # Per-country monthly hook: never apply a fixed GER/SOV scope to every country.
    on_monthly = {
        effect = {
            if = {
                limit = { original_tag = GER has_country_flag = hro_initialized has_capitulated = no date < 1947.1.1 }
                hro_ger_check_programme_crises = yes
            }
            if = {
                limit = { original_tag = SOV has_country_flag = hro_initialized has_capitulated = no date < 1947.1.1 }
                hro_sov_check_programme_crises = yes
            }
        }
    }
    on_daily = {
        effect = {
            if = {
                limit = {
                    OR = { original_tag = GER original_tag = SOV }
                    has_capitulated = yes
                    OR = { has_country_flag = hro_industry_programme_busy has_country_flag = hro_operations_programme_busy has_country_flag = hro_state_programme_busy }
                }
                hro_cancel_all_programmes = yes
            }
        }
    }
}''')
    for language, values in localisations.items():
        text = 'l_' + language + ':\n' + ''.join(
            ' ' + key + ':0 ' + json.dumps(value, ensure_ascii=False) + '\n' for key, value in values.items())
        write(f'localisation/{language}/hro_gameplay_l_{language}.yml', text, bom=True)
    if len(programmes) != 36 or len(events) - 1 != 20 or len(set(idea_ids)) != len(idea_ids):
        raise ValueError('Gameplay catalogue size/identity invariant failed')
    return {
        'decisions': len(programmes), 'events': len(events) - 1,
        'programme_ideas': len(idea_ids), 'categories': len(categories),
        'scripted_effects': len(programmes) * 2 + 3,
        'scripted_triggers': len(triggers),
        'localisation_keys_per_language': len(localisations['russian']),
        'native_systems_replaced': [], 'max_parallel_programmes_per_country': 3,
        'programme_rewards_on_completion_only': True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(generate(args.output), ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
