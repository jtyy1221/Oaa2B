# 🧠 Obsidian as a 2nd Brain (Oaa2B)

A shared AI memory layer: your **Obsidian** vault, synced by **iCloud** to iPhone/iPad, mirrored to a **private GitHub repo** by an always-on Mac, readable and writable by your AI assistants (Claude, Grok, ChatGPT…) from any device.

- 📝 Notes live in iCloud — Obsidian works everywhere
- 🗄️ Git history lives *outside* iCloud (`--separate-git-dir`) — the corruption class is gone
- 🔄 A launchd relay commits & pushes on every change (plus a 3-min timer), with a heartbeat your AIs check before trusting anything
- ⭐ A two-level star graph: one home note → five hubs → leaves. No mess.

## Install (one line)

Prerequisites: a Mac that stays on, iCloud Drive, Obsidian (Mac + phone), a GitHub account, [Claude Code](https://claude.com/claude-code).

Paste this into Claude Code on your Mac:

```
Fetch https://raw.githubusercontent.com/jKelvin-com/Oaa2B/main/Oaa2B_setup.html and follow its AI-RUNBOOK section to set up "Obsidian as a 2nd Brain" for me.
```

Claude interviews you for your **vault name**, **repo name**, and preferences, then builds and verifies the whole thing — including the macOS privacy (TCC) and GitHub auth traps documented in the runbook's Gotchas table.

## What you get

- A private GitHub repo of your vault, safely split from iCloud
- An automatic sync relay with 6 failure guards and a liveness heartbeat
- `CORE/INSTRUCTIONS.md` — one standing law every connected AI obeys
- A vault-doctor skill for health checks and weekly memory reconciliation
- Connector guidance for Claude, Grok, ChatGPT (Gemini honestly assessed: skip)

## Credits

Built and battle-tested by [jKelvin.com](https://jkelvin.com) with Claude Code · August 2026 · Share freely 🧠
