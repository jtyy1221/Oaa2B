#!/usr/bin/env python3
"""Keep the graph a tree, in place. Run by oaa2b_build on every sync.

    oaa2b_tree.py <vault-dir> [--dry-run]

Ten stars, one per branch, and every node has exactly one parent:
the home note names the hubs as plain text and links none of them, so the stars stay apart.
  * a note's parent is its folder hub, or the note in its own branch named in `parent:`
  * a data file's parent is its data hub, or the note that lists it in `children: [a, b]`
    (data files are raw, so the note adopts them and keeps the links; missing ones are added);
    a data file some note names as `parent:` (a log, such as home-log) hangs off the branch hub
  * a warning's parent is the one note named in its `about:` field
A link survives only between a node and its parent. Every other wikilink becomes plain text:
  * data files and warnings keep exactly the words a reader saw (only the brackets go)
  * prose notes keep the target's name in backticks, so an AI can still find it
Generated pages, the memory mirror and parked conflicts are left alone.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oaa2b_vault as cm  # noqa: E402

LINK = cm.LINK
BRANCH_KEYS = [b[0] for b in cm.BRANCHES]
SKIP = ("9-system/claude-code-memory/", "9-system/conflicts/", "9-system/warnings/data/", "9-system/warnings/resolved/")
UP_LINE = re.compile(r"^↑ \[\[[^\]]+\]\]\s*$")
WARN_UP = re.compile(r"^(↑|⚠️) \[\[[^\]]+\]\]\s*$")
CODE_SPAN = re.compile(r"(`+)(.+?)\1")


def branch(rel):
    top = rel.split("/")[0]
    return top if top in BRANCH_KEYS else None


def is_data(rel):
    return "data" in rel.split("/")[:-1]


def is_warning(rel):
    return rel.startswith("9-system/warnings/") and rel.count("/") == 2 and Path(rel).name.startswith(("P1-", "P2-"))


def up_hub(rel):
    parts = rel.split("/")
    if len(parts) == 2:
        return cm.BR[parts[0]][1]
    return cm.hub_name(f"{parts[0]}/{parts[1]}")


def managed(rel):
    """Files this pass may change: every note except generated pages and machine folders."""
    if "/" not in rel or rel.startswith(SKIP) or not rel.endswith(".md") or not branch(rel):
        return False
    stem = Path(rel).stem
    return not stem.isupper() or stem == "HANDOFF"


def index(vault):
    names = {}
    for p in vault.rglob("*"):
        if p.is_file() and not any(x.startswith(".") for x in p.relative_to(vault).parts):
            rel = p.relative_to(vault).as_posix()
            names.setdefault(p.name.lower(), rel)
            if p.suffix == ".md":
                names.setdefault(p.stem.lower(), rel)
    return names


def tree_map(vault, names=None):
    """rel -> stem of its one parent, for every note, data file and warning in a branch."""
    vault = Path(vault)
    names = names or index(vault)
    metas, nodes = {}, []
    for p in sorted(vault.rglob("*.md")):
        rel = p.relative_to(vault).as_posix()
        if any(x.startswith(".") for x in rel.split("/")) or "/" not in rel or not branch(rel) or rel.startswith(SKIP):
            continue
        if p.stem.isupper() and not is_warning(rel):
            continue
        nodes.append(rel)
        if not is_data(rel):
            metas[rel], _ = cm.front(p.read_text(encoding="utf-8", errors="replace"))
    want = {}
    for rel in nodes:
        meta = metas.get(rel, {})
        if is_warning(rel):
            want[rel] = (meta.get("about") or "").strip().strip("[]\"'")
            continue
        par = (meta.get("parent") or "").strip().strip("[]\"'")
        tgt = names.get(par.lower()) if par else None
        if tgt and tgt != rel and branch(tgt) == branch(rel) and tgt in nodes and not is_warning(tgt):
            want[rel] = Path(tgt).stem
    for rel in nodes:  # a note adopts data files, which cannot carry a parent: line themselves
        if is_data(rel) or is_warning(rel):
            continue
        for kid in re.split(r"[,\s]+", (metas[rel].get("children") or "").strip("[] ")):
            krel = names.get(kid.strip("[]\"'").lower()) if kid else None
            if krel and krel in nodes and is_data(krel) and branch(krel) == branch(rel) and krel not in want:
                want[krel] = Path(rel).stem
    # a cycle of parent: lines falls back to the folder hubs
    for rel in list(want):
        if is_warning(rel):
            continue
        seen, cur = {rel}, rel
        while cur in want and not is_warning(cur):
            nxt = names.get(want[cur].lower())
            if nxt is None or nxt in seen:
                break
            seen.add(nxt)
            cur = nxt
        else:
            continue
        if nxt in seen:
            for r in seen:
                want.pop(r, None)
    parent_stems = {v.lower() for k, v in want.items() if not is_warning(k)}
    out = {}
    for rel in nodes:
        if rel in want:
            out[rel] = want[rel]
        elif is_data(rel) and Path(rel).stem.lower() in parent_stems:
            out[rel] = cm.BR[branch(rel)][1]  # a log: straight off the branch hub
        elif is_data(rel):
            out[rel] = cm.hub_name("/".join(rel.split("/")[:-1][:2]))
        else:
            out[rel] = up_hub(rel)
    return out


def allowed(src, tgt, parents):
    if tgt is None:
        return False
    return parents.get(src, "").lower() == Path(tgt).stem.lower() or parents.get(tgt, "").lower() == Path(src).stem.lower()


def fix_text(rel, text, names, parents):
    meta, _ = cm.front(text)
    about = (meta.get("about") or "").strip().strip("[]\"'")
    raw = is_data(rel) or is_warning(rel)
    lines = text.split("\n")

    # where the body starts (after frontmatter, if the file opens with it)
    body = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                body = i + 1
                break

    def delink(m, target_rel):
        target, head, alias = m.group(1), m.group(2) or "", m.group(3)
        bare = target.rstrip("\\").strip()
        shown = alias[1:] if alias else bare + head
        if raw:
            return shown
        name = (Path(target_rel).stem if target_rel and target_rel.endswith(".md") else Path(target_rel).name) if target_rel else bare
        if alias and shown.strip().lower() != name.lower():
            return f"{shown} (`{name}{head}`)"
        return f"`{name}{head}`"

    def fix_segment(seg):
        def sub(m):
            bare = m.group(1).rstrip("\\").strip()
            tgt = names.get(bare.split("/")[-1].lower())
            return m.group(0) if allowed(rel, tgt, parents) else delink(m, tgt)
        return LINK.sub(sub, seg)

    # the navigation line under the frontmatter is set first, then kept out of the link pass
    first = next((i for i in range(body, len(lines)) if lines[i].strip()), None)
    nav = None
    if is_warning(rel):
        want = f"⚠️ [[{about}]]" if about and names.get(about.lower()) else None
        if first is not None and WARN_UP.match(lines[first]):
            if want:
                lines[first] = want
                nav = first
            else:
                del lines[first]
        elif want:
            lines[body:body] = [want]
            nav = body
    elif not raw:
        want = f"↑ [[{parents.get(rel) or up_hub(rel)}]]"
        if first is not None and UP_LINE.match(lines[first]):
            lines[first] = want
        else:
            lines[body:body] = [want, ""]
            first = body
        nav = first

    # a note that adopted data files keeps one link to each (the data side cannot hold it)
    if not raw:
        adopted = sorted(Path(r).stem for r, par in parents.items() if is_data(r) and par.lower() == Path(rel).stem.lower())
        text_now = "\n".join(lines)
        missing = [k for k in adopted if not re.search(r"\[\[" + re.escape(k) + r"(\]\]|\||#)", text_now)]
        if missing:
            while lines and not lines[-1].strip():
                lines.pop()
            if "## Data, kept word for word" not in text_now:
                lines += ["", "## Data, kept word for word", ""]
            start = sum(1 for l in lines if re.match(r"^\d+\. \[\[", l))
            lines += [f"{start + i}. [[{k}]]" for i, k in enumerate(missing, 1)]
            lines.append("")

    out, fenced = [], False
    for i, line in enumerate(lines):
        if i < body or i == nav:
            out.append(line)
            continue
        if line.lstrip().startswith("```"):
            fenced = not fenced
            out.append(line)
            continue
        if fenced or "[[" not in line:
            out.append(line)
            continue
        pieces, last = [], 0
        for m in CODE_SPAN.finditer(line):  # leave inline code alone
            pieces.append(fix_segment(line[last:m.start()]))
            pieces.append(m.group(0))
            last = m.end()
        pieces.append(fix_segment(line[last:]))
        out.append("".join(pieces))
    return "\n".join(out)


def visible_same(before, after):
    """Raw files: the words a reader sees must not change."""
    return cm.visible(before) == cm.visible(after)


def enforce(vault, dry=False):
    vault = Path(vault).resolve()
    names = index(vault)
    parents = tree_map(vault, names)
    changed, refused = [], []
    for p in sorted(vault.rglob("*.md")):
        rel = p.relative_to(vault).as_posix()
        if any(x.startswith(".") for x in rel.split("/")) or not managed(rel):
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        new = fix_text(rel, text, names, parents)
        if new == text:
            continue
        if is_data(rel) and not visible_same(text, new):
            refused.append(rel)
            continue
        if is_warning(rel):
            head_end = new.find("## History")
            if head_end > 0 and not visible_same(text[text.find("## History"):], new[head_end:]):
                refused.append(rel)
                continue
        changed.append(rel)
        if not dry:
            p.write_text(new, encoding="utf-8")
    return changed, refused


if __name__ == "__main__":
    c, r = enforce(sys.argv[1], dry="--dry-run" in sys.argv)
    print(f"changed {len(c)}, refused {len(r)}")
    for x in r:
        print("refused:", x)
