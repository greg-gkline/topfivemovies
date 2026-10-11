"""Read table rows straight from the phpMyAdmin dumps in legacy/sql/.

The dumps are written with SET NAMES utf8mb4, so the file is UTF-8 even though the
tables are declared latin1. Reading the file as UTF-8 is the latin1 -> UTF-8 step.
"""

import re

_INSERT = re.compile(r"INSERT INTO `(\w+)` \(([^)]*)\) VALUES\s*", re.S)
_NUMBER = re.compile(r"NULL|-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")
_ESCAPES = {"0": "\0", "b": "\b", "n": "\n", "r": "\r", "t": "\t", "Z": "\x1a"}


def _parse_values(sql, pos):
    """Parse `(v, v, ...), (...);` starting at pos. Returns (rows, end)."""
    rows = []
    n = len(sql)
    while True:
        while sql[pos].isspace():
            pos += 1
        if sql[pos] != "(":
            raise ValueError(f"expected '(' at offset {pos}")
        pos += 1
        row = []
        while True:
            while sql[pos].isspace():
                pos += 1
            c = sql[pos]
            if c == "'":
                pos += 1
                buf = []
                while True:
                    c = sql[pos]
                    if c == "\\":
                        nxt = sql[pos + 1]
                        buf.append(_ESCAPES.get(nxt, nxt))
                        pos += 2
                    elif c == "'":
                        if pos + 1 < n and sql[pos + 1] == "'":
                            buf.append("'")
                            pos += 2
                        else:
                            pos += 1
                            break
                    else:
                        buf.append(c)
                        pos += 1
                row.append("".join(buf))
            else:
                m = _NUMBER.match(sql, pos)
                if not m:
                    raise ValueError(f"unexpected value at offset {pos}: {sql[pos:pos + 20]!r}")
                tok = m.group(0)
                if tok == "NULL":
                    row.append(None)
                elif re.fullmatch(r"-?\d+", tok):
                    row.append(int(tok))
                else:
                    row.append(float(tok))
                pos = m.end()
            while sql[pos].isspace():
                pos += 1
            if sql[pos] == ",":
                pos += 1
                continue
            if sql[pos] == ")":
                pos += 1
                break
            raise ValueError(f"expected ',' or ')' at offset {pos}")
        rows.append(row)
        while sql[pos].isspace():
            pos += 1
        if sql[pos] == ",":
            pos += 1
            continue
        if sql[pos] == ";":
            return rows, pos + 1
        raise ValueError(f"expected ',' or ';' at offset {pos}")


def read_tables(path):
    """Return {table: [ {column: value} ]} for every INSERT in the dump."""
    with open(path, encoding="utf-8") as f:
        sql = f.read()
    tables = {}
    pos = 0
    while True:
        m = _INSERT.search(sql, pos)
        if not m:
            return tables
        table = m.group(1)
        cols = [c.strip().strip("`") for c in m.group(2).split(",")]
        rows, pos = _parse_values(sql, m.end())
        for row in rows:
            if len(row) != len(cols):
                raise ValueError(f"{table}: row has {len(row)} values, expected {len(cols)}")
            tables.setdefault(table, []).append(dict(zip(cols, row)))
