#!/usr/bin/env python3
"""Report the focus-day cost of one compatible campaign prerequisite plan.

This is a workload review, not a game simulation or a minimum-cost solver.
Availability triggers, bypasses, dates, focus speed, DLC visibility and events
can change what a player can actually complete and when.
"""
from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from validate_overhaul import _compatible_plan, _groups, _mutex
from clausewitz import parse, walk

HISTORICAL_POLITICAL_EXCLUSIONS = (
    'GER_oppose_hitler', 'GER_oppose_hitler_ww',
    'SOV_the_left_opposition', 'SOV_the_right_opposition',
    'SOV_beaten_but_not_defeated',
)


def _number(value):
    return int(value) if value == value.to_integral_value() else float(value)


def _cost(focus, constants):
    value = focus.scalar('cost')
    visited = set()
    while isinstance(value, str) and value.startswith('@'):
        if value in visited:
            raise ValueError(f'Cost constant cycle in {focus.scalar("id")}: {value}')
        visited.add(value)
        if value not in constants:
            raise ValueError(f'Unresolved cost constant in {focus.scalar("id")}: {value}')
        value = constants[value]
    try:
        cost = Decimal(value)
    except (TypeError, InvalidOperation):
        raise ValueError(f'Non-numeric or missing focus cost: {focus.scalar("id")} / {value}') from None
    if not cost.is_finite() or cost <= 0:
        raise ValueError(f'Non-positive or non-finite focus cost: {focus.scalar("id")}')
    return cost


def _load(directory):
    focuses, constants, paths = {}, {}, {}
    focus_directory = directory / 'common' / 'national_focus'
    for path in sorted(focus_directory.rglob('*.txt')):
        roots = parse(path.read_text(encoding='utf-8-sig'))
        local_constants = {n.key: n.value for n in roots
                           if n.key and n.key.startswith('@') and isinstance(n.value, str)}
        for node in walk(roots):
            if node.key not in ('focus', 'shared_focus', 'joint_focus') or not isinstance(node.value, list):
                continue
            identity = node.scalar('id')
            if not identity:
                continue
            if identity in focuses:
                raise ValueError(f'Duplicate focus ID: {identity}')
            focuses[identity] = node
            constants[identity] = local_constants
            paths[identity] = path.relative_to(directory).as_posix()
    if not focuses:
        raise ValueError(f'No compiled focus definitions found: {focus_directory}')
    return focuses, constants, paths


def _ordered_plan(chosen, groups):
    """Give a completion order satisfying AND groups of OR alternatives."""
    done, result, pending = set(), [], set(chosen)
    while pending:
        ready = sorted(identity for identity in pending
                       if all(any(parent in done for parent in group)
                              for group in groups.get(identity, ())))
        if not ready:
            raise ValueError('Selected prerequisite plan has no valid completion order')
        for identity in ready:
            result.append(identity)
            done.add(identity)
            pending.remove(identity)
    return result


def _day(value):
    try:
        return date(*map(int, value.replace('-', '.').split('.')))
    except (TypeError, ValueError, AttributeError):
        raise ValueError(f'Invalid calendar date: {value}') from None


def review_route(mod_dir: Path, goals, forbidden=(), historical=False,
                 start_date='1936.1.1', deadline=None):
    focuses, constants, paths = _load(Path(mod_dir))
    goals = list(dict.fromkeys(goals))
    if not goals:
        raise ValueError('At least one goal focus is required')
    forbidden = set(forbidden)
    if historical:
        forbidden.update(identity for identity in HISTORICAL_POLITICAL_EXCLUSIONS if identity in focuses)
    for identity in goals + sorted(forbidden):
        if identity not in focuses:
            raise ValueError(f'Unknown goal or forbidden focus: {identity}')
    groups = {identity: _groups(focus) for identity, focus in focuses.items()}
    exclusions = {identity: _mutex(focus) for identity, focus in focuses.items()}
    for identity, requirements in groups.items():
        for group in requirements:
            if not group:
                raise ValueError(f'Empty prerequisite group: {identity}')
            for parent in group:
                if parent not in focuses:
                    raise ValueError(f'Unknown prerequisite {parent} in {identity}')
    synthetic = '__hro_campaign_route__'
    while synthetic in focuses:
        synthetic += '_'
    groups[synthetic] = [(identity,) for identity in goals]
    chosen = _compatible_plan(synthetic, groups, exclusions, frozenset(forbidden))
    if chosen is None:
        raise ValueError('The requested goals have no mutually compatible prerequisite plan')
    chosen.remove(synthetic)
    order = _ordered_plan(chosen, groups)
    plan, date_checks = [], []
    weeks = {'native': Decimal(0), 'authored': Decimal(0)}
    for identity in order:
        focus = focuses[identity]
        kind = 'authored' if identity.startswith('hro_') else 'native'
        cost = _cost(focus, constants[identity])
        weeks[kind] += cost
        plan.append({'id': identity, 'kind': kind, 'weeks': _number(cost),
                     'workdays': _number(cost * 7), 'source': paths[identity]})
        checks = [dict(operator=n.op, date=n.value)
                  for available in focus.all('available') for n in walk(available.value)
                  if n.key == 'date' and isinstance(n.value, str)]
        if checks:
            date_checks.append({'id': identity, 'kind': kind, 'checks': checks})
    total_days = sum(weeks.values()) * 7
    result = {
        'goals': goals,
        'forbidden': sorted(forbidden),
        'plan_selection': 'one compatible prerequisite plan; not a minimum or optimized route',
        'runtime_verified': False,
        'availability_and_calendar_verified': False,
        'focuses': len(plan),
        'focuses_by_kind': {kind: sum(item['kind'] == kind for item in plan) for kind in weeks},
        'weeks': {kind: _number(value) for kind, value in weeks.items()},
        'workdays': {**{kind: _number(value * 7) for kind, value in weeks.items()},
                     'total': _number(total_days)},
        'plan': plan,
        'own_date_checks': [entry for entry in date_checks if entry['kind'] == 'authored'],
        'native_date_checks': [entry for entry in date_checks if entry['kind'] == 'native'],
        'date_check_note': 'Raw available-script comparisons; OR rules can disable individual date gates.',
        'limitations': [
            'All selected focuses are charged their nominal full cost; native bypasses are not simulated.',
            'War, political events, industry, DLC visibility, availability and historical trial waits are not simulated.',
            'Focus speed modifiers, saved progress and interruption are not simulated.',
            'Historical mode only excludes the named opposition roots; it does not solve political triggers.',
        ],
    }
    if deadline is not None:
        start, end = _day(start_date), _day(deadline)
        if end < start:
            raise ValueError('Deadline precedes campaign start')
        available_days = (end - start).days
        result['calendar_workload_budget'] = {
            'start': start.isoformat(), 'deadline': end.isoformat(),
            'calendar_days': available_days,
            'nominal_spare_days': _number(Decimal(available_days) - total_days),
            'accounts_for_waits_or_availability': False,
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mod-dir', required=True, type=Path)
    parser.add_argument('--goal', action='append', required=True, help='Required completed focus; may repeat')
    parser.add_argument('--forbid', action='append', default=[], help='Exclude an alternative focus; may repeat')
    parser.add_argument('--historical', action='store_true', help='Exclude known GER/SOV opposition roots')
    parser.add_argument('--start-date', default='1936.1.1')
    parser.add_argument('--deadline', help='Optional workload comparison date; does not simulate waits')
    args = parser.parse_args()
    try:
        report = review_route(args.mod_dir, args.goal, args.forbid, args.historical, args.start_date, args.deadline)
    except (OSError, ValueError) as exc:
        print(f'Campaign route review failed: {exc}', file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
