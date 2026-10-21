"""Small, lossless-span reader for Clausewitz text; not a game-engine validator."""
from dataclasses import dataclass


@dataclass
class Token:
    text: str
    start: int
    end: int


@dataclass
class Node:
    key: str | None
    op: str | None
    value: str | list
    start: int
    end: int
    value_start: int
    value_end: int

    def all(self, key):
        return [n for n in self.value if n.key == key] if isinstance(self.value, list) else []

    def one(self, key):
        nodes = self.all(key)
        if len(nodes) > 1:
            raise ValueError(f"Multiple {key!r} blocks at {self.start}")
        return nodes[0] if nodes else None

    def scalar(self, key, default=None):
        n = self.one(key)
        return n.value if n is not None and isinstance(n.value, str) else default


def tokens(text):
    i = 0
    while i < len(text):
        c = text[i]
        if c.isspace() or c == '\ufeff':
            i += 1
        elif c == '#':
            j = text.find('\n', i)
            i = len(text) if j < 0 else j + 1
        elif c == '"':
            start = i
            i += 1
            while i < len(text):
                if text[i] == '\\':
                    i += 2
                elif text[i] == '"':
                    i += 1
                    break
                else:
                    i += 1
            else:
                raise ValueError(f"Unterminated string at {start}")
            yield Token(text[start:i], start, i)
        elif c in '{}=<>!?':
            start = i
            i += 1
            if c in '<>!?' and i < len(text) and text[i] == '=':
                i += 1
            yield Token(text[start:i], start, i)
        else:
            start = i
            while i < len(text) and not text[i].isspace() and text[i] not in '{}=<>!?#"':
                i += 1
            yield Token(text[start:i], start, i)


def parse(text):
    ts = list(tokens(text))
    pos = 0

    def block(nested=False):
        nonlocal pos
        result = []
        while pos < len(ts) and ts[pos].text != '}':
            first = ts[pos]
            if first.text in {'{', '=', '>', '<', '>=', '<=', '!=', '?='}:
                raise ValueError(f"Unexpected {first.text!r} at {first.start}")
            pos += 1
            if pos < len(ts) and ts[pos].text in {'=', '>', '<', '>=', '<=', '!=', '?='}:
                op = ts[pos].text
                pos += 1
                if pos == len(ts) or ts[pos].text == '}':
                    raise ValueError(f"Missing value for {first.text}")
                val = ts[pos]
                pos += 1
                if val.text == '{':
                    children = block(True)
                    if pos == len(ts):
                        raise ValueError(f"Unclosed block at {val.start}")
                    close = ts[pos]
                    pos += 1
                    result.append(Node(first.text, op, children, first.start, close.end, val.start, close.end))
                else:
                    result.append(Node(first.text, op, val.text, first.start, val.end, val.start, val.end))
            else:
                result.append(Node(None, None, first.text, first.start, first.end, first.start, first.end))
        if not nested and pos != len(ts):
            raise ValueError(f"Unexpected closing brace at {ts[pos].start}")
        return result

    return block()


def walk(nodes):
    for node in nodes:
        yield node
        if isinstance(node.value, list):
            yield from walk(node.value)


def edit(text, edits):
    """Apply disjoint (start, end, replacement) edits without reformatting source."""
    ordered = sorted(edits, key=lambda e: (e[0], e[1]))
    previous_end = -1
    for start, end, replacement in ordered:
        if start < previous_end or not 0 <= start <= end <= len(text):
            raise ValueError('Overlapping or invalid source edits')
        previous_end = end
    for start, end, replacement in reversed(ordered):
        text = text[:start] + replacement + text[end:]
    return text
