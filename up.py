# upload_only_netlify.py

"""
Upload already-encoded clips from public/ to Instagram Reels using Netlify URLs.
Usage:
    python upload_only_netlify.py           # start from first clip
    python upload_only_netlify.py 17        # start from clip index 17
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")
GRAPH_BASE = os.getenv("GRAPH_BASE", "https://graph.facebook.com/v24.0")
VIDEO_TITLE = os.getenv("VIDEO_TITLE", "Video")
EPISODE_NUMBER = int(os.getenv("EPISODE_NUMBER", "1"))

# Netlify base URL (apna URL daalo)
NETLIFY_BASE = os.getenv("NETLIFY_BASE", "https://splashyx.netlify.app")

BASE_DIR = Path.cwd()
PUBLIC_DIR = BASE_DIR / "public"


def create_media_container(public_url: str, caption: str) -> Optional[str]:
    url = f"{GRAPH_BASE}/{IG_USER_ID}/media"
    payload = {
        "media_type": "REELS",
        "video_url": public_url,
        "caption": caption,
        "access_token": ACCESS_TOKEN,
    }
    print("Creating container for:", public_url)
    print("  Caption:", caption)
    r = requests.post(url, json=payload, timeout=60)
    print("  Status:", r.status_code)
    print("  Resp  :", r.text)
    if r.status_code != 200:
        return None
    return r.json().get("id")


def check_container_status(creation_id: str) -> str:
    url = f"{GRAPH_BASE}/{creation_id}"
    params = {"fields": "status_code", "access_token": ACCESS_TOKEN}
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        return r.json().get("status_code", "UNKNOWN")
    except Exception:
        return "ERROR"


def publish_media(creation_id: str) -> bool:
    url = f"{GRAPH_BASE}/{IG_USER_ID}/media_publish"
    payload = {"creation_id": creation_id, "access_token": ACCESS_TOKEN}

    for attempt in range(1, 8):
        status = check_container_status(creation_id)
        print(f"  Attempt {attempt}: container status = {status}")
        if status == "FINISHED":
            r = requests.post(url, data=payload, timeout=60)
            print("  Publish status:", r.status_code, r.text)
            return r.status_code == 200
        if status == "ERROR":
            print("  Container ERROR, abort.")
            return False
        wait = 20 * attempt
        print(f"  Waiting {wait}s before re-check...")
        time.sleep(wait)
    return False


def main():
    if not ACCESS_TOKEN or not IG_USER_ID:
        print("ACCESS_TOKEN / IG_USER_ID missing in .env")
        sys.exit(1)

    # CLI start index (resume support)
    if len(sys.argv) >= 2:
        try:
            start_index = int(sys.argv[1])
        except ValueError:
            print("Invalid start index, use: python upload_only_netlify.py 17")
            sys.exit(1)
    else:
        start_index = 1

    files: List[Path] = sorted(PUBLIC_DIR.glob("final_*.mp4"))
    if not files:
        print("No final_*.mp4 found in public/ for upload.")
        sys.exit(0)

    print(f"Found {len(files)} clips in public/")
    print(f"Will start uploading from index {start_index}")

    success = 0
    for idx, f in enumerate(files, start=1):
        if idx < start_index:
            continue  # already done earlier

        print(f"\n--- Clip {idx}/{len(files)} :: {f.name} ---")

        # IMPORTANT: browser me yeh chalna chahiye:
        # https://splashyx.netlify.app/final_001.mp4
        public_url = f"{NETLIFY_BASE}/{f.name}"

        # Caption: "TITLE E<episode> P<part> #tags"
        part_label = f"E{EPISODE_NUMBER} P{idx}"
        base_caption = f"{VIDEO_TITLE} {part_label}"
        hashtags = "#anime #animereels #reels #edit #fyp"
        caption = f"{base_caption} {hashtags}"

        cid = create_media_container(public_url, caption)
        if not cid:
            print("!! Skipping, container create failed.")
            continue

        print("  Waiting 45s before publish...")
        time.sleep(45)

        if publish_media(cid):
            success += 1
            print(f"✅ Posted {f.name}")
        else:
            print(f"⚠️ Failed to publish {f.name}")

        if idx < len(files):
            print("  Cooldown 30s before next clip...")
            try:
                time.sleep(30)
            except KeyboardInterrupt:
                print("\nInterrupted during cooldown. You can resume later with:")
                print(f"  python upload_only_netlify.py {idx+1}")
                break

    print(f"\nDone. Success: {success}/{len(files)}")


if __name__ == "__main__":
    main()
