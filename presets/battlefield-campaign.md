# YAPCUT PRESET: Battlefield Campaign

*Solo playthrough of BF6 campaign missions. Jay voiced Dylan Murphy — the player character. This is not a standard playthrough; this is an actor experiencing his own performance in a shipped game.*

## Output Mode: `post-ready-cut`

This preset produces a **post-ready cut** — a dual-layer XML with a publishable edit on V1 and a marker reference track on V2. The goal is zero additional editing required. Claude makes every cut decision; the editor reviews and uploads.

### Output Format
- **V1/A1-A2:** Post-ready cut with physical edit points, internal polish applied (dead air removed, fillers cut, pacing tightened)
- **V2:** Full VOD with spanned markers showing every editorial decision and reasoning
- **Teaser:** 2-3 options (15-30 seconds each) at top of timeline, separated by 2-second gaps, before the main edit

## Target Output
- Format: YouTube VOD Edit (Episodic Series, Must Work Standalone)
- Ratio: Compress 1.5-3 hours into 20-35 minutes
- Teaser: 15-30 seconds (matches YouTube hover autoplay window)

## Editorial Lens
The core draw is NOT the gameplay. It is Jay's real-time experience of a game he starred in.
Every editorial decision runs through this filter:
> "Does this moment reveal something about what it's like to BE Jay Walker playing Dylan Murphy?"

Gameplay that has nothing to do with this lens is filler. Good story beats with flat Jay reactions are filler. The intersection of both is gold.

## Content Priority Stack (Highest to Lowest)
1. **REACTION Moments** — Jay reacting to his own voice or performance. First time hearing a Murphy line in-game, calling out a take he remembers from the session, noticing a delivery that surprised him, laughing at or being moved by his own work. Detectable from transcript via: sudden shift in tone, self-referential commentary ("that's me," "oh that's the line where—", "I remember recording this"), laughter immediately following in-game dialogue, or unprompted production context following a game audio moment. Unique to this creator and this game. Flag everything.
2. **Behind-the-Scenes Commentary** — Jay offering production context: why a line was delivered a certain way, what the session was like, alternate takes, studio anecdotes, things the player wouldn't know.
3. **Story Beats** — Cutscenes or in-game dialogue sequences where Murphy is central. Keep if Jay's reactions or commentary are active. Cut if Jay goes silent and lets the game run without adding anything.
4. **Genuine Gameplay Skill** — Jay actually playing well. Keep if tight and paired with strong vocal energy. Cut if it's clean but quiet.
5. **CONTEXT Tags** — Brief setup moments before a major story beat or gameplay sequence. Use sparingly. Never more than 45 seconds.

## Implicit CUT Zones
- Quiet traversal and exploration with no commentary
- Repeated death/checkpoint loops unless Jay's frustration or commentary becomes the content
- Cutscenes or NPC dialogue where Jay has gone fully quiet and passive (watching, not reacting)
- Loadout / settings / map screen navigation
- Moments where Jay breaks entirely to read chat without a gameplay anchor

## Title-Specific Rules (Campaign)
- **Murphy Lines Playing ≠ Automatic Keep.** Jay needs to be actively reacting or commentating. A silent stretch of in-game dialogue — even if it's Murphy speaking — is still a cut. From transcript: flag silent windows of 10+ seconds during what appears to be a cutscene or heavy NPC dialogue section.
- **Episodic Continuity:** Each edit must make sense to a first-time viewer. Flag any moment that requires previous episode context without a quick verbal recap. If Jay doesn't provide it, it may need a title card note.
- **First Reactions Are Non-Repeatable.** If Jay hears a line for the first time and reacts authentically, that's a once-per-game opportunity. Flag it regardless of what else is happening.
- **Self-Commentary Elevates Everything.** A mediocre gameplay moment becomes a KEEP if Jay simultaneously explains something about how that sequence was recorded or designed.

## Marker Types
> **Note:** `REACTION` is a custom marker type for this preset. It represents actor-reacting-to-own-performance — a distinct editorial category that warrants independent filtering in Premiere's Markers panel.

- `KEEP` — Include in the edit
- `MAYBE` — Strong commentary but not directly about Jay's performance. Preserve for editorial judgment — often good bridge material.
- `CUT` — Explicit dead air or off-lens content
- `MOMENT` — Short extraction candidate. See MOMENT Extraction section below.
- `REACTION` — Jay's verbal/vocal response to his own performance. High priority. Always flag.
- `CONTEXT` — Setup/bridge material. Use sparingly, hard cap 45 seconds.

## Audio Priority Rules
- Jay's vocal commentary is the primary content layer. Game audio is secondary.
- Strong Jay reaction with mediocre game moment = KEEP
- Impressive game moment with flat, silent Jay = CUT. Cannot be flagged as MOMENT from transcript alone — requires manual pass.
- In-game Murphy dialogue followed by 5+ seconds of Jay silence is ambiguous. Do not cut mid-silence. Flag as MAYBE and note the timestamp — editorial call on whether Jay is processing or has checked out.

## Internal Polish Rules (Post-Ready Cut)

When generating the V1 cut, apply these within every kept segment:

- **Dead air removal:** Cut gaps > 1.5 seconds between speech that have no editorial purpose. Exception: silence before a vocal reaction (reaction lead-in rule — keep the silence, the visual payoff happened during it).
- **Filler word removal:** Cut "um," "uh," "like" at sentence boundaries. Exception: fillers that are part of Jay's natural delivery or a comedic beat ("like... LIKE WHAT?!").
- **Cut padding:** 0.4-0.5 seconds of natural space between internal cuts. Not robotic-tight, not sloppy.
- **Sentence boundary cuts:** Always prefer cutting on `eos: true` boundaries for clean audio.
- **Pacing modulation:** High-energy segments (reactions, gameplay peaks) get tighter internal cuts. Commentary and BTS discussion segments get more breathing room. The edit should feel like it accelerates during peaks and cruises during valleys.

## Pacing Quality Gate

After assembling the full edit, validate against these checkpoints:

| Time | Checkpoint |
|---|---|
| 0:00-0:30 | Teaser montage — best 3-5 moments in rapid-fire. Maximum hook. |
| 0:30-3:00 | First real segment drops the viewer into strong content fast. No slow build. |
| ~3:00 | Re-engagement beat — a reaction, a gameplay peak, or an energy shift. If chronological flow doesn't deliver one here, flag it. |
| 3:00-6:00 | Story investment building — the audience is getting to know Jay's relationship to the game. |
| ~6:00 | Second re-engagement — deeper BTS content or a strong reaction moment. |
| Every 2-3 min | Re-hook present — tease, payoff, energy shift, or new element introduced. No 3-minute stretches of flat energy. |
| Ending | Abrupt cutoff on a strong moment. Never signal the video is ending. No "thanks for watching," no wind-down. |

If a checkpoint fails, either adjust the cut (compress a flat zone, reorder if necessary) or flag it with a marker comment explaining the pacing risk.

## Teaser Rules (Integrated)

The teaser is the first 15-30 seconds of the video. It plays during YouTube's hover autoplay and must convert hover-to-click.

- **2-3 teaser options** placed at the top of the timeline, separated by 2-second gaps
- **15-30 seconds each** — tight montage of the best moments across the full VOD
- **0.3-0.5 seconds per shot** — fast cutting, hard to stop watching
- **Must work with AND without audio** — visual impact alone should be compelling
- **Frame 1 at full energy** — no countdown, no logo, no greeting. Mid-action, mid-laugh, mid-line.
- **Prefer material from the back half** — the viewer hasn't seen it yet
- **Curiosity gaps** — cut before payoffs land. Make the viewer need to see what happens.
- **Closing shot** — strongest single moment. End hard.

## MOMENT Extraction (Campaign Shorts)
Campaign produces a specific, high-value Short structure that should be flagged explicitly:

**The First-Reaction Arc:** Game audio plays a Murphy line → brief silence (Jay processing) → immediate verbal response. This is a complete, self-contained narrative in 20-30 seconds. Structure: setup (game moment or NPC prompt) → the performance lands → Jay's unscripted reaction. These are non-repeatable and among the best Short candidates in any VOD.

Detection signal: Jay says something self-referential immediately after a period of relative quiet. Phrases like "wait," "oh," "that's-", laughter with no apparent game-event trigger, or sudden shift into production commentary.

MOMENT duration target for Campaign: 20-40 seconds. Longer than typical (Shorts preset caps at 60s), but these clips need the breath before the reaction to work.
