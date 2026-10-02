#!/usr/bin/env python3
"""Oaa2B view: export the committed shadow tree one way into the iCloud Obsidian folder.

    oaa2b_view.py [--force]

Runs every 180 s, and only does work when the relay's HEAD moved. The iCloud folder is a
view you look at for the graph (Mac, iPhone, iPad); nothing in it is ever read back into the vault.
  * overwrites are backed up first (view-overwrites/)
  * a file edited on a device is rescued to view-rescue/ before it is overwritten
  * files the vault no longer has are MOVED to view-removed/, never deleted
  * .obsidian keeps your settings; only the colour groups and the graph filter are merged in
"""
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

OPS = Path(__file__).resolve().parent
sys.path.insert(0, str(OPS))
import oaa2b_vault as vt  # noqa: E402

SHADOW = vt.cfg_path("shadow")
VIEW = vt.cfg_path("view")
STATE = vt.cfg_path("state")
BACKUPS = vt.cfg_path("backups")
LOG = vt.cfg_path("log").with_name("view.log")
STAMP = datetime.now().strftime("%Y-%m-%d-%H%M%S")
EXPORT_EXT = {".md", ".html"}
HIDE = ("9-system/conflicts/",)


def sha(p):
    return hashlib.sha1(p.read_bytes()).hexdigest()


def files(root):
    out = {}
    for p in root.rglob("*"):
        if p.is_file() and p.suffix in EXPORT_EXT:
            rel = p.relative_to(root).as_posix()
            if rel.startswith(".") or "/." in rel or rel.startswith(HIDE):
                continue
            out[rel] = p
    return out


def log(**kw):
    kw["t"] = datetime.now().astimezone().isoformat(timespec="seconds")
    with LOG.open("a") as fh:
        fh.write(json.dumps(kw, ensure_ascii=False) + "\n")


def merge_graph():
    src = SHADOW / "9-system/obsidian/graph.json"
    if not src.exists():
        return
    want = json.loads(src.read_text())
    dst = VIEW / ".obsidian/graph.json"
    have = json.loads(dst.read_text()) if dst.exists() else {}
    changed = False
    for key in ("colorGroups", "search", "showTags"):
        if key in want and have.get(key) != want[key]:
            have[key] = want[key]
            changed = True
    if changed:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(have, indent=2))


def main():
    head_file = STATE / "last-head"
    seen_file = STATE / "last-view-head"
    head = head_file.read_text().strip() if head_file.exists() else ""
    if "--force" not in sys.argv and seen_file.exists() and seen_file.read_text().strip() == head:
        return
    if not VIEW.exists() or not SHADOW.exists():
        log(event="blocked", reason="view or shadow folder missing")
        return
    src, dst = files(SHADOW), files(VIEW)
    manifest_path = STATE / "view-manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    wrote = removed = rescued = 0
    for rel, p in src.items():
        target = VIEW / rel
        new = sha(p)
        if target.exists():
            cur = sha(target)
            if cur == new:
                manifest[rel] = new
                continue
            if rel in manifest and cur != manifest[rel]:  # edited on a device since our last export
                keep = BACKUPS / "view-rescue" / STAMP / rel
                keep.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, keep)
                rescued += 1
            back = BACKUPS / "view-overwrites" / STAMP / rel
            back.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, back)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
        manifest[rel] = new
        wrote += 1
    for rel, p in dst.items():
        if rel not in src:
            gone = BACKUPS / "view-removed" / STAMP / rel
            gone.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(gone))
            manifest.pop(rel, None)
            removed += 1
    # tidy folders the move left empty
    for d in sorted((x for x in VIEW.rglob("*") if x.is_dir() and not x.name.startswith(".")), key=lambda x: -len(x.parts)):
        if ".obsidian" in d.parts:
            continue
        rest = [x for x in d.iterdir()]
        if rest and all(x.is_file() and x.name.startswith(".") for x in rest):
            for x in rest:  # only dotfiles left (.DS_Store, .mirror-managed): move them out too
                gone = BACKUPS / "view-removed" / STAMP / x.relative_to(VIEW)
                gone.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(x), str(gone))
        try:
            d.rmdir()
        except OSError:
            pass
    merge_graph()
    manifest_path.write_text(json.dumps(manifest))
    seen_file.write_text(head)
    if wrote or removed or rescued:
        log(event="export", wrote=wrote, removed=removed, rescued=rescued, head=head[:9])


if __name__ == "__main__":
    main()
