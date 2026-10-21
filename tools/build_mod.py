#!/usr/bin/env python3
"""Build a local, DLC-preserving overlay from a legally installed copy of HOI4."""
import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile
import zipfile

from clausewitz import edit, parse, walk
from validate import validate

ROOT = Path(__file__).resolve().parents[1]
TAGS = ('GER', 'SOV')
WEST = ('moscow', 'moskva', 'leningrad', 'minsk', 'smolensk', 'kiev', 'kyiv',
        'kharkov', 'kharkiv', 'dnepropetrovsk', 'zaporozhe', 'vitebsk')
EAST = ('sverdlovsk', 'chelyabinsk', 'magnitogorsk', 'novosibirsk', 'omsk',
        'tomsk', 'krasnoyarsk', 'kemerovo', 'barnaul', 'orenburg', 'ufa', 'zlatoust')


def read_game(game):
    """Return virtual focus/state files. Ambiguous DLC overlays fail closed."""
    files, origins = {}, {}

    def add(name, data, source):
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError(f'Unsafe game path: {name}')
        if not (name.startswith('common/national_focus/') or name.startswith('history/states/')):
            return
        if not name.endswith('.txt'):
            return
        if name in files and files[name] != data:
            raise ValueError(f'Ambiguous game/DLC override for {name}: {origins[name]} and {source}. '
                             'Use an unmodified game installation; automatic load-order guessing is disabled.')
        files[name], origins[name] = data, source

    for directory in ('common/national_focus', 'history/states'):
        base = game / directory
        if not base.is_dir():
            raise ValueError(f'Missing {base}; select the Hearts of Iron IV game directory.')
        for p in sorted(base.rglob('*.txt')):
            add(p.relative_to(game).as_posix(), p.read_bytes(), p.relative_to(game).as_posix())
    dlc = game / 'dlc'
    if dlc.exists():
        for p in sorted(dlc.rglob('*.txt')):
            name = p.as_posix()
            for marker in ('common/national_focus/', 'history/states/'):
                if marker in name:
                    add(name[name.index(marker):], p.read_bytes(), p.relative_to(game).as_posix())
        for p in sorted(dlc.rglob('*.zip')):
            with zipfile.ZipFile(p) as archive:
                for info in archive.infolist():
                    name = info.filename
                    if name.startswith(('common/national_focus/', 'history/states/')) and name.endswith('.txt'):
                        add(name, archive.read(info), f'{p.relative_to(game)}!{name}')
    return files, origins


def tree_tag(tree):
    country = tree.one('country')
    if country is None:
        return None
    # Do not mistake a NOT = { tag = X } exclusion for country selection.
    found = set()

    def positive(nodes):
        for n in nodes:
            if n.key in ('tag', 'original_tag') and n.value in TAGS and n.op == '=':
                found.add(n.value)
            elif n.key in ('modifier', 'AND', 'OR') and isinstance(n.value, list):
                positive(n.value)

    positive(country.value)
    if len(found) > 1:
        raise ValueError(f'Ambiguous country selector in tree {tree.scalar("id")}')
    return next(iter(found), None)


def focus_definitions(docs):
    result = {}
    for nodes in docs.values():
        for n in walk(nodes):
            if n.key in ('focus', 'shared_focus', 'joint_focus') and isinstance(n.value, list):
                identity = n.scalar('id')
                if identity:
                    if identity in result:
                        raise ValueError(f'Duplicate original focus ID: {identity}')
                    result[identity] = n
    return result


def right_edge(tree, definitions):
    resolved = {}

    def x_of(n, stack=()):
        identity = n.scalar('id')
        if identity in resolved:
            return resolved[identity]
        if identity in stack:
            raise ValueError(f'Cyclic relative_position_id: {identity}')
        x = float(n.scalar('x', '0'))
        parent = n.scalar('relative_position_id')
        if parent:
            if parent not in definitions:
                raise ValueError(f'Unresolved focus position {parent}')
            x += x_of(definitions[parent], stack + (identity,))
        # DLC layout overrides can shift a focus farther right.
        for override in n.all('offset'):
            x += max(0.0, float(override.scalar('x', '0')))
        resolved[identity] = x
        return x

    nodes = list(tree.all('focus'))
    for ref in tree.all('shared_focus'):
        if isinstance(ref.value, str):
            if ref.value not in definitions:
                raise ValueError(f'Unresolved shared focus: {ref.value}')
            nodes.append(definitions[ref.value])
    return max((x_of(n) for n in nodes), default=0)


def calendar_gate(date):
    return ('OR = {\n'
            '    has_game_rule = { rule = HRS_PACING option = HRS_PACING_OPEN }\n'
            f'    date > {date}\n'
            '}')


def build(game, output, launcher_dir=None, focus_files=None):
    game, output = game.resolve(), output.resolve()
    if output.exists():
        raise ValueError(f'Output already exists: {output}. Choose a new output directory; nothing was overwritten.')
    if output == game or game in output.parents:
        raise ValueError('Output must be outside the game installation.')
    launcher = launcher_dir.resolve() / 'historical_reality.mod' if launcher_dir else None
    if launcher and launcher.exists():
        raise ValueError(f'Launcher descriptor already exists: {launcher}; nothing was overwritten.')
    if launcher and (launcher == game or game in launcher.parents or output in launcher.parents):
        raise ValueError('Launcher directory must be outside the game and output directories.')
    files, origins = read_game(game)
    texts = {p: b.decode('utf-8-sig') for p, b in files.items() if p.startswith('common/national_focus/')}
    if focus_files is not None:
        requested = set()
        for name in focus_files:
            relative = PurePosixPath(name)
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError(f'Unsafe selected focus path: {name}')
            path = name if name.startswith('common/national_focus/') else 'common/national_focus/' + name
            if path not in texts:
                raise ValueError(f'Selected focus file not found: {name}')
            requested.add(path)
        texts = {p: t for p, t in texts.items() if p in requested}
    docs = {}
    for path, text in texts.items():
        try:
            docs[path] = parse(text)
        except ValueError as exc:
            raise ValueError(f'{path}: {exc}') from exc
    definitions = focus_definitions(docs)
    selected = [(p, tree, tree_tag(tree)) for p, nodes in docs.items() for tree in nodes
                if tree.key == 'focus_tree' and tree_tag(tree)]
    for tag in TAGS:
        if not any(t == tag for _, _, t in selected):
            raise ValueError(f'No unambiguous {tag} focus tree found. No mod was installed.')
    offsets = {tag: math.ceil(max(right_edge(t, definitions) for _, t, c in selected if c == tag)) + 14 for tag in TAGS}
    catalog = json.loads((ROOT / 'data/focuses.json').read_text(encoding='utf-8'))
    policy = json.loads((ROOT / 'data/historical_gates.json').read_text(encoding='utf-8'))
    reworks = json.loads((ROOT / 'data/rework_effects.json').read_text(encoding='utf-8'))
    edits, patched, added_effects, seen = {}, [], [], set()
    for path, tree, tag in selected:
        patches = edits.setdefault(path, [])
        refs = ''.join(f'\n    shared_focus = {f["id"]}' for f in catalog if f['tag'] == tag)
        root_focus = f'hrs_{tag.lower()}_balance'
        refs += (f'\n    shortcut = {{ name = {root_focus} target = {root_focus}'
                 ' trigger = { always = yes } }\n')
        patches.append((tree.value_end - 1, tree.value_end - 1, refs + '\n'))
        originals = list(tree.all('focus'))
        originals += [definitions[r.value] for r in tree.all('shared_focus') if isinstance(r.value, str)]
        for focus in originals:
            identity = focus.scalar('id')
            if identity not in (policy.keys() | reworks.keys()) or identity in seen:
                continue
            seen.add(identity)
            # Shared definitions may be located in another virtual source file.
            owner = next(p for p, ns in docs.items() if any(n is focus for n in walk(ns)))
            target = edits.setdefault(owner, [])
            if identity in policy:
                gate = calendar_gate(policy[identity]['earliest_start'])
                available = focus.one('available')
                if available:
                    target.append((available.value_end - 1, available.value_end - 1, '\n    # HRS historical pacing\n    ' + gate + '\n'))
                else:
                    target.append((focus.value_end - 1, focus.value_end - 1, '\n    available = { ' + gate + ' }\n'))
                patched.append({'id': identity, **policy[identity]})
            if identity in reworks:
                reward = focus.one('completion_reward')
                effect = reworks[identity]['effect']
                if reward:
                    target.append((reward.value_end - 1, reward.value_end - 1, '\n    # HRS historical costs / preparation\n    ' + effect + '\n'))
                else:
                    target.append((focus.value_end - 1, focus.value_end - 1, '\n    completion_reward = { ' + effect + ' }\n'))
                added_effects.append({'id': identity, **reworks[identity]})
    for tag in TAGS:
        if not any(p['id'].startswith(tag + '_') for p in patched):
            raise ValueError(f'No known historical {tag} milestones found. The game version needs a mapping update.')

    pools = {'west': [], 'east': []}
    state_sources = []
    for path, raw in files.items():
        if not path.startswith('history/states/'):
            continue
        raw_text = raw.decode('utf-8-sig')
        stem = PurePosixPath(path).stem.lower()
        # Vanilla uses placeholder filenames such as "653-Sov state 7.txt";
        # its explicit name/id line comment identifies Sverdlovsk instead.
        labels = [stem] + re.findall(r'(?m)^\s*(?:name|id)\s*=\s*[^#\n]+#\s*([^\n]*)', raw_text.lower())
        groups = {group for group, names in (('west', WEST), ('east', EAST))
                  if any(re.search(r'(?<![a-z])' + name + r'(?![a-z])', label) for name in names for label in labels)}
        if len(groups) > 1:
            raise ValueError(f'Ambiguous evacuation geography: {path}')
        group = next(iter(groups), None)
        if group:
            state = next((n for n in parse(raw_text) if n.key == 'state'), None)
            if state is None or not str(state.scalar('id', '')).isdigit():
                raise ValueError(f'Cannot read state ID: {path}')
            identity = int(state.scalar('id'))
            pools[group].append(identity)
            state_sources.append({'id': identity, 'group': group, 'file': path, 'labels': labels})
    if not all(pools.values()) or set(pools['west']) & set(pools['east']):
        raise ValueError('Cannot safely identify disjoint western and eastern evacuation states from game filenames.')

    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.hrs-build-', dir=output.parent))
    report = {
        'mod_version': '0.1.0', 'runtime_verified': False,
        'schema_reference': 'cwtools/cwtools-hoi4-config@297dd69c42aabe10078a8b7ab7f2d07ee631d4ef',
        'trees': [{'file': p, 'id': t.scalar('id'), 'tag': c} for p, t, c in selected],
        'focus_source_selection': sorted(texts) if focus_files is not None else 'all',
        'historical_gates_applied': patched,
        'historical_gates_not_found': sorted(set(policy) - seen),
        'original_focus_effects_added': added_effects,
        'original_focus_effect_ids_not_found': sorted(set(reworks) - seen),
        'evacuation_states': pools, 'branch_offsets': offsets,
        'evacuation_state_sources': state_sources,
        'source_sha256': {p: hashlib.sha256(files[p]).hexdigest() for p in edits},
        'source_origins': {p: origins[p] for p in edits},
        'shared_focuses_added': len(catalog),
        'warning': 'Not engine-tested. Rebuild after every game update; do not redistribute generated vanilla overlays.'
    }
    try:
        shutil.copytree(ROOT / 'mod', stage, dirs_exist_ok=True)
        for path, changes in edits.items():
            changed = edit(texts[path], changes)
            parse(changed)
            dest = stage / path
            if dest.exists():
                raise ValueError(f'Generated vanilla path collides with mod content: {path}')
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(changed.encode('utf-8-sig'))
        shared_path = stage / 'common/national_focus/hrs_shared_focuses.txt'
        shared_text = shared_path.read_text(encoding='utf-8-sig')
        for tag, x in offsets.items():
            shared_text = shared_text.replace(f'@HRS_{tag}_OFFSET@', str(x))
        parse(shared_text)
        shared_path.write_text(shared_text, encoding='utf-8')
        triggers = stage / 'common/scripted_triggers/hrs_evacuation_states.txt'
        triggers.write_text(''.join(
            f'hrs_evacuation_{group}_state = {{ OR = {{ ' + ' '.join(f'state = {s}' for s in sorted(ids)) + ' } }\n'
            for group, ids in pools.items()), encoding='utf-8')
        (stage / 'BUILD_REPORT.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        shutil.copytree(ROOT / 'docs', stage / 'docs')
        shutil.copy2(ROOT / 'README.md', stage / 'README.md')
        validate(stage, built=True)
        stage.rename(output)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    if launcher:
        launcher.parent.mkdir(parents=True, exist_ok=True)
        descriptor = (output / 'descriptor.mod').read_text(encoding='utf-8')
        # JSON string quoting also escapes Windows separators and quote characters.
        descriptor += 'path=' + json.dumps(output.as_posix(), ensure_ascii=False) + '\n'
        with launcher.open('x', encoding='utf-8') as f:
            f.write(descriptor)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir', required=True, type=Path)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'dist/Historical_Reality')
    parser.add_argument('--launcher-dir', type=Path, help='Optional HOI4 user mod directory (Documents/Paradox Interactive/Hearts of Iron IV/mod).')
    parser.add_argument('--focus-file', action='append', help='Optional explicit focus source filename; repeat for all required tree/shared source files. Other countries are left untouched.')
    args = parser.parse_args()
    try:
        report = build(args.game_dir, args.output_dir, args.launcher_dir, args.focus_file)
    except (ValueError, OSError, zipfile.BadZipFile, UnicodeError) as exc:
        print(f'Build stopped: {exc}', file=sys.stderr)
        return 1
    print(f'Built: {args.output_dir.resolve()}')
    print(f'Trees: {len(report["trees"])}; added focuses: {report["shared_focuses_added"]}; patched milestones: {len(report["historical_gates_applied"])}')
    print('Review BUILD_REPORT.json. Start a NEW 1936 campaign with historical AI; engine validation is still required.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
