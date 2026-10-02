#!/usr/bin/env python3
"""Oaa2B relay: Google Drive (master) <-> local shadow clone <-> GitHub.

    oaa2b_relay.py [--actor NAME] [--dry-run]

First run on a new vault: --actor migration (lifts the bulk-change pause once).

One cycle, run by launchd every 36 s:
  1. lock, pause and safety guards; strip the time stamp from new inbox, warning and
     handoff-history names, in Drive and the shadow together (old -> new goes in RENAMES)
  2. Drive -> shadow: copy new and changed files (never deletes; a file missing from
     Drive is held and listed, not removed)
  3. optional Claude Code memory mirror -> shadow (script-owned folder)
  4. rebuild generated files in the shadow, commit
  5. fetch + merge GitHub; a clash keeps Drive's version and parks GitHub's copy;
     a deletion arriving from GitHub is refused and restored
  6. write back into Drive, in place and after a backup, every file the shadow has
     newer than Drive (from GitHub or from the rebuild)
  7. push, heartbeat, log

Git runs only in the shadow clone on local disk, never inside Drive or iCloud.
Python 3.9 stdlib only.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HOME = Path.home()
OPS = Path(__file__).resolve().parent
sys.path.insert(0, str(OPS))
import oaa2b_platform as plat  # noqa: E402
import oaa2b_vault as vt  # noqa: E402

CFG = vt.CFG
if not CFG:
    sys.exit(f"no config at {vt.CFG_PATH}; copy config.example.json to config.json and fill it in")
VAULT = vt.cfg_path("vault")                              # Drive master
SHADOW = vt.cfg_path("shadow")                            # local clone, the only git work tree
STATE = vt.cfg_path("state")
BACKUPS = vt.cfg_path("backups")
MEMORY_SRC = vt.cfg_path("memory_src")                    # optional: Claude Code auto-memory folder
LOG = vt.cfg_path("log")
QUARANTINE = vt.cfg_path("quarantine") or VAULT.parent / "Files/_quarantine"
BRANCH = CFG.get("branch", "main")
HUMAN = vt.HUMAN

SCRIPT_OWNED = ("9-system/claude-code-memory/",)          # mirrored with deletions
SKIP_PARTS = {".git", ".obsidian", ".DS_Store", ".tmp.drivedownload", ".tmp.driveupload", "desktop.ini", "Thumbs.db"}
TEXT_EXT = {".md", ".html", ".json", ".csv", ".txt", ".py", ".svg"}
QUIET_SECONDS = 21
MIN_FREE_GB = 9
MAX_CHANGES = 33                                          # more than this in one cycle pauses the relay

ACTOR = "drive"
DRY = "--dry-run" in sys.argv
if "--actor" in sys.argv:
    ACTOR = sys.argv[sys.argv.index("--actor") + 1]

STAMP = datetime.now().strftime("%Y-%m-%d-%H%M%S")
NOW = datetime.now().astimezone()


def log(event, **kw):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    kw.update(t=NOW.isoformat(timespec="seconds"), event=event, actor=ACTOR)
    with LOG.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(kw, ensure_ascii=False) + "\n")
    if LOG.stat().st_size > 3 * 1024 * 1024:
        LOG.rename(LOG.with_suffix(f".{STAMP}.log"))


def git(*args, check=True, capture=True):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    r = subprocess.run(["git", "-C", str(SHADOW), "-c", "http.lowSpeedLimit=1000", "-c", "http.lowSpeedTime=33", *args],
                       capture_output=capture, text=True, env=env)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()[:400]}")
    return r.stdout.strip() if capture else ""


def sha(path):
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def listing(root):
    out = {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if set(rel.split("/")) & SKIP_PARTS or p.name.startswith("~$") or p.name == "Icon\r":
            continue
        if rel.startswith(".") and "/" not in rel:
            continue  # .gitignore, .gitattributes and friends live only in the shadow
        out[rel] = p
    return out


def write_in_place(src, dst):
    """Overwrite dst's bytes without replacing the file, so Drive keeps its file ID and history."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    data = src.read_bytes()
    with open(dst, "r+b" if dst.exists() else "wb") as fh:
        fh.seek(0)
        fh.write(data)
        fh.truncate()


def backup(path, kind):
    if path.exists():
        rel = path.relative_to(VAULT) if str(path).startswith(str(VAULT)) else Path(path.name)
        dst = BACKUPS / kind / STAMP / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst)


STAMPED = re.compile(r"^(?P<base>.+?)-\d{4}-\d{2}-\d{2}-\d{4}$")    # <slug>-<agent>-<surface>-YYYY-MM-DD-HHMM
WARN_DATED = re.compile(r"^(?P<base>P[12]-.+-w\d+)-\d{4}-\d{2}-\d{2}$")  # P2-<slug>-wNNN-YYYY-MM-DD
AGENTS = {"claude", "grok", "gemini", "gpt", "chatgpt", "codex", "copilot", "perplexity"}
SURFACES = {"code", "cowork", "voice", "chat", "desktop", "web", "mobile", "app", "ios", "android", "ipad", "iphone", "cli", "api", "browser"}
STAMP_DIRS = ("0-inbox", "9-system/handoff/history", "9-system/warnings")


def slug_of(path):
    """The name without its stamp, or None when it carries none. Graph nodes show the slug only."""
    m = WARN_DATED.match(path.stem)
    if m and path.parent.name == "warnings":
        return m.group("base")
    m = STAMPED.match(path.stem)
    if not m:
        return None
    base = m.group("base")
    meta = dict(re.findall(r"^(agent|surface):\s*(\S+)\s*$", path.read_text(encoding="utf-8", errors="replace")[:1500], re.M))
    surface, agent = meta.get("surface", "").strip("\"'"), meta.get("agent", "").strip("\"'")
    toks = base.split("-")
    if surface and base.endswith("-" + surface):
        base = base[:-len(surface) - 1]
    elif len(toks) > 2 and toks[-1] in SURFACES and toks[-2] in AGENTS:
        base = base.rsplit("-", 1)[0]
    if agent and base.endswith("-" + agent):
        base = base[:-len(agent) - 1]
    elif base.rsplit("-", 1)[-1] in AGENTS and "-" in base:
        base = base.rsplit("-", 1)[0]
    return base or None


def strip_stamps():
    taken = {p.stem.lower() for p in VAULT.rglob("*.md")}
    renames = []
    for d in STAMP_DIRS:
        for p in sorted((VAULT / d).glob("*.md")):
            base = slug_of(p)
            if not base:
                continue
            new, n = base, 2
            while new.lower() in taken:
                new, n = f"{base}-{n}", n + 1
            dst = p.with_name(new + p.suffix)
            old_rel, new_rel = p.relative_to(VAULT).as_posix(), dst.relative_to(VAULT).as_posix()
            os.rename(p, dst)
            taken.discard(p.stem.lower())
            taken.add(new.lower())
            if (SHADOW / old_rel).exists():
                if git("ls-files", "--", old_rel):
                    git("mv", "-f", "--", old_rel, new_rel)
                else:
                    (SHADOW / old_rel).rename(SHADOW / new_rel)
            renames.append((old_rel, new_rel))
    if renames:
        rn = SHADOW / "9-system/renames/RENAMES.md"
        text = rn.read_text(encoding="utf-8") if rn.exists() else "# RENAMES\n\n"
        num = len(re.findall(r"^\d+\. ", text, re.M))
        add = "".join(f"{num + i}. `{o}` → `{n}` · stamp stripped {NOW.strftime('%Y-%m-%d %H:%M')}\n" for i, (o, n) in enumerate(renames, 1))
        rn.parent.mkdir(parents=True, exist_ok=True)
        plat.write_text(rn, text.rstrip("\n") + "\n" + add)
        log("stamps-stripped", paths=[n for _, n in renames])


def guards():
    if not VAULT.exists():
        return "Drive vault folder not found; is Google Drive running and signed in?"
    sentinel = VAULT / "9-system/state/vault-id"
    mine = STATE / "vault-id"
    if (not sentinel.exists() or not mine.exists()
            or sentinel.read_text(encoding="utf-8").strip() != mine.read_text(encoding="utf-8").strip()):
        return "vault-id sentinel missing or different; refusing to sync the wrong folder"
    free = shutil.disk_usage(str(HOME)).free / 1e9
    if free < MIN_FREE_GB:
        return f"only {free:.1f} GB free"
    if plat.online_only(VAULT):
        return "some Drive files are online-only placeholders; mark the vault folder Available offline"
    newest = max((p.stat().st_mtime for p in VAULT.rglob("*.md")), default=0)
    own = STATE / "own-write-mtime"  # the relay's own write-backs don't count as someone typing
    own_t = float(own.read_text(encoding="utf-8")) if own.exists() else 0.0
    if newest > own_t + 1 and time.time() - newest < QUIET_SECONDS:
        return "quiet"  # someone is writing right now; try next cycle
    if (SHADOW / ".git/MERGE_HEAD").exists():
        return "a merge is in progress in the shadow"
    return None


def main():
    STATE.mkdir(parents=True, exist_ok=True)
    lock = STATE / "lock"
    try:
        lock.mkdir()
    except FileExistsError:
        if time.time() - lock.stat().st_mtime < 9 * 60:
            return
        lock.rmdir()
        lock.mkdir()
    try:
        cycle()
    except Exception as e:  # never die silently: log it and show it on the heartbeat
        log("error", error=str(e)[:500])
        heartbeat(f"error: {str(e)[:120]}")
    finally:
        lock.rmdir()


def cycle():
    pause = STATE / "PAUSE"
    if pause.exists() and time.time() - pause.stat().st_mtime < 33 * 60 and ACTOR != "reconcile":
        return
    why = guards()
    if why == "quiet":
        return
    if why:
        log("blocked", reason=why)
        heartbeat(f"blocked: {why}")
        return

    if not DRY:
        strip_stamps()
    drive = listing(VAULT)
    shadow_tracked = set(git("ls-files").splitlines())

    # 1. Drive -> shadow (new and changed only; never deletes)
    changed = []
    drive_sha = {}
    for rel, p in drive.items():
        if rel.startswith(SCRIPT_OWNED):
            continue
        if p.suffix == ".gdoc" or p.suffix == ".gsheet" or p.suffix == ".gslides":
            log("quarantine", path=rel)
            q = QUARANTINE / STAMP / rel
            q.parent.mkdir(parents=True, exist_ok=True)
            if not DRY:
                shutil.move(str(p), str(q))
            continue
        s = sha(p)
        drive_sha[rel] = s
        target = SHADOW / rel
        if not target.exists() or sha(target) != s:
            changed.append(rel)
    missing = sorted(r for r in shadow_tracked if r not in drive and not r.startswith(SCRIPT_OWNED) and not r.startswith("."))
    if len(changed) > MAX_CHANGES and ACTOR not in ("reconcile", "migration"):
        pause.touch()
        log("paused", reason=f"{len(changed)} changed files in one cycle", sample=changed[:9])
        heartbeat(f"paused: {len(changed)} files changed at once, waiting for {HUMAN}")
        return
    for rel in changed:
        if not DRY:
            dst = SHADOW / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(VAULT / rel, dst)
    pend = STATE / "pending-deletes.tsv"
    pend_text = "".join(f"{r}\n" for r in missing)
    held_changed = not pend.exists() or pend.read_text(encoding="utf-8") != pend_text
    plat.write_text(pend, pend_text)

    # 2. Claude Code memory mirror (script-owned, deletions mirrored)
    mem_dst = SHADOW / "9-system/claude-code-memory"
    if MEMORY_SRC and MEMORY_SRC.exists() and any(MEMORY_SRC.glob("*.md")) and not DRY:
        mem_dst.mkdir(parents=True, exist_ok=True)
        (mem_dst / ".mirror-managed").touch()
        want = {p.name for p in MEMORY_SRC.glob("*.md")}
        for p in MEMORY_SRC.glob("*.md"):
            d = mem_dst / p.name
            if not d.exists() or sha(d) != sha(p):
                shutil.copy2(p, d)
        for d in mem_dst.glob("*.md"):
            if d.name not in want and d.name != "SYSTEM-CLAUDE-CODE-MEMORY.md":
                d.unlink()

    # 3. rebuild generated files, commit what Drive and the mirror brought
    if not DRY:
        sys.path.insert(0, str(OPS))
        import oaa2b_build
        oaa2b_build.build(SHADOW)
    git("add", "-A", "--", ".", ":!*.icloud")
    for rel in missing:  # held deletes: never commit them
        git("reset", "-q", "--", rel, check=False)
        git("checkout", "--", rel, check=False)
    if git("status", "--porcelain"):
        if not DRY:
            git("commit", "-q", "-m", f"vault: {NOW.strftime('%Y-%m-%d %H:%M')}", "-m", f"Oaa2B-Actor: {ACTOR}")
    before = git("rev-parse", "HEAD")

    # 4. GitHub, both ways
    fetched = git("fetch", "-q", "origin", BRANCH, check=False) is not None
    ahead_remote = git("rev-list", "--count", f"HEAD..origin/{BRANCH}", check=False) or "0"
    conflicts = []
    if ahead_remote != "0" and not DRY:
        r = subprocess.run(["git", "-C", str(SHADOW), "merge", "--no-ff", "--no-commit", f"origin/{BRANCH}"],
                           capture_output=True, text=True)
        unmerged = git("diff", "--name-only", "--diff-filter=U", check=False).splitlines()
        for rel in unmerged:
            theirs = subprocess.run(["git", "-C", str(SHADOW), "show", f"origin/{BRANCH}:{rel}"], capture_output=True)
            park = SHADOW / "9-system/conflicts" / STAMP / (rel.replace("/", "__") + ".github.md")
            park.parent.mkdir(parents=True, exist_ok=True)
            park.write_bytes(theirs.stdout)
            git("checkout", "--ours", "--", rel, check=False)
            git("add", "--", rel)
            conflicts.append(rel)
        # a deletion arriving from GitHub is refused
        deleted = git("diff", "--cached", "--name-only", "--diff-filter=D", before, check=False).splitlines()
        for rel in deleted:
            if rel.startswith(SCRIPT_OWNED):
                continue
            git("checkout", before, "--", rel, check=False)
            log("refused-delete", path=rel)
        git("add", "-A")
        git("commit", "-q", "--no-edit", "-m", f"merge(github): {NOW.strftime('%Y-%m-%d %H:%M')}",
            "-m", "Oaa2B-Actor: github", check=False)
        if conflicts:
            log("conflict", paths=conflicts)
        import oaa2b_build
        oaa2b_build.build(SHADOW)
        git("add", "-A")
        if git("status", "--porcelain"):
            git("commit", "-q", "-m", f"build: {NOW.strftime('%Y-%m-%d %H:%M')}", "-m", "Oaa2B-Actor: build")

    # 5. write back into Drive everything the shadow has that Drive doesn't
    wrote = []
    for rel, p in listing(SHADOW).items():
        if rel.startswith("9-system/state/vault-id"):
            continue
        in_drive = VAULT / rel
        if rel in missing:
            continue  # held delete: don't resurrect it in Drive
        if in_drive.exists():
            now_sha = sha(in_drive)
            if now_sha != drive_sha.get(rel, now_sha):
                continue  # Drive changed during this cycle; Drive wins, next cycle picks it up
            if now_sha == sha(p):
                continue
        if not DRY:
            backup(in_drive, "drive-overwrites")
            write_in_place(p, in_drive)
        wrote.append(rel)
    if wrote and not DRY:
        plat.write_text(STATE / "own-write-mtime",
                        str(max((VAULT / r).stat().st_mtime for r in wrote if (VAULT / r).exists())))
    # script-owned folders mirror deletions into Drive too
    for rel, p in listing(VAULT).items():
        if rel.startswith(SCRIPT_OWNED) and not (SHADOW / rel).exists() and not DRY:
            backup(p, "drive-overwrites")
            p.unlink()

    # 6. push, heartbeat, log
    pushed = True
    if not DRY and git("rev-list", "--count", f"origin/{BRANCH}..HEAD", check=False) not in ("", "0"):
        r = subprocess.run(["git", "-C", str(SHADOW), "push", "-q", "origin", f"HEAD:{BRANCH}"], capture_output=True, text=True)
        pushed = r.returncode == 0
        if not pushed:
            log("push-failed", error=r.stderr.strip()[:300])
    plat.write_text(STATE / "last-head", git("rev-parse", "HEAD"))
    if changed or wrote or conflicts or held_changed:
        log("cycle", from_drive=len(changed), to_drive=len(wrote), conflicts=len(conflicts),
            held_deletes=len(missing), pushed=pushed, sample_in=changed[:5], sample_out=wrote[:5])
    warn = []
    if conflicts:
        warn.append(f"{len(conflicts)} conflict(s) parked in 9-system/conflicts")
    if missing:
        warn.append(f"{len(missing)} file(s) missing from Drive, held for {HUMAN}'s word")
    if not pushed:
        warn.append("push to GitHub failed, retrying next cycle")
    heartbeat("; ".join(warn) or "none", force=bool(warn))


def heartbeat(warnings, force=True):
    if DRY or not VAULT.is_dir():
        return  # never mkdir a stub vault at a stale path
    hb = VAULT / "9-system/state/HEARTBEAT.md"
    if (hb.exists() and "not yet" not in hb.read_text(encoding="utf-8", errors="replace")
            and time.time() - hb.stat().st_mtime < 54 * 60):
        same_warning = f"warnings: {warnings}\n" in hb.read_text(encoding="utf-8", errors="replace")
        if same_warning:
            return  # refresh at most every 54 min, or at once when the warning itself changes (clearing included)
    text = (f"---\ntitle: HEARTBEAT\nkind: state\nrelay: {plat.HOST}\n"
            f"last_sync: {NOW.isoformat(timespec='seconds')}\nwarnings: {warnings}\n---\n↑ [[SYSTEM]]\n\n# HEARTBEAT\n\n"
            f"1. Written by the relay. If last_sync is more than 2 hours old, the {plat.NAME} is not syncing.\n")
    try:
        if hb.exists() and hb.read_text(encoding="utf-8") == text:
            return
        hb.parent.mkdir(parents=True, exist_ok=True)
        write_in_place_text(hb, text)
        own = STATE / "own-write-mtime"
        plat.write_text(own, str(max(hb.stat().st_mtime, float(own.read_text(encoding="utf-8")) if own.exists() else 0)))
        (SHADOW / "9-system/state").mkdir(parents=True, exist_ok=True)
        plat.write_text(SHADOW / "9-system/state/HEARTBEAT.md", text)
    except Exception as e:
        log("heartbeat-failed", error=str(e)[:200])


def write_in_place_text(path, text):
    with open(path, "r+" if path.exists() else "w", encoding="utf-8", newline="\n") as fh:
        fh.seek(0)
        fh.write(text)
        fh.truncate()


if __name__ == "__main__":
    main()
