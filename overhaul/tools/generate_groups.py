"""Native focus-tree inlay headers; no replacement of countryfocusview.gui."""
from pathlib import Path
import json


def generate(output, catalogs):
    output=Path(output)
    definitions=[];windows=[];loc={'russian':{},'english':{}}
    summary={}
    for catalog in catalogs:
        summary[catalog['tag']]=catalog.get('groups',[])
        for group in catalog.get('groups',[]):
            identity=group['id'];width=group['width']*80
            definitions.append(f'{identity} = {{ window_name = {identity}_window internal = no visible = {{ original_tag = {catalog["tag"]} }} }}')
            windows.append(f'''containerWindowType = {{
    name = "{identity}_window"
    position = {{ x = 0 y = 0 }} size = {{ width = {width} height = 68 }}
    moveable = no clipping = no
    instantTextBoxType = {{ name = "chapter_title" position = {{ x = 0 y = 0 }}
        font = "hoi_20b" text = "{identity}" maxWidth = {width} maxHeight = 28 format = center }}
    instantTextBoxType = {{ name = "chapter_subtitle" position = {{ x = 0 y = 32 }}
        font = "hoi_16mbs" text = "{identity}_desc" maxWidth = {width} maxHeight = 24 format = center }}
}}''')
            for language,suffix in [('russian','ru'),('english','en')]:
                loc[language][identity]='§Y'+group['name_'+suffix]+'§!'
                loc[language][identity+'_desc']=('Подготовка  •  Специализация  •  Военный опыт' if language=='russian' else 'Preparation  •  Specialisation  •  Wartime experience')
    def put(path,value,bom=False):
        target=output/path;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(value+'\n',encoding='utf-8-sig' if bom else 'utf-8')
    put('common/focus_inlay_windows/hro_group_headers.txt','\n'.join(definitions))
    put('interface/hro_focus_groups.gui','guiTypes = {\n'+'\n'.join(windows)+'\n}')
    for language,entries in loc.items():
        put(f'localisation/{language}/hro_groups_l_{language}.yml',f'l_{language}:\n'+''.join(f' {key}:0 {json.dumps(value,ensure_ascii=False)}\n' for key,value in entries.items()),True)
    return summary
