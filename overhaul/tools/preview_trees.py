#!/usr/bin/env python3
"""Draw the compiled GER/SOV focus graphs for author review, without game assets.

This is a schematic of base coordinates, not a screenshot or an engine layout
emulator. Conditional ``offset`` blocks and hidden political branches are listed
in the report rather than evaluated against an invented game state.
"""
from __future__ import annotations

import argparse
from collections import Counter
from html import escape
import json
import math
from pathlib import Path
import re
import sys
import textwrap

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from clausewitz import parse, walk

TAGS = ('GER', 'SOV')
SCALE_X = 76
SCALE_Y = 112
CARD_W = 134
CARD_H = 70
MARGIN = 96
# Only the location comes from the game file. The panel footprint is a
# schematic approximation, not a reproduction of countryfocusview.gui.
GUI_GRID_X = 80
GUI_GRID_Y = 130
CONTINUOUS_PANEL_GUI_WIDTH = 600
CONTINUOUS_PANEL_GUI_HEIGHT = 360


def _tag(tree):
    country = tree.one('country')
    found = set()

    def visit(nodes):
        for node in nodes:
            if node.key in ('tag', 'original_tag') and node.value in TAGS:
                found.add(node.value)
            elif node.key in ('modifier', 'AND', 'OR') and isinstance(node.value, list):
                visit(node.value)
    if country:
        visit(country.value)
    return next(iter(found)) if len(found) == 1 else None


def _localisation(mod_dir):
    result = {}
    pattern = re.compile(r'^\s+([^\s:]+):\d*\s+(".*")\s*(?:#.*)?$')
    for path in sorted((mod_dir / 'localisation/russian').glob('*.yml')):
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            match = pattern.match(line)
            if match:
                try:
                    result[match[1]] = json.loads(match[2])
                except json.JSONDecodeError:
                    result[match[1]] = match[2][1:-1]
    return result


def load_focuses(mod_dir):
    """Return country-local definitions; resolve shared focuses from the build."""
    definitions = {}
    trees = {}
    for path in sorted((mod_dir / 'common/national_focus').glob('*.txt')):
        document = parse(path.read_text(encoding='utf-8-sig'))
        for node in walk(document):
            if node.key in ('focus', 'shared_focus', 'joint_focus') and isinstance(node.value, list):
                identity = node.scalar('id')
                if identity:
                    if identity in definitions:
                        raise ValueError(f'Duplicate focus definition: {identity}')
                    definitions[identity] = node
        for tree in document:
            if tree.key == 'focus_tree' and (tag := _tag(tree)):
                if tag in trees:
                    raise ValueError(f'Multiple country focus trees: {tag}')
                trees[tag] = tree
    countries = {}
    for tag in TAGS:
        if tag not in trees:
            raise ValueError(f'No compiled {tag} tree')
        own = {node.scalar('id'): node for node in trees[tag].all('focus')}
        for field in ('shared_focus', 'joint_focus'):
            for ref in trees[tag].all(field):
                if isinstance(ref.value, str):
                    if ref.value not in definitions:
                        raise ValueError(f'Unknown {tag} shared focus: {ref.value}')
                    own[ref.value] = definitions[ref.value]
        countries[tag] = own
    return countries


def load_continuous_positions(mod_dir):
    """Read native GUI-pixel positions without changing load_focuses' API."""
    result = {}
    for path in sorted((Path(mod_dir) / 'common/national_focus').glob('*.txt')):
        for tree in parse(path.read_text(encoding='utf-8-sig')):
            if tree.key != 'focus_tree' or not (tag := _tag(tree)):
                continue
            if tag in result:
                raise ValueError(f'Multiple country focus trees: {tag}')
            panel = tree.one('continuous_focus_position')
            result[tag] = ({key: float(panel.scalar(key, '0')) for key in ('x', 'y')}
                           if panel is not None else None)
    return result


def continuous_panel_report(focuses, position):
    """Report the real location and conservative clearance of an approximate box."""
    if position is None:
        return None
    # Import by sibling path as build_overhaul also loads this file dynamically.
    helper_path = str(Path(__file__).resolve().parent)
    if helper_path not in sys.path:
        sys.path.insert(0, helper_path)
    from native_layout_fix import continuous_layout_report
    x, y = (float(position[key]) for key in ('x', 'y'))
    if not all(math.isfinite(value) for value in (x, y)):
        raise ValueError('Non-finite continuous-focus panel position')
    bounds = continuous_layout_report(focuses)
    minimum_y = bounds['position']['y']
    return {
        'position_gui': {'x': x, 'y': y},
        'grid_bounds': {'left': x / GUI_GRID_X, 'top': y / GUI_GRID_Y,
                        'right': (x + CONTINUOUS_PANEL_GUI_WIDTH) / GUI_GRID_X,
                        'bottom': (y + CONTINUOUS_PANEL_GUI_HEIGHT) / GUI_GRID_Y},
        'approximate_size_gui': {'width': CONTINUOUS_PANEL_GUI_WIDTH,
                                 'height': CONTINUOUS_PANEL_GUI_HEIGHT},
        'standard_grid_gui': {'x': GUI_GRID_X, 'y': GUI_GRID_Y},
        'max_conditional_focus_y': bounds['max_conditional_focus_y'],
        'required_top_gui_y': minimum_y,
        'safe_below_all_focuses': y >= minimum_y,
        'scope': 'actual file position; approximate panel dimensions; game assets, visibility, resolution and UI mods not emulated',
    }


def resolve_positions(focuses):
    result = {}

    def one(identity, stack=()):
        if identity in result:
            return result[identity]
        if identity in stack:
            raise ValueError(f'Cyclic relative position: {identity}')
        if identity not in focuses:
            raise ValueError(f'Unknown relative position: {identity}')
        focus = focuses[identity]
        x, y = float(focus.scalar('x', '0')), float(focus.scalar('y', '0'))
        parent = focus.scalar('relative_position_id')
        if parent:
            px, py = one(parent, stack + (identity,))
            x, y = x + px, y + py
        result[identity] = x, y
        return x, y
    for identity in sorted(focuses):
        one(identity)
    return result


def _groups(node):
    return [[ref.value for ref in group.all('focus')] for group in node.all('prerequisite')]


def _friendly(identity, loc):
    value = loc.get(identity)
    if value:
        return re.sub(r'§.', '', value)
    return re.sub(r'^(?:GER|SOV|hro_ger|hro_sov)_', '', identity).replace('_', ' ')


def draw_country(tag, focuses, positions, reworked, loc, continuous_position=None):
    panel = continuous_panel_report(focuses, continuous_position)
    minimum_x = min(x for x, y in positions.values())
    maximum_x = max(x for x, y in positions.values())
    minimum_y = min(y for x, y in positions.values())
    maximum_y = max(y for x, y in positions.values())
    if panel:
        box = panel['grid_bounds']
        minimum_x, maximum_x = min(minimum_x, box['left']), max(maximum_x, box['right'])
        minimum_y, maximum_y = min(minimum_y, box['top']), max(maximum_y, box['bottom'])
    width = round((maximum_x - minimum_x) * SCALE_X + 2 * MARGIN + CARD_W)
    height = round((maximum_y - minimum_y) * SCALE_Y + 2 * MARGIN + CARD_H)

    def point(identity):
        x, y = positions[identity]
        return (round((x - minimum_x) * SCALE_X + MARGIN + CARD_W / 2, 2),
                round((y - minimum_y) * SCALE_Y + MARGIN + CARD_H / 2, 2))

    output = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="{tag} focus tree schematic">',
              '<style>text{font-family:Arial,sans-serif}.label{font-size:11px;fill:#f0f3f6}.cost{font-size:10px;fill:#bac6d3}.edge{fill:none;stroke:#526477;stroke-width:1.6}.or{stroke-dasharray:5 4}.exclusive{stroke:#aa6d70;stroke-dasharray:3 5;fill:none}.focus rect{stroke-width:1.5}.focus:hover rect,.focus.found rect{stroke:#fff;stroke-width:4}.native rect{fill:#202c3a;stroke:#64788b}.reworked rect{fill:#35432f;stroke:#a2ba74}.added rect{fill:#244855;stroke:#63d3db}.marker{fill:#e7a26c;font-size:12px;font-weight:bold}.continuous-panel rect{fill:#26323f;fill-opacity:.94;stroke:#d3bb78;stroke-width:2.5;stroke-dasharray:8 5}.continuous-panel.unsafe rect{fill:#512d35;stroke:#ed8795}.continuous-panel text{fill:#f0e2b9;font-size:13px}.continuous-panel .panel-title{font-size:19px;font-weight:bold}</style>',
              f'<rect width="{width}" height="{height}" fill="#101923"/>',
              f'<text x="30" y="36" fill="#eef3fa" font-family="Arial" font-size="23">{tag} · схема основного расположения</text>',
              '<text x="30" y="60" fill="#b4c3d2" font-family="Arial" font-size="13">Новые — голубые · изменённые исходные — зелёные · исходные — серые · пунктир — OR / взаимоисключение. Условные смещения не вычисляются.</text>']
    edges = 0
    for identity in sorted(focuses):
        x2, y2 = point(identity)
        for group in _groups(focuses[identity]):
            for parent in group:
                if parent not in positions:
                    continue
                x1, y1 = point(parent)
                bend = (y1 + y2) / 2
                extra = ' or' if len(group) > 1 else ''
                output.append(f'<path class="edge{extra}" d="M{x1},{y1 + CARD_H / 2} V{bend} H{x2} V{y2 - CARD_H / 2}"/>')
                edges += 1
        for block in focuses[identity].all('mutually_exclusive'):
            for ref in block.all('focus'):
                other = ref.value
                if other in positions and identity < other:
                    x1, y1 = point(other)
                    output.append(f'<path class="exclusive" d="M{x1},{y1} L{x2},{y2}"/>')

    for identity in sorted(focuses, key=lambda n: (positions[n][1], positions[n][0], n)):
        focus = focuses[identity]
        cx, cy = point(identity)
        x, y = cx - CARD_W / 2, cy - CARD_H / 2
        title = _friendly(identity, loc)
        status = 'added' if identity.startswith('hro_') else 'reworked' if identity in reworked else 'native'
        details = [identity, title, f'Стоимость: {focus.scalar("cost", "?")} недель',
                   f'Координаты: {positions[identity]}',
                   'Требования: ' + ' AND '.join(' OR '.join(group) for group in _groups(focus)),
                   'Значок: ' + str(focus.scalar('icon', 'не указан'))]
        if focus.all('offset'):
            details.append('Есть условные offset: здесь показано базовое положение.')
        if focus.one('allow_branch'):
            details.append('Видимость ветки управляется allow_branch.')
        output.append(f'<g id="{escape(identity)}" class="focus {status}" data-id="{escape(identity)}" data-name="{escape(title, quote=True)}"><title>{escape(chr(10).join(details))}</title>')
        output.append(f'<rect x="{x}" y="{y}" width="{CARD_W}" height="{CARD_H}" rx="8"/>')
        lines = textwrap.wrap(title, width=21, break_long_words=True, break_on_hyphens=False)
        if len(lines) > 3:
            lines = lines[:3]
            lines[-1] = lines[-1][:19] + '…'
        for index, line in enumerate(lines):
            output.append(f'<text class="label" text-anchor="middle" x="{cx}" y="{y + 16 + index * 13}">{escape(line)}</text>')
        output.append(f'<text class="cost" text-anchor="middle" x="{cx}" y="{y + CARD_H - 7}">{escape(str(focus.scalar("cost", "?")))} нед.</text>')
        if focus.all('offset'):
            output.append(f'<text class="marker" x="{x + CARD_W - 12}" y="{y + 13}">↔</text>')
        output.append('</g>')
    if panel:
        box = panel['grid_bounds']
        x = round((box['left'] - minimum_x) * SCALE_X + MARGIN + CARD_W / 2, 2)
        y = round((box['top'] - minimum_y) * SCALE_Y + MARGIN + CARD_H / 2, 2)
        panel_width = round((box['right'] - box['left']) * SCALE_X, 2)
        panel_height = round((box['bottom'] - box['top']) * SCALE_Y, 2)
        safe = panel['safe_below_all_focuses']
        detail = ('Панель ниже всех возможных рядов фокусов.' if safe
                  else 'ВНИМАНИЕ: панель не вынесена ниже всех рядов фокусов.')
        source = panel['position_gui']
        title = (f'Непрерывные фокусы\nGUI x={source["x"]:g}, y={source["y"]:g}\n'
                 f'{detail}\nПриблизительный контур: размеры интерфейса и разрешение не эмулируются.')
        output.append(f'<g class="continuous-panel {"safe" if safe else "unsafe"}" id="continuous-panel-{tag}"><title>{escape(title)}</title>')
        output.append(f'<rect x="{x}" y="{y}" width="{panel_width}" height="{panel_height}" rx="12"/>')
        for index, (line, css) in enumerate((('Непрерывные фокусы', 'panel-title'),
                                           (f'Позиция GUI: x={source["x"]:g}, y={source["y"]:g}', ''),
                                           (detail, ''),
                                           ('Приблизительный контур панели.', ''),
                                           ('Интерфейс HOI4, разрешение и масштаб не эмулируются.', ''))):
            output.append(f'<text class="{css}" x="{x + 22}" y="{y + 42 + index * 30}">{escape(line)}</text>')
        output.append('</g>')
    output.append('</svg>')
    return '\n'.join(output), {'width': width, 'height': height, 'prerequisite_edges': edges}


def layout_report(focuses, positions):
    new = sorted(identity for identity in focuses if identity.startswith('hro_'))
    native = sorted(set(focuses) - set(new))
    collisions = []
    for first in new:
        x1, y1 = positions[first]
        for second in native:
            x2, y2 = positions[second]
            if abs(x1 - x2) < 1.8 and abs(y1 - y2) < .8:
                collisions.append({'new': first, 'native': second, 'new_position': [x1, y1],
                                   'native_position': [x2, y2],
                                   'native_conditional': bool(focuses[second].all('offset') or focuses[second].one('allow_branch'))})
    new_collisions = []
    for index, first in enumerate(new):
        x1, y1 = positions[first]
        for second in new[index + 1:]:
            x2, y2 = positions[second]
            if abs(x1 - x2) < 1.8 and abs(y1 - y2) < .8:
                new_collisions.append({'first': first, 'second': second, 'positions': [[x1, y1], [x2, y2]]})
    return {'focus_count': len(focuses), 'new_focus_count': len(new),
            'new_vs_native_collision_candidates': collisions, 'new_vs_new_collisions': new_collisions,
            'conditional_offsets': {identity: [{'x': block.scalar('x', '0'), 'y': block.scalar('y', '0')}
                                                for block in node.all('offset')]
                                    for identity, node in sorted(focuses.items()) if node.all('offset')},
            'positions': {identity: list(positions[identity]) for identity in sorted(positions)}}


def generate(mod_dir, output_dir):
    mod_dir, output_dir = Path(mod_dir), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    countries = load_focuses(mod_dir)
    panel_positions = load_continuous_positions(mod_dir)
    loc = _localisation(mod_dir)
    report_file = mod_dir / 'OVERHAUL_BUILD_REPORT.json'
    built = json.loads(report_file.read_text(encoding='utf-8')) if report_file.is_file() else {}
    changed = {patch['id'] for patch in built.get('native_patches', [])}
    report = {'kind': 'authoring_base_coordinate_schematic', 'engine_layout_verified': False,
              'warning': 'Conditional offsets and branch visibility are not evaluated; collision candidates require review.',
              'countries': {}}
    svgs = {}
    for tag, focuses in countries.items():
        positions = resolve_positions(focuses)
        panel = panel_positions.get(tag)
        svg, dimensions = draw_country(tag, focuses, positions, changed, loc, panel)
        svgs[tag] = svg
        (output_dir / f'{tag}_tree.svg').write_text(svg, encoding='utf-8')
        report['countries'][tag] = dict(layout_report(focuses, positions), **dimensions)
        report['countries'][tag]['continuous_focus_panel'] = continuous_panel_report(focuses, panel)
    (output_dir / 'layout_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    panes = ''.join(f'<div class="country" id="pane-{tag}"{ " hidden" if tag != "GER" else ""}>{svgs[tag]}</div>' for tag in TAGS)
    html = '''<!doctype html><html lang="ru"><meta charset="utf-8"><title>Historical Reality — схема деревьев</title>
<style>body{margin:0;background:#101923;color:#e5ecf3;font:15px Arial,sans-serif}header{position:sticky;top:0;z-index:5;background:#1d2b39;padding:12px;box-shadow:0 2px 8px #0006}button,input,select{font:inherit;padding:5px}header p{margin:8px 0 0;color:#bfcedb;font-size:13px}.viewport{height:calc(100vh - 114px);overflow:auto}.country svg{display:block}.country[hidden]{display:none}#result{margin-left:12px}a{color:#78d7e7}</style>
<header><select id="country"><option>GER</option><option>SOV</option></select> <label>Масштаб <input id="zoom" type="range" min="20" max="150" value="65"> <span id="zoomlabel">65%</span></label> <input id="find" placeholder="ID или название фокуса" size="34"> <button id="search">Найти</button> <button id="continuous">Непрерывные фокусы</button><span id="result"></span>
<p>Схема файлов сборки, не снимок из HOI4. Голубые узлы — новые, зелёные — изменённые исходные; золотой контур — приблизительная панель непрерывных фокусов. Наведи курсор на элемент для подробностей. Видимость веток, размеры окон и разрешение игры не эмулируются. <a href="layout_report.json">Отчёт координат</a></p></header>
<main class="viewport">''' + panes + '''</main>
<script>const panes=[...document.querySelectorAll('.country')], choice=document.getElementById('country'), zoom=document.getElementById('zoom');
function resize(){document.getElementById('zoomlabel').textContent=zoom.value+'%';for(const pane of panes){const s=pane.querySelector('svg'),v=s.viewBox.baseVal;s.style.width=v.width*zoom.value/100+'px';s.style.height=v.height*zoom.value/100+'px';}}
choice.onchange=()=>{for(const p of panes)p.hidden=p.id!=='pane-'+choice.value;document.getElementById('result').textContent='';};zoom.oninput=resize;resize();
function find(){const q=document.getElementById('find').value.toLowerCase().trim(), nodes=[...document.querySelectorAll('#pane-'+choice.value+' .focus')];for(const n of nodes)n.classList.remove('found');const matches=q?nodes.filter(n=>n.dataset.id.toLowerCase().includes(q)||n.dataset.name.toLowerCase().includes(q)):[];for(const n of matches)n.classList.add('found');document.getElementById('result').textContent=matches.length+' найдено';if(matches[0])matches[0].scrollIntoView({block:'center',inline:'center',behavior:'smooth'});}
document.getElementById('search').onclick=find;document.getElementById('find').onkeydown=e=>{if(e.key==='Enter')find();};
document.getElementById('continuous').onclick=()=>{const panel=document.querySelector('#pane-'+choice.value+' .continuous-panel');if(panel)panel.scrollIntoView({block:'center',inline:'center',behavior:'smooth'});};</script></html>'''
    (output_dir / 'index.html').write_text(html, encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mod-dir', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    report = generate(args.mod_dir, args.output_dir)
    for tag, country in report['countries'].items():
        print(tag, 'focuses:', country['focus_count'], 'new/native collision candidates:',
              len(country['new_vs_native_collision_candidates']), 'new/new collisions:', len(country['new_vs_new_collisions']))
    print('Preview:', (args.output_dir / 'index.html').resolve())


if __name__ == '__main__':
    main()
