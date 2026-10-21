#!/usr/bin/env python3
"""Build the GER/SOV 1936–1946 overhaul against the user's supplied game trees."""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

PROJECT = Path(__file__).resolve().parents[2]
OVERHAUL = PROJECT / 'overhaul'
sys.path.insert(0, str(PROJECT / 'tools'))
from clausewitz import Node, edit, parse, walk
from build_mod import tree_tag, right_edge, focus_definitions

VERSION = '0.5.0'
FOLDER = 'historical_reality_overhaul'
NAME = 'Historical Reality: Total War 1936-1946'
BRANCHES = ('industry', 'army', 'logistics', 'air', 'navy', 'state', 'diplomacy', 'war')
BRANCH_TITLES = {
    'industry': ('Промышленная программа', 'Industrial Programme'),
    'army': ('Армия и командование', 'Army and Command'),
    'logistics': ('Транспорт и снабжение', 'Transport and Supply'),
    'air': ('Воздушная стратегия', 'Air Strategy'),
    'navy': ('Военно-морская программа', 'Naval Programme'),
    'state': ('Государство и тыл', 'State and Home Front'),
    'diplomacy': ('Внешняя политика', 'Foreign Policy'),
    'war': ('Адаптация и восстановление', 'Adaptation and Recovery'),
}
ICONS = {
    'industry': 'construct_mil_factory', 'army': 'army_doctrines',
    'logistics': 'army_motorized', 'air': 'air_fighter', 'navy': 'navy_doctrines_tactics',
    'state': 'national_unity', 'diplomacy': 'improve_relations', 'war': 'defence',
}
STRUCTURAL_FIELDS = {'prerequisites': 'prerequisite', 'x': 'x', 'y': 'y',
                     'relative_position_id': 'relative_position_id', 'icon': 'icon'}


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def put(root, relative, text, bom=False):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode('utf-8-sig' if bom else 'utf-8'))


def loc_file(root, name, entries):
    for lang in ('russian', 'english'):
        text = f'l_{lang}:\n' + ''.join(f' {k}:0 {json.dumps(v, ensure_ascii=False)}\n' for k, v in entries[lang].items())
        put(root, f'localisation/{lang}/{name}_l_{lang}.yml', text, bom=True)


def number(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f'Expected numeric modifier, got {value!r}')
    return format(value, '.9g')


def date_gate(date):
    return f'OR = {{ has_game_rule = {{ rule = HRO_PACING option = HRO_OPEN }} date > {date} }}'


def signature(nodes):
    return [(n.key, n.op, signature(n.value) if isinstance(n.value, list) else n.value) for n in nodes]


def with_value(node, value):
    return Node(node.key, node.op, value, node.start, node.end, node.value_start, node.value_end)


def structural_script(key, value):
    """Render an explicitly authorised replacement, including multi-OR groups."""
    if key == 'prerequisites':
        if not isinstance(value, list) or any(not isinstance(g, list) or not g for g in value):
            raise ValueError('Native prerequisites must be a list of nonempty OR groups')
        return '\n    '.join('prerequisite = { ' + ' '.join(f'focus = {i}' for i in group) + ' }'
                             for group in value)
    if value is None:
        if key != 'relative_position_id':
            raise ValueError(f'Cannot remove structural field {key}')
        return ''
    return f'{key} = {number(value) if key in ("x", "y") else value}'


def verify_native_preservation(original_nodes, modified_nodes, changes, continuous_positions=None, inlay_positions=None):
    """Audit declared graph/layout edits and preserve all other native behaviour.

    Native rewards, bypasses, political visibility and DLC cleanup remain exact.
    Prerequisite and coordinate replacements are compared to their declared
    target before being restored for the full original-source comparison.
    """
    patches = {p['id']: p for p in changes}
    continuous_positions = continuous_positions or {}
    inlay_positions = inlay_positions or {}
    if len(original_nodes) != len(modified_nodes):
        raise ValueError('Unexpected top-level change in native focus source')
    restored = []
    checked = 0
    for original, modified in zip(original_nodes, modified_nodes):
        if original.key != 'focus_tree':
            restored.append(modified)
            continue
        panel = continuous_positions.get(original.scalar('id'))
        if panel is not None:
            expected = parse(f'continuous_focus_position = {{ x = {panel["x"]} y = {panel["y"]} }}')
            if signature(modified.all('continuous_focus_position')) != signature(expected):
                raise ValueError('Continuous focus position differs from declared layout fix')
        original_focuses = {n.scalar('id'): n for n in original.all('focus')}
        children = []
        for node in modified.value:
            if node.key == 'inlay_window' and str(node.scalar('id','')).startswith('hro_'):
                continue
            if node.key == 'inlay_window' and node.scalar('id') in inlay_positions:
                identity = node.scalar('id')
                expected = inlay_positions[identity]
                if signature(node.all('position')) != signature(parse(f'position = {{ x = {expected["x"]} y = {expected["y"]} }}')):
                    raise ValueError('Native inlay differs from declared position: ' + identity)
                previous = next(n for n in original.all('inlay_window') if n.scalar('id') == identity)
                node = with_value(node, [previous.one('position') if n.key == 'position' else n for n in node.value])
            if panel is not None and node.key == 'continuous_focus_position':
                if previous := original.one('continuous_focus_position'):
                    children.append(previous)
                continue
            if node.key == 'shared_focus' and isinstance(node.value, str) and node.value.startswith('hro_'):
                continue
            if node.key == 'shortcut' and str(node.scalar('name', '')).startswith('hro_'):
                continue
            if node.key != 'focus':
                children.append(node)
                continue
            identity = node.scalar('id')
            if identity not in original_focuses:
                raise ValueError(f'Unexpected native focus: {identity}')
            old = original_focuses[identity]
            patch = patches.get(identity, {})
            structural = {field: key for key, field in STRUCTURAL_FIELDS.items() if key in patch}
            for field, key in structural.items():
                expected = parse(structural_script(key, patch[key]))
                if signature(node.all(field)) != signature(expected):
                    raise ValueError(f'Native structural edit differs from declaration: {identity}/{key}')
            fields = []
            for field in node.value:
                if field.key in structural:
                    continue
                if field.key == 'cost' and 'new_cost' in patch:
                    field = with_value(field, old.one('cost').value)
                elif field.key == 'available' and (patch.get('earliest') or patch.get('require')):
                    expected = []
                    if patch.get('earliest'):
                        expected.extend(parse(date_gate(patch['earliest'])))
                    if patch.get('require'):
                        expected.extend(parse(patch['require']))
                    if signature(field.value[-len(expected):]) != signature(expected):
                        raise ValueError(f'Native conditions modified outside declared additions: {identity}')
                    value = field.value[:-len(expected)]
                    if old.one('available') is None:
                        if value:
                            raise ValueError(f'Unexpected native conditions: {identity}')
                        continue
                    field = with_value(field, value)
                elif field.key == 'completion_reward' and patch.get('extra_reward'):
                    expected = parse(patch['extra_reward'])
                    if signature(field.value[-len(expected):]) != signature(expected):
                        raise ValueError(f'Native rewards modified outside declared additions: {identity}')
                    value = field.value[:-len(expected)]
                    if old.one('completion_reward') is None:
                        if value:
                            raise ValueError(f'Unexpected native rewards: {identity}')
                        continue
                    field = with_value(field, value)
                fields.append(field)
            # Compare in source field order, placing original structural fields
            # back at their source indices. This also audits a removed anchor.
            if structural:
                unchanged = iter(fields)
                reconstructed = []
                for original_field in old.value:
                    reconstructed.append(original_field if original_field.key in structural else next(unchanged))
                reconstructed.extend(unchanged)
                fields = reconstructed
            if signature(fields) != signature(old.value):
                raise ValueError(f'Unexpected change to native focus structure: {identity}')
            children.append(with_value(node, fields))
            checked += 1
        restored.append(with_value(modified, children))
    if signature(restored) != signature(original_nodes):
        raise ValueError('Native tree fields or source constants changed unexpectedly')
    return checked


def read_catalogs(directory):
    catalogs = [json.loads((directory / filename).read_text(encoding='utf-8')) for filename in ('ger.json', 'sov.json')]
    if {x['tag'] for x in catalogs} != {'GER', 'SOV'}:
        raise ValueError('Expected GER and SOV country catalogs')
    focuses = [f for c in catalogs for f in c['focuses']]
    ideas = [i for c in catalogs for i in c['ideas']]
    for records, kind in ((focuses, 'focus'), (ideas, 'idea')):
        ids = [x['id'] for x in records]
        if len(ids) != len(set(ids)):
            raise ValueError(f'Duplicate authored {kind} ID')
    for c in catalogs:
        for f in c['focuses']:
            if not f['id'].startswith('hro_' + c['tag'].lower() + '_'):
                raise ValueError(f'Invalid focus namespace: {f["id"]}')
            if f['branch'] not in BRANCHES or not f['prerequisites'] or f['cost'] <= 0:
                raise ValueError(f'Invalid focus structure: {f["id"]}')
            for key in ('available', 'reward'):
                parse(f.get(key, ''))
        patches = [p['id'] for p in c['native_patches']]
        if len(patches) != len(set(patches)):
            raise ValueError(f'Duplicate native patch in {c["tag"]}')
    return catalogs


def author_country_content(stage, catalogs, offsets):
    focus_loc = {'russian': {}, 'english': {}}
    idea_loc = {'russian': {}, 'english': {}}
    focuses, ideas = [], []
    families = defaultdict(list)
    for catalog in catalogs:
        for idea in catalog['ideas']:
            families[idea['family']].append(idea)
    for catalog in catalogs:
        tag = catalog['tag']
        for f in catalog['focuses']:
            x = f.get('x', offsets[tag] + BRANCHES.index(f['branch']) * 6 + f.get('lane', 0) * 2)
            y = f.get('y', f.get('row', 1))
            anchor = f'relative_position_id = {f["relative_position_id"]}' if f.get('relative_position_id') else ''
            icon = f.get('icon', 'GFX_goal_generic_' + ICONS[f['branch']])
            prerequisite = '\n    '.join('prerequisite = { ' + ' '.join(f'focus = {identity}' for identity in group) + ' }' for group in f['prerequisites'])
            excluded = ' '.join(f'focus = {identity}' for identity in f.get('mutually_exclusive', []))
            mutual = f'mutually_exclusive = {{ {excluded} }}' if excluded else ''
            date = date_gate(f['earliest']) if f.get('earliest') else ''
            flags = ' '.join('set_country_flag = ' + flag for flag in f.get('flags', []))
            filter_map = {'army':'FOCUS_FILTER_ARMY_XP','logistics':'FOCUS_FILTER_ARMY_XP','war':'FOCUS_FILTER_ARMY_XP',
                          'industry':'FOCUS_FILTER_INDUSTRY','air':'FOCUS_FILTER_AIR_XP','navy':'FOCUS_FILTER_NAVY_XP',
                          'state':'FOCUS_FILTER_INTERNAL_AFFAIRS','diplomacy':'FOCUS_FILTER_INTERNATIONAL_TRADE'}
            focuses.append(f'''shared_focus = {{
    id = {f['id']}
    icon = {icon}
    x = {x}
    y = {y}
    {anchor}
    cost = {f['cost']}
    {prerequisite}
    {mutual}
    available = {{ original_tag = {tag} has_capitulated = no {date} {f.get('available', '')} }}
    cancel_if_invalid = yes
    search_filters = {{ {filter_map[f['branch']]} FOCUS_FILTER_RESEARCH }}
    ai_will_do = {{ factor = 0.5 }}
    completion_reward = {{ {f.get('reward', '')} {flags} }}
}}
''')
            for lang, suffix in (('russian', 'ru'), ('english', 'en')):
                focus_loc[lang][f['id']] = f['name_' + suffix]
                focus_loc[lang][f['id'] + '_desc'] = f['desc_' + suffix]
        for i in catalog['ideas']:
            modifiers = ' '.join(f'{k} = {number(v)}' for k, v in i['modifiers'].items())
            ideas.append(f'''    {i['id']} = {{
        picture = generic_industry
        allowed = {{ original_tag = {tag} }}
        removal_cost = -1
        modifier = {{ {modifiers} }}
    }}''')
            for lang, suffix in (('russian', 'ru'), ('english', 'en')):
                idea_loc[lang][i['id']] = i['name_' + suffix]
                idea_loc[lang][i['id'] + '_desc'] = i['desc_' + suffix]
    put(stage, 'common/national_focus/hro_country_focuses.txt', '\n'.join(focuses))
    put(stage, 'common/ideas/hro_country_ideas.txt', 'ideas = { country = {\n' + '\n'.join(ideas) + '\n} }\n')
    loc_file(stage, 'hro_focuses', focus_loc)
    loc_file(stage, 'hro_country_ideas', idea_loc)

    setters = []
    for family, members in families.items():
        for idea in members:
            # A late native milestone must preserve an already chosen same-tier
            # specialisation as well as a higher reform tier.
            higher = [m['id'] for m in members if m['stage'] >= idea['stage']]
            limit = 'NOT = { OR = { ' + ' '.join('has_idea = ' + x for x in higher) + ' } }' if higher else 'always = yes'
            remove = ' '.join('remove_ideas = ' + m['id'] for m in members)
            setters.append(f'hro_set_{idea["id"]} = {{ if = {{ limit = {{ {limit} }} {remove} add_ideas = {idea["id"]} }} }}')
    initialize = ['hro_initialize_country = { set_country_flag = hro_initialized']
    for catalog in catalogs:
        initial = [i for i in catalog['ideas'] if i.get('initial')]
        initialize.append(f'if = {{ limit = {{ original_tag = {catalog["tag"]} }} ' + ' '.join(f'hro_set_{i["id"]} = yes' for i in initial) + ' }')
    initialize.append('}')
    put(stage, 'common/scripted_effects/hro_country_progression.txt', '\n'.join(setters + initialize) + '\n')
    put(stage, 'common/scripted_triggers/hro_core_triggers.txt', 'hro_supported_country = { OR = { original_tag = GER original_tag = SOV } }\n')
    put(stage, 'common/on_actions/hro_init_on_actions.txt', '''on_actions = {
    on_startup = { effect = { every_country = {
        limit = { hro_supported_country = yes NOT = { has_country_flag = hro_initialized } }
        hro_initialize_country = yes
    } } }
    on_monthly = { effect = { if = {
        limit = { hro_supported_country = yes NOT = { has_country_flag = hro_initialized } }
        hro_initialize_country = yes
    } } }
}
''')


def author_rules(stage):
    put(stage, 'common/game_rules/hro_rules.txt', '''HRO_PACING = {
    name = HRO_PACING
    desc = HRO_PACING_DESC
    group = HRO_RULES
    default = { name = HRO_HISTORICAL text = HRO_HISTORICAL desc = HRO_HISTORICAL_DESC allow_achievements = no }
    option = { name = HRO_OPEN text = HRO_OPEN desc = HRO_OPEN_DESC allow_achievements = no }
}
''')
    pairs = {
        'HRO_RULES': ('Historical Reality: большая переработка', 'Historical Reality: Overhaul'),
        'HRO_PACING': ('Исторический темп подготовки', 'Historical Preparation Pacing'),
        'HRO_PACING_DESC': ('Дополнительные нижние границы начала важных фокусов. Условия войн и ответы стран сохраняются.', 'Additional earliest dates for major focuses. Actual war conditions and country responses remain in force.'),
        'HRO_HISTORICAL': ('Исторические условия, свободный исход', 'Historical Conditions, Free Outcome'),
        'HRO_HISTORICAL_DESC': ('Ключевые дипломатические этапы и поздние реформы открываются в соответствующий период. Скрипты мода не назначают победителя.', 'Major diplomatic milestones and late reforms unlock in their relevant periods. The overhaul does not choose the winner.'),
        'HRO_OPEN': ('Свободные сроки', 'Open Preparation Dates'),
        'HRO_OPEN_DESC': ('Отключает дополнительные условия даты HRO. Все ресурсные, военные и исходные требования остаются.', 'Disables additional HRO date gates. Resource, war and original conditions remain in force.'),
    }
    entries = {'russian': {}, 'english': {}}
    for key, values in pairs.items():
        entries['russian'][key], entries['english'][key] = values
    for tag in ('GER', 'SOV'):
        for branch, values in BRANCH_TITLES.items():
            key = f'hro_section_{tag.lower()}_{branch}'
            entries['russian'][key], entries['english'][key] = values
    loc_file(stage, 'hro_core', entries)


def native_overlay(stage, game, catalogs):
    source_paths = {'GER': 'common/national_focus/germany.txt', 'SOV': 'common/national_focus/soviet.txt'}
    texts = {tag: (game / path).read_bytes().decode('utf-8-sig') for tag, path in source_paths.items()}
    docs = {tag: parse(text) for tag, text in texts.items()}
    definitions = focus_definitions(docs)
    source_icons = {n.value for nodes in docs.values() for n in walk(nodes)
                    if isinstance(n.value, str) and n.value.startswith('GFX_')}
    for catalog in catalogs:
        for focus in catalog['focuses']:
            if focus.get('icon') and focus['icon'] not in source_icons:
                raise ValueError(f'Focus icon not referenced by supplied native trees: {focus["id"]}/{focus["icon"]}')
    trees = {}
    for tag, nodes in docs.items():
        selected = [n for n in nodes if n.key == 'focus_tree' and tree_tag(n) == tag]
        if len(selected) != 1:
            raise ValueError(f'Expected one original {tag} tree, got {len(selected)}')
        trees[tag] = selected[0]
    offsets = {tag: int(right_edge(tree, definitions)) + 14 for tag, tree in trees.items()}
    pacing = json.loads((PROJECT / 'data/historical_gates.json').read_text(encoding='utf-8'))
    native_loc = {'russian': {}, 'english': {}}
    report = {'source_sha256': {}, 'original_focus_counts': {}, 'native_patches': [], 'branch_offsets': offsets,
              'continuous_focus_layout': {}, 'native_inlay_moves': {}, 'original_focus_ids_preserved': True, 'native_scripted_effects_preserved': True}
    layout = module('hro_native_layout_fix', OVERHAUL / 'tools/native_layout_fix.py')
    for catalog in catalogs:
        tag = catalog['tag']
        tree, text = trees[tag], texts[tag]
        originals = {f.scalar('id'): f for f in tree.all('focus')}
        patches = {p['id']: p for p in catalog['native_patches']}
        if unknown := patches.keys() - originals.keys():
            raise ValueError(f'Unknown native patch IDs for {tag}: {sorted(unknown)}')
        for identity, config in pacing.items():
            if identity in originals and identity not in patches:
                patches[identity] = {'id': identity, 'earliest': config['earliest_start']}
            elif identity in patches and 'earliest' not in patches[identity]:
                patches[identity] = dict(patches[identity], earliest=config['earliest_start'])
        edits = []
        for identity, patch in patches.items():
            focus = originals[identity]
            details = {'id': identity, 'tag': tag}
            for key, field in STRUCTURAL_FIELDS.items():
                if key not in patch:
                    continue
                replacement = structural_script(key, patch[key])
                current = focus.all(field)
                if current:
                    edits.append((current[0].start, current[0].end, replacement))
                    edits.extend((node.start, node.end, '') for node in current[1:])
                elif replacement:
                    edits.append((focus.value_end - 1, focus.value_end - 1, '\n    ' + replacement + '\n'))
                details[key] = patch[key]
                if key == 'prerequisites':
                    details['old_prerequisites'] = [[n.value for n in group.all('focus')]
                                                    for group in current]
                else:
                    details['old_' + key] = current[0].value if current else None
            if 'cost' in patch:
                cost = focus.one('cost')
                if cost is None or patch['cost'] <= 0:
                    raise ValueError(f'Invalid native cost patch: {identity}')
                edits.append((cost.value_start, cost.value_end, number(patch['cost'])))
                details.update(old_cost=cost.value, new_cost=patch['cost'])
            conditions = []
            if patch.get('earliest'):
                conditions.append(date_gate(patch['earliest']))
                details['earliest'] = patch['earliest']
            if patch.get('require'):
                parse(patch['require'])
                conditions.append(patch['require'])
                details['require'] = patch['require']
            if conditions:
                available = focus.one('available')
                addition = '\n    # HRO preparation conditions\n    ' + '\n    '.join(conditions) + '\n'
                if available:
                    edits.append((available.value_end - 1, available.value_end - 1, addition))
                else:
                    edits.append((focus.value_end - 1, focus.value_end - 1, '\n    available = { ' + addition + ' }\n'))
            if patch.get('extra_reward'):
                parse(patch['extra_reward'])
                reward = focus.one('completion_reward')
                addition = '\n    # HRO programme / reform progression\n    ' + patch['extra_reward'] + '\n'
                if reward:
                    edits.append((reward.value_end - 1, reward.value_end - 1, addition))
                else:
                    edits.append((focus.value_end - 1, focus.value_end - 1, '\n    completion_reward = { ' + addition + ' }\n'))
                details['extra_reward'] = patch['extra_reward']
            for lang, suffix in (('russian', 'ru'), ('english', 'en')):
                if patch.get('name_' + suffix):
                    native_loc[lang][identity] = patch['name_' + suffix]
                if patch.get('desc_' + suffix):
                    native_loc[lang][identity + '_desc'] = patch['desc_' + suffix]
            report['native_patches'].append(details)
        attached = ''.join('\n    shared_focus = ' + f['id'] for f in catalog['focuses'])
        attached += ''.join(f'\n    inlay_window = {{ id = {g["id"]} position = {{ x = {g["x"]*80} y = {g["y"]*130} }} }}' for g in catalog.get('groups',[]))
        for group in catalog.get('groups',[]):
            target=group['target']
            if target not in originals and target not in {f['id'] for f in catalog['focuses']}:
                raise ValueError('Unknown chapter navigation target: '+target)
            attached += f'\n    shortcut = {{ name = {group["id"]} target = {target} scroll_wheel_factor = 1.0 trigger = {{ always = yes }} }}'
        for branch in (() if catalog.get('groups') else BRANCHES):
            candidates = [f for f in catalog['focuses'] if f['branch'] == branch]
            if candidates:
                first = min(candidates, key=lambda f: (f.get('y', f.get('row', 1)), f.get('x', f.get('lane', 0))))
                attached += f'\n    shortcut = {{ name = hro_section_{tag.lower()}_{branch} target = {first["id"]} trigger = {{ always = yes }} }}'
        edits.append((tree.value_end - 1, tree.value_end - 1, attached + '\n'))
        modified = edit(text, edits)
        result = parse(modified)
        # Keep the original DLC inner-circle panel with its moved focus root.
        inlay_positions = {}
        current_tree = next(n for n in result if n.key == 'focus_tree' and tree_tag(n) == tag)
        if tag == 'GER' and 'GER_fuhrerprinzip' in originals:
            old_y = layout.focus_vertical_bounds(originals)['GER_fuhrerprinzip'][0]
            new_y = layout.focus_vertical_bounds({n.scalar('id'):n for n in current_tree.all('focus')})['GER_fuhrerprinzip'][0]
            inlay_edits = []
            for inlay in current_tree.all('inlay_window'):
                if inlay.scalar('id') != 'ger_inner_circle_inlay_window':
                    continue
                old = next(n for n in tree.all('inlay_window') if n.scalar('id') == inlay.scalar('id')).one('position')
                pos = {'x':int(old.scalar('x')),'y':int(float(old.scalar('y'))+(new_y-old_y)*130)}
                value = inlay.one('position')
                inlay_edits.append((value.start,value.end,f'position = {{ x = {pos["x"]} y = {pos["y"]} }}'))
                inlay_positions[inlay.scalar('id')] = pos
            modified = edit(modified,inlay_edits)
            result = parse(modified)
        report['native_inlay_moves'][tag] = inlay_positions
        changed_tree = next(n for n in result if n.key == 'focus_tree' and tree_tag(n) == tag)
        positioned = {n.scalar('id'): n for n in changed_tree.all('focus')}
        for authored in catalog['focuses']:
            x = authored.get('x', offsets[tag] + BRANCHES.index(authored['branch']) * 6 + authored.get('lane', 0) * 2)
            y = authored.get('y', authored.get('row', 1))
            anchor = f'relative_position_id = {authored["relative_position_id"]}' if authored.get('relative_position_id') else ''
            positioned[authored['id']] = parse(f'shared_focus = {{ id = {authored["id"]} x = {x} y = {y} {anchor} }}')[0]
        previous_panel = changed_tree.one('continuous_focus_position')
        layout_report = layout.continuous_layout_report(positioned, previous_panel)
        position = layout_report['position']
        replacement = f'continuous_focus_position = {{ x = {position["x"]} y = {position["y"]} }}'
        if previous_panel:
            modified = edit(modified, [(previous_panel.start, previous_panel.end, replacement)])
        else:
            modified = edit(modified, [(changed_tree.value_end - 1, changed_tree.value_end - 1, '\n    ' + replacement + '\n')])
        result = parse(modified)
        layout_report['old_position'] = ({'x': previous_panel.scalar('x'), 'y': previous_panel.scalar('y')} if previous_panel else None)
        report['continuous_focus_layout'][tag] = layout_report
        if {f.scalar('id') for f in changed_tree.all('focus')} != set(originals):
            raise ValueError(f'Native focus IDs changed unexpectedly: {tag}')
        verified = verify_native_preservation(docs[tag], result,
                                              [p for p in report['native_patches'] if p['tag'] == tag],
                                              {tree.scalar('id'): position}, inlay_positions)
        if verified != len(originals):
            raise ValueError(f'Native preservation count mismatch: {tag}')
        put(stage, source_paths[tag], modified, bom=True)
        report['source_sha256'][source_paths[tag]] = hashlib.sha256((game / source_paths[tag]).read_bytes()).hexdigest()
        report['original_focus_counts'][tag] = len(originals)
    report['native_structure_verified'] = True
    report['authored_icon_variants'] = len({f.get('icon') for c in catalogs for f in c['focuses']
                                           if f.get('icon')})
    report['native_prerequisite_rewrites'] = sum('prerequisites' in p for p in report['native_patches'])
    report['native_layout_rewrites'] = sum(any(k in p for k in ('x', 'y', 'relative_position_id'))
                                            for p in report['native_patches'])
    loc_file(stage, 'hro_native', native_loc)
    return report, offsets


def player_guide(catalogs, gameplay, report):
    text = f'''# Historical Reality: Total War 1936–1946 — {VERSION}

Большая переработка для двух игроков: Германия против СССР. Основной сценарий — новая историческая кампания 1936 года со всеми DLC и возможностью отклонения от истории. Срок поддержанного контента — до 1946 года.

## Установка

1. Выключи прежние версии Historical Reality и другие моды деревьев/баланса GER/SOV. При обновлении замени старую папку `historical_reality_overhaul` новой.
2. Распакуй папку `{FOLDER}` и файл `{FOLDER}.mod` в `Документы/Paradox Interactive/Hearts of Iron IV/mod`.
3. Включи **{NAME}** в одном и том же наборе у обоих игроков. У обоих должны совпадать версия игры, DLC и checksum.
4. Начните НОВУЮ кампанию 1936 года. Для стран под управлением ИИ включите исторические фокусы. Правило HRO по умолчанию сохраняет исторические окна подготовки; «Свободные сроки» снимает только добавленные условия даты.
5. Основные промышленные и военные ветки переработаны прямо в обычных деревьях. Голубые узлы на приложенной схеме — новые; для ключевых исходных реформ они теперь обязательны. Заголовки и ярлыки помогают перейти к тематическим разделам; у СССР появился раздел «Оборона и возрождение».

## Содержание

Исходных ID сохранено {sum(report['original_focus_counts'].values())}; индивидуально изменены {len(report['native_patches'])} исходных узлов. Связи переделаны у {report['native_prerequisite_rewrites']} исходных фокусов, расположение — у {report['native_layout_rewrites']}. Добавлено {sum(len(c['focuses']) for c in catalogs)} новых фокусов. Проверена обязательность новых этапов для {report['validation']['required_integrated_milestones']} объявленных переходов к основным реформам.

Дерево содержит развилки специализации, объединяющие этапы и связи промышленности с перевооружением. Награды включают реальные предприятия, существенные исследовательские ускорения, ограниченное расширение исследований и национальные реформы. Все исходные награды, политические последствия и вызовы событий DLC сохранены; их условия и снятие дебаффов продолжают действовать.

У каждой страны собственные начальные институциональные слабости. Последовательные фокусы улучшают их до устойчивых преимуществ. Текущие духи видны в окне страны; завершение старой реформы позднее не откатывает уже достигнутую стадию HRO. Взаимоисключающие программы требуют выбора приоритета.

Промышленность, армия, снабжение, авиация, флот, государственное управление, дипломатия и адаптация в войне образуют связанные направления. Не требуется закрыть все ветки до 1946 года: очередь фокусов остаётся ограниченным ресурсом.

Общие программы требуют политической власти и временных издержек. Промышленная, оперативная и управленческая программы выполняются в разных слотах. Полезный результат выдаётся после окончания подготовки; отмена не приносит награду. Фоновые MEFO, паранойя, настоящая эвакуация и политические системы DLC сохранены; старые две шкалы HRS 0.1 не используются.

## Восточный фронт: подготовка, кризис, адаптация

При первом оборонительном вступлении СССР в войну с Германией возникает новый кризис: организация −25%, её восстановление −25%, скорость планирования −35%, военный выпуск −20%, потребление снабжения +25%. Он длится 120 фактических дней войны; в мирное время опыт не накапливается. «Проверка мобилизационных округов» заранее смягчает кризис до −10% организации/выпуска и +10% снабжения. После острой фазы штраф ослабевает даже без реформ.

«Отчёты фронтов вместо сводок» закрепляют полную советскую адаптацию. После накопления опыта новые штрафы снимаются, а страна получает +25% восстановления организации, +35% планирования, +25% максимального плана, +10% военного выпуска и −10% снабжения. При советском наступлении дополнительной внезапности нет; опыт и реформа остаются доступны. Исходные ограничения Красной армии продолжают действовать по правилам DLC.

Германия во время войны с СССР получает зимние ограничения с ноября по март: без подготовки первая зима даёт +30% расхода снабжения, +75% зимнего истощения, −25% восстановления организации, −15% скорости и −30% планирования. «Единый моторный парк» смягчает кризис. «Континентальная система снабжения» вместе с 45 фактическими зимними днями войны снимает новые штрафы и даёт −40% зимнего истощения, +100% холодовой акклиматизации, −10% снабжения и +15% восстановления организации. Летом, в мирное время и после капитуляции сезонные штрафы убираются.

Заранее завершённые реформы запоминаются. Они не требуют повторного прохождения фокуса, но результат опыта включается после нужного числа военных/зимних дней. Ступени штрафов не складываются, повторное вступление в войну не выдаёт вторую награду. Это ежедневная проверка двух стран, поэтому изменение состояния может появиться на следующем игровом дне. Для версии 0.5 нужна новая кампания: старые сохранения не содержат истории новых счётчиков и контроля городов.

Награды основных реформ существенно усилены. Поздняя германская серийная школа даёт +35% выпуска и +25% предела эффективности ценой −15% её роста; гибкая школа — +28% выпуска, +40% роста и +35% сохранения эффективности. Советская промышленная семья достигает +25% выпуска, оборонная строительная школа — +45% военного строительства. «Слава Красной армии» дополнительно вводит постоянную реформу: +30% атаки, +25% защиты, +15% организации, +30% её восстановления, +8 п.п. подкрепления и −30% потерь опыта при пополнении. Это итоговая ступень семьи, она заменяет ранние ступени.

## Потеря городов и возвращение инициативы

Падение Минска, Киева, Ленинграда, Москвы, Сталинграда или Харькова в войне с Германией вызывает дополнительный кризис. Важен контроль самого города, а не всей области. Общий штраф имеет три ступени: до −22% организации, −30% восстановления, −25% военного выпуска и +30% потребления снабжения. Москва и Ленинград учитываются с двойным весом. Неразрешённый вклад города ослабевает через 90 фактических дней войны.

Региональные решения стоят 60–110 ПВ и требуют 45–75 дней. Одновременно готовится одно; его результат можно также получить соответствующим фокусом. Награда за город общая и одноразовая: 50–120 тысяч людских ресурсов, 2–4 военных завода на востоке при наличии места и исследовательские ускорения. При невозможности строительства выдаются промышленные исследования. Это новые мощности, а не повторение исходной эвакуации.

Ответы открывают 240-дневную мобилизационную волну: до +30% защиты, +35% восстановления, +20% выпуска, +10% организации, −30% времени обучения и +8 п.п. подкрепления. Усиление ступени не продлевает текущее окно. «Общесоюзный стратегический резерв» даёт первую волну и 120 тысяч людских ресурсов без потери городов.

Освобождение города один раз запускает 180-дневное восстановление: до +75% ремонта и +15% строительства. «Вернуть оперативную инициативу» после необходимых реформ и освобождения открывает одно 180-дневное наступательное окно: +25% атаки, +15% скорости и +25% восстановления организации. Повторная сдача города награды не обновляет. Полная таблица — `docs/EXPANSION_050_RU.md`.

Панель непрерывных фокусов перемещена ниже всех узлов и положительных условных смещений. Координаты записаны в `OVERHAUL_BUILD_REPORT.json`; схема теперь показывает и панель.

## Проверка и ограничения

Проверены структура файлов, ссылки, графы, локализация, упаковка и соответствие исходным ID. Работа предыдущей лёгкой версии подтверждена пользователем. ЭТА версия ещё не запускалась в HOI4: сетевой баланс, ответы ИИ и фактическая совместимость требуют тестовой партии.

Это масштабная интеграция и переработка фокусов, а не замена всех скрытых скриптов DLC. Исходные определения событий и фоновых систем пользователь не передавал, поэтому они используются через сохранённые игровые этапы. После обновления игры нужна новая сборка под изменившиеся исходные файлы.

Открой `preview/index.html` в браузере: это интерактивная схема фактических связей и координат сборки с поиском и масштабом. Она не заменяет проверку отображения в игре: скрытие политических веток и условные смещения рассчитывает движок HOI4.

Игроки могут договариваться о политических правилах и сроке начала большой войны; мод не навязывает победителя, автокапитуляцию, передачу чужой территории или безусловное принятие сделок противником. Переговорные войны и замена мирной конференции не реализованы.

Для ошибки пришли относящиеся к HRO строки `logs/error.log`, номер версии и описание шага. Для сетевой рассинхронизации нужны наблюдения от обоих игроков. Проверку лучше начать с нескольких месяцев за обе страны, затем с реформ и военного периода.

## Изменённые исходные этапы

'''
    for catalog in catalogs:
        text += f'\n### {catalog["tag"]}\n\n'
        for patch in catalog['native_patches']:
            description = patch.get('name_ru', patch['id'])
            text += '- ' + description + ' (`' + patch['id'] + '`)' + (f', стоимость {patch["cost"]} недель' if 'cost' in patch else '') + '.\n'
        text += '\n### Новые программы\n\n'
        for branch, title in BRANCH_TITLES.items():
            text += f'**{title[0]}:** ' + '; '.join(f['name_ru'] for f in catalog['focuses'] if f['branch'] == branch) + '.\n\n'
    return text


def audit_integrated_layout(game, preview, schematic):
    """Reject added overlaps without rejecting pre-existing hidden alternatives.

    This audits base positions, not engine-calculated branch visibility/offsets.
    A two-unit horizontal grid leaves room for the native focus card and icon.
    """
    counts = {}
    for tag, filename in (('GER', 'germany.txt'), ('SOV', 'soviet.txt')):
        data = schematic['countries'][tag]
        if data['new_vs_native_collision_candidates'] or data['new_vs_new_collisions']:
            conflicts = data['new_vs_native_collision_candidates'] + data['new_vs_new_collisions']
            raise ValueError(f'New focus base-layout overlaps: {tag}/{conflicts}')
        if panel := data.get('continuous_focus_panel'):
            if not panel['safe_below_all_focuses']:
                raise ValueError(f'Continuous focus panel can overlap the expanded tree: {tag}')
        original = parse((game / 'common/national_focus' / filename).read_text(encoding='utf-8-sig'))
        tree = next(n for n in original if n.key == 'focus_tree' and tree_tag(n) == tag)
        definitions = {n.scalar('id'): n for n in tree.all('focus')}
        before = preview.resolve_positions(definitions)
        after = data['positions']
        ids = list(definitions)
        def pairs(positions):
            return {(a, b) for i, a in enumerate(ids) for b in ids[i + 1:]
                    if abs(positions[a][0] - positions[b][0]) < 1.8
                    and abs(positions[a][1] - positions[b][1]) < .8}
        if introduced := pairs(after) - pairs(before):
            raise ValueError(f'Introduced native base-layout overlaps: {tag}/{sorted(introduced)}')
        counts[tag] = {'new_native_overlaps': 0, 'new_new_overlaps': 0,
                       'introduced_native_native_overlaps': 0,
                       'continuous_panel_below_focuses': bool(panel and panel['safe_below_all_focuses'])}
    return {'scope': 'base coordinates; native conditional offsets and visibility require engine review',
            'countries': counts}


def permanent_reform_envelopes(catalogs, adaptation):
    """Bound permanent HRO families plus earned war adaptation together.

    One tier/choice per family can be active. Temporary programmes and the
    native game's spirits, laws, traits and weather are outside this envelope.
    """
    limits = {'industrial_capacity_factory': (.65, max), 'army_org_factor': (.50, max),
              'supply_consumption_factor': (-.45, min), 'winter_attrition_factor': (-.80, min),
              'experience_loss_factor':(-.85,min), 'attrition':(-.80,min),
              'out_of_supply_factor':(-.75,min), 'army_attack_factor':(.70,max),
              'army_defence_factor':(1.0,max), 'land_reinforce_rate':(.20,max)}
    result = {}
    for catalog in catalogs:
        grouped = defaultdict(list)
        for idea in catalog['ideas']:
            grouped[idea['family']].append(idea['modifiers'])
        earned = adaptation.get('permanent_rewards', {}).get(catalog['tag'], {})
        totals = {key: sum(operation(values.get(key, 0) for values in family) for family in grouped.values())
                  + earned.get(key, 0) for key, (limit, operation) in limits.items()}
        for key, (limit, operation) in limits.items():
            if (totals[key] > limit + 1e-8 if operation is max else totals[key] < limit - 1e-8):
                raise ValueError(f'Combined permanent HRO bonus budget exceeded: {catalog["tag"]}/{key}/{totals[key]}')
        result[catalog['tag']] = {key: round(value, 6) for key, value in totals.items()}
    return {'scope': 'one active tier per country family plus earned war adaptation; excludes DLC and temporary programmes',
            'countries': result}


def build(game, output, catalog_dir=None, schema_dir=None):
    game, output = game.resolve(), output.resolve()
    catalog_dir = (catalog_dir or OVERHAUL / 'data').resolve()
    if output.exists():
        raise ValueError(f'Output already exists: {output}')
    if game == output or game in output.parents:
        raise ValueError('Output must be outside the game directory')
    catalogs = read_catalogs(catalog_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.hro-build-', dir=output.parent))
    try:
        report, offsets = native_overlay(stage, game, catalogs)
        author_country_content(stage, catalogs, offsets)
        author_rules(stage)
        gameplay_module = module('hro_gameplay_generator', OVERHAUL / 'tools/generate_gameplay.py')
        gameplay = gameplay_module.generate(stage)
        adaptation_module = module('hro_war_adaptation_generator', OVERHAUL / 'tools/generate_war_adaptation.py')
        war_adaptation = adaptation_module.generate(stage)
        emergency_module = module('hro_emergency_generator', OVERHAUL / 'tools/generate_emergency.py')
        city_geography = emergency_module.validate_geography(game)
        emergency = emergency_module.generate(stage)
        groups_module = module('hro_group_generator', OVERHAUL / 'tools/generate_groups.py')
        focus_groups = groups_module.generate(stage, catalogs)
        combined_rewards = permanent_reform_envelopes(catalogs, war_adaptation)
        put(stage, 'descriptor.mod', f'version="{VERSION}"\ntags={{ "Historical" "National Focuses" "Events" }}\nname="{NAME}"\nsupported_version="1.*"\n')
        report.update(version=VERSION, folder=FOLDER, native_background_systems='preserved',
                      target='1936-1946, two human opponents GER/SOV, all DLC', runtime_verified=False,
                      player_requirements={'players': 2, 'countries': ['GER', 'SOV'], 'campaign_end_year': 1946,
                                           'historical_default': True, 'allow_deviations': True, 'complexity': 'high'},
                      new_focus_counts={c['tag']: len(c['focuses']) for c in catalogs},
                      family_spirit_counts={c['tag']: len(c['ideas']) for c in catalogs}, gameplay=gameplay,
                      war_adaptation=war_adaptation,
                      city_emergency=emergency, city_geography=city_geography, focus_groups=focus_groups,
                      city_catalog_sha256=hashlib.sha256((OVERHAUL / 'data/cities.json').read_bytes()).hexdigest(),
                      permanent_reform_envelopes=combined_rewards,
                      country_catalog_sha256={c['tag']: hashlib.sha256((catalog_dir / (c['tag'].lower() + '.json')).read_bytes()).hexdigest() for c in catalogs})
        validator = module('hro_content_validator', OVERHAUL / 'tools/validate_overhaul.py')
        checks = validator.validate(stage, catalog_dir=catalog_dir, schema_dir=schema_dir)
        report['validation'] = checks
        put(stage, 'OVERHAUL_BUILD_REPORT.json', json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        preview = module('hro_tree_preview', OVERHAUL / 'tools/preview_trees.py')
        schematic = preview.generate(stage, stage / 'preview')
        report['layout_audit'] = audit_integrated_layout(game, preview, schematic)
        put(stage, 'OVERHAUL_BUILD_REPORT.json', json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        put(stage, 'README_RU.md', player_guide(catalogs, gameplay, report))
        documentation = OVERHAUL / 'docs'
        if documentation.is_dir():
            for path in sorted(documentation.glob('*.md')):
                put(stage, 'docs/' + path.name, path.read_text(encoding='utf-8'))
        stage.rename(output)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return report


def package(built, output):
    built, output = built.resolve(), output.resolve()
    if not (built / 'OVERHAUL_BUILD_REPORT.json').is_file():
        raise ValueError('Expected a validated overhaul build')
    if output.exists():
        raise ValueError(f'Archive already exists: {output}')
    if built == output or built in output.parents:
        raise ValueError('Archive must be outside the mod folder')
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor = (built / 'descriptor.mod').read_text(encoding='utf-8-sig').rstrip() + f'\npath="mod/{FOLDER}"\n'
    created = False
    try:
        with output.open('xb') as stream:
            created = True
            with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
                archive.writestr(FOLDER + '.mod', descriptor.encode('utf-8'))
                archive.writestr('INSTALL_RU.txt', (
                    f'{NAME} {VERSION}\n\n'
                    f'Распакуй {FOLDER} (папку) и {FOLDER}.mod (файл) в:\n'
                    'Документы/Paradox Interactive/Hearts of Iron IV/mod\n\n'
                    f'Выключи прежние версии и включи {NAME} {VERSION} в лаунчере.\n'
                    'При обновлении замени старую папку historical_reality_overhaul новой.\n'
                    'Оба игрока используют одинаковый архив, версию игры и DLC. Начните новую кампанию 1936 года.\n'
                    'В папку Steam ничего копировать не нужно. Python и установщик не нужны.\n'
                    f'Подробности и ограничения: {FOLDER}/README_RU.md\n'
                    'Новая версия прошла статические проверки, но ещё не проверена в игровом движке и сетевой партии.\n'
                ).encode('utf-8-sig'))
                for path in sorted(built.rglob('*')):
                    if path.is_symlink():
                        raise ValueError('Symlinks are not supported in the release')
                    if path.is_file():
                        archive.writestr(FOLDER + '/' + path.relative_to(built).as_posix(), path.read_bytes())
    except BaseException:
        if created:
            output.unlink(missing_ok=True)
        raise
    output.with_suffix('.zip.sha256').write_text(hashlib.sha256(output.read_bytes()).hexdigest() + '  ' + output.name + '\n', encoding='ascii')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--catalog-dir', type=Path)
    parser.add_argument('--schema-dir', type=Path)
    parser.add_argument('--archive', type=Path)
    args = parser.parse_args()
    try:
        report = build(args.game_dir, args.output_dir, args.catalog_dir, args.schema_dir)
        print('Build:', args.output_dir.resolve())
        print('New focuses:', report['new_focus_counts'], 'Native changes:', len(report['native_patches']))
        if args.archive:
            print('Archive:', package(args.output_dir, args.archive))
    except (ValueError, OSError, UnicodeError) as exc:
        print(f'Overhaul build stopped: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
