"""YouTube live chat replay fetcher.

Pulls chat messages from a stream VOD and saves them as JSON for editorial
signal use. Chat density spikes and sentiment clustering help inform edit
decisions (KEEP vs MAYBE).

Three lookup modes:
    --video-id ID     Fetch chat for a specific video ID
    --search "query"  Search the channel for a video by title, pick one
    --recent          List recent uploads from the channel, pick one

Auth: OAuth2 via credentials at C:\\Users\\jaywa.NEUTRON\\Projects\\config\\
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CONFIG_DIR = r"C:\Users\jaywa.NEUTRON\Projects\config"
DEFAULT_OUTPUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "input", "chat.json"
)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def load_credentials() -> Credentials:
    """Load OAuth2 credentials from youtube_token.json, auto-refresh if expired."""
    token_path = os.path.join(CONFIG_DIR, "youtube_token.json")

    with open(token_path, encoding="utf-8") as f:
        token_data = json.load(f)

    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes"),
    )

    if creds.expired and creds.refresh_token:
        print("Refreshing expired token...")
        creds.refresh(Request())
        # Persist the refreshed token
        token_data["token"] = creds.token
        with open(token_path, "w", encoding="utf-8") as f:
            json.dump(token_data, f, indent=2)
        print("Token refreshed and saved.")

    return creds


def get_channel_id() -> str:
    """Load YOUTUBE_CHANNEL_ID from .env in CONFIG_DIR."""
    dotenv_path = os.path.join(CONFIG_DIR, ".env")
    load_dotenv(dotenv_path)
    channel_id = os.environ.get("YOUTUBE_CHANNEL_ID")
    if not channel_id:
        print(f"Error: YOUTUBE_CHANNEL_ID not found in {dotenv_path}")
        sys.exit(1)
    return channel_id


# ---------------------------------------------------------------------------
# YouTube API helpers
# ---------------------------------------------------------------------------

def get_live_chat_id(youtube, video_id: str) -> str:
    """Get the activeLiveChatId for a video (must be a past/current live stream)."""
    resp = youtube.videos().list(
        part="liveStreamingDetails",
        id=video_id,
    ).execute()

    items = resp.get("items", [])
    if not items:
        print(f"Error: Video {video_id} not found.")
        sys.exit(1)

    details = items[0].get("liveStreamingDetails", {})
    chat_id = details.get("activeLiveChatId")
    if not chat_id:
        print(f"Error: Video {video_id} has no live chat replay available.")
        sys.exit(1)

    return chat_id


def get_stream_start(youtube, video_id: str) -> str:
    """Get the actualStartTime ISO string for a live stream video."""
    resp = youtube.videos().list(
        part="liveStreamingDetails",
        id=video_id,
    ).execute()

    items = resp.get("items", [])
    if not items:
        print(f"Error: Video {video_id} not found.")
        sys.exit(1)

    details = items[0].get("liveStreamingDetails", {})
    start_time = details.get("actualStartTime")
    if not start_time:
        print(f"Error: Video {video_id} has no actualStartTime (may not be a live stream).")
        sys.exit(1)

    return start_time


def fetch_chat_messages(youtube, chat_id: str) -> list:
    """Paginate through all liveChatMessages for a chat replay. Returns raw API items."""
    all_messages = []
    page_token = None
    page_count = 0

    while True:
        kwargs = {
            "liveChatId": chat_id,
            "part": "snippet,authorDetails",
            "maxResults": 2000,
        }
        if page_token:
            kwargs["pageToken"] = page_token

        resp = youtube.liveChatMessages().list(**kwargs).execute()

        items = resp.get("items", [])
        all_messages.extend(items)
        page_count += 1

        total = resp.get("pageInfo", {}).get("totalResults", "?")
        print(f"  Page {page_count}: fetched {len(items)} messages (total so far: {len(all_messages)}, API total: {total})")

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return all_messages


# ---------------------------------------------------------------------------
# Data processing
# ---------------------------------------------------------------------------

def normalize_messages(raw_messages: list, stream_start_iso: str) -> list:
    """Convert raw YouTube API chat messages to YapCut schema.

    Timestamps are converted from absolute publishedAt to milliseconds
    relative to stream start. Messages before stream start are clamped to 0.
    """
    stream_start = datetime.fromisoformat(stream_start_iso.replace("Z", "+00:00"))

    normalized = []
    for msg in raw_messages:
        snippet = msg["snippet"]
        author_details = msg["authorDetails"]

        published = datetime.fromisoformat(
            snippet["publishedAt"].replace("Z", "+00:00")
        )
        delta_ms = int((published - stream_start).total_seconds() * 1000)

        # Clamp negative timestamps (messages sent before stream officially started)
        if delta_ms < 0:
            delta_ms = 0

        normalized.append({
            "timestamp_ms": delta_ms,
            "author": author_details["displayName"],
            "message": snippet["displayMessage"],
            "is_member": bool(author_details.get("isChatSponsor", False)),
            "is_moderator": bool(author_details.get("isChatModerator", False)),
        })

    return normalized


def save_chat_json(video_id: str, messages: list, output_path: str) -> None:
    """Write chat messages to JSON file in YapCut schema."""
    data = {
        "video_id": video_id,
        "messages": messages,
    }

    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(messages)} messages to {output_path}")


# ---------------------------------------------------------------------------
# Channel browsing helpers
# ---------------------------------------------------------------------------

def search_channel_videos(youtube, channel_id: str, query: str) -> list:
    """Search a channel for videos matching a query. Returns list of {id, title, date}."""
    resp = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        q=query,
        type="video",
        eventType="completed",
        maxResults=10,
        order="relevance",
    ).execute()

    videos = []
    for item in resp.get("items", []):
        videos.append({
            "id": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "date": item["snippet"]["publishedAt"][:10],
        })

    return videos


def list_recent_uploads(youtube, channel_id: str) -> list:
    """Get recent uploads from the channel's uploads playlist. Returns list of {id, title, date}."""
    # First, get the uploads playlist ID
    resp = youtube.channels().list(
        part="contentDetails",
        id=channel_id,
    ).execute()

    items = resp.get("items", [])
    if not items:
        print(f"Error: Channel {channel_id} not found.")
        sys.exit(1)

    uploads_playlist_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # Then list items from that playlist
    resp = youtube.playlistItems().list(
        part="snippet",
        playlistId=uploads_playlist_id,
        maxResults=15,
    ).execute()

    videos = []
    for item in resp.get("items", []):
        snippet = item["snippet"]
        videos.append({
            "id": snippet["resourceId"]["videoId"],
            "title": snippet["title"],
            "date": snippet["publishedAt"][:10],
        })

    return videos


def pick_video_interactive(videos: list, label: str) -> str:
    """Display a numbered list of videos and let the user pick one. Returns video ID."""
    if not videos:
        print(f"No {label} found.")
        sys.exit(1)

    print(f"\n{label}:")
    print("-" * 60)
    for i, video in enumerate(videos, 1):
        print(f"  {i:2d}. [{video['date']}] {video['title']}")
    print()

    while True:
        try:
            choice = input(f"Pick a video (1-{len(videos)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(videos):
                selected = videos[idx]
                print(f"\nSelected: {selected['title']} ({selected['id']})")
                return selected["id"]
            else:
                print(f"Please enter a number between 1 and {len(videos)}.")
        except ValueError:
            print("Please enter a valid number.")
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            sys.exit(0)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Fetch YouTube live chat replay for a stream VOD.",
        epilog="Chat data is saved as JSON for use as an editorial signal in YapCut sessions.",
    )
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--video-id",
        help="Fetch chat for a specific video ID",
    )
    mode_group.add_argument(
        "--search",
        metavar="QUERY",
        help="Search the channel for a video by title",
    )
    mode_group.add_argument(
        "--recent",
        action="store_true",
        help="List recent uploads from the channel and pick one",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Output JSON path (default: {DEFAULT_OUTPUT})",
    )

    args = parser.parse_args()

    # Authenticate
    print("Loading credentials...")
    creds = load_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    # Resolve video ID
    if args.video_id:
        video_id = args.video_id
    elif args.search:
        channel_id = get_channel_id()
        videos = search_channel_videos(youtube, channel_id, args.search)
        video_id = pick_video_interactive(videos, f'Search results for "{args.search}"')
    elif args.recent:
        channel_id = get_channel_id()
        videos = list_recent_uploads(youtube, channel_id)
        video_id = pick_video_interactive(videos, "Recent uploads")

    print(f"\nFetching chat for video: {video_id}")

    # Get stream metadata
    print("Getting stream start time...")
    stream_start = get_stream_start(youtube, video_id)
    print(f"Stream started at: {stream_start}")

    print("Getting live chat ID...")
    chat_id = get_live_chat_id(youtube, video_id)
    print(f"Chat ID: {chat_id}")

    # Fetch all chat messages
    print("\nFetching chat messages...")
    raw_messages = fetch_chat_messages(youtube, chat_id)
    print(f"Total raw messages: {len(raw_messages)}")

    # Normalize to YapCut schema
    messages = normalize_messages(raw_messages, stream_start)

    # Save
    save_chat_json(video_id, messages, args.output)
    print("\nDone!")


if __name__ == "__main__":
    main()
