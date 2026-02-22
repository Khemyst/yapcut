"""Generate FCP XML rough cut for BF6 Part 3 stream."""
import json
from urllib.parse import quote

TRANSCRIPT_PATH = r"C:\Users\jaywa.NEUTRON\Documents\heyJayWalker\Streams\Battlefield\BATTLEFIELD 6 VOICE ACTOR REACTS TO HIS OWN CHARACTER _ PART THREE.json"
SOURCE_PATH = "C:/Users/jaywa.NEUTRON/Documents/heyJayWalker/Streams/Battlefield/BATTLEFIELD 6 VOICE ACTOR REACTS TO HIS OWN CHARACTER _ PART THREE.mp4"
OUTPUT_PATH = r"C:\Users\jaywa.NEUTRON\Projects\claudedits\output\bf6_part3_rough_cut.xml"

TIMEBASE = 30
NTSC = "FALSE"
SOURCE_DURATION_SEC = 4558.146757
SOURCE_DURATION_FRAMES = int(SOURCE_DURATION_SEC * TIMEBASE)

with open(TRANSCRIPT_PATH, encoding="utf-8") as f:
    data = json.load(f)

segs = data["segments"]
pathurl = "file:///" + quote(SOURCE_PATH, safe=":/")

cuts = [
    ([20], "Context - first time seeing our work"),
    ([21, 22, 23], "Al Pacino impression"),
    ([32, 33], "Brooklyn excitement"),
    ([35, 36], "Helicopter mocap rig BTS"),
    ([39, 40], "Ashley Earl - Gekko"),
    ([41, 42], "Seeing himself in-game"),
    ([44, 45, 46, 47], "Player control vs acting craft"),
    ([57, 58, 59, 60, 61], "Hammer time"),
    ([62, 63], "Murphy night vision"),
    ([65], "Cant throw this hammer"),
    ([68], "Slipper energy"),
    ([78, 79, 80], "Trapdoor mocap rig BTS"),
    ([86, 87, 88, 89], "Hammer addiction"),
    ([92], "Forgot playing on veteran"),
    ([95], "Train chase pt1"),
    ([98], "Train chase pt2"),
    ([110, 111], "Red barrel death"),
    ([113, 114, 115], "Sidearm hero moment BTS"),
    ([116, 117], "Fell through map"),
    ([119, 120], "Military advisors BTS"),
    ([121], "Drivers test joke"),
    ([131], "Imagining the city"),
    ([133], "Bridge battle"),
    ([139, 140, 141], "Bridge combat intensity"),
    ([144, 145], "Teammate hammer apology"),
    ([149, 150], "Bonk bonk Super Smash"),
    ([158], "Murphy controlling Has"),
    ([159], "Refuse to suck at this game"),
    ([167], "Tony Curran - great actor"),
    ([169], "Mission resolution"),
    ([172, 173, 174], "This is what Dagger does"),
]

# Calculate clip data
clips = []
timeline_pos = 0
for seg_indices, label in cuts:
    first = segs[seg_indices[0]]
    last = segs[seg_indices[-1]]
    start_sec = first["start"]
    end_sec = last["start"] + last["duration"]

    in_frame = int(start_sec * TIMEBASE)
    out_frame = int(end_sec * TIMEBASE)
    clip_dur = out_frame - in_frame

    clips.append({
        "label": label,
        "in": in_frame,
        "out": out_frame,
        "start": timeline_pos,
        "end": timeline_pos + clip_dur,
    })
    timeline_pos += clip_dur

total_timeline_frames = timeline_pos
filename = "BATTLEFIELD 6 VOICE ACTOR REACTS TO HIS OWN CHARACTER _ PART THREE.mp4"

# Build XML
x = []
x.append('<?xml version="1.0" encoding="UTF-8"?>')
x.append('<!DOCTYPE xmeml>')
x.append('<xmeml version="5">')
x.append('  <sequence id="seq-001">')
x.append('    <name>BF6 Voice Actor Reacts Part 3 - Rough Cut</name>')
x.append(f'    <duration>{total_timeline_frames}</duration>')
x.append('    <rate>')
x.append(f'      <timebase>{TIMEBASE}</timebase>')
x.append(f'      <ntsc>{NTSC}</ntsc>')
x.append('    </rate>')
x.append('    <media>')

# VIDEO TRACK
x.append('      <video>')
x.append('        <format>')
x.append('          <samplecharacteristics>')
x.append('            <width>1280</width>')
x.append('            <height>720</height>')
x.append('            <pixelaspectratio>square</pixelaspectratio>')
x.append('          </samplecharacteristics>')
x.append('        </format>')
x.append('        <track>')

for i, clip in enumerate(clips):
    x.append(f'          <clipitem id="v-clip-{i+1:03d}">')
    x.append(f'            <name>{clip["label"]}</name>')
    x.append(f'            <duration>{SOURCE_DURATION_FRAMES}</duration>')
    x.append('            <rate>')
    x.append(f'              <timebase>{TIMEBASE}</timebase>')
    x.append(f'              <ntsc>{NTSC}</ntsc>')
    x.append('            </rate>')
    x.append(f'            <start>{clip["start"]}</start>')
    x.append(f'            <end>{clip["end"]}</end>')
    x.append(f'            <in>{clip["in"]}</in>')
    x.append(f'            <out>{clip["out"]}</out>')
    if i == 0:
        x.append('            <file id="file-001">')
        x.append(f'              <name>{filename}</name>')
        x.append(f'              <pathurl>{pathurl}</pathurl>')
        x.append(f'              <duration>{SOURCE_DURATION_FRAMES}</duration>')
        x.append('              <rate>')
        x.append(f'                <timebase>{TIMEBASE}</timebase>')
        x.append(f'                <ntsc>{NTSC}</ntsc>')
        x.append('              </rate>')
        x.append('              <media>')
        x.append('                <video>')
        x.append('                  <samplecharacteristics>')
        x.append('                    <width>1280</width>')
        x.append('                    <height>720</height>')
        x.append('                    <pixelaspectratio>square</pixelaspectratio>')
        x.append('                  </samplecharacteristics>')
        x.append('                </video>')
        x.append('                <audio>')
        x.append('                  <channelcount>2</channelcount>')
        x.append('                  <samplecharacteristics>')
        x.append('                    <depth>16</depth>')
        x.append('                    <samplerate>44100</samplerate>')
        x.append('                  </samplecharacteristics>')
        x.append('                </audio>')
        x.append('              </media>')
        x.append('            </file>')
    else:
        x.append('            <file id="file-001"/>')
    x.append('          </clipitem>')

x.append('        </track>')
x.append('      </video>')

# AUDIO TRACKS (2 tracks for stereo - one per channel)
x.append('      <audio>')
x.append('        <numOutputChannels>2</numOutputChannels>')
x.append('        <format>')
x.append('          <samplecharacteristics>')
x.append('            <depth>16</depth>')
x.append('            <samplerate>44100</samplerate>')
x.append('          </samplecharacteristics>')
x.append('        </format>')

for ch in (1, 2):
    x.append('        <track>')
    for i, clip in enumerate(clips):
        x.append(f'          <clipitem id="a{ch}-clip-{i+1:03d}">')
        x.append(f'            <name>{clip["label"]}</name>')
        x.append(f'            <duration>{SOURCE_DURATION_FRAMES}</duration>')
        x.append('            <rate>')
        x.append(f'              <timebase>{TIMEBASE}</timebase>')
        x.append(f'              <ntsc>{NTSC}</ntsc>')
        x.append('            </rate>')
        x.append(f'            <start>{clip["start"]}</start>')
        x.append(f'            <end>{clip["end"]}</end>')
        x.append(f'            <in>{clip["in"]}</in>')
        x.append(f'            <out>{clip["out"]}</out>')
        x.append('            <file id="file-001"/>')
        x.append('            <sourcetrack>')
        x.append('              <mediatype>audio</mediatype>')
        x.append(f'              <trackindex>{ch}</trackindex>')
        x.append('            </sourcetrack>')
        x.append('          </clipitem>')
    x.append('        </track>')

x.append('      </audio>')
x.append('    </media>')
x.append('  </sequence>')
x.append('</xmeml>')

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(x))

print(f"Written to: {OUTPUT_PATH}")
print(f"Total clips: {len(clips)}")
print(f"Timeline: {total_timeline_frames} frames = {total_timeline_frames/TIMEBASE:.1f}s = {total_timeline_frames/TIMEBASE/60:.1f} min")
