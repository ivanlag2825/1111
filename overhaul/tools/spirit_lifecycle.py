"""Visible, self-contained spirit assets and non-refreshing native idea timers."""
import math,struct
from pathlib import Path
from clausewitz import parse,edit

PICTURES=('hro_spirit_army','hro_spirit_industry','hro_spirit_crisis','hro_spirit_recovery')


def timed_selection(identities,desired,flag,duration):
    """Use the flag's original creation date, never a fresh full duration.

    HOI4 supports days comparisons on has_country_flag and variable durations
    on add_timed_idea. The age ladder runs only when a missing/new tier is added.
    Existing tiers are left alone. This also repairs an active 0.6 window.
    """
    remove=' '.join(f'if = {{ limit = {{ has_idea = {i} }} remove_ideas = {i} }}' for i in identities if i!=desired)
    ages=[]
    for age in range(duration-1,0,-1):
        branch='if' if not ages else 'else_if'
        ages.append(f'{branch} = {{ limit = {{ has_country_flag = {{ flag = {flag} days > {age-1} }} }} set_temp_variable = {{ hro_spirit_days_left = {duration-age} }} }}')
    return remove+f''' if = {{ limit = {{ has_country_flag = {flag} NOT = {{ has_idea = {desired} }} }}
        set_temp_variable = {{ hro_spirit_days_left = {duration} }}
        {' '.join(ages)}
        add_timed_idea = {{ idea = {desired} days = hro_spirit_days_left }}
    }}'''


def _inside(x,y,polygon):
    hit=False;j=len(polygon)-1
    for i,(xi,yi) in enumerate(polygon):
        xj,yj=polygon[j]
        if (yi>y)!=(yj>y) and x < (xj-xi)*(y-yi)/(yj-yi)+xi:hit=not hit
        j=i
    return hit


def _dds(kind):
    """64x64 uncompressed BGRA DDS, generated using only the standard library."""
    size=64;pixels=bytearray()
    colors={'army':(210,177,87),'industry':(186,165,114),'crisis':(189,74,59),'recovery':(82,159,112)}
    color=colors[kind]
    star=[(32+math.cos(-math.pi/2+i*math.pi/5)*(19 if i%2==0 else 8),32+math.sin(-math.pi/2+i*math.pi/5)*(19 if i%2==0 else 8)) for i in range(10)]
    shield=[(16,14),(48,14),(46,37),(40,46),(32,53),(24,46),(18,37)]
    for y in range(size):
        for x in range(size):
            d=math.hypot(x-31.5,y-31.5)
            if d>30:rgba=(0,0,0,0)
            elif d>27:rgba=(*color,255)
            else:
                rgba=(34,39,44,255)
                if kind=='army':mark=_inside(x+.5,y+.5,star)
                elif kind=='industry':mark=((14<=x<=49 and 35<=y<=48) or (17<=x<=23 and 17<=y<=42) or _inside(x,y,[(14,36),(29,25),(29,36),(43,25),(49,35)]))
                elif kind=='crisis':mark=_inside(x+.5,y+.5,[(32,11),(53,49),(11,49)])
                else:mark=_inside(x+.5,y+.5,shield)
                if mark:rgba=(*color,255)
                if kind=='crisis' and ((29<=x<=34 and 23<=y<=36) or (29<=x<=34 and 41<=y<=45)):rgba=(245,232,206,255)
                if kind=='recovery' and ((29<=x<=34 and 23<=y<=42) or (22<=x<=41 and 30<=y<=35)):rgba=(239,235,213,255)
                if kind=='industry' and y in range(39,45) and any(a<=x<=a+3 for a in (20,30,40)):rgba=(34,39,44,255)
            r,g,b,a=rgba;pixels.extend((b,g,r,a))
    header=[124,0x100F,size,size,size*4,0,0]+[0]*11+[32,0x41,0,32,0x00ff0000,0x0000ff00,0x000000ff,0xff000000,0x1000,0,0,0,0]
    assert len(header)==31
    return b'DDS '+struct.pack('<31I',*header)+pixels


def author_spirit_assets(root):
    root=Path(root);sprites=[]
    for picture in PICTURES:
        asset='gfx/interface/ideas/'+picture+'.dds';path=root/asset;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(_dds(picture.removeprefix('hro_spirit_')))
        sprites.append(f'spriteType = {{ name = "GFX_idea_{picture}" texturefile = "{asset}" }}')
    (root/'interface').mkdir(parents=True,exist_ok=True)
    (root/'interface/hro_spirit_icons.gfx').write_text('spriteTypes = {\n'+'\n'.join(sprites)+'\n}\n')
    count=0
    for path in sorted((root/'common/ideas').glob('hro*.txt')):
        source=path.read_text(encoding='utf-8-sig');patches=[]
        for section in parse(source):
            if section.key!='ideas':continue
            for category in section.value:
                for idea in category.value:
                    if not idea.key.startswith('hro_'):continue
                    picture=('hro_spirit_crisis' if any(s in idea.key for s in ('_crisis_','_surprise','_shock','_strain','_dislocated','_prepared_fronts','_regrouping','_first_winter','_prepared_winter','_later_winter','_adapted_winter','_working')) else
                             'hro_spirit_recovery' if any(s in idea.key for s in ('_mobilization_','_rebuilding_','_liberation_','_adapted','_battle_hardened')) else
                             'hro_spirit_industry' if path.name in ('hro_country_ideas.txt','hro_programme_ideas.txt') else 'hro_spirit_army')
                    if field:=idea.one('picture'):patches.append((field.start,field.end,'picture = '+picture))
                    for name,value in [('visible','{ always = yes }'),('cancel_if_invalid','no')]:
                        if field:=idea.one(name):patches.append((field.start,field.end,name+' = '+value))
                        else:patches.append((idea.value_end-1,idea.value_end-1,' '+name+' = '+value+' '))
                    count+=1
        path.write_text(edit(source,patches))
    return {'owned_icons':len(PICTURES),'visible_spirits':count,'external_texture_dependency':False}


def audit_spirit_assets(root):
    root=Path(root);errors=[];sprites={}
    manifest=root/'interface/hro_spirit_icons.gfx'
    if not manifest.is_file():return ['Missing owned national-spirit sprite manifest']
    for block in parse(manifest.read_text()):
        for sprite in block.all('spriteType'):
            sprites[str(sprite.scalar('name')).strip('"')]=str(sprite.scalar('texturefile')).strip('"')
    for path in sorted((root/'common/ideas').glob('hro*.txt')):
        for block in parse(path.read_text(encoding='utf-8-sig')):
            if block.key!='ideas':continue
            for category in block.value:
                for idea in category.value:
                    if not idea.key.startswith('hro_'):continue
                    picture=idea.scalar('picture','')
                    sprite='GFX_idea_'+picture
                    if sprite not in sprites:errors.append('Missing national-spirit sprite: '+idea.key+'/'+sprite)
                    if not idea.one('visible') or idea.one('visible').scalar('always')!='yes':errors.append('National spirit not explicitly visible: '+idea.key)
                    if idea.scalar('cancel_if_invalid')!='no':errors.append('National spirit can cancel outside lifecycle: '+idea.key)
    for name,texture in sprites.items():
        target=(root/texture).resolve()
        if not target.is_relative_to(root.resolve()) or not target.is_file():
            errors.append('Missing national-spirit texture: '+name+'/'+texture);continue
        data=target.read_bytes()
        if len(data)!=128+64*64*4 or data[:4]!=b'DDS ' or struct.unpack_from('<I',data,4)[0]!=124:
            errors.append('Invalid national-spirit DDS: '+texture)
    return errors
