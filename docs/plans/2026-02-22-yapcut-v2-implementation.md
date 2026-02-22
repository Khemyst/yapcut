# YapCut v2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the full YapCut v2 spec — marker-based FCP XML output, editorial presets, YouTube chat integration, EDL diff analysis, and style memory.

**Architecture:** Claude Code is the marker generation engine (no script). Python tools are utilities: XML validation, chat fetching, EDL diffing. Presets and editorial memory are markdown files Claude reads at session start. CLAUDE.md is updated to teach Claude the v2 workflow.

**Tech Stack:** Python 3.10+ (stdlib + google-auth + google-auth-oauthlib + python-dotenv), pytest for testing, FCP 7 XML (xmeml v5)

---

### Task 1: Directory Restructure

**Files:**
- Move: `scripts/validate_xml.py` → `tools/validate_xml.py`
- Move: `scripts/generate_xml.py` → `tools/generate_xml.py`
- Move: `transcripts/part3_readable.txt` → `input/part3_readable.txt`
- Modify: `.gitignore`
- Create: `presets/.gitkeep`
- Delete: empty `scripts/` and `transcripts/` directories

**Step 1: Create new directories**

```bash
mkdir -p tools input presets
```

**Step 2: Move files to new locations**

```bash
git mv scripts/validate_xml.py tools/validate_xml.py
git mv scripts/generate_xml.py tools/generate_xml.py
git mv transcripts/part3_readable.txt input/part3_readable.txt
rmdir scripts transcripts
```

**Step 3: Update .gitignore**

Replace contents of `.gitignore` with:

```
output/
input/
__pycache__/
*.pyc
.env
```

**Step 4: Create presets directory placeholder**

```bash
touch presets/.gitkeep
```

**Step 5: Commit**

```bash
git add -A
git commit -m "chore: restructure directories for v2 (scripts→tools, transcripts→input, add presets)"
```

---

### Task 2: Add Python Dependencies

**Files:**
- Create: `requirements.txt`

**Step 1: Create requirements.txt**

```
google-auth>=2.0.0
google-auth-oauthlib>=1.0.0
google-api-python-client>=2.0.0
python-dotenv>=1.0.0
pytest>=8.0.0
```

**Step 2: Install dependencies**

```bash
pip install -r requirements.txt
```

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add Python dependencies for v2 tools"
```

---

### Task 3: Update validate_xml.py for Marker Support

**Files:**
- Modify: `tools/validate_xml.py`
- Create: `tests/test_validate_xml.py`

**Step 1: Write tests for marker validation**

Create `tests/test_validate_xml.py`:

```python
"""Tests for YapCut FCP XML validator — marker support."""
import sys
import os
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from validate_xml import validate


def _write_xml(content: str) -> str:
    """Write XML content to a temp file, return path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False, encoding="utf-8")
    f.write(content)
    f.close()
    return f.name


# --- Existing v1 behavior (regression tests) ---

VALID_ROUGHCUT = '''<?xml version="1.0" encoding="UTF-8"?>
<xmeml version="5">
  <sequence id="seq-001">
    <name>Test</name>
    <duration>900</duration>
    <rate><timebase>30</timebase><ntsc>TRUE</ntsc></rate>
    <media>
      <video>
        <track>
          <clipitem id="v-clip-001">
            <name>Clip 1</name>
            <duration>9000</duration>
            <rate><timebase>30</timebase><ntsc>TRUE</ntsc></rate>
            <start>0</start><end>900</end>
            <in>0</in><out>900</out>
            <file id="file-001">
              <name>source.mp4</name>
              <pathurl>file:///C:/source.mp4</pathurl>
              <duration>9000</duration>
              <rate><timebase>30</timebase><ntsc>TRUE</ntsc></rate>
              <media>
                <video><samplecharacteristics><width>1920</width><height>1080</height></samplecharacteristics></video>
                <audio><samplecharacteristics><depth>16</depth><samplerate>48000</samplerate></samplecharacteristics></audio>
              </media>
            </file>
          </clipitem>
        </track>
      </video>
      <audio>
        <track>
          <clipitem id="a-clip-001">
            <name>Clip 1</name>
            <duration>9000</duration>
            <rate><timebase>30</timebase><ntsc>TRUE</ntsc></rate>
            <start>0</start><end>900</end>
            <in>0</in><out>900</out>
            <file id="file-001"/>
          </clipitem>
        </track>
      </audio>
    </media>
  </sequence>
</xmeml>'''


def test_valid_roughcut_passes():
    path = _write_xml(VALID_ROUGHCUT)
    issues = validate(path)
    os.unlink(path)
    assert issues == []


def test_missing_file_returns_error():
    issues = validate("/nonexistent/file.xml")
    assert len(issues) == 1
    assert "not found" in issues[0].lower()


def test_malformed_xml():
    path = _write_xml("<not valid xml>>>")
    issues = validate(path)
    os.unlink(path)
    assert len(issues) >= 1
    assert "parse error" in issues[0].lower()


# --- v2 marker validation ---

VALID_MARKERS = '''<?xml version="1.0" encoding="UTF-8"?>
<xmeml version="5">
  <sequence id="seq-001">
    <name>Marker Test</name>
    <duration>180000</duration>
    <rate><timebase>30</timebase><ntsc>TRUE</ntsc></rate>
    <media>
      <video>
        <track>
          <clipitem id="v-clip-001">
            <name>Primary_VOD_Track</name>
            <duration>180000</duration>
            <rate><timebase>30</timebase><ntsc>TRUE</ntsc></rate>
            <start>0</start><end>180000</end>
            <in>0</in><out>180000</out>
            <file id="file-001">
              <name>source.mp4</name>
              <pathurl>file:///C:/source.mp4</pathurl>
              <duration>180000</duration>
              <rate><timebase>30</timebase><ntsc>TRUE</ntsc></rate>
              <media>
                <video><samplecharacteristics><width>1920</width><height>1080</height></samplecharacteristics></video>
                <audio><samplecharacteristics><depth>16</depth><samplerate>48000</samplerate></samplecharacteristics></audio>
              </media>
            </file>
            <marker>
              <name>[KEEP] Great Moment</name>
              <comment>High energy, clean mechanics.</comment>
              <in>4500</in>
              <out>5850</out>
            </marker>
            <marker>
              <name>[CUT] Redundant Rant</name>
              <comment>Better version at 01:14:00.</comment>
              <in>8100</in>
              <out>8950</out>
            </marker>
            <marker>
              <name>[MOMENT] Sick Play</name>
              <comment>Standalone 22s clip.</comment>
              <in>12000</in>
              <out>13500</out>
            </marker>
            <marker>
              <name>[MAYBE] Could Be Good</name>
              <comment>Depends on pacing.</comment>
              <in>20000</in>
              <out>21000</out>
            </marker>
            <marker>
              <name>[CONTEXT] Setup for Next</name>
              <comment>Needed for following KEEP.</comment>
              <in>4200</in>
              <out>4440</out>
            </marker>
          </clipitem>
        </track>
      </video>
      <audio>
        <track>
          <clipitem id="a-clip-001">
            <name>Primary_VOD_Track</name>
            <duration>180000</duration>
            <rate><timebase>30</timebase><ntsc>TRUE</ntsc></rate>
            <start>0</start><end>180000</end>
            <in>0</in><out>180000</out>
            <file id="file-001"/>
          </clipitem>
        </track>
      </audio>
    </media>
  </sequence>
</xmeml>'''


def test_valid_markers_pass():
    path = _write_xml(VALID_MARKERS)
    issues = validate(path)
    os.unlink(path)
    assert issues == []


def test_marker_missing_comment():
    xml = VALID_MARKERS.replace(
        "<comment>High energy, clean mechanics.</comment>\n", ""
    )
    path = _write_xml(xml)
    issues = validate(path)
    os.unlink(path)
    assert any("comment" in i.lower() for i in issues)


def test_marker_missing_in_out():
    xml = VALID_MARKERS.replace(
        "<in>4500</in>\n              <out>5850</out>",
        ""
    )
    path = _write_xml(xml)
    issues = validate(path)
    os.unlink(path)
    assert any("in" in i.lower() or "out" in i.lower() for i in issues)


def test_marker_invalid_prefix():
    xml = VALID_MARKERS.replace("[KEEP]", "[INVALID]")
    path = _write_xml(xml)
    issues = validate(path)
    os.unlink(path)
    assert any("prefix" in i.lower() or "invalid" in i.lower() for i in issues)


def test_marker_out_before_in():
    xml = VALID_MARKERS.replace(
        "<in>4500</in>\n              <out>5850</out>",
        "<in>5850</in>\n              <out>4500</out>"
    )
    path = _write_xml(xml)
    issues = validate(path)
    os.unlink(path)
    assert any("out" in i.lower() and ("before" in i.lower() or "<=" in i.lower() or "less" in i.lower()) for i in issues)
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_validate_xml.py -v
```

Expected: Existing v1 tests pass, all marker tests fail (marker validation not implemented yet).

**Step 3: Add marker validation to validate_xml.py**

Add these constants and functions to `tools/validate_xml.py`:

After the imports, add:

```python
VALID_MARKER_PREFIXES = {"[KEEP]", "[MAYBE]", "[CUT]", "[MOMENT]", "[CONTEXT]"}
```

Add new function `_validate_markers`:

```python
def _validate_markers(clip: ET.Element, prefix: str, issues: list[str]):
    """Validate marker elements inside a clipitem."""
    markers = clip.findall("marker")
    for mi, marker in enumerate(markers):
        m_prefix = f"{prefix} marker {mi + 1}"

        name = marker.findtext("name")
        if name is None:
            issues.append(f"{m_prefix}: missing <name>")
        else:
            # Check for valid prefix
            has_valid_prefix = any(name.startswith(p) for p in VALID_MARKER_PREFIXES)
            if not has_valid_prefix:
                issues.append(
                    f"{m_prefix}: name '{name}' does not start with a valid prefix "
                    f"({', '.join(sorted(VALID_MARKER_PREFIXES))})"
                )

        if marker.find("comment") is None:
            issues.append(f"{m_prefix}: missing <comment> (reasoning required)")

        in_val = marker.findtext("in")
        out_val = marker.findtext("out")

        if in_val is None or out_val is None:
            if in_val is None:
                issues.append(f"{m_prefix}: missing <in> (start frame)")
            if out_val is None:
                issues.append(f"{m_prefix}: missing <out> (end frame)")
        else:
            try:
                in_frame = int(in_val)
                out_frame = int(out_val)
                if out_frame <= in_frame:
                    issues.append(f"{m_prefix}: out ({out_frame}) <= in ({in_frame})")
                if in_frame < 0 or out_frame < 0:
                    issues.append(f"{m_prefix}: negative frame value detected")
            except ValueError:
                issues.append(f"{m_prefix}: non-integer frame value in <in>/<out>")
```

Call `_validate_markers` from within the video track clipitem loop in `validate()`, right after `_validate_clipitem`:

```python
_validate_markers(clip, f"{prefix} video track {ti + 1} clip {ci + 1}", issues)
```

**Step 4: Update the docstring**

Change the module docstring to:

```python
"""
YapCut FCP XML Validator

Validates generated FCP 7 XML (xmeml v5) before importing into Premiere Pro.
Checks well-formedness, required elements, structural integrity, and marker validity.
Supports both marker-mode (v2) and rough-cut-mode (v1) XML.

Usage:
    python validate_xml.py <path_to_xml>
"""
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/test_validate_xml.py -v
```

Expected: ALL tests pass.

**Step 6: Commit**

```bash
git add tools/validate_xml.py tests/test_validate_xml.py
git commit -m "feat: add marker validation to validate_xml.py (KEEP/MAYBE/CUT/MOMENT/CONTEXT)"
```

---

### Task 4: Build chat_pull.py

**Files:**
- Create: `tools/chat_pull.py`
- Create: `tests/test_chat_pull.py`

**Step 1: Write tests for chat data processing**

Create `tests/test_chat_pull.py`. We test the data transformation logic, not the API calls themselves (those require real credentials):

```python
"""Tests for chat_pull.py data processing."""
import sys
import os
import json
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from chat_pull import (
    normalize_messages,
    save_chat_json,
)


def test_normalize_messages_converts_timestamps():
    raw = [
        {
            "snippet": {
                "displayMessage": "LMAOOO",
                "authorChannelId": "UC123",
                "publishedAt": "2026-02-10T15:30:45.000Z",
            },
            "authorDetails": {
                "displayName": "viewer1",
                "isChatMember": False,
                "isChatModerator": False,
            },
        }
    ]
    stream_start_iso = "2026-02-10T15:00:00.000Z"
    result = normalize_messages(raw, stream_start_iso)
    assert len(result) == 1
    assert result[0]["author"] == "viewer1"
    assert result[0]["message"] == "LMAOOO"
    # 30 min 45 sec = 1845000 ms
    assert result[0]["timestamp_ms"] == 1845000
    assert result[0]["is_member"] is False
    assert result[0]["is_moderator"] is False


def test_normalize_messages_negative_timestamp_clamped():
    """Messages before stream start get timestamp_ms = 0."""
    raw = [
        {
            "snippet": {
                "displayMessage": "early",
                "authorChannelId": "UC123",
                "publishedAt": "2026-02-10T14:59:00.000Z",
            },
            "authorDetails": {
                "displayName": "earlybird",
                "isChatMember": False,
                "isChatModerator": False,
            },
        }
    ]
    stream_start_iso = "2026-02-10T15:00:00.000Z"
    result = normalize_messages(raw, stream_start_iso)
    assert result[0]["timestamp_ms"] == 0


def test_save_chat_json_schema(tmp_path):
    messages = [
        {"timestamp_ms": 5000, "author": "test", "message": "hi",
         "is_member": False, "is_moderator": True}
    ]
    out_path = str(tmp_path / "chat.json")
    save_chat_json("abc123", messages, out_path)

    with open(out_path, encoding="utf-8") as f:
        data = json.load(f)

    assert data["video_id"] == "abc123"
    assert len(data["messages"]) == 1
    assert data["messages"][0]["timestamp_ms"] == 5000
    assert data["messages"][0]["author"] == "test"
    assert data["messages"][0]["message"] == "hi"
    assert data["messages"][0]["is_member"] is False
    assert data["messages"][0]["is_moderator"] is True
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_chat_pull.py -v
```

Expected: ImportError — `chat_pull` module doesn't exist yet.

**Step 3: Implement chat_pull.py**

Create `tools/chat_pull.py`:

```python
"""
YapCut YouTube Chat Fetcher

Pulls live chat replay from a YouTube stream VOD and saves as JSON
for use as an editorial signal during marker generation.

Lookup modes:
    --video-id ID       Fetch chat for a specific video ID
    --search "query"    Search your channel for a video by title, confirm, fetch
    --recent            List recent uploads from your channel, pick interactively

Usage:
    python chat_pull.py --video-id abc123
    python chat_pull.py --search "BATTLEFIELD 6 VOICE ACTOR"
    python chat_pull.py --recent
    python chat_pull.py --video-id abc123 --output input/chat.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

CONFIG_DIR = r"C:\Users\jaywa.NEUTRON\Projects\config"
DEFAULT_OUTPUT = os.path.join(os.path.dirname(__file__), "..", "input", "chat.json")


def load_credentials() -> Credentials:
    """Load and refresh OAuth2 credentials from config directory."""
    token_path = os.path.join(CONFIG_DIR, "youtube_token.json")
    with open(token_path, encoding="utf-8") as f:
        token_data = json.load(f)

    creds = Credentials(
        token=token_data["token"],
        refresh_token=token_data["refresh_token"],
        token_uri=token_data["token_uri"],
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
        scopes=token_data.get("scopes", ["https://www.googleapis.com/auth/youtube.readonly"]),
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Save refreshed token
        token_data["token"] = creds.token
        token_data["expiry"] = creds.expiry.isoformat() + "Z" if creds.expiry else None
        with open(token_path, "w", encoding="utf-8") as f:
            json.dump(token_data, f, indent=2)

    return creds


def get_channel_id() -> str:
    """Load channel ID from .env config."""
    load_dotenv(os.path.join(CONFIG_DIR, ".env"))
    channel_id = os.getenv("YOUTUBE_CHANNEL_ID")
    if not channel_id:
        print("Error: YOUTUBE_CHANNEL_ID not set in config .env")
        sys.exit(1)
    return channel_id


def get_live_chat_id(youtube, video_id: str) -> str:
    """Get the live chat ID for a video."""
    resp = youtube.videos().list(part="liveStreamingDetails", id=video_id).execute()
    items = resp.get("items", [])
    if not items:
        print(f"Error: Video {video_id} not found.")
        sys.exit(1)
    details = items[0].get("liveStreamingDetails", {})
    chat_id = details.get("activeLiveChatId")
    if not chat_id:
        print(f"Error: No live chat available for video {video_id}.")
        print("This video may not have been a live stream, or chat replay is disabled.")
        sys.exit(1)
    return chat_id


def get_stream_start(youtube, video_id: str) -> str:
    """Get the actual stream start time ISO string."""
    resp = youtube.videos().list(part="liveStreamingDetails", id=video_id).execute()
    items = resp.get("items", [])
    if not items:
        print(f"Error: Video {video_id} not found.")
        sys.exit(1)
    start = items[0].get("liveStreamingDetails", {}).get("actualStartTime")
    if not start:
        print("Warning: Could not determine stream start time. Timestamps may be absolute.")
    return start


def fetch_chat_messages(youtube, chat_id: str) -> list[dict]:
    """Fetch all live chat replay messages, paginating through results."""
    all_messages = []
    page_token = None

    while True:
        request = youtube.liveChatMessages().list(
            liveChatId=chat_id,
            part="snippet,authorDetails",
            maxResults=2000,
            pageToken=page_token,
        )
        resp = request.execute()
        items = resp.get("items", [])
        all_messages.extend(items)

        page_token = resp.get("nextPageToken")
        if not page_token or not items:
            break

        print(f"  Fetched {len(all_messages)} messages so far...")

    return all_messages


def normalize_messages(raw_messages: list[dict], stream_start_iso: str | None) -> list[dict]:
    """Convert raw YouTube API messages to YapCut chat schema."""
    if stream_start_iso:
        start_dt = datetime.fromisoformat(stream_start_iso.replace("Z", "+00:00"))
    else:
        start_dt = None

    normalized = []
    for msg in raw_messages:
        snippet = msg.get("snippet", {})
        author = msg.get("authorDetails", {})

        published = snippet.get("publishedAt", "")
        if start_dt and published:
            msg_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            delta_ms = int((msg_dt - start_dt).total_seconds() * 1000)
            timestamp_ms = max(0, delta_ms)
        else:
            timestamp_ms = 0

        normalized.append({
            "timestamp_ms": timestamp_ms,
            "author": author.get("displayName", "unknown"),
            "message": snippet.get("displayMessage", ""),
            "is_member": author.get("isChatMember", False),
            "is_moderator": author.get("isChatModerator", False),
        })

    return normalized


def save_chat_json(video_id: str, messages: list[dict], output_path: str):
    """Save chat messages in YapCut schema."""
    data = {
        "video_id": video_id,
        "messages": messages,
    }
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def search_channel_videos(youtube, channel_id: str, query: str) -> list[dict]:
    """Search for videos on a channel matching a query."""
    resp = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        q=query,
        type="video",
        eventType="completed",
        maxResults=10,
        order="date",
    ).execute()
    return resp.get("items", [])


def list_recent_uploads(youtube, channel_id: str) -> list[dict]:
    """List recent uploads from a channel."""
    # Get uploads playlist ID
    resp = youtube.channels().list(part="contentDetails", id=channel_id).execute()
    items = resp.get("items", [])
    if not items:
        print(f"Error: Channel {channel_id} not found.")
        sys.exit(1)
    uploads_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # Get recent videos
    resp = youtube.playlistItems().list(
        part="snippet",
        playlistId=uploads_id,
        maxResults=20,
    ).execute()
    return resp.get("items", [])


def pick_video_interactive(videos: list[dict], label: str) -> str:
    """Let user pick a video from a list. Returns video ID."""
    if not videos:
        print(f"No {label} found.")
        sys.exit(1)

    print(f"\n{label}:")
    for i, v in enumerate(videos):
        snippet = v.get("snippet", {})
        title = snippet.get("title", "Unknown")
        published = snippet.get("publishedAt", "")[:10]
        print(f"  [{i + 1}] {title} ({published})")

    while True:
        choice = input(f"\nPick a video (1-{len(videos)}): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(videos):
                v = videos[idx]
                # search results use id.videoId, playlist items use snippet.resourceId.videoId
                vid = v.get("id", {})
                if isinstance(vid, dict):
                    return vid.get("videoId") or v["snippet"]["resourceId"]["videoId"]
                return vid
        except (ValueError, KeyError):
            pass
        print("Invalid choice, try again.")


def main():
    parser = argparse.ArgumentParser(description="YapCut YouTube Chat Fetcher")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--video-id", help="YouTube video ID")
    group.add_argument("--search", help="Search your channel by title")
    group.add_argument("--recent", action="store_true", help="List recent uploads")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output JSON path")
    args = parser.parse_args()

    creds = load_credentials()
    youtube = build("youtube", "v3", credentials=creds)
    channel_id = get_channel_id()

    if args.video_id:
        video_id = args.video_id
    elif args.search:
        results = search_channel_videos(youtube, channel_id, args.search)
        video_id = pick_video_interactive(results, "Search results")
    else:  # --recent
        uploads = list_recent_uploads(youtube, channel_id)
        video_id = pick_video_interactive(uploads, "Recent uploads")

    print(f"\nFetching chat for video: {video_id}")

    stream_start = get_stream_start(youtube, video_id)
    chat_id = get_live_chat_id(youtube, video_id)

    print(f"Chat ID: {chat_id}")
    print("Fetching messages...")

    raw_messages = fetch_chat_messages(youtube, chat_id)
    print(f"Total messages fetched: {len(raw_messages)}")

    messages = normalize_messages(raw_messages, stream_start)
    save_chat_json(video_id, messages, args.output)
    print(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_chat_pull.py -v
```

Expected: All 3 tests pass (they test normalization and save logic, not API calls).

**Step 5: Commit**

```bash
git add tools/chat_pull.py tests/test_chat_pull.py
git commit -m "feat: add YouTube chat fetcher (--video-id, --search, --recent)"
```

---

### Task 5: Build diff_analysis.py

**Files:**
- Create: `tools/diff_analysis.py`
- Create: `tests/test_diff_analysis.py`

**Step 1: Write tests for EDL parsing and overlap matching**

Create `tests/test_diff_analysis.py`:

```python
"""Tests for diff_analysis.py — EDL vs marker comparison."""
import sys
import os
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from diff_analysis import (
    parse_edl,
    parse_markers_from_xml,
    compute_overlap,
    categorize_markers,
    format_session_report,
)


# --- EDL parsing ---

SAMPLE_EDL = """TITLE: Test Edit
FCM: NON-DROP FRAME

001  AX       V     C        00:00:05:00 00:00:35:15 00:00:00:00 00:00:30:15
* FROM CLIP NAME: Great Moment

002  AX       V     C        00:01:00:00 00:01:22:10 00:00:30:15 00:00:52:25
* FROM CLIP NAME: Sick Play

003  AX       V     C        00:02:10:00 00:02:25:00 00:00:52:25 00:01:07:25
* FROM CLIP NAME: Unexpected Keep
"""


def test_parse_edl_extracts_clips():
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".edl", delete=False)
    f.write(SAMPLE_EDL)
    f.close()
    clips = parse_edl(f.name, timebase=30)
    os.unlink(f.name)

    assert len(clips) == 3
    assert clips[0]["name"] == "Great Moment"
    assert clips[0]["in_frame"] == 150   # 5s * 30
    assert clips[0]["out_frame"] == 1065  # 35s*30 + 15
    assert clips[1]["name"] == "Sick Play"
    assert clips[2]["name"] == "Unexpected Keep"


def test_parse_edl_empty():
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".edl", delete=False)
    f.write("TITLE: Empty\nFCM: NON-DROP FRAME\n")
    f.close()
    clips = parse_edl(f.name, timebase=30)
    os.unlink(f.name)
    assert clips == []


# --- Overlap calculation ---

def test_compute_overlap_full():
    assert compute_overlap(100, 200, 100, 200) == 1.0


def test_compute_overlap_partial():
    # proposed: 100-200, edl: 150-250 → overlap 50 / proposed_dur 100 = 0.5
    assert compute_overlap(100, 200, 150, 250) == pytest.approx(0.5)


def test_compute_overlap_none():
    assert compute_overlap(100, 200, 300, 400) == 0.0


def test_compute_overlap_edl_inside_proposed():
    # proposed: 100-300, edl: 150-200 → overlap 50 / 200 = 0.25
    assert compute_overlap(100, 300, 150, 200) == pytest.approx(0.25)


# --- Categorization ---

def test_categorize_accepted():
    markers = [{"name": "[KEEP] Great Moment", "in": 150, "out": 1050, "type": "KEEP"}]
    edl_clips = [{"name": "Great Moment", "in_frame": 150, "out_frame": 1065}]
    result = categorize_markers(markers, edl_clips)
    assert result[0]["category"] == "ACCEPTED"


def test_categorize_rejected():
    markers = [{"name": "[KEEP] Cut This", "in": 150, "out": 1050, "type": "KEEP"}]
    edl_clips = []  # Nothing in EDL
    result = categorize_markers(markers, edl_clips)
    assert result[0]["category"] == "REJECTED"


def test_categorize_heavily_modified():
    markers = [{"name": "[KEEP] Modified", "in": 100, "out": 1000, "type": "KEEP"}]
    # EDL keeps only 40% of the proposed region
    edl_clips = [{"name": "Modified", "in_frame": 100, "out_frame": 460}]
    result = categorize_markers(markers, edl_clips)
    assert result[0]["category"] == "HEAVILY_MODIFIED"


def test_user_kept_dead_space():
    markers = [{"name": "[KEEP] Something", "in": 100, "out": 200, "type": "KEEP"}]
    # EDL has a clip in a region we never proposed
    edl_clips = [
        {"name": "Something", "in_frame": 100, "out_frame": 200},
        {"name": "Surprise", "in_frame": 5000, "out_frame": 6000},
    ]
    result = categorize_markers(markers, edl_clips)
    # The marker should be ACCEPTED, and there should be a dead_space entry
    categories = {r["category"] for r in result}
    assert "ACCEPTED" in categories
    assert "USER_KEPT_DEAD_SPACE" in categories


# --- Report formatting ---

def test_format_session_report_contains_stats():
    categorized = [
        {"name": "[KEEP] A", "category": "ACCEPTED", "type": "KEEP", "overlap": 0.9},
        {"name": "[KEEP] B", "category": "REJECTED", "type": "KEEP", "overlap": 0.0},
        {"name": "[MOMENT] C", "category": "ACCEPTED", "type": "MOMENT", "overlap": 0.85},
    ]
    report = format_session_report(categorized, preset="battlefield-highlights")
    assert "battlefield-highlights" in report
    assert "Proposed: 3" in report
    assert "[KEEP]" in report
    assert "[MOMENT]" in report
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_diff_analysis.py -v
```

Expected: ImportError — `diff_analysis` module doesn't exist.

**Step 3: Implement diff_analysis.py**

Create `tools/diff_analysis.py`:

```python
"""
YapCut EDL Diff Analysis

Compares proposed marker regions (from YapCut XML) against the editor's
final EDL (CMX 3600 from Premiere Pro) to build style memory.

Usage:
    python diff_analysis.py markers.xml final_edit.edl --timebase 30
    python diff_analysis.py markers.xml final_edit.edl --preset battlefield-highlights
"""

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime


VALID_PREFIXES = {"KEEP", "MAYBE", "CUT", "MOMENT", "CONTEXT"}
MEMORY_PATH = os.path.join(os.path.dirname(__file__), "..", "EDITORIAL_MEMORY.md")


def smpte_to_frames(tc: str, timebase: int) -> int:
    """Convert SMPTE timecode (HH:MM:SS:FF) to absolute frame count."""
    parts = tc.strip().split(":")
    if len(parts) != 4:
        raise ValueError(f"Invalid SMPTE timecode: {tc}")
    h, m, s, f = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
    return ((h * 3600 + m * 60 + s) * timebase) + f


def parse_edl(edl_path: str, timebase: int = 30) -> list[dict]:
    """Parse a CMX 3600 EDL file into a list of source clips with frame positions."""
    clips = []
    with open(edl_path, encoding="utf-8") as f:
        lines = f.readlines()

    current_clip = None
    for line in lines:
        line = line.rstrip()

        # Match edit decision lines: NNN  REEL  TRACK  CUT  SRC_IN SRC_OUT REC_IN REC_OUT
        edl_match = re.match(
            r"(\d{3})\s+\S+\s+\S+\s+\S+\s+"
            r"(\d{2}:\d{2}:\d{2}:\d{2})\s+"
            r"(\d{2}:\d{2}:\d{2}:\d{2})\s+"
            r"(\d{2}:\d{2}:\d{2}:\d{2})\s+"
            r"(\d{2}:\d{2}:\d{2}:\d{2})",
            line,
        )
        if edl_match:
            src_in = smpte_to_frames(edl_match.group(2), timebase)
            src_out = smpte_to_frames(edl_match.group(3), timebase)
            current_clip = {
                "edit_num": int(edl_match.group(1)),
                "in_frame": src_in,
                "out_frame": src_out,
                "name": "",
            }
            clips.append(current_clip)
            continue

        # Match clip name comment
        name_match = re.match(r"\*\s*FROM CLIP NAME:\s*(.+)", line)
        if name_match and current_clip is not None:
            current_clip["name"] = name_match.group(1).strip()

    return clips


def parse_markers_from_xml(xml_path: str) -> list[dict]:
    """Extract markers from a YapCut FCP XML file."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    markers = []

    for marker in root.iter("marker"):
        name = marker.findtext("name") or ""
        in_val = marker.findtext("in")
        out_val = marker.findtext("out")

        if in_val is None or out_val is None:
            continue

        # Extract marker type from prefix
        prefix_match = re.match(r"\[(\w+)\]", name)
        marker_type = prefix_match.group(1) if prefix_match else "UNKNOWN"

        markers.append({
            "name": name,
            "in": int(in_val),
            "out": int(out_val),
            "type": marker_type,
            "comment": marker.findtext("comment") or "",
        })

    return markers


def compute_overlap(
    proposed_in: int, proposed_out: int, edl_in: int, edl_out: int
) -> float:
    """Compute overlap percentage of an EDL clip against a proposed marker region."""
    proposed_dur = proposed_out - proposed_in
    if proposed_dur <= 0:
        return 0.0
    overlap = max(0, min(proposed_out, edl_out) - max(proposed_in, edl_in))
    return overlap / proposed_dur


def _name_similarity(marker_name: str, edl_name: str) -> float:
    """Simple word-overlap similarity between marker and EDL clip names."""
    # Strip prefix from marker name
    clean_marker = re.sub(r"^\[\w+\]\s*", "", marker_name).lower()
    clean_edl = edl_name.lower()
    if not clean_marker or not clean_edl:
        return 0.0
    marker_words = set(clean_marker.split())
    edl_words = set(clean_edl.split())
    if not marker_words or not edl_words:
        return 0.0
    intersection = marker_words & edl_words
    return len(intersection) / max(len(marker_words), len(edl_words))


def categorize_markers(
    markers: list[dict], edl_clips: list[dict]
) -> list[dict]:
    """Categorize each marker against EDL clips. Also detect USER_KEPT_DEAD_SPACE."""
    results = []
    matched_edl_indices = set()

    for marker in markers:
        best_overlap = 0.0
        best_edl_idx = -1

        for ei, edl_clip in enumerate(edl_clips):
            # Dual-axis matching: name similarity + temporal overlap
            name_sim = _name_similarity(marker["name"], edl_clip["name"])
            overlap = compute_overlap(marker["in"], marker["out"],
                                      edl_clip["in_frame"], edl_clip["out_frame"])

            # Name match boosts: if names match well, even partial overlap counts
            score = overlap
            if name_sim >= 0.5:
                score = max(score, overlap + 0.2)  # boost for name match

            if score > best_overlap:
                best_overlap = score
                best_edl_idx = ei

        # Use raw overlap (not boosted score) for category thresholds
        if best_edl_idx >= 0:
            raw_overlap = compute_overlap(
                marker["in"], marker["out"],
                edl_clips[best_edl_idx]["in_frame"], edl_clips[best_edl_idx]["out_frame"]
            )
        else:
            raw_overlap = 0.0

        if raw_overlap >= 0.7:
            category = "ACCEPTED"
            matched_edl_indices.add(best_edl_idx)
        elif raw_overlap > 0:
            category = "HEAVILY_MODIFIED"
            matched_edl_indices.add(best_edl_idx)
        else:
            category = "REJECTED"

        results.append({
            "name": marker["name"],
            "type": marker.get("type", "UNKNOWN"),
            "category": category,
            "overlap": raw_overlap,
        })

    # Detect USER_KEPT_DEAD_SPACE: EDL clips with no matching marker
    for ei, edl_clip in enumerate(edl_clips):
        if ei not in matched_edl_indices:
            # Check if this EDL clip overlaps with ANY marker
            has_any_overlap = False
            for marker in markers:
                overlap = compute_overlap(marker["in"], marker["out"],
                                          edl_clip["in_frame"], edl_clip["out_frame"])
                if overlap > 0:
                    has_any_overlap = True
                    break

            if not has_any_overlap:
                results.append({
                    "name": edl_clip["name"],
                    "type": "DEAD_SPACE",
                    "category": "USER_KEPT_DEAD_SPACE",
                    "overlap": 0.0,
                })

    return results


def format_session_report(
    categorized: list[dict], preset: str = "none", date: str | None = None
) -> str:
    """Format categorization results as a markdown session report."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    total_proposed = sum(1 for c in categorized if c["category"] != "USER_KEPT_DEAD_SPACE")
    survived = sum(1 for c in categorized if c["category"] == "ACCEPTED")
    rejected = sum(1 for c in categorized if c["category"] == "REJECTED")
    modified = sum(1 for c in categorized if c["category"] == "HEAVILY_MODIFIED")
    dead_space = sum(1 for c in categorized if c["category"] == "USER_KEPT_DEAD_SPACE")

    lines = [
        f"## Session: {date} - {preset}",
        "",
        "**Global Stats:**",
        f"- Proposed: {total_proposed} markers | Survived in EDL: {survived} | "
        f"Modified: {modified} | Not in EDL: {rejected}",
    ]

    if dead_space > 0:
        lines.append(f"- USER_KEPT_DEAD_SPACE: {dead_space} clips from unmarked regions survived")

    # Breakdown by type
    types_seen = sorted(set(
        c["type"] for c in categorized if c["type"] not in ("DEAD_SPACE", "UNKNOWN")
    ))
    if types_seen:
        lines.append("")
        lines.append("**Category Breakdown:**")
        for t in types_seen:
            type_items = [c for c in categorized if c["type"] == t]
            proposed = len(type_items)
            acc = sum(1 for c in type_items if c["category"] == "ACCEPTED")
            mod = sum(1 for c in type_items if c["category"] == "HEAVILY_MODIFIED")
            rej = sum(1 for c in type_items if c["category"] == "REJECTED")
            parts = []
            if acc: parts.append(f"{acc} ACCEPTED")
            if mod: parts.append(f"{mod} HEAVILY_MODIFIED")
            if rej: parts.append(f"{rej} REJECTED")
            lines.append(f"- [{t}]: {proposed} proposed -> {', '.join(parts)}")

    lines.append("")
    return "\n".join(lines)


def append_to_memory(report: str, memory_path: str | None = None):
    """Append a session report to EDITORIAL_MEMORY.md."""
    path = memory_path or MEMORY_PATH
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            existing = f.read()
    else:
        existing = "# Editorial Memory\n\nAuto-generated session reports from EDL diff analysis.\n\n---\n"

    with open(path, "w", encoding="utf-8") as f:
        f.write(existing.rstrip() + "\n\n---\n\n" + report)


def main():
    parser = argparse.ArgumentParser(description="YapCut EDL Diff Analysis")
    parser.add_argument("markers_xml", help="Path to YapCut markers XML")
    parser.add_argument("edl_file", help="Path to Premiere EDL export (CMX 3600)")
    parser.add_argument("--timebase", type=int, default=30, help="Timeline framerate (default: 30)")
    parser.add_argument("--preset", default="none", help="Preset name used for this session")
    parser.add_argument("--memory", default=None, help="Path to EDITORIAL_MEMORY.md")
    args = parser.parse_args()

    print(f"Parsing markers from: {args.markers_xml}")
    markers = parse_markers_from_xml(args.markers_xml)
    print(f"Found {len(markers)} markers")

    print(f"Parsing EDL from: {args.edl_file}")
    edl_clips = parse_edl(args.edl_file, args.timebase)
    print(f"Found {len(edl_clips)} EDL clips")

    categorized = categorize_markers(markers, edl_clips)

    report = format_session_report(categorized, preset=args.preset)
    print("\n" + report)

    append_to_memory(report, args.memory)
    memory_path = args.memory or MEMORY_PATH
    print(f"Report appended to: {memory_path}")


if __name__ == "__main__":
    main()
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_diff_analysis.py -v
```

Expected: ALL tests pass.

**Step 5: Commit**

```bash
git add tools/diff_analysis.py tests/test_diff_analysis.py
git commit -m "feat: add EDL diff analysis for style memory feedback loop"
```

---

### Task 6: Create Editorial Presets

**Files:**
- Create: `presets/battlefield-highlights.md`
- Create: `presets/full-vod-edit.md`
- Create: `presets/shorts-extraction.md`
- Create: `presets/battlefam-episode.md`
- Create: `presets/chill-stream.md`

**Step 1: Create battlefield-highlights.md**

Copy the full preset content from the v2 spec (lines 196-236 of `yapcut-v2-final-spec.md`). This is the reference preset.

**Step 2: Create full-vod-edit.md**

```markdown
# YAPCUT PRESET: Full VOD Edit

## Target Output
- Format: YouTube Full VOD Edit
- Ratio: Compress 2-4 hours into 30-50 minutes
- Marker Density Target: 30-40 markers per hour of source material

## Content Priority Stack (Highest to Lowest)
1. Narrative Arcs — story beats, building tension, payoff moments
2. High-Energy Reactions — genuine emotional peaks, laughter, surprise
3. Skill Moments — impressive gameplay, clutch plays
4. Quality Banter — entertaining conversation, funny exchanges
5. World-Building — context that makes the stream feel like an experience, not a clip reel

## Implicit CUT Zones (Do NOT Flag)
- Menu navigation, matchmaking, loading screens
- Extended AFK or bathroom breaks
- Technical difficulties (OBS issues, lag, restarts) unless the reaction is gold
- Repetitive gameplay with no commentary variation

## General Rules
- Bias toward KEEP over CUT — this is a long-form edit, not a highlight reel
- MAYBE markers are your friend here — flag generously, let the editor decide pacing
- Preserve conversation flow: if a KEEP moment references something said 2 minutes ago,
  flag the earlier part as CONTEXT
- Runtime is flexible — better to over-flag than under-flag for full VOD edits

## Short Extraction (MOMENT flags)
- Conservative MOMENT flagging — full VOD edits produce fewer standalone clips
- Only flag moments that are genuinely self-contained without surrounding context
- Target: 2-4 MOMENT flags per hour of source

## Audio Priority Rules
- Vocal energy matters but isn't the only signal for long-form
- Quiet, authentic moments can be just as keepable as high-energy peaks
- Commentary quality (insight, humor, storytelling) outranks raw volume
```

**Step 3: Create shorts-extraction.md**

```markdown
# YAPCUT PRESET: Shorts Extraction

## Target Output
- Format: YouTube Shorts / TikTok / Clips
- Ratio: Extract 5-15 standalone moments from a 2-4 hour stream
- Marker Density Target: 5-10 MOMENT markers per hour (plus supporting CONTEXT)

## Content Priority Stack (Highest to Lowest)
1. Reaction Peaks — genuine surprise, laughter, disbelief in a tight window
2. Mechanical Highlights — impressive plays with clear setup and payoff
3. One-Liner Gold — quotable moments, funny remarks, meme-worthy lines
4. Fails — comedic deaths, mistakes, rage moments (if short and punchy)
5. Chat Interactions — viewer-triggered moments with strong reaction

## Implicit CUT Zones (Do NOT Flag)
- Everything that isn't a self-contained 15-60 second moment
- Extended gameplay sequences (even good ones — save those for VOD edits)
- Conversations that require context from minutes earlier
- Slow builds without clear payoff within 60 seconds

## General Rules
- MOMENT is the primary marker type — KEEP/MAYBE are secondary
- Every MOMENT must be self-contained: setup, peak, reaction in 15-60 seconds
- If a moment needs more than 10 seconds of CONTEXT to make sense, it's not a Short
- Bias toward shorter clips — 20-30 seconds is the sweet spot
- Flag generously — editor will cherry-pick the best 3-5 from your suggestions

## Short Extraction (MOMENT flags)
- Aggressive flagging — this is the entire point of the preset
- Each MOMENT flag should include a suggested hook line in the comment
- Note the peak moment timestamp in the comment for thumbnail selection
- Target: self-contained 15-60 second clips

## Audio Priority Rules
- Vocal clarity is non-negotiable — if the reaction is muddy, skip it
- Volume spikes alone aren't enough — needs content (words, genuine reaction)
- Game audio can carry a moment if the visual is strong enough (rare)
```

**Step 4: Create battlefam-episode.md**

```markdown
# YAPCUT PRESET: BattleFam Episode (Collab / Squad Streams)

## Target Output
- Format: YouTube Squad/Collab Highlight Episode
- Ratio: Compress 2-4 hours into 20-35 minutes
- Marker Density Target: 25-30 markers per hour of source material

## Content Priority Stack (Highest to Lowest)
1. Squad Banter — funny arguments, roasts, bits between squad members
2. Coordinated Plays — squad wipes, team pushes, callout-to-execution sequences
3. Individual Pops — one person does something amazing, squad reacts
4. Running Jokes — callbacks, recurring bits within the session
5. Competitive Moments — close matches, clutch rounds, comeback arcs

## Implicit CUT Zones (Do NOT Flag)
- Solo gameplay with no comms (unless mechanically exceptional)
- Menu time, loadouts, matchmaking
- Side conversations about scheduling, technical setup, or stream logistics
- Extended periods where only one person is talking and others are silent

## Title-Specific Rules (Squad / Collab)
- Multi-voice energy is the signal — when multiple people are reacting, that's a KEEP
- Single-voice monologues need to be genuinely funny or insightful to survive
- If the guest/collab partner has a great moment, bias toward KEEP even if the host
  is quiet — the audience wants to see the dynamic
- Discord audio quality issues: flag in comment if audio is degraded. Editor may
  need to adjust levels or skip.

## Short Extraction (MOMENT flags)
- Moderate MOMENT flagging — squad moments often need 30-45 seconds of context
- Best squad Shorts: quick exchange → punchline → group reaction (under 30s)
- Flag moments where the squad energy is infectious

## Audio Priority Rules
- Multi-voice clarity is critical — moments where people talk over each other
  may sound chaotic but often edit well if the punchline lands clean
- Guest audio quality varies — note in comment when guest mic is hot/quiet
- Laughter is a strong keep signal, especially when it's genuine and contagious
```

**Step 5: Create chill-stream.md**

```markdown
# YAPCUT PRESET: Chill Stream

## Target Output
- Format: YouTube Relaxed/Chill Stream Edit
- Ratio: Compress 2-4 hours into 15-25 minutes
- Marker Density Target: 15-20 markers per hour of source material

## Content Priority Stack (Highest to Lowest)
1. Authentic Reactions — genuine emotion, not performed energy
2. Storytelling — personal anecdotes, thoughtful commentary, real talk
3. Quiet Humor — dry jokes, subtle moments, understated comedy
4. Viewer Interactions — meaningful chat responses, community moments
5. Ambient Vibes — moments where the game + commentary create a mood

## Implicit CUT Zones (Do NOT Flag)
- High-energy forced moments (if the streamer is clearly "performing" energy
  during a chill stream, it breaks the vibe)
- Extended silence beyond 10 seconds (unless the visual is carrying the moment)
- Repetitive gameplay loops with no commentary variation
- Standard donation/sub reads (unless they spark genuine conversation)

## General Rules
- Less is more — chill edits should breathe. Don't pack the timeline.
- MAYBE markers are more valuable here than in highlight presets —
  the editor needs options, not directives
- Preserve natural pacing: don't cut mid-thought even if the thought meanders
- A 2-minute unbroken segment is fine if the conversation is genuine
- CUT markers almost never needed — chill streams rarely have editorial traps

## Short Extraction (MOMENT flags)
- Rare MOMENT flagging — chill streams produce fewer Shorts
- Only flag moments with genuine standalone impact (a perfect one-liner,
  a surprisingly emotional moment, an unexpected event)
- Target: 1-3 MOMENT flags per hour of source at most

## Audio Priority Rules
- Authenticity over energy — quiet genuine moments beat loud performed ones
- Background music/game audio contributes to vibe — note when it enhances a moment
- Whispered or low-energy delivery can be a KEEP signal in this context
- Comfortable silence followed by a good thought = KEEP the silence too
```

**Step 6: Commit**

```bash
git add presets/
git commit -m "feat: add editorial presets (battlefield, full-vod, shorts, battlefam, chill)"
```

---

### Task 7: Update CLAUDE.md for v2

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Rewrite CLAUDE.md**

Replace the full content of `CLAUDE.md` with the updated v2 version. Keep all v1 FCP XML schema knowledge (it's still used for Mode 2 rough cuts). Add:

- Updated header: "# YapCut" with v2 description
- **How the Workflow Operates** — updated for marker-first, briefing-centric flow
- **The Briefing Conversation** — required info, topics, how it works (from spec)
- **Operating Modes** — Mode 1 (Markers/default) and Mode 2 (Rough Cut/opt-in)
- **Marker Types** — table of KEEP/MAYBE/CUT/MOMENT/CONTEXT with colors and meanings
- **CUT Marker Logic** — sparse by design, when to use vs not (from spec)
- **Marker XML Schema** — the `<marker>` node structure inside `<clipitem>` (from spec)
- **Editorial Presets** — how to load and use them, where they live
- **YouTube Chat Integration** — how chat is used as signal, where the data comes from
- **Style Memory** — EDITORIAL_MEMORY.md, how it's built, how to read it
- **Project Structure** — updated directory tree
- **Input Transcript Format** — keep from v1 (unchanged)
- **FCP 7 XML Schema** — keep from v1 (needed for both modes)
- **Media Path Conventions** — keep from v1 (unchanged)
- **Editorial Guidelines** — keep from v1, note presets extend these
- **Generating an Edit** — updated for marker-first flow
- **Validation** — updated path to `tools/validate_xml.py`

The full content should be written during implementation. Reference the v2 spec for exact wording on marker types, CUT logic, briefing topics, and XML schema. Reference v1 CLAUDE.md for FCP schema, transcript format, and media paths.

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for v2 marker-based workflow"
```

---

### Task 8: Create EDITORIAL_MEMORY.md and Final Cleanup

**Files:**
- Create: `EDITORIAL_MEMORY.md`
- Modify: `.gitignore` (ensure `input/` is ignored but `presets/` and `EDITORIAL_MEMORY.md` are tracked)
- Delete: `presets/.gitkeep` (presets directory now has real files)

**Step 1: Create EDITORIAL_MEMORY.md**

```markdown
# Editorial Memory

YapCut's evolving style memory. Auto-populated by `tools/diff_analysis.py` after
each editing session (EDL export vs. proposed markers). Manual notes can be added
at any time.

Read this file at the start of every YapCut session to calibrate marker generation
to the editor's demonstrated preferences.

---

*No sessions recorded yet. Memory will build after the first EDL diff analysis.*
```

**Step 2: Remove presets/.gitkeep**

```bash
rm presets/.gitkeep
```

**Step 3: Run full test suite**

```bash
pytest tests/ -v
```

Expected: ALL tests pass.

**Step 4: Run validator on existing output XML as regression check**

```bash
python tools/validate_xml.py output/bf6_part3_rough_cut.xml
```

Expected: PASS (the v1 rough cut should still validate under the updated validator).

**Step 5: Commit**

```bash
git add EDITORIAL_MEMORY.md
git add -A
git commit -m "feat: complete YapCut v2 implementation — markers, presets, chat, memory"
```

---

### Task Summary

| Task | Description | Dependencies |
|------|-------------|-------------|
| 1 | Directory restructure | None |
| 2 | Python dependencies | Task 1 |
| 3 | Validate XML marker support | Task 1 |
| 4 | YouTube chat fetcher | Task 2 |
| 5 | EDL diff analysis | Task 2 |
| 6 | Editorial presets | Task 1 |
| 7 | Update CLAUDE.md | Tasks 1, 3, 4, 5, 6 |
| 8 | Editorial memory + final cleanup | Tasks 1-7 |
