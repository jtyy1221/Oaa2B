# 🧠 Obsidian as a 2nd Brain (Oaa2B)

A shared AI memory layer that several AIs read and write together: one master copy of your notes, version history in a **private GitHub repo**, and an **Obsidian** graph on Mac, iPhone and iPad.

## v4.0: choose your master

- 🟢 **Google Drive master (recommended).** Notes live in a Drive folder kept offline on your Mac. Claude and other AIs reach it through their Drive connectors, and GitHub too. Git runs only in a shadow clone on local disk, so a cloud edit can never corrupt it. The iCloud Obsidian vault becomes a one-way copy for the graph.
- 🍎 **iCloud master (classic, v3.6).** Notes live in the iCloud Obsidian vault, with the git database kept outside iCloud.

## What you get

- 🌳 **Ten departments in a tree:** a home note, ten hubs, their notes, their data. Nothing links across departments, so the graph stays readable.
- 🔴 **Warnings as red nodes:** one file per warning, each hanging on the one note it is about.
- 📊 **Raw data kept word for word** in `data/` folders.
- 🧭 **START-HERE**, a generated boot page every AI reads first: sync health, the rules, the live handoff.
- 🔄 **A relay** every 36 s with guards: held deletes, refused remote deletes, parked conflicts, a bulk-change pause, a heartbeat.
- 🩺 **A daily reconcile** and a doctor skill.

## Install (one line)

Prerequisites: a Mac that stays on, Google Drive for Desktop (or iCloud Drive), Obsidian on Mac and phone, a GitHub account, [Claude Code](https://claude.com/claude-code).

Paste this into Claude Code on your Mac:

```
Fetch https://raw.githubusercontent.com/jKelvin-com/Oaa2B/main/Oaa2B_setup.html and follow its AI-RUNBOOK section to set up "Obsidian as a 2nd Brain" for me.
```

Claude interviews you (master, vault name, departments, repo), then builds and verifies everything, including the macOS privacy (TCC) and GitHub auth traps in the runbook's Gotchas table.

## Credits

Built and battle-tested by 富源承忠 [jKelvin.com](https://jkelvin.com) with Claude Code · August to September 2026 · Share freely 🧠
