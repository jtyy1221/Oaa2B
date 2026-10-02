#!/usr/bin/env python3
"""Scaffold a new Oaa2B vault from config.json. Safe to re-run: it never overwrites an existing file.

    oaa2b_init.py [--launchd LABEL_PREFIX]

  * creates the ten branch folders in the Drive vault, plus 9-system/{state,handoff,warnings,renames,runs}
  * seeds the law (9-system/sys-law.md), the live handoff and an empty RENAMES board
  * writes the same random vault-id into the vault and into the relay's state folder
    (the relay refuses to sync if they differ, so it can never sync the wrong folder)
  * writes .gitignore and .gitattributes into the shadow clone if it exists
  * --launchd com.you.brain writes the two LaunchAgent plists (relay 36 s, view 180 s) into
    ~/Library/LaunchAgents, without loading them; load them with launchctl when ready
"""
import secrets
import sys
from datetime import date
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
sys.path.insert(0, str(ENGINE))
import oaa2b_vault as vt  # noqa: E402

TEMPLATES = ENGINE.parent / "templates"


def seed(path, text):
    if path.exists():
        print("kept   ", path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print("created", path)


def fill(text):
    persona = f" You are **{vt.PERSONA}**." if vt.PERSONA else ""
    inbox = f" (folder id `{vt.CFG['drive_inbox_id']}`)" if vt.CFG.get("drive_inbox_id") else ""
    for k, v in {"{{TODAY}}": date.today().isoformat(), "{{HUMAN}}": vt.HUMAN, "{{PERSONA_LINE}}": persona,
                 "{{HOME_NOTE}}": vt.HOME_NOTE, "{{GITHUB_REPO}}": vt.CFG.get("github_repo", "<user>/<repo>"),
                 "{{DRIVE_INBOX}}": inbox}.items():
        text = text.replace(k, v)
    return text


PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>{label}</string>
  <key>ProgramArguments</key>
  <array><string>/bin/zsh</string><string>-c</string><string>/usr/bin/python3 '{script}'</string></array>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin</string>
        <key>OAA2B_CONFIG</key><string>{config}</string></dict>
  <key>StartInterval</key><integer>{interval}</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>{logdir}/{name}.out</string>
  <key>StandardErrorPath</key><string>{logdir}/{name}.err</string>
</dict>
</plist>
"""


def main():
    if not vt.CFG:
        sys.exit(f"no config at {vt.CFG_PATH}; copy config.example.json to config.json and fill it in")
    vault, state, shadow = vt.cfg_path("vault"), vt.cfg_path("state"), vt.cfg_path("shadow")
    for b in vt.BRANCHES:
        (vault / b[0]).mkdir(parents=True, exist_ok=True)
    for sub in ("state", "handoff/history", "warnings", "renames", "runs"):
        (vault / "9-system" / sub).mkdir(parents=True, exist_ok=True)
    seed(vault / "9-system/sys-law.md", fill((TEMPLATES / "sys-law.md").read_text(encoding="utf-8")))
    seed(vault / "9-system/handoff/HANDOFF.md", (TEMPLATES / "HANDOFF.md").read_text(encoding="utf-8"))
    seed(vault / "9-system/renames/RENAMES.md", "---\ntitle: RENAMES\nkind: board\n---\n↑ [[SYSTEM]]\n\n# RENAMES\n\n")

    state.mkdir(parents=True, exist_ok=True)
    vid_vault, vid_state = vault / "9-system/state/vault-id", state / "vault-id"
    if not vid_vault.exists() and not vid_state.exists():
        vid = secrets.token_hex(12)
        vid_vault.write_text(vid + "\n", encoding="utf-8")
        vid_state.write_text(vid + "\n", encoding="utf-8")
        print("created vault-id", vid)
    elif vid_vault.exists() and vid_state.exists() and vid_vault.read_text(encoding="utf-8") == vid_state.read_text(encoding="utf-8"):
        print("kept    vault-id")
    else:
        print("WARNING vault-id exists on one side only or differs; fix by hand before running the relay")

    if shadow.exists():
        seed(shadow / ".gitignore", ".DS_Store\n.obsidian/workspace*.json\n.obsidian/cache\n.trash/\n*.tmp\n*.swp\n*.icloud\n")
        seed(shadow / ".gitattributes", "*.md merge=binary\n")  # a clash never writes conflict markers into a note

    if "--launchd" in sys.argv:
        prefix = sys.argv[sys.argv.index("--launchd") + 1]
        logdir = vt.cfg_path("log").parent
        logdir.mkdir(parents=True, exist_ok=True)
        agents = Path.home() / "Library/LaunchAgents"
        for name, interval in (("relay", 36), ("view", 180)):
            label = f"{prefix}.{name}"
            seed(agents / f"{label}.plist", PLIST.format(label=label, script=ENGINE / f"oaa2b_{name}.py", config=vt.CFG_PATH,
                                                        interval=interval, logdir=logdir, name=name))
        print(f"load with: launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/{prefix}.relay.plist (and .view)")


if __name__ == "__main__":
    main()
