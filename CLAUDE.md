# ClaudEdits

ClaudEdits is a conversational video editing workflow. There is no automated pipeline, no scoring engine, no rendering. The human describes what they want from an edit, Claude reads the transcript, they discuss it, and Claude outputs an FCP XML file that Premiere Pro imports as a rough cut sequence.

## How the Workflow Operates

1. The human provides a **timecoded transcript** (JSON) of a stream VOD
2. Claude reads the transcript and understands the content
3. The human describes what kind of edit they want (highlights, funny moments, a narrative arc, etc.)
4. They discuss — Claude proposes segments, the human refines
5. Claude generates an **FCP 7 XML** file (xmeml v5) that Premiere Pro can import
6. The human imports the XML into Premiere Pro and has a rough cut timeline ready to polish

## Project Structure

```
claudedits/
├── CLAUDE.md              # This file — project knowledge base
├── claude instructions.md # Original project brief
├── scripts/
│   └── validate_xml.py    # FCP XML validator
├── transcripts/           # Input transcript JSON files
└── output/                # Generated FCP XML files
```

## Input Transcript Format

Transcripts come from a separate transcription tool (Stage 2 output). The JSON schema:

```json
{
  "language": "en-us",
  "segments": [
    {
      "start": 1.56,          // seconds from start of source media
      "duration": 21.9,       // segment duration in seconds
      "speaker": "uuid-here", // references speakers[] array
      "language": "en-us",
      "words": [
        {
          "start": 1.56,           // word start time in seconds
          "duration": 0.54,        // word duration in seconds
          "confidence": 0.88,      // transcription confidence 0-1
          "eos": false,            // end of sentence flag
          "tags": [],              // e.g. ["disfluency"]
          "text": "Hello,",        // the word text
          "type": "word"           // token type
        }
      ]
    }
  ],
  "speakers": [
    {
      "id": "uuid-here",
      "name": "Unknown"     // speaker label
    }
  ]
}
```

Key details:
- All timestamps are in **seconds** (float), not frames
- `eos: true` marks sentence boundaries — useful for finding natural cut points
- `tags: ["disfluency"]` marks filler words/stutters
- Segments group words by speaker turn and natural pauses
- A single speaker may have many segments (they represent pauses/breaks, not unique speakers)

## FCP 7 XML Schema (xmeml v5)

Premiere Pro imports FCP 7 XML (not FCPX). The format uses `xmeml version="5"` as the root element.

### Critical Concepts

- **All time values in the XML are in frames**, not seconds. Convert: `frame = seconds * timebase`
- **timebase**: The frame rate denominator. For 29.97fps: timebase=30, ntsc=TRUE. For 30fps: timebase=30, ntsc=FALSE
- **`start`/`end`**: Position on the sequence timeline (in frames)
- **`in`/`out`**: Trim points within the source media (in frames)
- **`file` elements**: Referenced by ID. Define once with full details, then reference by ID only in subsequent clipitems

### Minimal Valid Sequence

```xml
<?xml version="1.0" encoding="UTF-8"?>
<xmeml version="5">
  <sequence id="seq-001">
    <name>Rough Cut</name>
    <duration>{total_frames}</duration>
    <rate>
      <timebase>30</timebase>
      <ntsc>TRUE</ntsc>
    </rate>
    <media>
      <video>
        <track>
          <clipitem id="v-clip-001">
            <name>Clip 1</name>
            <duration>{source_total_frames}</duration>
            <rate>
              <timebase>30</timebase>
              <ntsc>TRUE</ntsc>
            </rate>
            <start>{timeline_start_frame}</start>
            <end>{timeline_end_frame}</end>
            <in>{source_in_frame}</in>
            <out>{source_out_frame}</out>
            <file id="file-001">
              <name>source.mp4</name>
              <pathurl>file:///C:/Users/jaywa.NEUTRON/Videos/Streams/source.mp4</pathurl>
              <duration>{source_total_frames}</duration>
              <rate>
                <timebase>30</timebase>
                <ntsc>TRUE</ntsc>
              </rate>
              <media>
                <video>
                  <samplecharacteristics>
                    <width>1920</width>
                    <height>1080</height>
                  </samplecharacteristics>
                </video>
                <audio>
                  <samplecharacteristics>
                    <depth>16</depth>
                    <samplerate>48000</samplerate>
                  </samplecharacteristics>
                </audio>
              </media>
            </file>
          </clipitem>
        </track>
      </video>
      <audio>
        <track>
          <clipitem id="a-clip-001">
            <name>Clip 1</name>
            <duration>{source_total_frames}</duration>
            <rate>
              <timebase>30</timebase>
              <ntsc>TRUE</ntsc>
            </rate>
            <start>{timeline_start_frame}</start>
            <end>{timeline_end_frame}</end>
            <in>{source_in_frame}</in>
            <out>{source_out_frame}</out>
            <file id="file-001"/>
          </clipitem>
        </track>
      </audio>
    </media>
  </sequence>
</xmeml>
```

### Rules for Generating XML

1. **One video track, one audio track minimum** — both referencing the same source file
2. **Clipitems on the timeline must not overlap** — `end` of one clip = `start` of next
3. **File element defined once** with full details (pathurl, duration, media characteristics), then referenced by `id` only in subsequent clips
4. **pathurl uses forward slashes** and `file:///` prefix. Spaces must be URL-encoded (`%20`)
5. **Rate block** must appear in sequence, each clipitem, and the file element
6. **Video and audio clipitems must be paired** — same `start`/`end`/`in`/`out` values for linked clips

### Time Conversion

```
frame_number = int(time_in_seconds * timebase)
```

When `ntsc=TRUE` and `timebase=30`, the actual rate is 29.97fps but frame numbers still use 30 as the multiplier. The NLE handles the pulldown internally.

## Media Path Conventions

- Source media lives at: `C:\Users\jaywa.NEUTRON\Documents\heyJayWalker\Streams\`
- In XML pathurl format: `file:///C:/Users/jaywa.NEUTRON/Documents/heyJayWalker/Streams/`
- URL-encode spaces and special characters in filenames
- The human will specify which source file to reference for each edit session
- Generated XML goes in `output/` with descriptive filenames

## Editorial Guidelines

*(Building these out over time — add preferences here as they emerge)*

- Default to cutting on sentence boundaries (`eos: true`) for cleaner edits
- Prefer leaving ~0.5s padding before/after cut points for breathing room
- When selecting highlights, favor segments with high word confidence scores
- Flag disfluencies (`tags: ["disfluency"]`) but don't auto-remove — let the human decide

## Generating an Edit

When the human asks for an edit:

1. Read and understand the full transcript
2. Propose specific segments with timestamps and brief descriptions of content
3. Discuss and refine the selection with the human
4. Once approved, generate the FCP XML with proper frame calculations
5. Save to `output/` and run `python scripts/validate_xml.py output/filename.xml`
6. Share the validation results and the file path

## Validation

Run the validator before delivering any XML:

```bash
python scripts/validate_xml.py output/my_edit.xml
```

The validator checks: XML well-formedness, required FCP elements, structural integrity, timeline continuity.
