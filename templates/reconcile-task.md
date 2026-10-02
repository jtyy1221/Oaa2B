---
name: daily-vault-reconcile
description: Daily health check + reconcile of the Oaa2B vault in Google Drive
---

Run the daily vault reconcile. Self-contained; no other session is available. Fill in the paths from `engine/config.json` when you install this task.

WHERE THINGS ARE
- Master vault (edit here, and only here): {{VAULT}}
- The law: 9-system/sys-law.md. The AI boot page: START-HERE.md. Home note: {{HOME_NOTE}}.md.
- Relay: launchd {{LABEL}}.relay runs {{ENGINE}}/oaa2b_relay.py every 36 s. It copies Drive into the shadow clone {{SHADOW}}, merges GitHub both ways, writes back into Drive, regenerates every UPPERCASE file and pushes. View job {{LABEL}}.view exports one way to the iCloud Obsidian folder every 3 min. Logs: {{LOG}} and view.log beside it. Heartbeat: 9-system/state/HEARTBEAT.md. Held deletes: {{STATE}}/pending-deletes.tsv.
- NEVER run git in Drive or iCloud. NEVER edit the iCloud folder. NEVER edit UPPERCASE files. NEVER touch 9-system/claude-code-memory/. NEVER rewrite anything inside a data/ folder.
- LINKS MAKE TEN STARS, ONE PARENT EACH: the home note links to no hub. A note links only up to its parent: its hub, or the same-branch note named in its frontmatter `parent:`. A note adopts raw data files with frontmatter `children: [a, b]`; a data file named as a parent (a log) hangs straight off the branch hub. One link per node. To group a crowded star, add parent: lines; never a second link. Name any other note as plain text in backticks.

STEPS
1. Health first. Heartbeat fresh (<2 h)? relay.log errors or "blocked"/"paused" in the last 24 h? {{STATE}}/PAUSE present? `git -C {{SHADOW}} status` clean and HEAD equal to `git -C {{SHADOW}} ls-remote origin main`? Held deletes? Drive conflict copies ("name (1).md") or .gdoc files in the vault? If the relay is unhealthy, write only a health report (step 5) and stop.
2. Early exit: if 0-inbox holds only INBOX.md and nothing in step 1 needs reporting, write the run row and stop.
3. Before editing, touch {{STATE}}/PAUSE so the relay waits; remove it when done (it expires after 33 min anyway).
4. Process every note in 0-inbox except INBOX.md, oldest first by `created`:
   a. Repair first where safe: frontmatter must start on line 1, then the line `↑ [[INBOX]]`; add missing keys agent/surface/created/kind/summary from the content. The relay strips name stamps, so a plain `<slug>.md` is correct. Count repairs.
   b. File the content: distil durable facts into the right branch note. Each note: frontmatter (title, branch, summary under 90 chars, status, updated; `parent:` if it sits under another note), line `↑ [[<HUB>]]`, `## TL;DR` with numbered lines stating the objective and where it stands, short numbered sections, a final `Related:` line naming notes in backticks. New filenames start with the branch word (me-, work-, biz-, money-, home-, life-, rel-, build-, sys-) and are unique. Large data goes in that branch's data/ folder. Mark personal notes `sensitive: true`.
   c. kind: append → append to the `target` file (data files: append only). kind: handoff → replace the body of 9-system/handoff/HANDOFF.md and move the old text to 9-system/handoff/history/. kind: memory / forget → apply to the vault. kind: resolves / warns → step d. kind: run → one line in 9-system/runs/<schedule>/YYYY-MM.md.
   d. Warnings, one per file in 9-system/warnings/, named P1-<slug>-wNNN.md (P1 needs the owner, P2 watched). `resolves: [n]` → status resolved, one dated line, move to 9-system/warnings/resolved/YYYY-MM/, write the answer into the note concerned. `warns:` → new file with the next number, frontmatter `about: <stem of the one note>`, first body line `⚠️ [[<that stem>]]`. At most one dated line per day, only when something changed.
   e. Move each processed inbox note to 9-system/inbox-done/YYYY-MM/.
5. Append one run row to 9-system/runs/vault-reconcile/YYYY-MM.md: `YYYY-MM-DD HH:MM · ok|health-only · N filed, N repaired, N warnings changed · one short note`.
6. Remove PAUSE. Within about 2 minutes check relay.log shows your changes committed and pushed; if not, say so in the run row.
