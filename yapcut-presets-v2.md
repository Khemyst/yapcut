# YAPCUT v2 PRESETS — heyJayWalker

---

## PRESET: Battlefield Campaign
*Solo playthrough of BF6 campaign missions. Jay voiced Dylan Murphy — the player character. This is not a standard playthrough; this is an actor experiencing his own performance in a shipped game.*

### Target Output
- Format: YouTube VOD Edit (Episodic Series, Must Work Standalone)
- Ratio: Compress 1.5–3 hours into 20–30 minutes
- Marker Density Target: 15–20 markers per hour of source material

### Editorial Lens
The core draw is NOT the gameplay. It is Jay's real-time experience of a game he starred in.
Every editorial decision runs through this filter:
> "Does this moment reveal something about what it's like to BE Jay Walker playing Dylan Murphy?"

Gameplay that has nothing to do with this lens is filler. Good story beats with flat Jay reactions are filler. The intersection of both is gold.

### Content Priority Stack (Highest to Lowest)
1. **REACTION Moments** — Jay reacting to his own voice or performance. First time hearing a Murphy line in-game, calling out a take he remembers from the session, noticing a delivery that surprised him, laughing at or being moved by his own work. Detectable from transcript via: sudden shift in tone, self-referential commentary ("that's me," "oh that's the line where—", "I remember recording this"), laughter immediately following in-game dialogue, or unprompted production context following a game audio moment. Unique to this creator and this game. Flag everything.
2. **Behind-the-Scenes Commentary** — Jay offering production context: why a line was delivered a certain way, what the session was like, alternate takes, studio anecdotes, things the player wouldn't know.
3. **Story Beats** — Cutscenes or in-game dialogue sequences where Murphy is central. Keep if Jay's reactions or commentary are active. Cut if Jay goes silent and lets the game run without adding anything.
4. **Genuine Gameplay Skill** — Jay actually playing well. Keep if tight and paired with strong vocal energy. Cut if it's clean but quiet.
5. **CONTEXT Tags** — Brief setup moments before a major story beat or gameplay sequence. Use sparingly. Never more than 45 seconds.

### Implicit CUT Zones
- Quiet traversal and exploration with no commentary
- Repeated death/checkpoint loops unless Jay's frustration or commentary becomes the content
- Cutscenes or NPC dialogue where Jay has gone fully quiet and passive (watching, not reacting)
- Loadout / settings / map screen navigation
- Moments where Jay breaks entirely to read chat without a gameplay anchor

### Title-Specific Rules (Campaign)
- **Murphy Lines Playing ≠ Automatic Keep.** Jay needs to be actively reacting or commentating. A silent stretch of in-game dialogue — even if it's Murphy speaking — is still a cut. From transcript: flag silent windows of 10+ seconds during what appears to be a cutscene or heavy NPC dialogue section.
- **Episodic Continuity:** Each edit must make sense to a first-time viewer. Flag any moment that requires previous episode context without a quick verbal recap. If Jay doesn't provide it, it may need a title card note.
- **First Reactions Are Non-Repeatable.** If Jay hears a line for the first time and reacts authentically, that's a once-per-game opportunity. Flag it regardless of what else is happening.
- **Self-Commentary Elevates Everything.** A mediocre gameplay moment becomes a KEEP if Jay simultaneously explains something about how that sequence was recorded or designed.

### Marker Types
> **Note for implementation:** `REACTION` is a 6th marker type specific to this preset. Add to `tools/validate_xml.py` alongside the standard five (`KEEP`, `MAYBE`, `CUT`, `MOMENT`, `CONTEXT`). It represents a distinct editorial category — actor-reacting-to-own-performance — that warrants independent filtering in Premiere's Markers panel.

- `KEEP` — Include in the edit
- `MAYBE` — Strong commentary but not directly about Jay's performance. Preserve for editorial judgment — often good bridge material.
- `CUT` — Explicit dead air or off-lens content
- `MOMENT` — Short extraction candidate. See MOMENT Extraction section above.
- `REACTION` — Jay's verbal/vocal response to his own performance. High priority. Always flag.
- `CONTEXT` — Setup/bridge material. Use sparingly, hard cap 45 seconds.

### Audio Priority Rules
- Jay's vocal commentary is the primary content layer. Game audio is secondary.
- Strong Jay reaction with mediocre game moment = KEEP
- Impressive game moment with flat, silent Jay = CUT. Cannot be flagged as MOMENT from transcript alone — requires manual pass.
- In-game Murphy dialogue followed by 5+ seconds of Jay silence is ambiguous. Do not cut mid-silence. Flag as MAYBE and note the timestamp — editorial call on whether Jay is processing or has checked out.

### MOMENT Extraction (Campaign Shorts)
Campaign produces a specific, high-value Short structure that should be flagged explicitly:

**The First-Reaction Arc:** Game audio plays a Murphy line → brief silence (Jay processing) → immediate verbal response. This is a complete, self-contained narrative in 20–30 seconds. Structure: setup (game moment or NPC prompt) → the performance lands → Jay's unscripted reaction. These are non-repeatable and among the best Short candidates in any VOD.

Detection signal: Jay says something self-referential immediately after a period of relative quiet. Phrases like "wait," "oh," "that's—", laughter with no apparent game-event trigger, or sudden shift into production commentary.

MOMENT duration target for Campaign: 20–40 seconds. Longer than typical (Shorts preset caps at 60s), but these clips need the breath before the reaction to work.

---

## PRESET: Battlefam
*Live interview show. Jay hosts cast, crew, consultants, and collaborators from Battlefield 6. He is simultaneously host and insider — a cast member interviewing fellow cast members.*

### Target Output
- Format: YouTube Podcast / Interview VOD
- Ratio: Compress 1–2 hour livestream into 40–60 minutes (looser than gameplay cuts — conversation has inherent pacing)
- Marker Density Target: 10–15 markers per hour of source material

### Editorial Lens
This is a talk show, not a gameplay video. The game is the shared context, not the content.
The editorial job is to identify where the conversation is *irreplaceable* — information, insight, or chemistry that can't be Googled — and cut everything that could've been in any other interview.

> "Would a Battlefield fan who's seen a hundred YouTube interviews still want to watch THIS moment?"

### Content Priority Stack (Highest to Lowest)
1. **Exclusive Insight** — Things only this guest knows. On-set stories, casting decisions, performance direction, cut content, production chaos, creative friction. Irreplaceable by definition.
2. **Jay + Guest Chemistry** — Moments where the actor-to-actor dynamic produces something you don't get from journalist interviews. Shared references, mutual respect, roasting each other.
3. **Fan-Relevant Lore / Context** — Guests explaining how a character was developed, how military consultants shaped gameplay or VO, how the cast interacted off-script.
4. **Jay's Host Commentary / Personal Angle** — Jay offering his own perspective as someone who is both creator and cast member. His take carries weight. Flag when he goes beyond "good host question" into genuine personal perspective.
5. **Live Chat Interaction** — Only if it triggers a strong guest or Jay reaction. Cut routine chat reads entirely.

### Implicit CUT Zones
- Technical difficulties, stream hold music, joining delays
- Intro/outro small talk that doesn't reveal character (first 2–3 minutes of warmup)
- Repeated explanations of who the guest is or what the show is (keep one per episode max)
- Tangents that run more than 90 seconds without landing anywhere specific
- Chat reads that don't add to the conversation
- Sponsor reads (unless they're funny or Jay improvises something good)

### Title-Specific Rules (Battlefam)
- **Guest Credibility Moments:** When a guest says something that only they could say — a specific production memory, a technique, a piece of trivia not in any press materials — that's the anchor of the edit. Build around it.
- **Jay's Dual Role:** He's host AND insider. Flag any moment where he breaks from standard host mode to contribute first-person knowledge as a cast member. These are the moments that differentiate Battlefam from every other BF6 interview.
- **Clip Architecture:** Battlefam edits should feel like they have a loose narrative arc — not just "good moments in order." Flag potential open, mid-point anchor (best exclusive moment), and close (something warm, funny, or memorable to end on). Tag as `OPEN`, `ANCHOR`, `CLOSE` in addition to standard markers.

### Marker Types
- `KEEP` — Include in the edit
- `CUT` — Dead air, filler, tangent without payoff
- `MOMENT` — Standalone clip extraction (strong enough to work without context)
- `OPEN` — Strong candidate for the episode's opening sequence
- `ANCHOR` — The best exclusive or most compelling exchange in the episode. One per episode.
- `CLOSE` — Warm, funny, or memorable moment to end on

### Audio Priority Rules
- Guest audio quality is a gating factor. Flag segments with severe guest audio issues — a great moment in a bad audio window may still need to be cut for watchability.
- If guest audio is marginal but Jay's verbal reaction is strong (laughing, building on what the guest said, clearly engaged), flag as MAYBE with note. Strong Jay response can indicate the guest moment was worth preserving even if the guest audio itself is rough.
- Silence and thinking pauses are valid in podcast format — do not over-cut for pace. Let breath in.
- Laughter > any other audio event. Both Jay and guest laughing = automatic KEEP.

---

## PRESET: Shorts
*30–60 second vertical content for YouTube Shorts, TikTok, or Instagram Reels. Cut from raw VOD. Chronological order is optional. The only rule is: do not lose the viewer.*

### Target Output
- Format: Vertical (9:16), Platform-Agnostic
- Duration: 30–60 seconds hard cap. 45 seconds is the sweet spot.
- Marker Density Target: Flag aggressively — 25–35 MOMENT candidates per hour of source material. Most won't be used. Volume is the point.
- Shot reordering: Permitted and encouraged when it creates a tighter narrative arc

### Editorial Lens
The viewer has already decided not to watch this. Your job is to make them wrong in the first 2 seconds.

> "If the first spoken word or audio beat of this clip appeared in someone's feed, would their thumb hesitate?"

Shorts don't reward patience. Every second must be working. Setup is not optional — it's just shorter than you think.

### Content Priority Stack (Highest to Lowest)
1. **Immediate Peak Energy** — Clips that open at or near their climax and sustain. A punchline mid-delivery, a yell, a reaction already in progress, a bit that's already running hot. No runway required. Transcript signal: high energy speech, crosstalk, laughter, or elevated vocal tempo in the first few lines.
2. **Self-Contained Funny** — A bit, a riff, an impression, or a comedic exchange that has a clear setup→punchline structure within the 60-second window.
3. **Skill Moment with Vocal Confirmation** — A gameplay moment where Jay's verbal reaction confirms it was exceptional. Yelling, disbelief, immediate excited commentary. Without the vocal confirmation, YapCut cannot detect the play — flag only when Jay's reaction makes the moment audibly legible.
4. **Character Moments** — Jay being distinctly Jay: the voice work, the impressions, the professional actor instincts surfacing in casual context. Clips where the "pro actor streaming" angle is *audible*.
5. **Reaction Chains** — A moment that starts with Jay reacting and builds — squad loses it, something escalates. The escalation is the content.

### Implicit CUT Zones
- Anything requiring 10+ seconds of context to understand
- Moments that pay off well but open on dead energy
- Long gameplay sequences without a clear "moment" — even impressive plays
- Any clip where the funniest part is past the 45-second mark

### Structural Rules
- **The Hook:** First 2 seconds must contain an audio hook — a line mid-sentence, an exclamation, a laugh already in progress, a punchline landing. Do not open on Jay's standard greeting, setup narration ("so basically what happened was..."), or flat explanatory tone.
- **The Hold:** After the hook, the clip must maintain tension, escalation, or comedy momentum. Flag any clip where there's a dead 5-second audio window in the middle.
- **The Out:** Clean ending — a laugh, a hard cut on a punchline, a reaction. If the clip trails off or returns to ambient gameplay chatter, it's not a Short. Re-evaluate the trim.
- **Reorder Logic:** When reordering shots, the rule is: the reordered version must make *more* sense to a first-time viewer than the chronological version. Never reorder in a way that introduces continuity confusion. Context is a resource — spend it in the first 5 seconds, not the last.

### Caption / Title Tags (for export metadata)
- Tag clips by type: `SKILL`, `COMEDY`, `IMPRESSION`, `REACTION`, `GAMING`, `CHAOS`
- Tag platform suitability: `SHORT_FIRST` (pure vertical energy), `CLIP_ADAPT` (needs minor reframe or caption work)

### Audio Priority Rules
- Jay's voice must be clear. Any Short where his audio is muddied or buried under game audio is a hard cut.
- Impressions are premium Short content. Flag every clean impression moment regardless of surrounding gameplay.
- Silence is never acceptable in a Short. If there's a 3-second dead audio window, either it gets trimmed or it's not a Short.
- Music/SFX layering decisions are downstream of this tool — but flag clips where the game audio itself is a significant part of the comedic or hype payoff (explosion timing, sound design gags, etc.)

---

## PRESET: Teaser
*Placed at the beginning of the final video. The viewer has clicked but hasn't committed. This is the closer — 60–120 seconds of the best material from the entire VOD, structured to make leaving feel wrong.*

### Target Output
- Format: Front-loaded video intro (horizontal, same project timeline)
- Duration: 60–120 seconds. 90 seconds is optimal.
- Marker Density: Select only — this is a curation pass, not a scan pass. Pull 6–10 TEASER-flagged clips from across the full VOD. Prefer material from the latter half (the viewer hasn't seen it yet).
- Chronological order: Irrelevant. This is a trailer.

### Editorial Lens
The viewer clicked the thumbnail. Now they're deciding if the next 25 minutes of their life belongs to this video.

> "After 90 seconds, does the viewer feel like they've seen the trailer for a movie they *have* to watch — but haven't actually seen the movie yet?"

The Teaser shows peaks. It does not explain them. If a clip makes sense without context, it's a candidate. If it needs setup, it's not.

### Content Priority Stack (Highest to Lowest)
1. **The Best 3 Moments in the VOD** — Whatever is objectively most impressive, funniest, or most unbelievable. These are the reason the video exists. Lead with one, end with one.
2. **Energy Escalation Clips** — Moments where something rapidly builds — a clutch in progress, a bit gaining momentum, a reaction getting bigger. Cut before the peak lands. Make them want to see it pay off.
3. **Audio-First Hooks** — A line, a yell, an impression, a laugh that's compelling without needing visual context. These work as cold opens.
4. **Curiosity Gaps** — Moments that are clearly significant but deliberately incomplete. Something that makes the viewer think "wait, what happens next?" Cut away before the resolution.
5. **Tonal Range Clips** — If the video has both hype and funny, show both. A Teaser that's only hype or only comedy undersells the full video.

### Implicit CUT Zones
- Anything that resolves too cleanly within the Teaser itself — save the payoff for the video
- Moments that require even 5 seconds of context to understand
- Quiet or slow moments — CONTEXT tags have no place here
- Repeated clip types — two kill moments, two impression clips. Diversity of beat > redundancy of quality.

### Structural Rules
- **Frame 1:** Must be at full energy. No countdown, no logo, no "hey guys." Start mid-action, mid-laugh, or mid-line.
- **Clip Length Within Teaser:** Individual clips should run 5–15 seconds each. Longer = you're giving it away.
- **Intentional Interruption:** Cut clips at moments of maximum tension or anticipation, not at resolution. The Teaser is a debt the rest of the video repays.
- **Closing Shot:** The last clip in the Teaser should be your single strongest individual moment — comedically, emotionally, or energetically. End hard.

### Marker Types
- `TEASER` — Pull candidate for the pre-roll intro. Apply selectively across the full VOD.
- `TEASER_OPEN` — Candidate for frame 1. Must work as a cold open with zero context.
- `TEASER_CLOSE` — Candidate for final clip. Must be the hardest-hitting moment in the Teaser.

### Audio Priority Rules
- Audio energy is the primary selector. If a clip doesn't hit aurally in the first 2 seconds, it's not a Teaser clip regardless of visual quality.
- Game audio can carry a Teaser moment — explosions, clutch sound design — but Jay's voice must be present somewhere in the first 30 seconds of the full Teaser sequence.
- No dead audio. Ever.

---

## PRESET: Chill Stream
*Rocket League, Arc Raiders, Battlefield multiplayer, or similar. Usually playing with friends on Discord. Comedy-first. Jay's differentiating value is professional actor / voice actor / impressionist — not mechanical skill.*

### Target Output
- Format: YouTube VOD Highlight Reel
- Ratio: Compress 2–4 hours into 20–30 minutes
- Marker Density Target: 18–25 markers per hour of source material

### Editorial Lens
This is a comedy show that happens to be set inside a video game.

Jay's skill level is not the draw (Rocket League is the exception where a legitimately great mechanical moment can carry its own weight). The draw is: professional actor energy, impressions, chemistry with friends, moments where the comedy or chaos surprises even Jay.

> "Would this be funny if the game audio was muted?"

If yes: strong KEEP. If no: it requires vocal confirmation to be flaggable. YapCut cannot detect a spectacular play from transcript alone — if Jay isn't reacting to it verbally, it doesn't exist to this tool. Moments that are visually impressive but audibly flat require a manual pass.

### Content Priority Stack (Highest to Lowest)
1. **Impressions** — Any time Jay does a voice. Doesn't matter what's happening in the game. A clean impression in a chill stream is always a KEEP and an automatic MOMENT flag for Shorts.
2. **Squad Banter / Riffs** — The Discord chemistry. Genuine laughter, escalating bits, friend reactions to Jay's impressions, arguments that resolve into comedy. This is the core content of chill streams.
3. **Comedic Fails** — Deaths, bad decisions, miscommunications that lead to failure, physics chaos. Always better with strong Jay vocal reaction.
4. **Legitimate Skill Moments (Rocket League Priority)** — In RL, a mechanically impressive play is worth keeping even without heavy comedy. However: YapCut cannot detect the play itself from transcript. The signal is Jay's vocal reaction — yelling, "let's go," disbelief, or squad eruption. Flag these when the verbal response indicates something exceptional happened. Plays with no vocal confirmation require a manual pass and cannot be auto-flagged.
5. **Momentum Runs** — Extended stretches of winning with strong squad energy. Keep if the energy is sustained throughout. Cut if it's competent but quiet.

### Implicit CUT Zones
- Long quiet gameplay stretches with no banter, no impressions, no comedy
- Repetitive grinding sequences (ranked queues, farming, looting) without audio value
- Friend technical issues / Discord drops / "can you hear me" loops
- Donation reads unless Jay's response is a full comedic bit or the timing creates a funny interruption
- Menu navigation, queue waiting without active conversation

### Title-Specific Rules (Chill Stream)
- **Impression Flagging:** Flag every impression. Don't evaluate them at scan time — that's an editorial call. But nothing gets missed. `IMPRESSION` is a first-class marker.
- **Discord Audio Quality Matters:** Flag moments where a friend's punchline or reaction is clearly present but audio quality drops. Strong friend moments with bad audio = MAYBE. Strong Jay moment with bad friend audio = KEEP if Jay's audio is clean.
- **Rocket League Exception:** A strong RL play is KEEP even without full comedy energy — but YapCut can only detect this through Jay's vocal response. The detection signal is immediate celebratory or disbelief language. If Jay doesn't react verbally, the play is invisible to this tool and requires a manual pass. Don't over-flag quiet RL moments as KEEP on the assumption that something spectacular happened.
- **Bit Tracking:** Some of the best chill stream moments are running bits that build over 10–20 minutes. Flag the origin of a bit as `BIT_OPEN` and its peak payoff as `BIT_PAY`. Both must appear in the edit — the payoff without the setup is half a joke.

### Marker Types
- `KEEP` — Include in the edit
- `CUT` — Dead air, repetitive gameplay, no comedy value
- `MOMENT` — Short extraction candidate
- `IMPRESSION` — Jay doing a voice. Always flag. Always.
- `BIT_OPEN` — The start of a recurring bit or running joke
- `BIT_PAY` — The payoff of that bit (often minutes later in the VOD)
- `MAYBE` — Skill moment or decent exchange that needs editorial judgment

### Audio Priority Rules
- Jay's vocal energy is the primary content axis. Game audio is set dressing.
- An impression with bad game audio still > good game moment with no vocal energy.
- Squad laughter — even from Discord — is a strong KEEP signal. Group reaction = the audience is already responding.
- Dead mic (Jay fully quiet for 20+ seconds) is an automatic scan flag — either something's wrong or it's dead air.
- Impression audio quality specifically: a blurry or buried impression is worse than no impression. Flag `IMPRESSION_AUDIO_ISSUE` if the bit is there but the audio quality undermines it.
