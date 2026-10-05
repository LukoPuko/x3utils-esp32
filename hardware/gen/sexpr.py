"""Minimal S-expression reader/writer for KiCad files.

Atoms are kept as Python strings; quoted strings are wrapped in `Q` so they
round-trip with their quotes. Lists are Python lists.
"""

import re


class Q(str):
    """A quoted string atom."""


_TOKEN = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)


def parse(text):
    stack = [[]]
    pos = 0
    n = len(text)
    while pos < n:
        m = _TOKEN.match(text, pos)
        if not m:
            if text[pos:].strip() == "":
                break
            raise ValueError("bad sexpr near %r" % text[pos:pos + 40])
        pos = m.end()
        if m.group(1):
            stack.append([])
        elif m.group(2):
            done = stack.pop()
            stack[-1].append(done)
        elif m.group(3) is not None:
            stack[-1].append(Q(m.group(3).replace('\\"', '"').replace("\\\\", "\\")))
        else:
            stack[-1].append(m.group(4))
    return stack[0]


def dump(node, indent=0):
    """Serialise, preserving element order (KiCad's parser is order-sensitive).

    Simple lists stay on one line; lists containing lists break onto new lines.
    """
    if isinstance(node, Q):
        return '"' + node.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(node, str):
        return node
    if isinstance(node, (int, float)):
        return fmt_num(node)
    if all(not isinstance(x, list) for x in node):
        return "(" + " ".join(dump(x) for x in node) + ")"
    out = "("
    first = True
    for x in node:
        if isinstance(x, list) and any(isinstance(y, list) for y in x):
            out += "\n" + "  " * (indent + 1) + dump(x, indent + 1)
        else:
            out += ("" if first else " ") + dump(x, indent + 1)
        first = False
    return out + ")"


def fmt_num(v):
    if isinstance(v, int):
        return str(v)
    s = ("%.4f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def find(node, key):
    """First child list whose head is `key`."""
    for x in node:
        if isinstance(x, list) and x and x[0] == key:
            return x
    return None


def find_all(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]
