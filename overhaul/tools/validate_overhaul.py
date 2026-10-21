#!/usr/bin/env python3
"""Static contracts for HRO data and built scripts; does not emulate HOI4."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import re
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'tools'))
from clausewitz import parse, walk

PREFIX = 'hro_'
COUNTRIES = ('GER', 'SOV')
BRANCHES = {'industry', 'army', 'logistics', 'air', 'navy', 'state', 'diplomacy', 'war'}
TOLERANCE = 1e-8


def _scalar_values(node):
    if isinstance(node.value, str):
        return [node.value]
    return [n.value for n in node.value if isinstance(n.value, str)]


def _signature(node):
    return (node.key, node.op, tuple(_signature(n) for n in node.value)
            if isinstance(node.value, list) else node.value)


def _country(tree):
    country = tree.one('country')
    found = set()
    if country is None:
        return None
    def visit(nodes):
        for n in nodes:
            if n.key in ('tag', 'original_tag') and n.value in COUNTRIES:
                found.add(n.value)
            elif n.key in ('modifier', 'OR', 'AND') and isinstance(n.value, list):
                visit(n.value)
    visit(country.value)
    return next(iter(found)) if len(found) == 1 else None


def _groups(focus):
    return [tuple(n.value for n in block.all('focus') if isinstance(n.value, str))
            for block in focus.all('prerequisite')]


def _mutex(focus):
    return {n.value for block in focus.all('mutually_exclusive') for n in block.all('focus')
            if isinstance(n.value, str)}


def _position(identity, focuses, cache=None, pending=None):
    """Resolve base focus coordinates, including anchors in retained trees.

    Native ``offset`` blocks move whole conditional branches at runtime. This
    helper intentionally describes their base positions; it does not claim to
    emulate the focus-tree UI or country-dependent branch visibility.
    """
    cache = {} if cache is None else cache
    pending = set() if pending is None else pending
    if identity in cache:
        return cache[identity]
    if identity not in focuses:
        raise ValueError(f'Unknown focus layout anchor: {identity}')
    if identity in pending:
        raise ValueError(f'Focus layout anchor cycle: {identity}')
    pending.add(identity)
    focus = focuses[identity]
    try:
        x, y = float(focus.scalar('x', '0')), float(focus.scalar('y', '0'))
    except (TypeError, ValueError):
        raise ValueError(f'Non-numeric focus coordinates: {identity}') from None
    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError(f'Non-finite focus coordinates: {identity}')
    anchor = focus.scalar('relative_position_id')
    if anchor:
        anchor_x, anchor_y = _position(anchor, focuses, cache, pending)
        x, y = x + anchor_x, y + anchor_y
    pending.remove(identity)
    cache[identity] = (x, y)
    return cache[identity]


def _compatible_plan(target, groups, exclusions, forbidden=frozenset(), max_states=40000):
    """Find a structurally possible completion plan, including OR alternatives.

    Availability dates, country flags and native event outcomes are deliberately
    outside this model. A result proves prerequisite compatibility only.
    """
    states = 0
    seen = set()

    def solve(chosen, pending):
        nonlocal states
        states += 1
        if states > max_states:
            raise ValueError(f'Prerequisite solver budget exceeded for {target}')
        cleaned = []
        banned = set(forbidden)
        for node in chosen:
            banned.update(exclusions.get(node, ()))
        if chosen & banned:
            return None
        for group in pending:
            if any(n in chosen for n in group):
                continue
            options = tuple(n for n in group if n not in banned)
            if not options:
                return None
            cleaned.append(options)
        if not cleaned:
            return chosen
        key = (frozenset(chosen), tuple(sorted(cleaned)))
        if key in seen:
            return None
        seen.add(key)
        cleaned.sort(key=lambda x: (len(x), x))
        first, rest = cleaned[0], cleaned[1:]
        for option in first:
            result = solve(chosen | {option}, rest + list(groups.get(option, ())))
            if result is not None:
                return result
        return None

    if target in forbidden:
        return None
    return solve(set(), [(target,)])


def _idea_trigger(nodes, state):
    """Evaluate only the documented boolean guard language of family setters."""
    def one(node):
        if node.key in ('AND', 'limit'):
            return _idea_trigger(node.value, state)
        if node.key == 'OR':
            return any(one(n) for n in node.value)
        if node.key == 'NOT':
            return not _idea_trigger(node.value, state)
        if node.key == 'has_idea':
            return node.value in state
        if node.key == 'always':
            return node.value == 'yes'
        raise ValueError(f'Unsupported family-setter guard: {node.key}')
    return all(one(n) for n in nodes)


def _run_idea_setter(nodes, state, effect_defs, stack=()):
    """Execute idea operations and simple guards for monotonicity contracts."""
    state = set(state)
    prior_matched = False
    for n in nodes:
        if n.key == 'if':
            condition = n.one('limit')
            matched = condition is None or _idea_trigger(condition.value, state)
            if matched:
                state = _run_idea_setter([x for x in n.value if x.key != 'limit'], state, effect_defs, stack)
            prior_matched = matched
        elif n.key == 'else_if':
            condition = n.one('limit')
            matched = not prior_matched and (condition is None or _idea_trigger(condition.value, state))
            if matched:
                state = _run_idea_setter([x for x in n.value if x.key != 'limit'], state, effect_defs, stack)
            prior_matched = prior_matched or matched
        elif n.key == 'else':
            if not prior_matched:
                state = _run_idea_setter(n.value, state, effect_defs, stack)
            prior_matched = True
        elif n.key == 'remove_ideas':
            state.difference_update(_scalar_values(n))
        elif n.key == 'add_ideas':
            state.update(_scalar_values(n))
        elif n.key in ('hidden_effect', 'effect_tooltip'):
            if n.key == 'hidden_effect':
                state = _run_idea_setter(n.value, state, effect_defs, stack)
        elif n.key in effect_defs and n.value == 'yes':
            if n.key in stack:
                raise ValueError(f'Recursive family setter: {n.key}')
            state = _run_idea_setter(effect_defs[n.key].value, state, effect_defs, stack + (n.key,))
        elif n.key not in ('custom_effect_tooltip', 'show_ideas_tooltip', 'log'):
            raise ValueError(f'Unsupported operation in family setter: {n.key}')
    return state


def _read_localisation(root, errors):
    result = {}
    for language in ('russian', 'english'):
        keys = {}
        paths = sorted((root / 'localisation' / language).glob('*.yml'))
        if not paths:
            errors.append(f'No {language} localisation files')
        for path in paths:
            raw = path.read_bytes()
            if not raw.startswith(b'\xef\xbb\xbf'):
                errors.append(f'Localisation missing UTF-8 BOM: {path.name}')
            try:
                lines = raw.decode('utf-8-sig').splitlines()
            except UnicodeError as exc:
                errors.append(f'Invalid UTF-8 localisation {path.name}: {exc}')
                continue
            if not lines or lines[0].strip() != 'l_' + language + ':':
                errors.append(f'Incorrect localisation language header: {path.name}')
            for number, line in enumerate(lines[1:], 2):
                if not line.strip() or line.lstrip().startswith('#'):
                    continue
                match = re.fullmatch(r'\s*([A-Za-z0-9_.-]+):\d+\s+(".*")\s*', line)
                if not match:
                    errors.append(f'Malformed localisation: {path.name}:{number}')
                    continue
                key, quoted = match.groups()
                if key in keys:
                    errors.append(f'Duplicate {language} localisation key: {key}')
                try:
                    keys[key] = json.loads(quoted)
                except json.JSONDecodeError:
                    errors.append(f'Invalid quoted localisation: {path.name}:{number}: {key}')
        result[language] = keys
    if set(result['russian']) != set(result['english']):
        errors.append('Russian/English localisation key sets differ')
    return result


def _catalogues(directory, errors):
    if directory is None:
        return []
    result = []
    for country in ('ger', 'sov'):
        path = directory / (country + '.json')
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            errors.append(f'Cannot read catalogue {path.name}: {exc}')
            continue
        if data.get('tag') != country.upper():
            errors.append(f'Incorrect catalogue tag: {path.name}')
        for field in ('focuses', 'ideas', 'native_patches'):
            if not isinstance(data.get(field), list):
                errors.append(f'Catalogue {path.name} requires list {field}')
                data[field] = []
        result.append(data)
    return result


def _keyword_audit(own_docs, all_focuses, effect_defs, trigger_defs, schema, errors):
    config = schema / 'Config'
    if not config.is_dir():
        errors.append(f'CWTools Config directory missing: {config}')
        return
    text = '\n'.join(p.read_text(encoding='utf-8-sig') for p in config.rglob('*.cwt'))
    effect_keys = set(re.findall(r'alias\[effect:([A-Za-z_][A-Za-z0-9_]*)\]', text)) | set(effect_defs)
    trigger_keys = set(re.findall(r'alias\[trigger:([A-Za-z_][A-Za-z0-9_]*)\]', text)) | set(trigger_defs)
    trigger_keys |= {'arms_factory', 'industrial_complex', 'dockyard', 'infrastructure', 'rail_way', 'supply_node'}
    # Calls already used by retained native trees are valid external interfaces.
    for focus in all_focuses.values():
        if str(focus.scalar('id', '')).startswith(PREFIX):
            continue
        for n in walk(focus.value):
            if n.key and n.key.startswith(('GER_', 'SOV_')) and n.value in ('yes', 'no'):
                effect_keys.add(n.key)
                trigger_keys.add(n.key)
    scope = re.compile(r'(?:[A-Z]{3}|ROOT|FROM|FROM\.FROM|PREV|THIS|\d+)\Z')
    trigger_containers = {'AND', 'OR', 'NOT', 'if', 'else_if', 'else', 'limit'}
    def triggers(nodes):
        for n in nodes:
            if n.key in trigger_containers or (n.key and scope.fullmatch(n.key)) or (n.key and n.key.startswith(('any_', 'all_'))):
                if isinstance(n.value, list):
                    triggers(n.value)
            elif n.key in ('custom_trigger_tooltip', 'hidden_trigger'):
                triggers([x for x in n.value if x.key not in ('tooltip', 'tooltip_evaluation')])
            elif n.key not in trigger_keys:
                errors.append(f'Unknown upstream trigger keyword: {n.key}')
    effect_containers = {'if', 'else_if', 'else', 'hidden_effect', 'effect_tooltip', 'while_loop_effect'}
    def effects(nodes):
        for n in nodes:
            if n.key == 'limit':
                triggers(n.value)
            elif n.key in effect_containers or (n.key and scope.fullmatch(n.key)) or (n.key and n.key.startswith(('every_', 'random_')) and isinstance(n.value, list) and n.key != 'random_list'):
                if isinstance(n.value, list):
                    effects([x for x in n.value if x.key not in ('random_select_amount', 'prioritize', 'order_by')])
            elif n.key not in effect_keys:
                errors.append(f'Unknown upstream effect keyword: {n.key}')
    for path, roots in own_docs.items():
        if path.startswith('common/scripted_effects/'):
            for root in roots:
                effects(root.value)
        if path.startswith('common/scripted_triggers/'):
            for root in roots:
                triggers(root.value)
        for n in walk(roots):
            if n.key in ('available', 'visible', 'allowed', 'trigger', 'target_trigger', 'cancel_trigger', 'remove_trigger') and isinstance(n.value, list):
                triggers(n.value)
            if n.key in ('completion_reward', 'complete_effect', 'remove_effect', 'cancel_effect', 'select_effect', 'effect', 'immediate') and isinstance(n.value, list):
                effects(n.value)
            if path.startswith('events/') and n.key == 'option' and isinstance(n.value, list) and n.scalar('name'):
                effects([x for x in n.value if x.key not in ('name', 'trigger', 'ai_chance', 'highlight')])
    modifier_keys = set(re.findall(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:country|army|aggressive|defensive|naval|air|state)\s*$', text, re.M))
    buildings = ('arms_factory', 'industrial_complex', 'dockyard', 'infrastructure', 'rail_way', 'supply_node', 'air_base', 'anti_air', 'radar_station', 'fuel_silo', 'synthetic_refinery', 'bunker', 'coastal_bunker')
    modifier_keys.update('production_speed_' + b + '_factor' for b in buildings)
    for path, roots in own_docs.items():
        if not path.startswith('common/ideas/'):
            continue
        for n in walk(roots):
            if n.key == 'modifier' and isinstance(n.value, list):
                for modifier in n.value:
                    if modifier.key not in modifier_keys:
                        errors.append(f'Unknown upstream idea modifier: {modifier.key}')


def validate(mod_dir: Path, catalog_dir: Path | None = None, schema_dir: Path | None = None) -> dict:
    root = Path(mod_dir)
    errors, warnings = [], []
    if not root.is_dir():
        raise ValueError(f'Mod directory does not exist: {root}')
    documents = {}
    for path in sorted(root.rglob('*.txt')):
        relative = path.relative_to(root).as_posix()
        if not relative.startswith(('common/', 'events/', 'history/')):
            continue
        try:
            text = path.read_text(encoding='utf-8-sig')
            if re.search(r'@(?:HRO|HRS)_[A-Z_]+@|\{\{[^}]+\}\}', text):
                errors.append(f'Unresolved build placeholder: {relative}')
            documents[relative] = parse(text)
        except (ValueError, UnicodeError) as exc:
            errors.append(f'Cannot parse {relative}: {exc}')
    if not documents:
        errors.append('No mod scripts found')
    own_docs = {p: ns for p, ns in documents.items() if Path(p).name.startswith(PREFIX)}
    all_focuses, own_focuses = {}, {}
    effect_defs, trigger_defs, ideas, events, decisions = {}, {}, {}, {}, {}
    rules = set()
    trees = []
    required_loc = set()
    for path, roots in documents.items():
        for n in walk(roots):
            if n.key in ('focus', 'shared_focus', 'joint_focus') and isinstance(n.value, list) and n.scalar('id'):
                identity = n.scalar('id')
                if identity in all_focuses:
                    errors.append(f'Duplicate focus ID: {identity}')
                all_focuses[identity] = n
                if identity.startswith(PREFIX):
                    own_focuses[identity] = n
                    required_loc.update((identity, identity + '_desc'))
        for n in roots:
            if n.key == 'focus_tree':
                trees.append(n)
        if path not in own_docs:
            continue
        if path.startswith('common/scripted_effects/'):
            for n in roots:
                if n.key in effect_defs:
                    errors.append(f'Duplicate scripted effect: {n.key}')
                effect_defs[n.key] = n
        if path.startswith('common/scripted_triggers/'):
            for n in roots:
                if n.key in trigger_defs:
                    errors.append(f'Duplicate scripted trigger: {n.key}')
                trigger_defs[n.key] = n
        if path.startswith('common/ideas/'):
            for top in roots:
                if top.key != 'ideas' or not isinstance(top.value, list):
                    continue
                for group in top.value:
                    if not isinstance(group.value, list):
                        continue
                    for idea in group.value:
                        if not idea.key or not idea.key.startswith(PREFIX):
                            continue
                        if idea.key in ideas:
                            errors.append(f'Duplicate idea ID: {idea.key}')
                        ideas[idea.key] = idea
                        required_loc.update((idea.key, idea.key + '_desc'))
        if path.startswith('events/'):
            for event in roots:
                if event.key not in ('country_event', 'news_event', 'state_event') or not isinstance(event.value, list):
                    continue
                identity = event.scalar('id')
                if identity in events:
                    errors.append(f'Duplicate event ID: {identity}')
                events[identity] = event
                if event.scalar('is_triggered_only') != 'yes' or event.scalar('fire_only_once') != 'yes':
                    errors.append(f'Event must be triggered and one-shot: {identity}')
                options = event.all('option')
                if not options:
                    errors.append(f'Event has no options: {identity}')
                elif not any(option.one('trigger') is None for option in options):
                    errors.append(f'Event needs an unconditional fallback option: {identity}')
        if path.startswith('common/decisions/'):
            for category in roots:
                if not category.key or not category.key.startswith(PREFIX):
                    continue
                required_loc.update((category.key, category.key + '_desc'))
                if '/categories/' in path:
                    continue
                for decision in category.value:
                    if not decision.key or not decision.key.startswith(PREFIX):
                        continue
                    if decision.key in decisions:
                        errors.append(f'Duplicate decision ID: {decision.key}')
                    decisions[decision.key] = decision
                    required_loc.update((decision.key, decision.key + '_desc'))
                    duration = decision.scalar('days_remove')
                    if duration is not None and float(duration) > 0 and decision.one('remove_effect') is None:
                        errors.append(f'Timed programme missing remove_effect: {decision.key}')
                    if decision.one('cancel_trigger') is not None and duration is not None and decision.one('cancel_effect') is None:
                        errors.append(f'Cancellable programme missing cancel_effect: {decision.key}')
        if path.startswith('common/game_rules/'):
            rules.update(n.key for n in roots)

    if not own_focuses:
        errors.append('No authored overhaul focuses found')
    # All hro_* country flags belong to this mod. A misspelled unlock flag can
    # otherwise leave a whole programme permanently hidden despite valid syntax.
    written_flags, required_flags = set(), set()
    for path, roots in documents.items():
        for node in walk(roots):
            if node.key not in ('set_country_flag', 'has_country_flag'):
                continue
            value = node.value if isinstance(node.value, str) else node.scalar('flag', '')
            if isinstance(value, str) and value.startswith(PREFIX):
                (written_flags if node.key == 'set_country_flag' else required_flags).add(value)
    for flag in sorted(required_flags - written_flags):
        errors.append(f'Overhaul country flag is read but never set: {flag}')
    groups = {identity: _groups(f) for identity, f in all_focuses.items()}
    exclusions = {identity: _mutex(f) for identity, f in all_focuses.items()}
    for identity, focus in all_focuses.items():
        if identity in own_focuses:
            try:
                if float(focus.scalar('cost', '0')) <= 0:
                    errors.append(f'Non-positive focus duration: {identity}')
            except ValueError:
                errors.append(f'Non-numeric authored focus duration: {identity}')
            if not groups[identity] or any(not g for g in groups[identity]):
                errors.append(f'Authored focus needs nonempty prerequisite groups: {identity}')
        for group in groups[identity]:
            for reference in group:
                if reference not in all_focuses:
                    errors.append(f'Unknown prerequisite {reference} in {identity}')
        for other in exclusions[identity]:
            if other not in all_focuses:
                errors.append(f'Unknown mutually exclusive focus {other} in {identity}')
            elif identity not in exclusions.get(other, ()):
                errors.append(f'Asymmetric mutually exclusive pair: {identity} / {other}')
        if identity in own_focuses and (focus.one('completion_reward') is None or not focus.one('completion_reward').value):
            errors.append(f'Focus has no completion reward: {identity}')
        elif identity in own_focuses and any(n.key == 'add_political_power' for n in walk(focus.one('completion_reward').value)):
            functional = {'add_tech_bonus','add_building_construction','add_research_slot','add_manpower',
                          'army_experience','air_experience','navy_experience','add_ideas','add_timed_idea',
                          'add_stability','add_war_support','country_event'}
            if not any(n.key in functional or (n.key and n.key.startswith('hro_') and n.value == 'yes')
                       for n in walk(focus.one('completion_reward').value)):
                errors.append(f'Authored focus offers only political power or flags: {identity}')
    visited, visiting = set(), set()
    def cycle(identity):
        if identity in visiting:
            errors.append(f'Focus prerequisite cycle: {identity}')
            return
        if identity in visited:
            return
        visiting.add(identity)
        for group in groups.get(identity, ()):
            for parent in group:
                if parent in all_focuses:
                    cycle(parent)
        visiting.remove(identity)
        visited.add(identity)
    for identity in all_focuses:
        cycle(identity)
    if not any('cycle:' in e or 'Unknown prerequisite' in e for e in errors):
        for identity in all_focuses:
            try:
                if _compatible_plan(identity, groups, exclusions) is None:
                    errors.append(f'Unreachable focus due to incompatible prerequisites: {identity}')
            except ValueError as exc:
                errors.append(str(exc))

    attached = defaultdict(set)
    for tree in trees:
        tag = _country(tree)
        tree_refs = [n.value for n in tree.all('shared_focus') if isinstance(n.value, str) and n.value.startswith(PREFIX)]
        for reference, count in Counter(tree_refs).items():
            if count > 1:
                errors.append(f'Duplicate shared focus attachment: {reference}')
            if reference not in own_focuses:
                errors.append(f'Unknown attached focus: {reference}')
            elif tag and not reference.startswith('hro_' + tag.lower() + '_'):
                errors.append(f'Focus attached to wrong country: {reference} / {tag}')
            if tag:
                attached[tag].add(reference)
    for identity in own_focuses:
        tag = next((t for t in COUNTRIES if identity.startswith('hro_' + t.lower() + '_')), None)
        if tag is None:
            errors.append(f'Unknown country prefix on authored focus: {identity}')
        elif identity not in attached[tag]:
            errors.append(f'Authored focus not attached to {tag} tree: {identity}')

    for path, roots in documents.items():
        for n in walk(roots):
            own_context = path in own_docs
            if n.key and n.key.startswith(PREFIX) and n.value in ('yes', 'no') and n.key not in effect_defs and n.key not in trigger_defs:
                errors.append(f'Unknown overhaul scripted call: {n.key}')
            if not own_context and not (isinstance(n.value, str) and n.value.startswith(('hro_', 'hro.'))):
                continue
            if n.key in ('add_ideas', 'remove_ideas', 'has_idea', 'show_ideas_tooltip'):
                for value in _scalar_values(n):
                    if value.startswith(PREFIX) and value not in ideas:
                        errors.append(f'Unknown overhaul idea: {value}')
            if n.key == 'add_timed_idea' and isinstance(n.value, list):
                value = n.scalar('idea', '')
                if value.startswith(PREFIX) and value not in ideas:
                    errors.append(f'Unknown timed overhaul idea: {value}')
            if n.key in ('country_event', 'news_event', 'state_event'):
                value = n.scalar('id', '') if isinstance(n.value, list) else n.value
                if isinstance(value, str) and value.startswith('hro.') and value not in events:
                    errors.append(f'Unknown overhaul event: {value}')
            if n.key in ('has_completed_focus', 'relative_position_id', 'focus') and isinstance(n.value, str):
                value = n.value
                if value.startswith(('hro_', 'GER_', 'SOV_')) and value not in all_focuses:
                    errors.append(f'Unknown focus reference: {value}')
            if own_context and n.key == 'exists' and n.value not in ('yes', 'no'):
                errors.append(f'Existence needs a country scope, not exists = {n.value}')
            if own_context and n.key in ('add_army_experience', 'political_power'):
                errors.append(f'Unsupported script keyword: {n.key}')
            if own_context and n.key in ('declare_war_on', 'annex_country', 'transfer_state'):
                errors.append(f'New programme forcibly changes war/territory: {n.key}')
            if own_context and n.key in ('title', 'desc', 'text', 'name', 'group', 'custom_effect_tooltip', 'tooltip', 'custom_cost_text') and isinstance(n.value, str) and n.value.startswith(('hro', 'HRO_')):
                required_loc.add(n.value)
            if n.key == 'unlock_decision_tooltip' and isinstance(n.value, list):
                value = n.scalar('decision', '')
                if value.startswith(PREFIX) and value not in decisions:
                    errors.append(f'Unknown overhaul decision: {value}')
            if own_context and n.key == 'has_game_rule' and isinstance(n.value, list):
                value = n.scalar('rule', '')
                if value.startswith('HRO_') and value not in rules:
                    errors.append(f'Unknown overhaul game rule: {value}')

    catalogues = _catalogues(Path(catalog_dir) if catalog_dir is not None else None, errors)
    expected_focuses, catalog_ideas, patch_count = {}, {}, 0
    integrated_count, graph_patch_count = 0, 0
    position_cache = {}
    for catalogue in catalogues:
        tag = catalogue.get('tag')
        occupied = {}
        for focus in catalogue['focuses']:
            identity = focus.get('id', '')
            if identity in expected_focuses:
                errors.append(f'Duplicate catalogue focus ID: {identity}')
            expected_focuses[identity] = focus
            if not identity.startswith('hro_' + str(tag).lower() + '_'):
                errors.append(f'Incorrect catalogue country prefix: {identity}')
            if focus.get('branch') not in BRANCHES:
                errors.append(f'Unknown catalogue branch: {identity}')
            explicit = 'x' in focus or 'y' in focus or 'relative_position_id' in focus
            if explicit:
                if any(not isinstance(focus.get(k), (int, float)) or isinstance(focus.get(k), bool)
                       or not math.isfinite(focus[k]) for k in ('x', 'y')):
                    errors.append(f'Invalid focus layout coordinates: {identity}')
                if focus.get('relative_position_id') is not None and not isinstance(focus['relative_position_id'], str):
                    errors.append(f'Invalid focus layout anchor: {identity}')
                position = ('invalid_explicit_layout', identity)
                if identity in own_focuses:
                    try:
                        position = ('resolved',) + _position(identity, all_focuses, position_cache)
                    except ValueError as exc:
                        errors.append(str(exc))
            else:
                if focus.get('lane', 0) not in (-1, 0, 1) or not isinstance(focus.get('row'), int) or focus.get('row', 0) <= 0:
                    errors.append(f'Invalid focus layout row/lane: {identity}')
                position = (focus.get('branch'), focus.get('row'), focus.get('lane', 0))
            if position in occupied:
                errors.append(f'Overlapping catalogue focus positions: {occupied[position]} / {identity}')
            occupied[position] = identity
            for key in ('name_ru', 'name_en', 'desc_ru', 'desc_en'):
                if not focus.get(key):
                    errors.append(f'Missing catalogue {key}: {identity}')
            if identity in own_focuses:
                actual = own_focuses[identity]
                expected_groups = {tuple(sorted(group)) for group in focus.get('prerequisites', [])}
                actual_groups = {tuple(sorted(group)) for group in groups[identity]}
                if expected_groups != actual_groups:
                    errors.append(f'Compiled prerequisites differ from catalogue: {identity}')
                if set(focus.get('mutually_exclusive', [])) != exclusions[identity]:
                    errors.append(f'Compiled exclusions differ from catalogue: {identity}')
                if explicit:
                    for key in ('x', 'y'):
                        try:
                            if float(focus[key]) != float(actual.scalar(key, '0')):
                                errors.append(f'Compiled coordinates differ from catalogue: {identity} / {key}')
                        except (KeyError, TypeError, ValueError):
                            errors.append(f'Invalid focus layout coordinates: {identity}')
                    if focus.get('relative_position_id') != actual.scalar('relative_position_id'):
                        errors.append(f'Compiled layout anchor differs from catalogue: {identity}')
                if 'icon' in focus and focus['icon'] != actual.scalar('icon'):
                    errors.append(f'Compiled icon differs from catalogue: {identity}')
                try:
                    if float(focus['cost']) != float(actual.scalar('cost', '0')):
                        errors.append(f'Compiled duration differs from catalogue: {identity}')
                except (ValueError, KeyError):
                    errors.append(f'Invalid catalogue focus duration: {identity}')
        for idea in catalogue['ideas']:
            identity = idea.get('id', '')
            if identity in catalog_ideas:
                errors.append(f'Duplicate catalogue idea: {identity}')
            catalog_ideas[identity] = idea
            if idea.get('tag') != tag or not identity.startswith(PREFIX) or not str(idea.get('family', '')).startswith('hro_family_'):
                errors.append(f'Invalid idea ownership/family: {identity}')
            if not isinstance(idea.get('stage'), int) or not 0 <= idea.get('stage', -1) <= 3:
                errors.append(f'Invalid idea stage: {identity}')
            if identity not in ideas:
                errors.append(f'Catalogue idea not compiled: {identity}')
            else:
                modifier = ideas[identity].one('modifier')
                actual = {n.key: float(n.value) for n in modifier.value} if modifier else {}
                expected = idea.get('modifiers', {})
                if (set(actual) != set(expected) or
                        any(not isinstance(value, (int, float)) or isinstance(value, bool) or
                            not math.isclose(actual.get(key, 0), value, rel_tol=TOLERANCE, abs_tol=TOLERANCE)
                            for key, value in expected.items())):
                    errors.append(f'Compiled idea modifiers differ from catalogue: {identity}')
        for patch in catalogue['native_patches']:
            patch_count += 1
            identity = patch.get('id', '')
            if identity not in all_focuses or identity.startswith(PREFIX):
                errors.append(f'Native patch target missing: {identity}')
                continue
            actual = all_focuses[identity]
            if 'prerequisites' in patch:
                graph_patch_count += 1
                declared = patch['prerequisites']
                if (not isinstance(declared, list) or
                        any(not isinstance(group, list) or not group or
                            any(not isinstance(parent, str) for parent in group) for group in declared)):
                    errors.append(f'Invalid native prerequisite patch: {identity}')
                elif {tuple(sorted(g)) for g in declared} != {tuple(sorted(g)) for g in groups[identity]}:
                    errors.append(f'Compiled native prerequisites differ from catalogue: {identity}')
            for key in ('x', 'y'):
                if key in patch:
                    try:
                        if isinstance(patch[key], bool) or not math.isfinite(float(patch[key])):
                            raise ValueError
                        if float(patch[key]) != float(actual.scalar(key, '0')):
                            errors.append(f'Compiled native coordinates differ from catalogue: {identity} / {key}')
                    except (TypeError, ValueError):
                        errors.append(f'Invalid native coordinate patch: {identity} / {key}')
            for key in ('relative_position_id', 'icon'):
                if key in patch and patch[key] != actual.scalar(key):
                    errors.append(f'Compiled native {key} differs from catalogue: {identity}')
        milestones = catalogue.get('integrated_milestones', [])
        if not isinstance(milestones, list):
            errors.append(f'Integrated milestones must be a list: {tag}')
            milestones = []
        seen_milestones = set()
        for milestone in milestones:
            if not isinstance(milestone, dict):
                errors.append(f'Invalid integrated milestone declaration: {tag}')
                continue
            native, required = milestone.get('native'), milestone.get('requires')
            if not isinstance(native, str) or native not in all_focuses or native.startswith(PREFIX):
                errors.append(f'Integrated milestone native target missing: {native}')
                continue
            if not isinstance(required, str) or required not in own_focuses:
                errors.append(f'Integrated milestone requires unknown authored focus: {required}')
                continue
            if not native.startswith(str(tag) + '_') or not required.startswith('hro_' + str(tag).lower() + '_'):
                errors.append(f'Integrated milestone crosses countries: {native} / {required}')
            pair = (native, required)
            if pair in seen_milestones:
                errors.append(f'Duplicate integrated milestone: {native} / {required}')
                continue
            seen_milestones.add(pair)
            integrated_count += 1
            if not any('cycle:' in error or 'Unknown prerequisite' in error for error in errors):
                try:
                    if _compatible_plan(native, groups, exclusions) is None:
                        errors.append(f'Integrated native milestone is unreachable: {native}')
                    elif _compatible_plan(native, groups, exclusions, forbidden=frozenset({required})) is not None:
                        errors.append(f'Integrated milestone can skip its required authored focus: {native} / {required}')
                except ValueError as exc:
                    errors.append(str(exc))
        patch_ids = [p.get('id') for p in catalogue['native_patches']]
        if len(set(patch_ids)) != len(patch_ids):
            errors.append(f'Duplicate native patch target in {tag}')
    if catalogues and set(expected_focuses) != set(own_focuses):
        for identity in sorted(set(expected_focuses) - set(own_focuses)):
            errors.append(f'Catalogue focus not compiled: {identity}')
        for identity in sorted(set(own_focuses) - set(expected_focuses)):
            errors.append(f'Compiled focus not in catalogues: {identity}')

    families = defaultdict(list)
    for idea in catalog_ideas.values():
        families[(idea.get('tag'), idea.get('family'))].append(idea)
    for tag in COUNTRIES:
        initial = [i for i in catalog_ideas.values() if i.get('tag') == tag and i.get('initial')]
        if len(initial) > 4:
            errors.append(f'Too many initial debuffs for {tag}: {len(initial)}')
        if len({i.get('family') for i in initial}) != len(initial):
            errors.append(f'Multiple initial ideas from one family: {tag}')
        totals = {key: sum(i.get('modifiers', {}).get(key, 0) for i in initial)
                  for key in ('industrial_capacity_factory', 'army_org_factor', 'supply_consumption_factor')}
        if totals['industrial_capacity_factory'] < -0.05 - TOLERANCE or totals['army_org_factor'] < -0.05 - TOLERANCE or totals['supply_consumption_factor'] > 0.06 + TOLERANCE:
            errors.append(f'Initial debuff budget exceeded for {tag}: {totals}')
        final = [values for (t, _), values in families.items() if t == tag]
        worst = {
            key: sum(operation(i.get('modifiers', {}).get(key, 0) for i in values) for values in final)
            for key, operation in (('industrial_capacity_factory', max), ('army_org_factor', max), ('supply_consumption_factor', min))
        }
        # Major specialisations are intentionally strong in 0.4. These ceilings
        # bound the whole set of permanent country families, not one spirit.
        # War adaptation and temporary programme effects are audited separately.
        if worst['industrial_capacity_factory'] > 0.60 + TOLERANCE or worst['army_org_factor'] > 0.50 + TOLERANCE or worst['supply_consumption_factor'] < -0.35 - TOLERANCE:
            errors.append(f'Final family bonus budget exceeded for {tag}: {worst}')
    for (tag, family), members in families.items():
        ids = {i['id'] for i in members}
        for idea in members:
            identity = idea['id']
            setter = 'hro_set_' + identity
            if setter not in effect_defs:
                errors.append(f'Missing family setter: {setter}')
                continue
            try:
                expected_state = _run_idea_setter(effect_defs[setter].value, {'external_sentinel'}, effect_defs, (setter,))
                if expected_state != {'external_sentinel', identity}:
                    errors.append(f'Family setter does not establish one idea: {setter}')
                for previous in members:
                    state = {previous['id'], 'external_sentinel'}
                    after = _run_idea_setter(effect_defs[setter].value, state, effect_defs, (setter,))
                    if previous['stage'] >= idea['stage']:
                        if after != state:
                            errors.append(f'Family setter can regress stage or overwrite a same-tier choice: {setter} over {previous["id"]}')
                    elif after != {identity, 'external_sentinel'}:
                        errors.append(f'Family setter leaves stacked or missing ideas: {setter} from {previous["id"]}')
                if not expected_state & ids:
                    errors.append(f'Family setter does not select its family: {setter}')
            except ValueError as exc:
                errors.append(str(exc))
    spirit_asset_audit = (root / 'interface/hro_spirit_icons.gfx').is_file() or any(str(i.scalar('picture','')).startswith('hro_spirit_') for i in ideas.values())
    if spirit_asset_audit:
        from spirit_lifecycle import audit_spirit_assets
        errors.extend(audit_spirit_assets(root))
    localisation = _read_localisation(root, errors)
    for language, values in localisation.items():
        for key in sorted(required_loc - values.keys()):
            errors.append(f'Missing {language} localisation: {key}')
        for focus in expected_focuses.values():
            suffix = 'ru' if language == 'russian' else 'en'
            identity = focus['id']
            if identity in values and values[identity] != focus.get('name_' + suffix):
                errors.append(f'Compiled {language} focus title differs: {identity}')
            if identity + '_desc' in values and values[identity + '_desc'] != focus.get('desc_' + suffix):
                # The builder may append generated numeric effects/requirements.
                if not values[identity + '_desc'].startswith(focus.get('desc_' + suffix, '')):
                    errors.append(f'Compiled {language} focus description differs: {identity}')
    if schema_dir is not None:
        _keyword_audit(own_docs, all_focuses, effect_defs, trigger_defs, Path(schema_dir), errors)
    if errors:
        raise ValueError('\n'.join(sorted(set(errors))))
    return {
        'runtime_verified': False,
        'script_files': len(documents),
        'authored_focuses': len(own_focuses),
        'focuses_per_country': {tag: len(attached[tag]) for tag in COUNTRIES},
        'native_focuses': len(all_focuses) - len(own_focuses),
        'catalogue_native_patches': patch_count,
        'native_prerequisite_patches': graph_patch_count,
        'required_integrated_milestones': integrated_count,
        'ideas': len(ideas),
        'idea_families': len(families),
        'events': len(events),
        'decisions': len(decisions),
        'localisation_keys_per_language': len(localisation['russian']),
        'prerequisite_checks': 'all native and authored AND/OR paths, exclusions, cycles; declared core milestones cannot be skipped',
        'family_checks': 'bounded budgets and executable upgrade-only setter contracts' if catalogues else 'catalogues not supplied',
        'schema_keyword_audit': schema_dir is not None,
        'national_spirit_asset_audit': spirit_asset_audit,
        'warnings': warnings,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mod-dir', type=Path, required=True)
    parser.add_argument('--catalog-dir', type=Path)
    parser.add_argument('--schema-dir', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(validate(args.mod_dir, args.catalog_dir, args.schema_dir), ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'Validation failed:\n{exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
