# Instruction pointers for each AI

Each surface carries only who you are and a pointer to START-HERE.md; the vault holds everything else, so you never have to update these. Replace `<START_HERE_ID>` and `<INBOX_ID>` with the Drive file ids (Drive → file → Share → Copy link; the id is the long part), and `<user>/<repo>` with your GitHub repo.

## 1. claude.ai, Settings → Profile → personal preferences

At the start of every conversation, before you answer: read START-HERE.md from Google Drive (file id <START_HERE_ID>; if that fails, read START-HERE.md in GitHub <user>/<repo>). Follow it; it wins over anything written here. Write memory only as a new .md note in the 0-inbox folder (Drive folder id <INBOX_ID>), contentMimeType text/markdown, disableConversionToGoogleType true. Never edit, move or delete existing files.

## 2. claude.ai projects → Project instructions

At the start of every chat in this project: read START-HERE.md from Google Drive (file id <START_HERE_ID>) and follow it.

## 3. Claude desktop, Cowork → global instructions

At the start of every session: read START-HERE.md with the Google Drive connector (file id <START_HERE_ID>). Follow it. Write memory only as a new .md note in 0-inbox (Drive folder id <INBOX_ID>). Never edit, move or delete existing files.

## 4. Grok, Customize Grok → instructions

At the start of every conversation: read START-HERE.md from Google Drive (file id <START_HERE_ID>); if Drive is not connected, read START-HERE.md in the private GitHub repo <user>/<repo> (main). Follow it. Write only by creating a new file in 0-inbox named <slug>-grok-web-YYYY-MM-DD-HHMM.md, frontmatter on line 1 (agent: grok, surface: web, created, kind, summary), then the line ↑ [[INBOX]]. Never edit, move or delete existing files.

## 5. ChatGPT or any other AI

Use block 4 with the agent word changed (chatgpt, codex) in the file name and frontmatter.

## 6. Gemini (saved info refuses file-reading instructions; use a Gem)

Gemini → Gems → New Gem. Instructions: "At the start of each chat, open START-HERE.md in my Google Drive (file id <START_HERE_ID>) and use it for how I like answers written and where my notes are kept."

## 7. Claude Code (the local agent that runs the relay)

In `~/.claude/CLAUDE.md`: "First step of every session: read <local path to the vault>/START-HERE.md and follow it. Never run git inside Google Drive or iCloud; the relay's work tree is <shadow path>."

## Test

Ask each AI: "Read START-HERE, is the sync alive?" A correct answer quotes a last sync under 2 hours old.
