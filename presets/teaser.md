# YAPCUT PRESET: Teaser

*Placed at the beginning of the final video. The viewer has clicked but hasn't committed. This is the closer — 60–120 seconds of the best material from the entire VOD, structured to make leaving feel wrong.*

## Output Mode: `cuts`

This preset produces **physical edit points**, not markers. Claude selects the best moments and assembles complete teaser sequences, ready to drop at the start of the main edit.

### Output Format
- **File:** `yapcut_teaser.xml`
- **Structure:** 2-3 **separate sequences** in one XML file, each a complete teaser option. Premiere imports them all; the editor picks their favorite.
- **Sequence naming:** `"Teaser A (hype)"`, `"Teaser B (comedy)"`, `"Teaser C (balanced)"` — or whatever tonal angles the VOD supports.
- **Each sequence:** 6-10 clips assembled as a rough cut. 60-120 seconds total. 90 seconds is optimal. Clips are ordered for maximum impact, NOT chronologically.

## Target Output
- Format: Front-loaded video intro (horizontal, same project timeline)
- Duration: 60–120 seconds. 90 seconds is optimal.
- Clip count: 6–10 clips per teaser sequence. Prefer material from the latter half (the viewer hasn't seen it yet).
- Chronological order: Irrelevant. This is a trailer.

## Editorial Lens
The viewer clicked the thumbnail. Now they're deciding if the next 25 minutes of their life belongs to this video.

> "After 90 seconds, does the viewer feel like they've seen the trailer for a movie they *have* to watch — but haven't actually seen the movie yet?"

The Teaser shows peaks. It does not explain them. If a clip makes sense without context, it's a candidate. If it needs setup, it's not.

## Content Priority Stack (Highest to Lowest)
1. **The Best 3 Moments in the VOD** — Whatever is objectively most impressive, funniest, or most unbelievable. These are the reason the video exists. Lead with one, end with one.
2. **Energy Escalation Clips** — Moments where something rapidly builds — a clutch in progress, a bit gaining momentum, a reaction getting bigger. Cut before the peak lands. Make them want to see it pay off.
3. **Audio-First Hooks** — A line, a yell, an impression, a laugh that's compelling without needing visual context. These work as cold opens.
4. **Curiosity Gaps** — Moments that are clearly significant but deliberately incomplete. Something that makes the viewer think "wait, what happens next?" Cut away before the resolution.
5. **Tonal Range Clips** — If the video has both hype and funny, show both. A Teaser that's only hype or only comedy undersells the full video.

## Implicit CUT Zones
- Anything that resolves too cleanly within the Teaser itself — save the payoff for the video
- Moments that require even 5 seconds of context to understand
- Quiet or slow moments — CONTEXT tags have no place here
- Repeated clip types — two kill moments, two impression clips. Diversity of beat > redundancy of quality.

## Structural Rules
- **Frame 1:** Must be at full energy. No countdown, no logo, no "hey guys." Start mid-action, mid-laugh, or mid-line.
- **Clip Length Within Teaser:** Individual clips should run 5–15 seconds each. Longer = you're giving it away.
- **Intentional Interruption:** Cut clips at moments of maximum tension or anticipation, not at resolution. The Teaser is a debt the rest of the video repays.
- **Closing Shot:** The last clip in the Teaser should be your single strongest individual moment — comedically, emotionally, or energetically. End hard.

## Marker Types
- `TEASER` — Pull candidate for the pre-roll intro. Apply selectively across the full VOD.
- `TEASER_OPEN` — Candidate for frame 1. Must work as a cold open with zero context.
- `TEASER_CLOSE` — Candidate for final clip. Must be the hardest-hitting moment in the Teaser.

## Audio Priority Rules
- Audio energy is the primary selector. If a clip doesn't hit aurally in the first 2 seconds, it's not a Teaser clip regardless of visual quality.
- Game audio can carry a Teaser moment — explosions, clutch sound design — but Jay's voice must be present somewhere in the first 30 seconds of the full Teaser sequence.
- No dead audio. Ever.
