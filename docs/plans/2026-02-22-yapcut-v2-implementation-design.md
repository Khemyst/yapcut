# YapCut v2 Implementation Design

> Design document for implementing the v2 spec (`yapcut-v2-final-spec.md`).

## Decisions Made

### Directory Restructure
- `scripts/` → `tools/`
- `transcripts/` → `input/`
- `generate_xml.py` kept in `tools/` as reference for future rough-cut mode
- New directories: `presets/`, `docs/plans/`
- `.gitignore` updated to reflect new paths + keep `input/` ignored

### Architecture Boundary
Claude Code IS the marker generation engine. No Python script generates markers. The CLAUDE.md teaches Claude how to read transcripts, conduct briefings, and output FCP XML with spanned markers. Python tools are utilities around that workflow.

### Tool Implementations

**`tools/validate_xml.py`** — Extended from v1:
- Auto-detects marker-mode vs rough-cut-mode XML
- Validates marker elements: `<name>` prefix format, `<comment>` presence, `<in>`/`<out>` as integers
- Keeps all existing structural validation (clipitem continuity, file refs, etc.)

**`tools/chat_pull.py`** — YouTube chat fetcher:
- OAuth2 via existing `C:\Users\jaywa.NEUTRON\Projects\config\youtube_token.json`
- Auto-refreshes expired tokens
- Three lookup modes: `--video-id`, `--search "title"`, `--recent` (list channel uploads)
- Channel ID from `C:\Users\jaywa.NEUTRON\Projects\config\.env`
- Outputs spec-defined JSON schema to `input/chat.json`

**`tools/diff_analysis.py`** — EDL comparison engine:
- Parses CMX 3600 EDL + YapCut marker XML
- Normalizes to frames using session timebase
- Fuzzy overlap matching (name similarity + temporal proximity, 85% overlap threshold)
- Categorizes: ACCEPTED / HEAVILY_MODIFIED / REJECTED / USER_KEPT_DEAD_SPACE / USER_KEPT_IN_EXISTING
- Appends structured session report to `EDITORIAL_MEMORY.md`

**`tools/generate_xml.py`** — Moved from `scripts/`, kept as-is for reference.

### Presets
All 5 presets drafted with reasonable defaults:
- `battlefield-highlights.md` — full content from spec
- `full-vod-edit.md` — longer form, higher marker density, less aggressive cuts
- `shorts-extraction.md` — aggressive MOMENT flagging, 15-60s self-contained clips
- `battlefam-episode.md` — collab/squad-focused, banter priority
- `chill-stream.md` — relaxed pacing, authentic reactions over high energy

### CLAUDE.md Update
- Retains all v1 FCP XML schema knowledge (needed for both modes)
- Adds: marker workflow, briefing process, preset system, chat integration, style memory
- Documents Mode 1 (markers/default) and Mode 2 (rough cut/opt-in)
- References marker XML schema and CUT logic from spec

### Config Path Convention
Tools reference credentials at `C:\Users\jaywa.NEUTRON\Projects\config\`:
- `youtube_token.json` — OAuth2 token with refresh
- `youtube_client_secret.json` — OAuth2 client credentials
- `.env` — channel ID and other config
