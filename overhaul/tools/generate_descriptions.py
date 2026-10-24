"""Attach narrative paragraphs without altering any executable game file."""
from pathlib import Path
import hashlib,json,re
from collections import Counter
from narrative_content import ROWS,SPECIFIC,STAGES
from clausewitz import parse,walk
ROOT=Path(__file__).resolve().parents[1]
PATTERN=re.compile(r'\s*([A-Za-z0-9_.-]+):\d+\s+(".*")\s*')

def read(root):
 result={}
 for lang in ('russian','english'):
  records={}
  for p in sorted((Path(root)/'localisation'/lang).glob('*.yml')):
   for line in p.read_text(encoding='utf-8-sig').splitlines()[1:]:
    m=PATTERN.fullmatch(line)
    if m:
     key,quoted=m.groups()
     if key in records:raise ValueError('Duplicate localisation: '+key)
     records[key]=(json.loads(quoted),p)
  result[lang]=records
 return result

def context(identity,title='',details='',kind=''):
 for stem,pair in SPECIFIC.items():
  if stem in identity:return stem,pair
 subject=(identity+' '+title).lower()
 if identity.startswith('hro_tech_front_'):
  return 'retired',('Эта прежняя программа оставлена только для совместимости сохранений. Развитие соответствующих служб представлено действующими фокусами и исследованиями.', 'This retired programme remains only for save compatibility. Current focuses and research represent further development of the corresponding services.')
 for pattern,ru,en in ROWS:
  if any(token in subject for token in pattern.split('|')):return pattern.split('|')[0],(ru,en)
 raise ValueError('Missing narrative subject: '+identity+' / '+title)

def normalize(text):
 # Only typography: do not change values, scope or duration.
 protected=re.split(r'(\$[^$]+\$|\[[^\]]+\]|§.)',text)
 for i in range(0,len(protected),2):
  protected[i]=re.sub(r'([А-Яа-яЁёA-Za-z])([0-9])',r'\1 \2',protected[i])
  protected[i]=re.sub(r'([0-9])([А-Яа-яЁёA-Za-z])',r'\1 \2',protected[i])
  protected[i]=re.sub(r'([%])([А-Яа-яЁёA-Za-z])',r'\1 \2',protected[i])
 return ''.join(protected)

def entities(root,catalogs):
 root=Path(root);result={}
 def add(kind,identity,desc=None):
  if identity:result.setdefault(kind,{})[identity]=desc or identity+'_desc'
 for c in catalogs:
  for f in c['focuses']:add('focuses',f['id'])
  for f in c['native_patches']:add('native_focuses',f['id'])
 for folder,kind,containers in [('common/ideas','ideas',('ideas','country')),('common/technologies','research',('technologies',)),('common/units/equipment/modules','modules',('equipment_modules',))]:
  for p in (root/folder).glob('*.txt'):
   for n in walk(parse(p.read_text(encoding='utf-8-sig'))):
    if n.key in containers and isinstance(n.value,list):
     for child in n.value:
      if child.key and child.key.startswith('hro_') and isinstance(child.value,list):add(kind,child.key)
 for p in (root/'common/decisions').glob('*.txt'):
  for category in parse(p.read_text(encoding='utf-8-sig')):
   if not category.key.startswith('hro_') or not isinstance(category.value,list):continue
   # Categories are defined separately by native HOI4 convention.
   for child in category.value:
    if child.key and child.key.startswith('hro_') and isinstance(child.value,list):add('decisions',child.key)
 for p in (root/'common/decisions/categories').glob('*.txt'):
  for n in parse(p.read_text(encoding='utf-8-sig')):
   if n.key.startswith('hro_'):add('decision_categories',n.key)
 for p in (root/'events').glob('*.txt'):
  for event in parse(p.read_text(encoding='utf-8-sig')):
   if event.key in ('country_event','news_event') and event.scalar('desc'):add('events',event.scalar('id'),event.scalar('desc'))
 return result

def encyclopedia(root,records,inventory):
 titles={'focuses':'Новые фокусы','native_focuses':'Изменённые ванильные фокусы','ideas':'Национальные духи','research':'Исследования','modules':'Модули техники','decisions':'Решения и задачи','decision_categories':'Категории решений','events':'События'}
 out=['# Энциклопедия Historical Reality 2.0.0','Полные игровые описания добавленного и изменённого контента. Численные всплывающие эффекты в игре остаются окончательным справочником результатов. Архивные исследования перечислены для совместимости сохранений.']
 native=json.loads((ROOT/'data/narrative_native.json').read_text())
 for kind,items in inventory.items():
  out+=['','## '+titles[kind]]
  for identity,key in items.items():
   titlekey=identity+'.t' if kind=='events' else identity
   title=records['russian'].get(titlekey,('',None))[0] or native.get(identity,{}).get('name_ru') or identity
   body=records['russian'][key][0]
   clean=lambda t:re.sub(r'§.','',t).replace('\\n','\n')
   out+=['','### '+clean(title),'',clean(body)]
 p=Path(root)/'docs/ENCYCLOPEDIA_RU.md';p.parent.mkdir(parents=True,exist_ok=True);p.write_text('\n'.join(line.rstrip() for block in out for line in block.split('\n'))+'\n')

def generate(output,catalogs):
 root=Path(output);records=read(root);changes={};coverage={};profiles=Counter()
 # Every generated description and event body, including hidden/retired IDs.
 targets={k for k in records['russian'] if k.endswith('_desc') or re.fullmatch(r'hro\.\d+\.d',k)}
 native=json.loads((ROOT/'data/narrative_native.json').read_text())
 targets.update(k+'_desc' for k in native)
 inventory=entities(root,catalogs)
 targets.update(k for items in inventory.values() for k in items.values())
 focus_ids={f['id'] for c in catalogs for f in c['focuses']}
 for key in sorted(targets):
  identity=key[:-5] if key.endswith('_desc') else key
  title=records['russian'].get(identity,('',None))[0]
  if re.fullmatch(r'hro\.\d+\.d',key):title=records['russian'].get(key[:-1]+'t',('',None))[0]
  if identity in native:
   prose=tuple(native[identity][lang] for lang in ('ru','en'));profile='native'
  elif identity in focus_ids:
   # Catalogue descriptions already contain their narrative introduction.
   prose=None;profile='focus_catalogue'
  else:profile,prose=context(identity,title)
  profiles[profile]+=1
  for lang,index in [('russian',0),('english',1)]:
   old,path=records[lang].get(key,('',root/f'localisation/{lang}/hro_narrative_native_l_{lang}.yml'))
   if identity in native and old:
    # Retain authored native reward and schedule descriptions verbatim.
    new=prose[index]+'\n\n'+normalize(old)
   elif identity in native:new=prose[index]
   elif prose is None:new=old
   else:
    phase='working' if identity.endswith('_working') else 'benefit' if identity.endswith('_benefit') else None
    phase_text=(' '+STAGES[phase][index]) if phase else ''
    new=prose[index]+phase_text+'\n\n'+normalize(old)
   if not new.strip():raise ValueError('Empty description: '+key)
   changes.setdefault(path,{})[key]=new
  coverage[key]=profile
 # Edit original files, never rely on localisation filename ordering.
 for path,values in changes.items():
  lang='russian' if 'russian' in path.parts else 'english'
  lines=path.read_text(encoding='utf-8-sig').splitlines() if path.exists() else ['l_'+lang+':']
  emitted=set();out=[]
  for line in lines:
   m=PATTERN.fullmatch(line)
   if m and m.group(1) in values:
    k=m.group(1);line=f' {k}:0 '+json.dumps(values[k],ensure_ascii=False);emitted.add(k)
   out.append(line)
  out.extend(' '+k+':0 '+json.dumps(v,ensure_ascii=False) for k,v in values.items() if k not in emitted)
  path.parent.mkdir(parents=True,exist_ok=True);path.write_text('\n'.join(out)+'\n',encoding='utf-8-sig')
 encyclopedia(root,read(root),inventory)
 report={'entity_counts':{k:len(v) for k,v in inventory.items()},'description_keys':len(targets),'languages':['russian','english'],'native_focuses':len(native),'authored_focuses':len(focus_ids),'profiles':dict(profiles),'keys':coverage,'mechanical_suffixes_preserved':True,'executable_files_changed':False,'runtime_verified':False}
 report['audit']=audit(root,report)
 return report

def audit(output,report):
 records=read(output);errors=[]
 for lang,items in records.items():
  for key in report['keys']:
   value=items.get(key,('',None))[0]
   if len(value)<90:errors.append('Short/absent description: '+lang+'/'+key)
   if '?'*3 in value or '\ufffd' in value:errors.append('Broken text: '+lang+'/'+key)
 if errors:raise ValueError('\n'.join(errors))
 return {'covered_keys':len(report['keys']),'both_languages_checked':True,'duplicates_absent':True}
