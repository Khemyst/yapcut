"""
ClaudEdits FCP XML Validator

Validates generated FCP 7 XML (xmeml v5) before importing into Premiere Pro.
Checks well-formedness, required elements, and structural integrity.

Usage:
    python validate_xml.py <path_to_xml>
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def validate(filepath: str) -> list[str]:
    """Validate an FCP XML file. Returns a list of issues (empty = valid)."""
    issues = []
    path = Path(filepath)

    if not path.exists():
        return [f"File not found: {filepath}"]

    # 1. XML well-formedness
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except ET.ParseError as e:
        return [f"XML parse error: {e}"]

    # 2. Root element must be xmeml
    if root.tag != "xmeml":
        issues.append(f"Root element is <{root.tag}>, expected <xmeml>")
        return issues

    version = root.get("version")
    if version is None:
        issues.append("Missing version attribute on <xmeml>")
    elif version != "5":
        issues.append(f"xmeml version is '{version}', expected '5'")

    # 3. Must contain at least one sequence
    sequences = root.findall(".//sequence")
    if not sequences:
        issues.append("No <sequence> element found")
        return issues

    for seq in sequences:
        seq_name = seq.findtext("name") or seq.get("id", "unnamed")
        prefix = f"Sequence '{seq_name}'"

        # Required sequence children
        if seq.find("name") is None:
            issues.append(f"{prefix}: missing <name>")
        if seq.find("duration") is None:
            issues.append(f"{prefix}: missing <duration>")

        rate = seq.find("rate")
        if rate is None:
            issues.append(f"{prefix}: missing <rate>")
        else:
            if rate.find("timebase") is None:
                issues.append(f"{prefix}: <rate> missing <timebase>")

        media = seq.find("media")
        if media is None:
            issues.append(f"{prefix}: missing <media>")
            continue

        # Check video track
        video = media.find("video")
        if video is None:
            issues.append(f"{prefix}: <media> missing <video>")
        else:
            tracks = video.findall("track")
            if not tracks:
                issues.append(f"{prefix}: <video> has no <track>")
            else:
                for ti, track in enumerate(tracks):
                    clipitems = track.findall("clipitem")
                    if not clipitems:
                        issues.append(f"{prefix}: video track {ti + 1} has no <clipitem>")
                    for ci, clip in enumerate(clipitems):
                        _validate_clipitem(clip, f"{prefix} video track {ti + 1} clip {ci + 1}", issues)

                # Check timeline continuity on first video track
                _check_continuity(tracks[0], f"{prefix} video track 1", issues)

        # Check audio track
        audio = media.find("audio")
        if audio is None:
            issues.append(f"{prefix}: <media> missing <audio>")
        else:
            tracks = audio.findall("track")
            if not tracks:
                issues.append(f"{prefix}: <audio> has no <track>")
            else:
                for ti, track in enumerate(tracks):
                    clipitems = track.findall("clipitem")
                    if not clipitems:
                        issues.append(f"{prefix}: audio track {ti + 1} has no <clipitem>")
                    for ci, clip in enumerate(clipitems):
                        _validate_clipitem(clip, f"{prefix} audio track {ti + 1} clip {ci + 1}", issues)

    # 4. Check file references
    _check_file_refs(root, issues)

    return issues


def _validate_clipitem(clip: ET.Element, prefix: str, issues: list[str]):
    """Validate a single clipitem element."""
    required = ["name", "duration", "rate", "start", "end", "in", "out"]
    for tag in required:
        if clip.find(tag) is None:
            issues.append(f"{prefix}: missing <{tag}>")

    # Validate in/out vs start/end consistency
    start = clip.findtext("start")
    end = clip.findtext("end")
    in_pt = clip.findtext("in")
    out_pt = clip.findtext("out")

    if all(v is not None for v in [start, end, in_pt, out_pt]):
        try:
            s, e, i, o = int(start), int(end), int(in_pt), int(out_pt)
            timeline_dur = e - s
            source_dur = o - i
            if timeline_dur != source_dur:
                issues.append(
                    f"{prefix}: timeline duration ({timeline_dur} frames) != "
                    f"source duration ({source_dur} frames)"
                )
            if s < 0 or e < 0 or i < 0 or o < 0:
                issues.append(f"{prefix}: negative frame value detected")
            if e <= s:
                issues.append(f"{prefix}: end ({e}) <= start ({s})")
            if o <= i:
                issues.append(f"{prefix}: out ({o}) <= in ({i})")
        except ValueError:
            issues.append(f"{prefix}: non-integer frame value in start/end/in/out")

    # Must reference a file
    if clip.find("file") is None:
        issues.append(f"{prefix}: missing <file> reference")

    # Rate must have timebase
    rate = clip.find("rate")
    if rate is not None and rate.find("timebase") is None:
        issues.append(f"{prefix}: <rate> missing <timebase>")


def _check_continuity(track: ET.Element, prefix: str, issues: list[str]):
    """Check that clipitems don't overlap on the timeline."""
    clips = track.findall("clipitem")
    positions = []
    for clip in clips:
        start = clip.findtext("start")
        end = clip.findtext("end")
        if start is not None and end is not None:
            try:
                positions.append((int(start), int(end)))
            except ValueError:
                continue

    positions.sort()
    for i in range(1, len(positions)):
        prev_end = positions[i - 1][1]
        curr_start = positions[i][0]
        if curr_start < prev_end:
            issues.append(
                f"{prefix}: overlap detected — clip ending at frame {prev_end} "
                f"overlaps with clip starting at frame {curr_start}"
            )


def _check_file_refs(root: ET.Element, issues: list[str]):
    """Check that file elements are properly defined and referenced."""
    # Find all file elements with full definitions (have pathurl)
    defined_files = set()
    for f in root.iter("file"):
        if f.find("pathurl") is not None:
            fid = f.get("id")
            if fid:
                defined_files.add(fid)

    # Find all file references (have id but no pathurl — reference-only)
    for f in root.iter("file"):
        if f.find("pathurl") is None and len(f) == 0:
            fid = f.get("id")
            if fid and fid not in defined_files:
                issues.append(f"File reference id='{fid}' has no definition with <pathurl>")

    if not defined_files:
        issues.append("No <file> elements with <pathurl> found — no source media defined")


def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <path_to_xml>")
        sys.exit(1)

    filepath = sys.argv[1]
    print(f"Validating: {filepath}")
    print()

    issues = validate(filepath)

    if not issues:
        print("PASS — No issues found. XML is valid for Premiere Pro import.")
    else:
        print(f"FOUND {len(issues)} ISSUE(S):")
        print()
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")

    sys.exit(0 if not issues else 1)


if __name__ == "__main__":
    main()
