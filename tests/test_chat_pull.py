"""Tests for tools/chat_pull.py — data processing logic only, no API credentials needed."""

import json
import sys
import tempfile
from pathlib import Path

# Allow importing from tools/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from chat_pull import normalize_messages, save_chat_json  # noqa: E402


# ---------------------------------------------------------------------------
# normalize_messages tests
# ---------------------------------------------------------------------------

def test_normalize_messages_converts_timestamps():
    """Raw API messages with publishedAt are converted to stream-relative timestamp_ms."""
    stream_start_iso = "2026-01-15T20:00:00.000Z"

    raw_messages = [
        {
            "snippet": {
                "publishedAt": "2026-01-15T20:02:25.000Z",  # 145s after start
                "displayMessage": "LMAOOO",
                "authorChannelId": "UCxyz",
            },
            "authorDetails": {
                "displayName": "TestUser",
                "isChatOwner": False,
                "isChatModerator": False,
                "isChatSponsor": False,
            },
        },
        {
            "snippet": {
                "publishedAt": "2026-01-15T20:05:00.000Z",  # 300s after start
                "displayMessage": "nice play!",
                "authorChannelId": "UCabc",
            },
            "authorDetails": {
                "displayName": "AnotherUser",
                "isChatOwner": False,
                "isChatModerator": True,
                "isChatSponsor": True,
            },
        },
    ]

    result = normalize_messages(raw_messages, stream_start_iso)

    assert len(result) == 2

    # First message: 145 seconds = 145000 ms
    assert result[0]["timestamp_ms"] == 145000
    assert result[0]["author"] == "TestUser"
    assert result[0]["message"] == "LMAOOO"
    assert result[0]["is_member"] is False
    assert result[0]["is_moderator"] is False

    # Second message: 300 seconds = 300000 ms
    assert result[1]["timestamp_ms"] == 300000
    assert result[1]["author"] == "AnotherUser"
    assert result[1]["message"] == "nice play!"
    assert result[1]["is_member"] is True
    assert result[1]["is_moderator"] is True


def test_normalize_messages_negative_timestamp_clamped():
    """Messages with publishedAt before stream start get timestamp_ms = 0."""
    stream_start_iso = "2026-01-15T20:00:00.000Z"

    raw_messages = [
        {
            "snippet": {
                "publishedAt": "2026-01-15T19:58:00.000Z",  # 2 min BEFORE start
                "displayMessage": "waiting for stream!",
                "authorChannelId": "UCearly",
            },
            "authorDetails": {
                "displayName": "EarlyBird",
                "isChatOwner": False,
                "isChatModerator": False,
                "isChatSponsor": False,
            },
        },
    ]

    result = normalize_messages(raw_messages, stream_start_iso)

    assert len(result) == 1
    assert result[0]["timestamp_ms"] == 0
    assert result[0]["author"] == "EarlyBird"
    assert result[0]["message"] == "waiting for stream!"


def test_save_chat_json_schema():
    """Output JSON file matches the expected schema with video_id and messages array."""
    messages = [
        {
            "timestamp_ms": 145000,
            "author": "TestUser",
            "message": "LMAOOO",
            "is_member": False,
            "is_moderator": False,
        },
        {
            "timestamp_ms": 300000,
            "author": "AnotherUser",
            "message": "nice play!",
            "is_member": True,
            "is_moderator": True,
        },
    ]

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        output_path = f.name

    save_chat_json("abc123", messages, output_path)

    with open(output_path, encoding="utf-8") as f:
        data = json.load(f)

    # Top-level keys
    assert "video_id" in data
    assert "messages" in data
    assert data["video_id"] == "abc123"

    # Messages array
    assert isinstance(data["messages"], list)
    assert len(data["messages"]) == 2

    # Each message has the required fields
    required_fields = {"timestamp_ms", "author", "message", "is_member", "is_moderator"}
    for msg in data["messages"]:
        assert set(msg.keys()) == required_fields

    # Spot-check values
    assert data["messages"][0]["timestamp_ms"] == 145000
    assert data["messages"][0]["author"] == "TestUser"
    assert data["messages"][1]["is_moderator"] is True
