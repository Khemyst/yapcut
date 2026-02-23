# YAPCUT PRESET: Chill Stream

*Rocket League, Arc Raiders, Battlefield multiplayer, or similar. Usually playing with friends on Discord. Comedy-first. Jay's differentiating value is professional actor / voice actor / impressionist — not mechanical skill.*

## Target Output
- Format: YouTube VOD Highlight Reel
- Ratio: Compress 2–4 hours into 20–30 minutes
- Marker Density Target: 18–25 markers per hour of source material

## Editorial Lens
This is a comedy show that happens to be set inside a video game.

Jay's skill level is not the draw (Rocket League is the exception where a legitimately great mechanical moment can carry its own weight). The draw is: professional actor energy, impressions, chemistry with friends, moments where the comedy or chaos surprises even Jay.

> "Would this be funny if the game audio was muted?"

If yes: strong KEEP. If no: it requires vocal confirmation to be flaggable. YapCut cannot detect a spectacular play from transcript alone — if Jay isn't reacting to it verbally, it doesn't exist to this tool. Moments that are visually impressive but audibly flat require a manual pass.

## Content Priority Stack (Highest to Lowest)
1. **Impressions** — Any time Jay does a voice. Doesn't matter what's happening in the game. A clean impression in a chill stream is always a KEEP and an automatic MOMENT flag for Shorts.
2. **Squad Banter / Riffs** — The Discord chemistry. Genuine laughter, escalating bits, friend reactions to Jay's impressions, arguments that resolve into comedy. This is the core content of chill streams.
3. **Comedic Fails** — Deaths, bad decisions, miscommunications that lead to failure, physics chaos. Always better with strong Jay vocal reaction.
4. **Legitimate Skill Moments (Rocket League Priority)** — In RL, a mechanically impressive play is worth keeping even without heavy comedy. However: YapCut cannot detect the play itself from transcript. The signal is Jay's vocal reaction — yelling, "let's go," disbelief, or squad eruption. Flag these when the verbal response indicates something exceptional happened. Plays with no vocal confirmation require a manual pass and cannot be auto-flagged.
5. **Momentum Runs** — Extended stretches of winning with strong squad energy. Keep if the energy is sustained throughout. Cut if it's competent but quiet.

## Implicit CUT Zones
- Long quiet gameplay stretches with no banter, no impressions, no comedy
- Repetitive grinding sequences (ranked queues, farming, looting) without audio value
- Friend technical issues / Discord drops / "can you hear me" loops
- Donation reads unless Jay's response is a full comedic bit or the timing creates a funny interruption
- Menu navigation, queue waiting without active conversation

## Title-Specific Rules (Chill Stream)
- **Impression Flagging:** Flag every impression. Don't evaluate them at scan time — that's an editorial call. But nothing gets missed. `IMPRESSION` is a first-class marker.
- **Discord Audio Quality Matters:** Flag moments where a friend's punchline or reaction is clearly present but audio quality drops. Strong friend moments with bad audio = MAYBE. Strong Jay moment with bad friend audio = KEEP if Jay's audio is clean.
- **Rocket League Exception:** A strong RL play is KEEP even without full comedy energy — but YapCut can only detect this through Jay's vocal response. The detection signal is immediate celebratory or disbelief language. If Jay doesn't react verbally, the play is invisible to this tool and requires a manual pass. Don't over-flag quiet RL moments as KEEP on the assumption that something spectacular happened.
- **Bit Tracking:** Some of the best chill stream moments are running bits that build over 10–20 minutes. Flag the origin of a bit as `BIT_OPEN` and its peak payoff as `BIT_PAY`. Both must appear in the edit — the payoff without the setup is half a joke.

## Marker Types
- `KEEP` — Include in the edit
- `CUT` — Dead air, repetitive gameplay, no comedy value
- `MOMENT` — Short extraction candidate
- `IMPRESSION` — Jay doing a voice. Always flag. Always.
- `BIT_OPEN` — The start of a recurring bit or running joke
- `BIT_PAY` — The payoff of that bit (often minutes later in the VOD)
- `MAYBE` — Skill moment or decent exchange that needs editorial judgment

## Audio Priority Rules
- Jay's vocal energy is the primary content axis. Game audio is set dressing.
- An impression with bad game audio still > good game moment with no vocal energy.
- Squad laughter — even from Discord — is a strong KEEP signal. Group reaction = the audience is already responding.
- Dead mic (Jay fully quiet for 20+ seconds) is an automatic scan flag — either something's wrong or it's dead air.
- Impression audio quality specifically: a blurry or buried impression is worse than no impression. Flag `IMPRESSION_AUDIO_ISSUE` if the bit is there but the audio quality undermines it.
