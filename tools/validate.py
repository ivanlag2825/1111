#!/usr/bin/env python3
"""Static checks for HRS. These checks do not emulate the HOI4 engine."""
import argparse
import json
from pathlib import Path
import re
import sys
from clausewitz import parse, walk

ROOT = Path(__file__).resolve().parents[1]


def validate(root, schema=None, built=False):
    errors = []
    documents = {}
    for p in sorted(root.rglob('*.txt')):
        try:
            documents[p.relative_to(root).as_posix()] = parse(p.read_text(encoding='utf-8-sig'))
        except (ValueError, UnicodeError) as exc:
            errors.append(f'{p}: {exc}')
    all_nodes = [n for nodes in documents.values() for n in walk(nodes)]
    focus_nodes = [n for nodes in documents.values() for n in nodes
                   if n.key == 'shared_focus' and isinstance(n.value, list) and str(n.scalar('id', '')).startswith('hrs_')]
    focus_ids = [n.scalar('id') for n in focus_nodes]
    if len(focus_ids) != 50 or len(set(focus_ids)) != 50:
        errors.append(f'Expected 50 unique authored focuses; found {len(focus_ids)}')
    graph = {}
    for n in focus_nodes:
        graph[n.scalar('id')] = [c.scalar('focus') for c in n.all('prerequisite')]
        if float(n.scalar('cost', '0')) <= 0:
            errors.append(f'Non-positive focus duration: {n.scalar("id")}')
        for edge in graph[n.scalar('id')]:
            if edge not in focus_ids:
                errors.append(f'Missing prerequisite: {edge}')
    def visit(node, path):
        if node in path:
            errors.append(f'Focus cycle: {node}')
            return
        for parent in graph.get(node, []):
            visit(parent, path + (node,))
    for identity in graph:
        visit(identity, ())
    authored = {p: nodes for p, nodes in documents.items() if Path(p).name.startswith('hrs_')}
    nodes = [n for ns in authored.values() for n in walk(ns)]
    event_nodes = [n for ns in authored.values() for n in ns if n.key == 'country_event']
    events = {n.scalar('id') for n in event_nodes}
    idea_ids = set()
    for ns in authored.values():
        for root_node in ns:
            if root_node.key == 'ideas':
                country = root_node.one('country')
                idea_ids |= {n.key for n in country.value}
    effect_ids = {n.key for p, ns in authored.items() if p.startswith('common/scripted_effects/') for n in ns}
    trigger_ids = {n.key for p, ns in authored.items() if p.startswith('common/scripted_triggers/') for n in ns}
    # Generated evacuation state triggers exist only in the installed build.
    if not built:
        trigger_ids |= {'hrs_evacuation_west_state', 'hrs_evacuation_east_state'}
    for n in nodes:
        if n.key == 'country_event' and isinstance(n.value, list):
            event_id = n.scalar('id')
            if event_id and event_id.startswith('hrs.') and event_id not in events:
                errors.append(f'Unknown event: {event_id}')
        if n.key in ('add_ideas', 'remove_ideas') and isinstance(n.value, str) and n.value.startswith('hrs_') and n.value not in idea_ids:
            errors.append(f'Unknown idea: {n.value}')
        if n.key == 'add_timed_idea' and n.scalar('idea') not in idea_ids:
            errors.append(f'Unknown timed idea: {n.scalar("idea")}')
        if n.key in ('has_completed_focus', 'focus') and isinstance(n.value, str) and n.value.startswith('hrs_') and n.value not in focus_ids:
            errors.append(f'Unknown focus: {n.value}')
        if n.key == 'has_idea' and isinstance(n.value, str) and n.value.startswith('hrs_') and n.value not in idea_ids:
            errors.append(f'Unknown idea condition: {n.value}')
        if n.key == 'exists' and n.value not in ('yes', 'no'):
            errors.append(f'Country existence must use a country scope, not exists = {n.value}')
        if n.key in ('add_army_experience', 'political_power'):
            errors.append(f'Unsupported script keyword: {n.key}')
        if n.key == 'state' and isinstance(n.value, str) and not n.value.isdigit():
            errors.append(f'Invalid evacuation state: {n.value}')
    for event in event_nodes:
        if event.scalar('is_triggered_only') != 'yes' or event.scalar('fire_only_once') != 'yes':
            errors.append(f'Event must be triggered and one-shot: {event.scalar("id")}')
        if not event.all('option'):
            errors.append(f'Event has no choices: {event.scalar("id")}')

    required_loc = set(focus_ids) | {i + '_desc' for i in focus_ids} | idea_ids | {i + '_desc' for i in idea_ids}
    for n in nodes:
        if n.key in ('title', 'desc', 'text', 'name', 'group') and isinstance(n.value, str) and n.value.startswith(('hrs', 'HRS_')):
            required_loc.add(n.value)
    for p, ns in authored.items():
        if p.startswith('common/decisions/'):
            for category in ns:
                required_loc |= {category.key, category.key + '_desc'}
                if isinstance(category.value, list):
                    for d in category.value:
                        if d.key and d.key.startswith('hrs_'):
                            required_loc |= {d.key, d.key + '_desc'}
    localisations = {}
    for lang in ('russian', 'english'):
        keys = {}
        for p in (root / 'localisation' / lang).glob('*.yml'):
            data = p.read_bytes()
            if not data.startswith(b'\xef\xbb\xbf'):
                errors.append(f'Localisation missing UTF-8 BOM: {p.name}')
            lines = data.decode('utf-8-sig').splitlines()
            if not lines or lines[0] != 'l_' + lang + ':':
                errors.append(f'Incorrect language header: {p.name}')
            for line in lines[1:]:
                m = re.fullmatch(r' ([A-Za-z0-9_.]+):0 (".*")', line)
                if not m:
                    errors.append(f'Malformed localisation line: {p.name}: {line[:80]}')
                    continue
                if m[1] in keys:
                    errors.append(f'Duplicate localisation key: {m[1]}')
                try:
                    keys[m[1]] = json.loads(m[2])
                except json.JSONDecodeError:
                    errors.append(f'Invalid quoted localisation: {m[1]}')
        localisations[lang] = keys
        for missing in sorted(required_loc - keys.keys()):
            errors.append(f'Missing {lang} localisation: {missing}')
    if set(localisations['english']) != set(localisations['russian']):
        errors.append('English/Russian localisation key sets differ')

    # Optional upstream keyword audit: a subset, not a full CWTools type/scope pass.
    if schema:
        schema_text = '\n'.join(p.read_text(encoding='utf-8-sig') for p in (schema / 'Config').rglob('*.cwt'))
        known_effects = set(re.findall(r'alias\[effect:([A-Za-z_][A-Za-z0-9_]*)\]', schema_text)) | effect_ids
        known_triggers = set(re.findall(r'alias\[trigger:([A-Za-z_][A-Za-z0-9_]*)\]', schema_text)) | trigger_ids | {'arms_factory'}
        countries = {'GER', 'SOV', 'AUS', 'ENG', 'USA', 'FIN', 'JAP', 'ROOT', 'FROM', 'PREV'}
        containers = {'AND', 'OR', 'NOT', 'any_owned_state', 'any_controlled_state'}
        def triggers(ns):
            for n in ns:
                if n.key in countries | containers:
                    if isinstance(n.value, list):
                        triggers(n.value)
                elif n.key not in known_triggers:
                    errors.append(f'Unknown upstream trigger keyword: {n.key}')
        def effects(ns):
            for n in ns:
                if n.key == 'limit':
                    triggers(n.value)
                elif n.key in countries | {'if', 'else_if', 'else', 'random_owned_controlled_state'}:
                    if isinstance(n.value, list):
                        effects(n.value)
                elif n.key not in known_effects:
                    errors.append(f'Unknown upstream effect keyword: {n.key}')
        for p, ns in authored.items():
            if p.startswith('common/scripted_effects/'):
                for n in ns:
                    effects(n.value)
            if p.startswith('common/scripted_triggers/'):
                for n in ns:
                    triggers(n.value)
            for n in walk(ns):
                if n.key in ('available', 'visible', 'allowed', 'trigger', 'target_trigger') and isinstance(n.value, list):
                    triggers(n.value)
                if n.key in ('completion_reward', 'complete_effect', 'effect') and isinstance(n.value, list):
                    effects(n.value)
                if n.key == 'option' and isinstance(n.value, list) and n.one('ai_chance'):
                    effects([x for x in n.value if x.key not in ('name', 'trigger', 'ai_chance')])
        # Modifier names with <building> substitution are expanded for the ones used here.
        known_mods = set(re.findall(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:country|army|aggressive|defensive)\s*$', schema_text, re.M))
        known_mods |= {'production_speed_arms_factory_factor', 'production_speed_industrial_complex_factor'}
        for p, ns in authored.items():
            if p.startswith('common/ideas/'):
                for n in walk(ns):
                    if n.key == 'modifier':
                        for mod in n.value:
                            if mod.key not in known_mods:
                                errors.append(f'Unknown upstream idea modifier: {mod.key}')
    if built:
        for path in root.rglob('*.txt'):
            if '@HRS_' in path.read_text(encoding='utf-8-sig'):
                errors.append(f'Unresolved build placeholder: {path.name}')
        attached = {'GER': 0, 'SOV': 0}
        for ns in documents.values():
            for n in walk(ns):
                if n.key == 'shared_focus' and isinstance(n.value, str) and n.value.startswith('hrs_'):
                    for tag in attached:
                        if n.value.startswith('hrs_' + tag.lower() + '_'):
                            attached[tag] += 1
        if any(count < 25 for count in attached.values()):
            errors.append(f'New branches not attached to both original trees: {attached}')
    if errors:
        raise ValueError('\n'.join(sorted(set(errors))))
    decisions = sum(1 for p, ns in authored.items() if p.startswith('common/decisions/') and '/categories/' not in p
                    for cat in ns for n in cat.value if isinstance(n.value, list))
    return {'script_files': len(documents), 'focuses': len(focus_ids), 'events': len(events),
            'decisions': decisions, 'ideas': len(idea_ids), 'localisation_keys_per_language': len(localisations['russian'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mod-dir', type=Path, default=ROOT / 'mod')
    parser.add_argument('--schema-dir', type=Path)
    parser.add_argument('--built', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(validate(args.mod_dir, args.schema_dir, args.built), ensure_ascii=False))
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
