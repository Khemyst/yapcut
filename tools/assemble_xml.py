"""
YapCut Stage 3 — Assemble FCP 7 XML from segment_list.json

Takes a segment_list.json (precise timestamps from Stage 2) and produces a
valid FCP 7 XML file (xmeml v5) with:

- V1/A1-A2: Physical edit points (the actual cut timeline), internal dead air removed
- V2: Full VOD reference with spanned markers showing editorial decisions
- Teaser sequences at the top of the XML

This is a deterministic script — no LLM calls, just frame math and XML string building.

Usage:
    python assemble_xml.py segment_list.json [-o output.xml] [--name basename] [--skip-validate]
"""

import argparse
import io
import json
import sys
from pathlib import Path
from urllib.parse import quote


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _sf(sec: float, timebase: int) -> int:
    """Convert seconds to frames: int(sec * timebase)."""
    return int(sec * timebase)


def _xml_esc(text: str) -> str:
    """Escape &, <, >, \" for XML."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _make_pathurl(filepath: str) -> str:
    """Convert a Windows path to a file:/// URL.

    Drive letter colon is NOT encoded. Rest is URL-encoded.
    Backslashes become forward slashes.
    """
    # Normalize to forward slashes
    fwd = filepath.replace("\\", "/")
    # Split drive letter (e.g. "C:") from rest
    drive = fwd[:2]   # "C:"
    rest = fwd[2:]     # "/Users/test/..."
    # URL-encode the rest, preserving forward slashes
    encoded_rest = quote(rest, safe="/")
    return "file:///" + drive + encoded_rest


def _build_file_elem(fid: str, source: dict, full: bool = False) -> str:
    """Build a <file> element.

    full=True: full definition with name, pathurl, duration, rate, media.
    full=False: reference-only, just <file id="..."/>.
    """
    if not full:
        return f'            <file id="{fid}"/>'

    filename = Path(source["path"]).name
    pathurl = _make_pathurl(source["path"])
    dur_frames = _sf(source["duration_sec"], source["timebase"])
    tb = source["timebase"]
    ntsc = "TRUE" if source["ntsc"] else "FALSE"
    w = source["width"]
    h = source["height"]

    return (
        f'            <file id="{fid}">\n'
        f"              <name>{_xml_esc(filename)}</name>\n"
        f"              <pathurl>{pathurl}</pathurl>\n"
        f"              <duration>{dur_frames}</duration>\n"
        f"              <rate><timebase>{tb}</timebase><ntsc>{ntsc}</ntsc></rate>\n"
        f"              <media>\n"
        f"                <video><samplecharacteristics>\n"
        f"                  <width>{w}</width><height>{h}</height>\n"
        f"                  <pixelaspectratio>square</pixelaspectratio>\n"
        f"                </samplecharacteristics></video>\n"
        f"                <audio><channelcount>2</channelcount><samplecharacteristics>\n"
        f"                  <depth>16</depth><samplerate>48000</samplerate>\n"
        f"                </samplecharacteristics></audio>\n"
        f"              </media>\n"
        f"            </file>"
    )


def _split_segment_by_internal_cuts(seg: dict) -> list[tuple[float, float]]:
    """Split a segment into sub-ranges by removing internal cuts.

    If no internal cuts, returns [(start_sec, end_sec)].
    With cuts, returns only the kept portions.
    """
    cuts = seg.get("internal_cuts", [])
    if not cuts:
        return [(seg["start_sec"], seg["end_sec"])]

    # Sort cuts by start time
    sorted_cuts = sorted(cuts, key=lambda c: c["start_sec"])

    ranges = []
    cursor = seg["start_sec"]

    for cut in sorted_cuts:
        if cut["start_sec"] > cursor:
            ranges.append((cursor, cut["start_sec"]))
        cursor = cut["end_sec"]

    # Remaining portion after last cut
    if cursor < seg["end_sec"]:
        ranges.append((cursor, seg["end_sec"]))

    return ranges


def _build_teaser_seq(sid: str, teaser: dict, source: dict, fid: str,
                      file_written: list[bool]) -> tuple[str, float]:
    """Build a teaser <sequence> element.

    Returns (xml_string, duration_seconds).
    """
    tb = source["timebase"]
    ntsc = "TRUE" if source["ntsc"] else "FALSE"
    dur_frames = _sf(source["duration_sec"], tb)
    w = source["width"]
    h = source["height"]

    # Build timeline clips
    tl = []
    pos = 0
    for clip in teaser["clips"]:
        inf = _sf(clip["start_sec"], tb)
        outf = _sf(clip["end_sec"], tb)
        dur = outf - inf
        tl.append({
            "label": clip["label"],
            "in": inf,
            "out": outf,
            "start": pos,
            "end": pos + dur,
        })
        pos += dur

    total = pos
    name = teaser["name"]

    L = []
    L.append(f'  <sequence id="{sid}"><name>{_xml_esc(name)}</name>')
    L.append(f"    <duration>{total}</duration>")
    L.append(f"    <rate><timebase>{tb}</timebase><ntsc>{ntsc}</ntsc></rate>")
    L.append("    <media><video>")
    L.append(
        f"      <format><samplecharacteristics>"
        f"<width>{w}</width><height>{h}</height>"
        f"<pixelaspectratio>square</pixelaspectratio>"
        f"</samplecharacteristics></format>"
    )
    L.append("      <track>")

    for i, c in enumerate(tl):
        cid = f"{sid}-v-{i+1:03d}"
        L.append(f'        <clipitem id="{cid}"><name>{_xml_esc(c["label"])}</name>')
        L.append(
            f"          <duration>{dur_frames}</duration>"
            f"<rate><timebase>{tb}</timebase><ntsc>{ntsc}</ntsc></rate>"
        )
        L.append(
            f'          <start>{c["start"]}</start><end>{c["end"]}</end>'
            f'<in>{c["in"]}</in><out>{c["out"]}</out>'
        )
        if not file_written[0]:
            L.append(_build_file_elem(fid, source, full=True))
            file_written[0] = True
        else:
            L.append(_build_file_elem(fid, source, full=False))
        L.append("        </clipitem>")

    L.append("      </track></video>")
    L.append("      <audio><numOutputChannels>2</numOutputChannels>")
    L.append(
        "        <format><samplecharacteristics>"
        "<depth>16</depth><samplerate>48000</samplerate>"
        "</samplecharacteristics></format>"
    )

    for ch in (1, 2):
        L.append("        <track>")
        for i, c in enumerate(tl):
            cid = f"{sid}-a{ch}-{i+1:03d}"
            L.append(f'          <clipitem id="{cid}"><name>{_xml_esc(c["label"])}</name>')
            L.append(
                f"            <duration>{dur_frames}</duration>"
                f"<rate><timebase>{tb}</timebase><ntsc>{ntsc}</ntsc></rate>"
            )
            L.append(
                f'            <start>{c["start"]}</start><end>{c["end"]}</end>'
                f'<in>{c["in"]}</in><out>{c["out"]}</out>'
            )
            L.append(f'            <file id="{fid}"/>')
            L.append(
                f"            <sourcetrack><mediatype>audio</mediatype>"
                f"<trackindex>{ch}</trackindex></sourcetrack>"
            )
            L.append("          </clipitem>")
        L.append("        </track>")

    L.append("      </audio></media>")
    L.append("  </sequence>")

    return "\n".join(L), total / tb


def _build_main_seq(segments: list[dict], source: dict, fid: str,
                    file_written: list[bool]) -> tuple[str, int, int]:
    """Build the main <sequence> element with V1 cuts + V2 markers.

    Returns (xml_string, total_timeline_frames, v1_clip_count).
    """
    tb = source["timebase"]
    ntsc = "TRUE" if source["ntsc"] else "FALSE"
    src_dur_frames = _sf(source["duration_sec"], tb)
    w = source["width"]
    h = source["height"]

    # Build V1 clips: split each segment by internal cuts
    v1_clips = []
    pos = 0
    for seg in segments:
        ranges = _split_segment_by_internal_cuts(seg)
        for start_sec, end_sec in ranges:
            inf = _sf(start_sec, tb)
            outf = _sf(end_sec, tb)
            dur = outf - inf
            v1_clips.append({
                "label": seg["label"],
                "in": inf,
                "out": outf,
                "start": pos,
                "end": pos + dur,
            })
            pos += dur

    total_frames = pos

    # Build V2 markers from segments
    markers_xml = []
    for seg in segments:
        inf = _sf(seg["start_sec"], tb)
        outf = _sf(seg["end_sec"], tb)
        mtype = seg["marker_type"]
        label = seg["label"]
        comment = seg.get("comment", "")
        markers_xml.append(
            f"            <marker><name>[{mtype}] {_xml_esc(label)}</name>\n"
            f"              <comment>{_xml_esc(comment)}</comment>\n"
            f"              <in>{inf}</in><out>{outf}</out></marker>"
        )

    L = []
    L.append('  <sequence id="seq-main"><name>YapCut Post-Ready Cut</name>')
    L.append(f"    <duration>{total_frames}</duration>")
    L.append(f"    <rate><timebase>{tb}</timebase><ntsc>{ntsc}</ntsc></rate>")
    L.append("    <media><video>")
    L.append(
        f"      <format><samplecharacteristics>"
        f"<width>{w}</width><height>{h}</height>"
        f"<pixelaspectratio>square</pixelaspectratio>"
        f"</samplecharacteristics></format>"
    )

    # V1 — physical cuts
    L.append("      <track>")
    for i, c in enumerate(v1_clips):
        cid = f"m-v1-{i+1:03d}"
        L.append(f'        <clipitem id="{cid}"><name>{_xml_esc(c["label"])}</name>')
        L.append(
            f"          <duration>{src_dur_frames}</duration>"
            f"<rate><timebase>{tb}</timebase><ntsc>{ntsc}</ntsc></rate>"
        )
        L.append(
            f'          <start>{c["start"]}</start><end>{c["end"]}</end>'
            f'<in>{c["in"]}</in><out>{c["out"]}</out>'
        )
        if not file_written[0]:
            L.append(_build_file_elem(fid, source, full=True))
            file_written[0] = True
        else:
            L.append(_build_file_elem(fid, source, full=False))
        L.append("        </clipitem>")
    L.append("      </track>")

    # V2 — full VOD with markers
    L.append("      <track>")
    L.append('        <clipitem id="m-v2-ref"><name>Reference - Full VOD with Markers</name>')
    L.append(
        f"          <duration>{src_dur_frames}</duration>"
        f"<rate><timebase>{tb}</timebase><ntsc>{ntsc}</ntsc></rate>"
    )
    L.append(
        f"          <start>0</start><end>{src_dur_frames}</end>"
        f"<in>0</in><out>{src_dur_frames}</out>"
    )
    L.append(f'          <file id="{fid}"/>')
    for m in markers_xml:
        L.append(m)
    L.append("        </clipitem>")
    L.append("      </track>")

    L.append("    </video>")

    # Audio — 2 stereo tracks
    L.append("    <audio><numOutputChannels>2</numOutputChannels>")
    L.append(
        "      <format><samplecharacteristics>"
        "<depth>16</depth><samplerate>48000</samplerate>"
        "</samplecharacteristics></format>"
    )

    for ch in (1, 2):
        L.append("      <track>")
        for i, c in enumerate(v1_clips):
            cid = f"m-a{ch}-{i+1:03d}"
            L.append(f'        <clipitem id="{cid}"><name>{_xml_esc(c["label"])}</name>')
            L.append(
                f"          <duration>{src_dur_frames}</duration>"
                f"<rate><timebase>{tb}</timebase><ntsc>{ntsc}</ntsc></rate>"
            )
            L.append(
                f'          <start>{c["start"]}</start><end>{c["end"]}</end>'
                f'<in>{c["in"]}</in><out>{c["out"]}</out>'
            )
            L.append(f'          <file id="{fid}"/>')
            L.append(
                f"          <sourcetrack><mediatype>audio</mediatype>"
                f"<trackindex>{ch}</trackindex></sourcetrack>"
            )
            L.append("        </clipitem>")
        L.append("      </track>")

    L.append("    </audio></media>")
    L.append("  </sequence>")

    return "\n".join(L), total_frames, len(v1_clips)


# ---------------------------------------------------------------------------
# Main assembly function
# ---------------------------------------------------------------------------

def assemble(segment_list: dict) -> str:
    """Assemble a complete FCP 7 XML string from a segment_list dict.

    Returns the XML string.
    """
    source = segment_list["source"]
    segments = segment_list["segments"]
    teasers = segment_list.get("teasers", [])

    fid = "file-001"
    file_written = [False]  # mutable flag for first-file-full-definition tracking

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<!DOCTYPE xmeml>",
        '<xmeml version="5">',
    ]

    # Build teaser sequences
    teaser_stats = []
    for i, teaser in enumerate(teasers):
        sid = f"t-{i+1:02d}"
        xml, dur_sec = _build_teaser_seq(sid, teaser, source, fid, file_written)
        lines.append(xml)
        teaser_stats.append((teaser["name"], dur_sec, len(teaser["clips"])))

    # Build main sequence
    main_xml, total_frames, v1_count = _build_main_seq(
        segments, source, fid, file_written
    )
    lines.append(main_xml)

    lines.append("</xmeml>")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Collision-safe output path
# ---------------------------------------------------------------------------

def get_safe_path(directory: Path, basename: str) -> Path:
    """Return a path in directory that won't overwrite existing files."""
    candidate = directory / f"{basename}.xml"
    if not candidate.exists():
        return candidate
    version = 2
    while True:
        candidate = directory / f"{basename}_v{version}.xml"
        if not candidate.exists():
            return candidate
        version += 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    # Force UTF-8 stdout/stderr on Windows (only in CLI mode, not when imported)
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding="utf-8", errors="replace"
        )

    parser = argparse.ArgumentParser(
        description="YapCut Stage 3 — Assemble FCP 7 XML from segment_list.json"
    )
    parser.add_argument(
        "segment_list",
        help="Path to segment_list.json",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output XML path (default: collision-safe path in source media directory)",
    )
    parser.add_argument(
        "--name",
        help="Base name for the output file (default: yapcut_cut)",
        default="yapcut_cut",
    )
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="Skip auto-validation after generation",
    )
    args = parser.parse_args()

    # Load segment list
    with open(args.segment_list, encoding="utf-8") as f:
        segment_list = json.load(f)

    source = segment_list["source"]
    segments = segment_list["segments"]
    teasers = segment_list.get("teasers", [])
    tb = source["timebase"]

    print("YapCut Stage 3 — XML Assembly")
    print(f"Source: {Path(source['path']).name}")
    print()

    # Assemble XML
    xml_str = assemble(segment_list)

    # Determine output path
    if args.output:
        out_path = Path(args.output)
    else:
        source_dir = Path(source["path"]).parent
        out_path = get_safe_path(source_dir, args.name)

    # Write XML
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(xml_str, encoding="utf-8")
    print(f"Saved: {out_path}")

    # Summary
    # Count V1 clips (segments split by internal cuts)
    v1_count = 0
    for seg in segments:
        v1_count += len(_split_segment_by_internal_cuts(seg))

    total_sec = 0
    for seg in segments:
        ranges = _split_segment_by_internal_cuts(seg)
        for start, end in ranges:
            total_sec += end - start

    print(f"\nSegments: {len(segments)}")
    print(f"V1 clips: {v1_count}")
    print(f"V1 duration: {total_sec:.1f}s ({total_sec/60:.1f} min)")
    print(f"V2 markers: {len(segments)}")
    print(f"Teasers: {len(teasers)}")

    for teaser in teasers:
        clips = teaser["clips"]
        t_dur = sum(c["end_sec"] - c["start_sec"] for c in clips)
        print(f"  {teaser['name']}: {t_dur:.1f}s ({len(clips)} clips)")

    # Validate unless skipped
    if not args.skip_validate:
        print("\n--- Validation ---")
        # Import validate_xml from the same directory
        tools_dir = Path(__file__).resolve().parent
        sys.path.insert(0, str(tools_dir))
        from validate_xml import validate

        issues = validate(str(out_path))
        if not issues:
            print("PASS -- No issues found. XML is valid for Premiere Pro import.")
        else:
            print(f"FOUND {len(issues)} ISSUE(S):")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. {issue}")
    else:
        print("\nValidation skipped (--skip-validate).")

    return str(out_path)


if __name__ == "__main__":
    main()
