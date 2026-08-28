"""
Project Concord | Reverse-engineered ERD generator (Graphviz)
================================================================
Parses 001_schema.sql directly (rather than hand-copying table/column
lists into a diagram tool) so the diagram can never silently drift
from the actual schema. Renders entity boxes with PK/FK markers and
real crow's-foot relationship lines, entirely offline -- no CDN, no
browser, no JavaScript required to view the output.
"""

import re
from pathlib import Path

SCHEMA = Path("001_schema.sql").read_text()

MODULE_COLORS = {
    "hub":  ("#1c2b4a", "#e8ecf5"),
    "ret":  ("#1f5f7a", "#e3f0f4"),
    "log":  ("#2f6d5c", "#e6f2ee"),
    "vfs":  ("#8c2f39", "#f7e6e7"),
    "agr":  ("#3f6b2b", "#eef4e7"),
    "prop": ("#5b3a7a", "#efe7f5"),
}
MODULE_NAMES = {
    "hub": "CORE SERVICES HUB", "ret": "MERIDIAN RETAIL", "log": "CONCORD LOGISTICS",
    "vfs": "VERIDIAN FINANCIAL SERVICES", "agr": "AGRICORE", "prop": "VERIDIAN PROPERTIES",
}

# ---------------------------------------------------------------
# 1. Parse every CREATE TABLE block: table name + column defs
# ---------------------------------------------------------------
table_pattern = re.compile(r"create table (\w+) \((.*?)\n\);", re.DOTALL)
tables = {}
for match in table_pattern.finditer(SCHEMA):
    name, body = match.group(1), match.group(2)
    cols = []
    for raw_line in body.split("\n"):
        line = raw_line.strip().rstrip(",")
        if not line or line.startswith("--") or line.startswith("check") or line.startswith("unique"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        col_name = parts[0]
        is_pk = "primary" in line and "key" in line
        is_fk = "references" in line
        fk_target = None
        if is_fk:
            fk_match = re.search(r"references (\w+)\(", line)
            fk_target = fk_match.group(1) if fk_match else None
        cols.append({"name": col_name, "pk": is_pk, "fk": is_fk, "fk_target": fk_target})
    tables[name] = cols

print(f"Parsed {len(tables)} tables from 001_schema.sql")

# ---------------------------------------------------------------
# 2. Parse ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY (deferred FKs)
# ---------------------------------------------------------------
alter_pattern = re.compile(
    r"alter table (\w+)\s+add constraint \w+\s+foreign key \((\w+)\) references (\w+)\(", re.IGNORECASE)
deferred_fks = []
for m in alter_pattern.finditer(SCHEMA):
    table, col, target = m.group(1), m.group(2), m.group(3)
    deferred_fks.append((table, col, target))
    for c in tables[table]:
        if c["name"] == col:
            c["fk"] = True
            c["fk_target"] = target

print(f"Parsed {len(deferred_fks)} deferred (ALTER TABLE) foreign keys")

# ---------------------------------------------------------------
# 3. Build edge list: (from_table, to_table, from_col)
# ---------------------------------------------------------------
edges = []
for tname, cols in tables.items():
    for c in cols:
        if c["fk"] and c["fk_target"]:
            edges.append((tname, c["fk_target"], c["name"]))

print(f"Total relationships: {len(edges)}")

# ---------------------------------------------------------------
# 4. Emit Graphviz DOT
# ---------------------------------------------------------------
def module_of(table_name):
    return table_name.split("_")[0]

def html_label(tname, cols):
    border, fill = MODULE_COLORS[module_of(tname)]
    rows = ""
    for c in cols:
        marker = ""
        if c["pk"]:
            marker = '<font color="#b8860b"><b>PK</b></font>'
        elif c["fk"]:
            marker = '<font color="#1f5f7a"><b>FK</b></font>'
        weight = "b" if c["pk"] else ""
        name_cell = f"<{weight}>{c['name']}</{weight}>" if weight else c["name"]
        rows += (f'<tr><td align="left" port="{c["name"]}" bgcolor="white">'
                  f'{name_cell}</td><td align="right" bgcolor="white">{marker}</td></tr>')
    return (f'<<table border="1" cellborder="0" cellspacing="0" cellpadding="4" bgcolor="{fill}" color="{border}">'
            f'<tr><td colspan="2" bgcolor="{border}"><font color="white"><b>{tname}</b></font></td></tr>'
            f'{rows}</table>>')

dot = []
dot.append('digraph ProjectConcordERD {')
dot.append('  rankdir=LR;')
dot.append('  graph [fontname="Helvetica", nodesep=0.35, ranksep=1.1, splines=ortho, bgcolor="white"];')
dot.append('  node [shape=plaintext, fontname="Helvetica"];')
dot.append('  edge [fontname="Helvetica", fontsize=9, color="#73726c", arrowsize=0.8];')

for module, label in MODULE_NAMES.items():
    border, fill = MODULE_COLORS[module]
    module_tables = [t for t in tables if module_of(t) == module]
    dot.append(f'  subgraph cluster_{module} {{')
    dot.append(f'    label="{label}"; fontname="Helvetica-Bold"; fontsize=13; '
               f'color="{border}"; style="rounded"; bgcolor="{fill}22";')
    for t in module_tables:
        dot.append(f'    "{t}" [label={html_label(t, tables[t])}];')
    dot.append('  }')

for src, dst, col in edges:
    # crow's-foot style: "many" end (source, FK side) gets a crow;
    # "one" end (target, PK side) gets a tee bar
    dot.append(f'  "{src}":"{col}" -> "{dst}" '
                f'[arrowhead=crow, arrowtail=tee, dir=both, color="#73726c"];')

dot.append('}')

Path("project_concord_erd.dot").write_text("\n".join(dot))
print("Wrote project_concord_erd.dot")
