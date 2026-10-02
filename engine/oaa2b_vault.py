#!/usr/bin/env python3
"""Shared helpers for the Oaa2B engine: config, frontmatter, and every generated page.

Generated pages (UPPERCASE names, never edited by hand): the ten branch hubs, their sub-hubs,
the home note, INDEX, the WARNINGS board, START-HERE and the graph colours.
Every writer here writes a file only when its content changes, so an unchanged vault makes no churn.
Python 3.9 standard library only.
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oaa2b_platform as plat  # noqa: E402

ENGINE = Path(__file__).resolve().parent
CFG_PATH = Path(os.environ.get("OAA2B_CONFIG", str(ENGINE / "config.json")))
CFG = json.loads(CFG_PATH.read_text(encoding="utf-8")) if CFG_PATH.exists() else {}


def cfg_path(key, default=""):
    v = CFG.get(key, default)
    return Path(os.path.expanduser(v)) if v else None


DEFAULT_BRANCHES = [
    ["0-inbox", "INBOX", "📥", "FF8C00", "New notes from every AI, waiting to be filed"],
    ["1-me", "ME", "🪪", "2E86DE", "Who I am, my identities, and how the AIs talk to me"],
    ["2-work", "WORK", "🎧", "00B8A9", "The job, shifts, study, career"],
    ["3-business", "BUSINESS", "🏢", "9B59B6", "Ventures, clients and side projects"],
    ["4-money", "MONEY", "💰", "C79A00", "Cash flow, debt, and every statement"],
    ["5-home", "HOME", "🏡", "2ECC40", "The home: utilities, layout, kitchen, the home log"],
    ["6-life", "LIFE", "🌿", "5856D6", "Days, health, journal, trips, gear and play"],
    ["7-relationship", "RELATIONSHIP", "💐", "FF6FB5", "The people close to me"],
    ["8-builds", "BUILDS", "🛠️", "00A5BB", "Code, plugins, automations, and this system as a project"],
    ["9-system", "SYSTEM", "⚙️", "8E8E93", "Machine owned: the law, warnings, runs, handoff, mirrors"],
]
BRANCHES = [tuple(b) for b in CFG.get("branches", DEFAULT_BRANCHES)]
BR = {b[0]: b for b in BRANCHES}
HOME_NOTE = CFG.get("home_note", "home")
HUMAN = CFG.get("human", "the human")          # how the AIs address the owner
PERSONA = CFG.get("persona", "")               # optional shared name the AIs answer to
WARN_RGB = int(CFG.get("warning_colour", "262626"), 16)   # darker than data, so warnings recede
DATA_RGB = int(CFG.get("data_colour", "5A5A5A"), 16)

LINK = re.compile(r"\[\[([^\]\|#]+)(#[^\]\|]*)?(\|[^\]]*)?\]\]")


def visible(text):
    """What a reader sees: every wikilink reduced to its display text."""
    def show(m):
        target, head, alias = m.group(1).rstrip("\\"), m.group(2) or "", m.group(3)
        return alias[1:] if alias else target + head
    return LINK.sub(show, text)


def plain(s):
    s = re.sub(r"\s*—\s*", ", ", s)  # no em dash in anything generated
    return re.sub(r"\s+", " ", re.sub(r"[*_`]", "", s)).strip()


def front(text):
    m = re.match(r"^(?:\[\[[^\]]+\]\]\s*\n)?---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"')
    return meta, text[m.end():]


def summary_of(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    meta, body = front(text)
    for key in ("summary", "description"):
        if meta.get(key):
            return plain(meta[key])[:120]
    tl = re.search(r"## TL;DR\s*\n+\s*(?:1\.\s*)?(.+)", body)
    if tl:
        return tl.group(1).strip()[:120]
    for line in body.splitlines():
        line = line.strip()
        if line and not line.startswith(("#", "↑", "[[", "Related", "---", "|", ">")):
            return plain(line)[:120]
    return ""


def write_if_changed(path, text):
    path = Path(path)
    if path.exists() and path.read_text(encoding="utf-8", errors="replace") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    plat.write_text(path, text)
    return True


def hub_name(folder):
    parts = folder.split("/")
    base = BR[parts[0]][1]
    return base if len(parts) == 1 else f"{base}-{parts[1].upper()}"


# ---------------------------------------------------------------- warnings
def load_warnings(vault):
    made = []
    for p in sorted((Path(vault) / "9-system/warnings").glob("P[12]-*.md")):
        text = p.read_text(encoding="utf-8", errors="replace")
        meta, _ = front(text)
        num = int(meta.get("warning", "0") or 0)
        title = re.sub(r"^W-\d+\s*", "", meta.get("title", p.stem))
        m = re.search(r"Settles when: (.+)", text)
        made.append((meta.get("priority", "P2"), num, title, p.stem, meta.get("first_seen", ""),
                     meta.get("last_seen", ""), m.group(1).strip() if m else ""))
    return made


# ---------------------------------------------------------------- hubs, home, index, board
def nested(p, kids, depth=1):
    """A node's children, named as plain text under it: the hub shows the whole star, the graph keeps one link each."""
    lines = []
    for c in sorted(kids.get(p.stem.lower(), []), key=lambda c: c.stem):
        s = summary_of(c)
        lines.append("   " * depth + f"- `{c.stem}`" + (f" · {s}" if s else ""))
        if depth < 4:
            lines += nested(c, kids, depth + 1)
    return lines


def write_subhub(out, key, d, sub_hub, kids):
    mine = set(kids.get(sub_hub.lower(), []))
    items = sorted(p for p in d.rglob("*") if p.is_file() and p.stem != sub_hub
                   and ((p.suffix == ".md" and p in mine) or (p.suffix == ".html" and not p.stem.isupper())))
    label = "data, kept word for word" if d.name == "data" else d.name
    lines = [f"---\ntitle: {key} / {label}\nkind: hub\n---", f"↑ [[{BR[key][1]}]]", "",
             f"# {BR[key][2]} {key} / {label} · {len(items)} files", ""]
    for i, p in enumerate(items, 1):
        s = summary_of(p) if p.suffix == ".md" else "source file"
        lines.append(f"{i}. [[{p.name if p.suffix != '.md' else p.stem}]]" + (f" · {s}" if s else ""))
        if p.suffix == ".md":
            lines += nested(p, kids)
    write_if_changed(d / f"{sub_hub}.md", "\n".join(lines) + "\n")


def generate(out, warnings_made):
    import oaa2b_tree  # here, not at the top: oaa2b_tree imports this module
    out = Path(out)
    parents = oaa2b_tree.tree_map(out)
    kids = {}
    for rel, par in parents.items():
        if not oaa2b_tree.is_warning(rel):
            kids.setdefault(par.lower(), []).append(out / rel)
    counts = {}
    for key, hub, emoji, _, about in BRANCHES:
        bdir = out / key
        bdir.mkdir(exist_ok=True)
        subs = sorted(d for d in bdir.iterdir() if d.is_dir())
        total = sum(1 for p in bdir.rglob("*.md") if p.stem != hub and not p.stem.isupper())
        counts[key] = total
        lines = [f"---\ntitle: {emoji} {key}\nkind: hub\n---", f"🌟 Its own star. Home is `{HOME_NOTE}`, named, never linked.", "",
                 f"# {emoji} {key} · {total} notes", "", "## TL;DR", "", f"1. {about}.", ""]
        notes_here = sorted(kids.get(hub.lower(), []), key=lambda p: p.stem)
        if notes_here:
            lines += ["## Notes", ""]
            for i, p in enumerate(notes_here, 1):
                s = summary_of(p)
                lines.append(f"{i}. [[{p.stem}]]" + (f" · {s}" if s else ""))
                lines += nested(p, kids)
            lines.append("")
        for d in subs:
            if key == "9-system" and d.name == "warnings":
                lines += ["## Warnings", "", "1. [[WARNINGS]] · the board, one file per warning", ""]
                continue
            sub_hub = hub_name(f"{key}/{d.name}")
            n = len(kids.get(sub_hub.lower(), []))
            label = "Data, kept word for word" if d.name == "data" else d.name.capitalize()
            lines += [f"## {label}", "", f"1. [[{sub_hub}]] · {n} files", ""]
            write_subhub(out, key, d, sub_hub, kids)
        write_if_changed(bdir / f"{hub}.md", "\n".join(lines).rstrip() + "\n")

    # home note: names the branches, links none of them, so the ten stars stay apart
    p1 = sorted((w for w in warnings_made if w[0] == "P1"), key=lambda w: w[1])
    who = f"{HUMAN}'s" if HUMAN != "the human" else "The"
    home = [f"---\ntitle: {HOME_NOTE}\nkind: home\nnode_size: 100\n---", f"# 🧠 {HOME_NOTE}", "", "## TL;DR", "",
            f"1. {who} shared AI memory. Ten numbered branches; the folder, the filename prefix and the graph colour all name the same branch.",
            "2. AIs read `START-HERE` first. Everything is filed by the reconcile; AIs only add notes to the inbox.",
            "3. The graph is ten separate stars: each branch hub is the centre of its own star, and this note names the branches "
            "without linking them. Every node has one parent and one link: a note to its hub, or to the note named in its `parent:` "
            "line; a data file to its data hub, to the note that adopts it with `children:`, or (a log) straight to the branch hub. "
            "Warnings are the darkest grey dots, each tied to the one note it is about.", "",
            "## Branches", ""]
    for i, b in enumerate(BRANCHES, 1):
        home.append(f"{i}. {b[2]} **{b[0]}** · `{b[1]}` · {counts.get(b[0], 0)} notes · {b[4]}")
    home += ["", "## Needs you", ""]
    home += [f"{i}. W-{w[1]:03d} {w[2]}" for i, w in enumerate(p1[:9], 1)] or ["1. Nothing right now."]
    write_if_changed(out / f"{HOME_NOTE}.md", "\n".join(home) + "\n")

    idx = ["---\ntitle: INDEX\nkind: board\n---", f"↑ `{HOME_NOTE}`", "", "# INDEX", "",
           "One line per note, grouped by branch. Data files are listed in their branch hub.", ""]
    for b in BRANCHES:
        items = sorted(p for p in (out / b[0]).rglob("*.md") if "data" not in p.relative_to(out).parts
                       and (not p.stem.isupper() or p.stem.startswith(("P1-", "P2-"))))
        if not items:
            continue
        idx += [f"## {b[2]} {b[0]}", ""]
        idx += [f"{i}. `{p.relative_to(out).as_posix()}` · {summary_of(p)}" for i, p in enumerate(items, 1)]
        idx.append("")
    write_if_changed(out / "INDEX.md", "\n".join(idx))

    n1 = len([w for w in warnings_made if w[0] == "P1"])
    n2 = len([w for w in warnings_made if w[0] == "P2"])
    board = ["---\ntitle: WARNINGS\nkind: board\n---", "↑ [[SYSTEM]]", "", "# ⚠️ WARNINGS", "", "## TL;DR", "",
             f"1. {n1} need {HUMAN} (P1), {n2} are watched (P2).",
             "2. One file per warning, named priority, slug and number. Resolved ones move to `9-system/warnings/resolved/`.", ""]
    for prio, label in (("P1", f"Needs {HUMAN}"), ("P2", "Watched, self-healing or auto-repaired")):
        board += [f"## {prio}, {label}", ""]
        for i, w in enumerate(sorted((w for w in warnings_made if w[0] == prio), key=lambda w: w[1]), 1):
            board.append(f"{i}. [[{w[3]}|W-{w[1]:03d}]] {w[2]}" + (f" · since {w[4]}" if w[4] else ""))
        board.append("")
    write_if_changed(out / "9-system/warnings/WARNINGS.md", "\n".join(board))


# ---------------------------------------------------------------- graph colours
GRAPH_HIDDEN = ["9-system/claude-code-memory", "9-system/state", "9-system/renames", "9-system/obsidian",
                "9-system/conflicts", "9-system/inbox-done", "9-system/runs", "9-system/warnings/data",
                "9-system/warnings/resolved"]
GRAPH_HIDDEN_FILES = ["WARNINGS.md", "INDEX.md", "START-HERE.md"]


def graph_settings():
    """Colour groups (first match wins) and the filter that keeps boards and machine folders off the graph."""
    groups = [{"query": 'path:"9-system/warnings/"', "color": {"a": 1, "rgb": WARN_RGB}},
              {"query": 'path:"/data/"', "color": {"a": 1, "rgb": DATA_RGB}},
              {"query": f'file:"{HOME_NOTE}.md"', "color": {"a": 1, "rgb": 0xFFFFFF}}]
    groups += [{"query": f'path:"{b[0]}/"', "color": {"a": 1, "rgb": int(b[3], 16)}} for b in BRANCHES]
    search = " ".join([f'-path:"{h}"' for h in GRAPH_HIDDEN] + [f'-file:"{f}"' for f in GRAPH_HIDDEN_FILES])
    return {"colorGroups": groups, "search": search, "showTags": False}


def write_graph(out):
    return write_if_changed(Path(out) / "9-system/obsidian/graph.json", json.dumps(graph_settings(), indent=2))


# ---------------------------------------------------------------- START-HERE
def rules():
    """The rules in short. Core rules keep the system working; config `rules` adds house rules."""
    inbox = CFG.get("drive_inbox_id", "")
    repo = CFG.get("github_repo", "")
    where = []
    if inbox:
        where.append(f"Google Drive: `create_file` with `parentId` `{inbox}` (the 0-inbox folder), a title ending `.md`, "
                     "`contentMimeType` `text/markdown`, `disableConversionToGoogleType: true`.")
    if repo:
        where.append(f"GitHub: create `0-inbox/<name>` on `{repo}` main.")
    address = f"Call the owner **{HUMAN}**." + (f" You are **{PERSONA}**." if PERSONA else "")
    core = [
        address,
        "**Write only by creating a new file in `0-inbox`**, named `<slug>-<agent>-<surface>-YYYY-MM-DD-HHMM.md`, "
        "frontmatter on line 1 (agent, surface, created, kind, summary), then the line `↑ [[INBOX]]`. "
        "Never edit, move, rename or delete a file you did not create. " + " ".join(where),
        "Every memory add, amend or forget goes to **both** your platform memory and the inbox.",
        "**Never rewrite anything in a `data/` folder.** Raw data is read only.",
        f"When two sources disagree, {HUMAN}'s own word wins, then documents, then AI observations, then AI inferences.",
        "**One parent, one link.** A note links only up to its parent (`↑ [[HUB]]`, or the note named in its `parent:` line, "
        "same branch). Name anything else, data files included, as plain text in backticks; the sync turns stray links into "
        "plain text. A warning links to exactly one note, the one it is about. The sync strips the time stamp from inbox names.",
    ]
    return core + list(CFG.get("rules", []))


def start_here(out, warnings_made):
    out = Path(out)
    hf = out / "9-system/handoff/HANDOFF.md"
    handoff_body = ""
    if hf.exists():
        _, handoff_body = front(hf.read_text(encoding="utf-8"))
        handoff_body = re.sub(r"^↑ \[\[[^\]]+\]\]\s*\n", "", handoff_body.strip())
        handoff_body = re.sub(r"^# .*\n", "", handoff_body).strip()
    hb = out / "9-system/state/HEARTBEAT.md"
    m = re.search(r"last_sync: (.+)", hb.read_text(encoding="utf-8")) if hb.exists() else None
    beat = m.group(1) if m else "unknown"
    p1 = [w for w in warnings_made if w[0] == "P1"]
    lines = ["---", "title: START-HERE", "kind: board", "---", "# 🧭 START-HERE", "",
             "Every AI reads this first. It is written by a script; never edit it.", "",
             "## Trust", "",
             f"1. Last sync: **{beat}**. Older than 2 hours means the sync is down; treat what you read as possibly stale.",
             f"2. Open warnings that need {HUMAN}: **{len(p1)}** → [[WARNINGS]].", "",
             "## The rules in short (full law → [[sys-law]])", ""]
    lines += [f"{i}. {r}" for i, r in enumerate(rules(), 1)]
    lines += ["", "## Live handoff", "", handoff_body or "Nothing handed off yet.", "", "## Where to look", ""]
    lines += [f"{i}. {b[2]} **{b[0]}** → [[{b[1]}]] · {b[4]}" for i, b in enumerate(BRANCHES, 1)]
    lines += ["", "## How to find a fact", "",
              "1. Open the branch hub above, then the note. Every hub line carries a one-line summary.",
              "2. Not sure of the branch: [[INDEX]] lists every note with its summary.",
              "3. Remember an old name: `9-system/renames/RENAMES.md` maps old to new.", ""]
    write_if_changed(out / "START-HERE.md", "\n".join(lines))
