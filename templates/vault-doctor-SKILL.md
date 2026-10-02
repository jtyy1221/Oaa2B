---
name: vault-doctor
description: Health check and repair for the Oaa2B vault (Google Drive master, relay to GitHub, iCloud view). Use whenever the user says "check my vault", "vault doctor", mentions sync problems, conflict copies, duplicate notes, a stale heartbeat, relay down, notes missing on a device, or git errors, and before any bulk operation on the vault. Also handles "reconcile my vault" by following the daily reconcile task.
---

# Vault Doctor 🩺

Fill in the paths from `engine/config.json` when you install this skill.

- **Master:** `{{VAULT}}` (single-quote it in shell if it holds `$` or `~`). Ten branches `0-inbox` to `9-system`; home `{{HOME_NOTE}}.md`; AI boot page `START-HERE.md`; law `9-system/sys-law.md`.
- **Relay:** `{{LABEL}}.relay`, every 36 s, `{{ENGINE}}/oaa2b_relay.py`. Shadow clone (the only git work tree): `{{SHADOW}}`. State: `{{STATE}}` (lock, PAUSE, vault-id, pending-deletes.tsv, last-head). Log: `{{LOG}}` (JSON lines) and `relay.err` beside it.
- **View:** `{{LABEL}}.view`, every 180 s, exports one way into `{{VIEW}}`. Log `view.log`.
- **Backups:** `{{BACKUPS}}` (drive-overwrites, view-overwrites, view-rescue, view-removed).
- **Heartbeat:** `9-system/state/HEARTBEAT.md` in the vault.

## Health check (default)

1. **Heartbeat:** `last_sync` older than 2 h = relay down; read its `warnings:` line.
2. **Jobs:** `launchctl list | grep {{LABEL}}` shows both with exit 0; tail `relay.err`, `view.err`.
3. **Log:** in `relay.log`, look for `error`, `blocked`, `paused`, `push-failed`, `conflict`, `refused-delete` in the last 24 h. Explain each in plain words.
4. **In sync:** `git -C {{SHADOW}} status --short` empty, and `git -C {{SHADOW}} rev-parse HEAD` equals `git -C {{SHADOW}} ls-remote origin main` (never `fetch` from a health check).
5. **Held deletes:** `{{STATE}}/pending-deletes.tsv`. Each line is a file deleted in Drive; it stays in git until the owner confirms. On their word, `git rm` it in the shadow, commit `delete: <path>`, and push.
6. **Pause:** `{{STATE}}/PAUSE` stops the relay for 33 min (the relay writes it itself when more than 33 files change at once). Check why before removing it.
7. **Drive:** no `* (1).md` duplicates, no `.gdoc` files in the vault (the relay quarantines them), no online-only placeholders (`find <vault> -flags +dataless`); if placeholders exist, the vault folder must be set Available offline.
8. **Disk:** `df -h ~`; the relay stops under 9 GB free.
9. **Git objects:** `git -C {{SHADOW}} fsck --no-progress`. A damaged shadow is re-cloned from GitHub, never hand-repaired; Drive and GitHub stay intact.
10. **Tree:** `python3 {{ENGINE}}/oaa2b_tree.py {{SHADOW}} --dry-run` must say `changed 0, refused 0`. A `refused` file is a data file whose visible words would change; leave it and report it.

## Rules

1. Never run git inside Drive or iCloud. Never edit the iCloud folder. Never edit UPPERCASE generated files. Never rewrite `data/` folders. Never force-push.
2. Warnings are one file each in `9-system/warnings/` with the board `WARNINGS.md`. To answer "any warnings?", read the board.
3. "Reconcile my vault": follow the prompt of the daily reconcile task.
