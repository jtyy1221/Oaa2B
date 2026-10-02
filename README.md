# 🧠 Obsidian as a 2nd Brain (Oaa2B)

A shared AI memory layer that several AIs read and write together: one master copy of your notes in **Google Drive**, version history in a **private GitHub repo**, and an **Obsidian** graph on Mac, iPhone and iPad.

## v5.0: the live engine

v5 ships the actual code that runs the author's own vault every day, with personal content removed. Python 3 standard library only, one config file.

- 🔄 **Relay** (`engine/oaa2b_relay.py`, every 36 s): Drive ↔ a shadow git clone on local disk ↔ GitHub. Git never runs inside a cloud folder. Guards: held deletes, refused remote deletes, parked conflicts, a bulk-change pause, a vault-id sentinel, a heartbeat.
- 🌳 **Tree pass** (`engine/oaa2b_tree.py`): ten separate stars, one parent per node. `parent:` puts a note under another note; `children:` lets a note adopt raw data files. Stray links become plain text, so the graph stays readable.
- 🏗️ **Build** (`engine/oaa2b_build.py`): regenerates the hubs, home note, INDEX, WARNINGS, START-HERE and graph colours. Idempotent.
- 👀 **View** (`engine/oaa2b_view.py`, every 180 s): one-way export into the iCloud Obsidian vault for the graph.
- 🧰 **Scaffold** (`engine/oaa2b_init.py`): creates the ten branches, seeds the law and handoff, writes the vault-id pair and the LaunchAgents.
- 🏷️ **Slug-only names:** AIs write stamped inbox names; the relay strips the stamp so the graph shows clean names.
- ⚫ **Quiet warnings:** one file per warning, a darkest-grey dot on the one note it's about.
- 📄 **Templates** (`templates/`): the law, the handoff seed, the vault-doctor skill, the daily reconcile task, and the instruction line for each AI.

## Install (one line)

📦 Repo: [github.com/jkelvin-com/Oaa2B](https://github.com/jkelvin-com/Oaa2B) · full runbook: [Oaa2B_setup.html](Oaa2B_setup.html)

1. **Prerequisites:** a Mac or Windows PC that stays on, Google Drive for Desktop, Obsidian on the computer and phone (iCloud Drive on), a GitHub account, [Claude Code](https://claude.com/claude-code). On Windows, see the runbook's *macOS and Windows* table.
2. **Paste this into Claude Code on that computer:**

   ```
   Fetch https://raw.githubusercontent.com/jKelvin-com/Oaa2B/main/Oaa2B_setup.html and follow its AI-RUNBOOK section to set up "Obsidian as a 2nd Brain" for me.
   ```

3. **Answer the interview** (vault name, how the AIs address you, branches, repo) and do the steps Claude hands you: browser logins, Full Disk Access, keeping the Mac awake. It clones this repo, fills `engine/config.json`, scaffolds, syncs, and tests everything.
4. **Test:** ask any connected AI *"Read START-HERE, is the sync alive?"*

## Layout

```
Oaa2B_setup.html        the runbook (human steps + AI-RUNBOOK)
engine/                 relay, tree, build, view, init, vault and platform helpers, config.example(.windows).json
templates/              sys-law, HANDOFF, vault-doctor skill, reconcile task, AI instructions
```

`engine/config.json` holds your personal paths and is git-ignored.

## Credits

Built and battle-tested by 富源承忠 [jKelvin.com](https://jkelvin.com) with Claude Code · August to October 2026 · Share freely 🧠
