"""Separate readable public rewards from guarded housekeeping operations."""
from clausewitz import edit, parse


def present_effects(source, presentations):
    definitions = {n.key: n for n in parse(source)}
    missing = presentations.keys() - definitions.keys()
    if missing:
        raise ValueError('Unknown public effects: ' + ', '.join(sorted(missing)))
    replacements = []
    for identity, visible in presentations.items():
        node = definitions[identity]
        body = source[node.value_start + 1:node.value_end - 1]
        replacement = f'{identity} = {{\n    {visible}\n    hidden_effect = {{\n{body}\n    }}\n}}'
        replacements.append((node.start, node.end, replacement))
    return edit(source, replacements)
