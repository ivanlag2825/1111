"""Place the native continuous-focus panel below the expanded focus graph.

``continuous_focus_position`` uses GUI pixels; ordinary focus x/y values are
grid coordinates.  Moving focus rows therefore does not move that panel.  The
standard HOI4 vertical grid is 130 px.  This helper keeps the native horizontal
position and reserves three extra rows after every possible focus position.

Conditional offsets are not evaluated against an invented political state.
Their positive vertical components are conservatively included, including
those inherited through relative_position_id.  This is a layout calculation,
not a substitute for checking the actual GUI in HOI4.
"""
from __future__ import annotations

from collections.abc import Mapping
import math

ROW_HEIGHT_PX = 130
PANEL_MARGIN_ROWS = 3


def _number(value, context):
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise ValueError(f'Non-numeric focus layout value: {context}/{value}') from None
    if not math.isfinite(result):
        raise ValueError(f'Non-finite focus layout value: {context}/{value}')
    return result


def _coordinate(position, key, default):
    if position is None:
        return default
    value = position.get(key, default) if isinstance(position, Mapping) else position.scalar(key, str(default))
    return _number(value, 'continuous_focus_position/' + key)


def focus_vertical_bounds(focuses):
    """Return base and conservative conditional upper bounds per focus ID.

    ``focuses`` is the country-local ID -> parsed Node mapping, including its
    attached shared focuses.  Unknown anchors and cycles fail before delivery.
    """
    cache = {}

    def resolve(identity, stack=()):
        if identity in cache:
            return cache[identity]
        if identity in stack:
            raise ValueError(f'Cyclic relative focus layout: {identity}')
        if identity not in focuses:
            raise ValueError(f'Unknown relative focus layout anchor: {identity}')
        node = focuses[identity]
        base = upper = _number(node.scalar('y', '0'), identity + '/y')
        if parent := node.scalar('relative_position_id'):
            parent_base, parent_upper = resolve(parent, stack + (identity,))
            base += parent_base
            upper += parent_upper
        # Several offsets may apply together; summing positive components is
        # safe even if their triggers are mutually exclusive in the game.
        upper += sum(max(0, _number(offset.scalar('y', '0'), identity + '/offset/y'))
                     for offset in node.all('offset'))
        cache[identity] = base, upper
        return cache[identity]

    for identity in focuses:
        resolve(identity)
    return cache


def continuous_layout_report(focuses, current_position=None, *,
                             row_height_px=ROW_HEIGHT_PX,
                             margin_rows=PANEL_MARGIN_ROWS):
    """Describe an integer panel position safe for the supplied focus bounds."""
    if not focuses:
        raise ValueError('Cannot place continuous focuses without focus bounds')
    if row_height_px <= 0 or margin_rows < 2:
        raise ValueError('Continuous-focus layout requires positive row height and at least two margin rows')
    bounds = focus_vertical_bounds(focuses)
    max_base = max(base for base, upper in bounds.values())
    max_upper = max(upper for base, upper in bounds.values())
    x = math.ceil(_coordinate(current_position, 'x', 50))
    prior_y = _coordinate(current_position, 'y', 0)
    y = math.ceil(max(prior_y, (max_upper + margin_rows) * row_height_px))
    return {
        'position': {'x': x, 'y': y},
        'max_base_focus_y': max_base,
        'max_conditional_focus_y': max_upper,
        'row_height_px': row_height_px,
        'margin_rows': margin_rows,
        'focus_count': len(focuses),
        'scope': 'standard GUI pixel grid; conservative vertical offset envelope; engine GUI not verified',
    }


def choose_continuous_position(focuses, current_position=None, **options):
    """Return {'x': int, 'y': int}; preserve a panel already below all nodes."""
    return continuous_layout_report(focuses, current_position, **options)['position']
