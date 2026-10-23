"""Player-facing numeric descriptions derived from the actual reward dictionaries."""
LABELS = {
 'army_infantry_attack_factor': ('Атака пехоты', 'Infantry attack'),
 'fuel_gain_factor': ('Прирост топлива', 'Fuel gain'),
 'production_speed_bunker_factor': ('Строительство наземных укреплений', 'Land fort construction'),
 'production_speed_coastal_bunker_factor': ('Строительство береговых укреплений', 'Coastal fort construction'),
 'recon_factor': ('Разведка', 'Reconnaissance'),
 'army_intel_to_others': ('Разведданные об армии для противника', 'Army intelligence to enemies'),
 'airforce_intel_to_others': ('Разведданные об авиации для противника', 'Air intelligence to enemies'),
 'out_of_supply_factor': ('Штраф за недостаток снабжения', 'Out-of-supply penalty'),
 'production_speed_rail_way_factor': ('Строительство железных дорог', 'Railway construction'),
 'production_speed_arms_factory_factor': ('Строительство военных заводов', 'Military factory construction'),
 'army_fuel_consumption_factor': ('Расход топлива армией', 'Army fuel consumption'),
 'air_intercept_efficiency': ('Эффективность перехвата', 'Interception efficiency'),
 'army_armor_attack_factor': ('Атака бронетанковых частей', 'Armour attack'),
 'army_armor_defence_factor': ('Защита бронетанковых частей', 'Armour defence'),
 'air_attack_factor': ('Воздушная атака', 'Air attack'),
 'air_cas_efficiency': ('Эффективность непосредственной авиаподдержки', 'Close air support efficiency'),
 'ground_attack_factor': ('Атака авиации по наземным целям', 'Air ground attack'),
 'experience_loss_factor': ('Потери опытных бойцов', 'Experience losses'),
 'army_core_defence_factor': ('Защита на национальной территории', 'Core territory defence'),
 'max_dig_in': ('Максимальная укреплённость', 'Maximum entrenchment'),
 'dig_in_speed_factor': ('Скорость окапывания', 'Entrenchment speed'),
 'army_artillery_attack_factor': ('Атака артиллерии', 'Artillery attack'),
 'coordination_bonus': ('Координация', 'Coordination'),
 'license_purchase_cost': ('Стоимость лицензий', 'Licence purchase cost'),
 'naval_coordination': ('Координация флота', 'Naval coordination'),
 'army_attack_factor': ('Атака дивизий', 'Division attack'),
 'army_speed_factor': ('Скорость дивизий', 'Division speed'),
 'attrition': ('Истощение', 'Attrition'),
 'air_accidents_factor': ('Вероятность авиакатастроф', 'Air accident chance'),
 'air_fuel_consumption_factor': ('Расход топлива авиацией', 'Air fuel consumption'),
 'army_org_factor': ('Организация дивизий', 'Division organisation'),
 'convoy_escort_efficiency': ('Эффективность сопровождения конвоев', 'Convoy escort efficiency'),
 'experience_gain_air_factor': ('Прирост опыта авиации', 'Air experience gain'),
 'industrial_capacity_dockyard': ('Выпуск верфей', 'Dockyard output'),
 'industrial_capacity_factory': ('Выпуск военных заводов', 'Military factory output'),
 'industry_repair_factor': ('Скорость ремонта предприятий', 'Factory repair speed'),
 'max_planning_factor': ('Максимальный бонус планирования', 'Maximum planning bonus'),
 'navy_fuel_consumption_factor': ('Расход топлива флотом', 'Naval fuel consumption'),
 'planning_speed': ('Скорость планирования', 'Planning speed'),
 'political_power_gain': ('Ежедневная политическая власть', 'Daily political power'),
 'production_factory_efficiency_gain_factor': ('Рост эффективности производства', 'Production efficiency growth'),
 'production_factory_start_efficiency_factor': ('Базовая эффективность производства', 'Base production efficiency'),
 'production_speed_buildings_factor': ('Скорость строительства', 'Construction speed'),
 'production_speed_industrial_complex_factor': ('Строительство гражданских фабрик', 'Civilian factory construction'),
 'stability_factor': ('Стабильность', 'Stability'),
 'supply_consumption_factor': ('Расход снабжения', 'Supply consumption'),
 'training_time_army_factor': ('Время подготовки дивизий', 'Division training time'),
 'truck_attrition_factor': ('Потери грузовиков от истощения', 'Truck attrition'),
 'winter_attrition_factor': ('Зимнее истощение', 'Winter attrition'),
 'army_defence_factor': ('Защита дивизий', 'Division defence'),
 'army_org_regain': ('Восстановление организации', 'Organisation recovery'),
 'land_reinforce_rate': ('Скорость пополнения', 'Reinforce rate'),
}


def describe(modifiers, language):
    parts = []
    for key, value in modifiers.items():
        ru, en = LABELS[key]  # Fail closed rather than expose an untranslated script keyword.
        numeric = f'{value if key in ("political_power_gain", "max_dig_in") else value * 100:+g}'
        if language == 'russian':
            numeric = numeric.replace('.', ',')
        unit = '' if key == 'max_dig_in' else (' ПВ/день' if language == 'russian' else ' PP/day') if key == 'political_power_gain' else (' п.п.' if language == 'russian' else ' pp') if key == 'land_reinforce_rate' else '%'
        parts.append((ru if language == 'russian' else en) + ': ' + numeric + unit)
    return '; '.join(parts)


def experience(effect, language):
    if not effect:
        return ''
    key, amount = [part.strip() for part in effect.split('=')]
    labels = {'army_experience': ('Опыт армии', 'Army experience'),
              'air_experience': ('Опыт авиации', 'Air experience'),
              'navy_experience': ('Опыт флота', 'Navy experience')}
    return f'{labels[key][0 if language == "russian" else 1]}: +{amount}.'
