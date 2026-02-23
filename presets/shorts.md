# YAPCUT PRESET: Shorts

*10–60 second vertical content for YouTube Shorts, TikTok, or Instagram Reels. Cut from raw VOD. Chronological order is optional. The only rule is: do not lose the viewer.*

## Output Mode: `cuts`

This preset produces **physical edit points**, not markers. Claude finds every viable Short in the VOD and outputs them all as clips on a single timeline.

### Output Format
- **File:** `yapcut_shorts.xml`
- **Structure:** One sequence. All Shorts as clipitems on a single timeline, separated by **2-second gaps** (60 frames at 30fps).
- **Clip naming:** Each clipitem gets a descriptive title — `"Morgan Freeman impression"`, `"Squad wipe no-scope"`, `"Discord argument escalates"`, etc. The name should be what you'd title the Short.
- **Volume:** Find everything. If a 2-hour stream yields 10 viable Shorts, output all 10. If it yields 3, output 3. Don't pad — but don't hold back.
- **Gaps:** The 2-second gaps between clips let the editor see where one Short ends and the next begins when scrubbing the timeline. Gaps are empty (no content).

## Target Output
- Format: Vertical (9:16), Platform-Agnostic
- Duration: **10–60 seconds**. 20-45 seconds is the sweet spot. A tight 12-second reaction arc is a valid Short.
- Shot reordering: Permitted and encouraged when it creates a tighter narrative arc

## Editorial Lens
The viewer has already decided not to watch this. Your job is to make them wrong in the first 2 seconds.

> "If the first spoken word or audio beat of this clip appeared in someone's feed, would their thumb hesitate?"

Shorts don't reward patience. Every second must be working. Setup is not optional — it's just shorter than you think.

## Content Priority Stack (Highest to Lowest)
1. **Immediate Peak Energy** — Clips that open at or near their climax and sustain. A punchline mid-delivery, a yell, a reaction already in progress, a bit that's already running hot. No runway required. Transcript signal: high energy speech, crosstalk, laughter, or elevated vocal tempo in the first few lines.
2. **Self-Contained Funny** — A bit, a riff, an impression, or a comedic exchange that has a clear setup→punchline structure within the 60-second window.
3. **Skill Moment with Vocal Confirmation** — A gameplay moment where Jay's verbal reaction confirms it was exceptional. Yelling, disbelief, immediate excited commentary. Without the vocal confirmation, YapCut cannot detect the play — flag only when Jay's reaction makes the moment audibly legible.
4. **Character Moments** — Jay being distinctly Jay: the voice work, the impressions, the professional actor instincts surfacing in casual context. Clips where the "pro actor streaming" angle is *audible*.
5. **Reaction Chains** — A moment that starts with Jay reacting and builds — squad loses it, something escalates. The escalation is the content.

## Implicit CUT Zones
- Anything requiring 10+ seconds of context to understand
- Moments that pay off well but open on dead energy
- Long gameplay sequences without a clear "moment" — even impressive plays
- Any clip where the funniest part is past the 45-second mark

## Structural Rules
- **The Hook:** First 2 seconds must contain an audio hook — a line mid-sentence, an exclamation, a laugh already in progress, a punchline landing. Do not open on Jay's standard greeting, setup narration ("so basically what happened was..."), or flat explanatory tone.
- **The Hold:** After the hook, the clip must maintain tension, escalation, or comedy momentum. Flag any clip where there's a dead 5-second audio window in the middle.
- **The Out:** Clean ending — a laugh, a hard cut on a punchline, a reaction. If the clip trails off or returns to ambient gameplay chatter, it's not a Short. Re-evaluate the trim.
- **Reorder Logic:** When reordering shots, the rule is: the reordered version must make *more* sense to a first-time viewer than the chronological version. Never reorder in a way that introduces continuity confusion. Context is a resource — spend it in the first 5 seconds, not the last.

## Caption / Title Tags (for export metadata)
- Tag clips by type: `SKILL`, `COMEDY`, `IMPRESSION`, `REACTION`, `GAMING`, `CHAOS`
- Tag platform suitability: `SHORT_FIRST` (pure vertical energy), `CLIP_ADAPT` (needs minor reframe or caption work)

## Audio Priority Rules
- Jay's voice must be clear. Any Short where his audio is muddied or buried under game audio is a hard cut.
- Impressions are premium Short content. Flag every clean impression moment regardless of surrounding gameplay.
- Silence is never acceptable in a Short. If there's a 3-second dead audio window, either it gets trimmed or it's not a Short.
- Music/SFX layering decisions are downstream of this tool — but flag clips where the game audio itself is a significant part of the comedic or hype payoff (explosion timing, sound design gags, etc.)
