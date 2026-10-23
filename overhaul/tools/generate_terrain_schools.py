"""Slot-researched terrain specialisations. Existing school IDs remain intact."""
from clausewitz import parse,edit
from generate_frontier import script
CHOICES={
 'urban':[
  ('assault','Штурмовые группы','Assault Groups',{'infantry':{'urban':{'attack':.10}},'engineer':{'fort':{'attack':.10}}},'Сапёры и пехота отрабатывают зачистку кварталов.','Infantry and engineers rehearse clearing city blocks.'),
  ('defence','Оборона кварталов','Block Defence',{'infantry':{'urban':{'defence':.15}}},'Опорные пункты и перекрёстный огонь удерживают город.','Strongpoints and crossfire hold the city.')],
 'forest':[
  ('ambush','Лесные засады','Forest Ambushes',{'infantry':{'forest':{'attack':.10,'defence':.05}}},'Засады и короткие огневые налёты поддерживают наступление.','Ambushes and short fire raids support the advance.'),
  ('rangers','Егерские маршруты','Ranger Routes',{'infantry':{'forest':{'movement':.15}},'mountaineers':{'forest':{'attack':.10,'movement':.10}}},'Егеря находят обходы и ведут колонны сквозь лес.','Rangers find bypasses and guide columns through woodland.')],
 'mountain':[
  ('assault','Высотный штурм','High-Altitude Assault',{'mountaineers':{'mountain':{'attack':.15},'hills':{'attack':.10}}},'Связки и огневая поддержка помогают брать перевалы.','Rope teams and supporting fire help seize mountain passes.'),
  ('supply','Высотное снабжение','Mountain Supply',{'mountaineers':{'mountain':{'movement':.15,'defence':.10},'supply_consumption_factor':-.10}},'Вьючные колонны и горные склады снижают нагрузку снабжения.','Pack columns and mountain depots reduce the supply burden.')],
}
def generate(output,put,text):
 source_path=output/'common/technologies/hro_front_schools.txt';source=source_path.read_text();patches=[];techs=[];roots=[];icons={}
 nodes={n.key:n for r in parse(source) for n in r.value}
 for tag in ('ger','sov'):
  for school,choices in CHOICES.items():
   parent=f'hro_tech_{tag}_{school}';ids=[parent+'_'+c[0] for c in choices]
   paths=' '.join('path = { leads_to_tech = '+k+' research_cost_coeff = 1 }' for k in ids)
   if school=='mountain':
    roots.append((parent,250,1150));icons[parent]='tech_mountaineers'
    text(parent,'Школа горной войны','Mountain Warfare School')
    text(parent+'_desc','Горнострелки: атака в горах +10%, защита в горах +10%. Затем выберите штурм или снабжение.','Mountaineers: mountain attack +10%, mountain defence +10%. Then choose assault or supply.')
    techs.append(f'{parent} = {{ allow_branch = {{ original_tag = {tag.upper()} }} allow = {{ original_tag = {tag.upper()} }} research_cost = 0.65 start_year = 1938 dependencies = {{ tech_mountaineers = 1 }} folder = {{ name = hro_front_folder position = {{ x = 0 y = 0 }} }} categories = {{ hro_front_research }} {paths} mountaineers = {{ mountain = {{ attack = 0.10 defence = 0.10 }} }} }}')
   else:
    node=nodes[parent];patches.append((node.value_end-1,node.value_end-1,' '+paths+' '))
   for index,(key,ru,en,mods,why,why_en) in enumerate(choices):
    identity=ids[index];other=ids[1-index];year=1940 if school=='mountain' or tag=='ger' else (1943 if school=='urban' else 1942)
    techs.append(f'{identity} = {{ allow_branch = {{ original_tag = {tag.upper()} }} allow = {{ original_tag = {tag.upper()} }} research_cost = 0.75 start_year = {year} dependencies = {{ {parent} = 1 }} xor = {{ {other} }} folder = {{ name = hro_front_folder position = {{ x = {-1 if index==0 else 1} y = 3 }} }} categories = {{ hro_front_research }} {script(mods)} }}')
    values=[];names={'infantry':('Пехота','Infantry'),'engineer':('Сапёры','Engineers'),'mountaineers':('Горнострелки','Mountaineers')};terrains={'urban':('город','urban'),'forest':('лес','forest'),'mountain':('горы','mountain'),'hills':('холмы','hills'),'fort':('укрепления','fort')};stats={'attack':('атака','attack'),'defence':('защита','defence'),'movement':('передвижение','movement')}
    descs=[]
    for lang in (0,1):
     values=[]
     for unit,fields in mods.items():
      for terrain,entries in fields.items():
       if isinstance(entries,dict):
        values.extend(f'{names[unit][lang]}: {terrains[terrain][lang]}, {stats[k][lang]} {v:+.0%}' for k,v in entries.items())
       else:values.append(f'{names[unit][lang]}: '+('расход припасов ' if lang==0 else 'supply consumption ')+f'{entries:+.0%}')
     descs.append((why if lang==0 else why_en)+' '+ '; '.join(values)+'.')
    text(identity,ru,en);text(identity+'_desc',*descs);icons[identity]='tech_mountaineers' if school=='mountain' else 'tech_engineers'
 source_path.write_text(edit(source,patches))
 return techs,roots,icons
