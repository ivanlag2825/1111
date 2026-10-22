"""Bounded operation styles; positive fatigue attack bonuses stay user-defined."""
PROFILES={
 'decisive':dict(days=14,step=7,fatigue_factor=1.25,ru='Решительный прорыв',en='Decisive Breakthrough',
  assault={'army_attack_factor':.50,'army_speed_factor':.20,'planning_speed':.50,'army_org_regain':.15,'supply_consumption_factor':-.05}),
 'sequential':dict(days=21,step=10,fatigue_factor=.75,ru='Последовательные операции',en='Successive Operations',
  assault={'army_attack_factor':.20,'army_speed_factor':.05,'planning_speed':.25,'army_org_regain':.35,'supply_consumption_factor':-.15})}


def fatigue_modifiers(values,factor):
 return {key:value if key=='army_attack_factor' and value>0 else round(value*factor,6) for key,value in values.items()}
