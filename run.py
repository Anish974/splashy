"""
Instagram Reels Automation — Single-file Python Script (Netlify Version)
----------------------------------------------------------------------
Features:
1) Slice input video into N-second segments
2) Add cinematic text overlay (top title + bottom part number (E# P#))
3) Add padding: top and bottom (black bars)
4) Save edited clips into public/ for Netlify
5) Upload clips to Instagram Reels via Graph API using Netlify URLs
6) Memory-efficient processing (one clip at a time)
"""

import os
import sys
import time
import math
import subprocess
from pathlib import Path
from typing import List, Optional

import requests
from dotenv import load_dotenv

# --- Load environment variables ---
load_dotenv()

# Required
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")

# Optional with defaults
VIDEO_TITLE = os.getenv("VIDEO_TITLE", "Video")
CLIP_SECONDS = int(os.getenv("CLIP_SECONDS", "30"))
FONTFILE = os.getenv("FONTFILE", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
GRAPH_BASE = os.getenv("GRAPH_BASE", "https://graph.facebook.com/v24.0")
TOP_FONTSIZE = int(os.getenv("TOP_FONTSIZE", "90"))
BOTTOM_FONTSIZE = int(os.getenv("BOTTOM_FONTSIZE", "80"))
VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", "1080"))
VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", "1920"))
PAD_TOP = int(os.getenv("PAD_TOP", "200"))
PAD_BOTTOM = int(os.getenv("PAD_BOTTOM", "200"))
EPISODE_NUMBER = int(os.getenv("EPISODE_NUMBER", "1"))

# Netlify base URL (apna site URL daalo)
NETLIFY_BASE = os.getenv("NETLIFY_BASE", "https://splashyx.netlify.app")

# --- Directories ---
BASE_DIR = Path.cwd()
PARTS_DIR = BASE_DIR / "parts"
FINAL_DIR = BASE_DIR / "final"
STATIC_DIR = BASE_DIR / "public"

for d in (PARTS_DIR, FINAL_DIR, STATIC_DIR):
    d.mkdir(exist_ok=True)

# -------------------------------------------------------------------
# Utility / debug helpers
# -------------------------------------------------------------------

def check_dependencies():
    """Check if required tools are installed."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except Exception:
        print("❌ ERROR: ffmpeg not found. Install with: apt-get install ffmpeg")
        sys.exit(1)

def validate_env():
    """Validate required environment variables."""
    print(f"DEBUG ACCESS_TOKEN prefix: {str(ACCESS_TOKEN)[:10] if ACCESS_TOKEN else 'None'}")
    print(f"DEBUG IG_USER_ID: {IG_USER_ID}")

    if not ACCESS_TOKEN:
        print("❌ ERROR: ACCESS_TOKEN not set in .env")
        sys.exit(1)

    if not IG_USER_ID:
        print("❌ ERROR: IG_USER_ID not set in .env")
        sys.exit(1)

def test_token():
    """Quick self‑test: call /me with current token, print result."""
    url = f"{GRAPH_BASE}/me"
    params = {
        "fields": "id,username",
        "access_token": ACCESS_TOKEN,
    }
    print("\n=== TOKEN SELF-TEST: GET /me?fields=id,username ===")
    print("Request URL:", url)
    try:
        r = requests.get(url, params=params, timeout=20)
        print("Status:", r.status_code)
        print("Response:", r.text)
    except Exception as e:
        print("❌ /me test failed:", e)
    print("=== END SELF-TEST ===\n")

# -------------------------------------------------------------------
# FFmpeg helpers
# -------------------------------------------------------------------

def ffprobe_duration(path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path)
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
        return float(out)
    except Exception as e:
        print(f"❌ Error getting video duration: {e}")
        return 0.0

def slice_video(input_path: Path, out_dir: Path, segment_sec: int = 30) -> List[Path]:
    duration = ffprobe_duration(input_path)
    if duration == 0:
        print("❌ Could not determine video duration")
        return []

    num_clips = math.ceil(duration / segment_sec)
    parts: List[Path] = []

    print("\n📹 Video Info:")
    print(f"   Duration: {duration:.2f}s")
    print(f"   Creating {num_clips} clips of {segment_sec}s each\n")

    for i in range(num_clips):
        start = i * segment_sec
        out = out_dir / f"part_{i:03d}.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", str(input_path),
            "-t", str(segment_sec),
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            str(out)
        ]
        print(f"✂️  Slicing clip {i+1}/{num_clips}...")
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            parts.append(out)
            print(f"   ✅ Created: {out.name}")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Failed to slice clip {i+1}: {e.stderr.decode()}")
    return parts

# --------- OVERLAY FUNCTION (TITLE TOP, E# P# BOTTOM) ---------

def overlay_and_encode(
    input_path: Path,
    output_path: Path,
    title: str,
    part_num: int,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    pad_top: int = PAD_TOP,
    pad_bottom: int = PAD_BOTTOM,
    top_fontsize: int = TOP_FONTSIZE,
    bottom_fontsize: int = BOTTOM_FONTSIZE,
) -> Optional[Path]:
    # Escape for FFmpeg
    title_escaped = title.replace("'", r"\'").replace(":", r"\:")
    part_label = f"E{EPISODE_NUMBER} P{part_num}"    # E1 P1, E1 P2, ...
    part_text_escaped = part_label.replace("'", r"\'").replace(":", r"\:")
    fontfile = FONTFILE.replace("\\", "/")

    content_height = height - pad_top - pad_bottom

    video_filter = (
        # scale into content area respecting aspect ratio
        f"scale="
        f"w='if(gt(a,{width}/{content_height}),{width},-2)':"
        f"h='if(gt(a,{width}/{content_height}),-2,{content_height})',"
        # pad to full size, video centered between top/bottom bars
        f"pad=width={width}:height={height}:"
        f"x=(ow-iw)/2:"
        f"y={pad_top}+(oh-{pad_top}-{pad_bottom}-ih)/2:color=black,"
        # TOP TITLE (upper bar, center)
        f"drawtext=fontfile='{fontfile}':text='{title_escaped}':"
        f"fontsize={top_fontsize}:fontcolor=white:"
        f"x=(w-text_w)/2:"
        f"y={pad_top*1.8}-text_h/2:"
        f"box=1:boxcolor=black@1:boxborderw=30,"
        # BOTTOM LABEL: E# P#
        f"drawtext=fontfile='{fontfile}':text='{part_text_escaped}':"
        f"fontsize={bottom_fontsize}:fontcolor=white:"
        f"x=(w-text_w)/2:"
        f"y=h-{pad_bottom*1.8}-text_h/2:"
        f"box=1:boxcolor=black@1:boxborderw=30"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", video_filter,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-profile:v", "high",
        "-level", "4.0",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-movflags", "+faststart",
        str(output_path),
    ]

    print(f"🎬 Encoding clip {part_num} with overlay...")
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"   ✅ Encoded: {output_path.name}")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Encoding failed: {e.stderr.decode()}")
        return None

# -------------------------------------------------------------------
# Instagram API helpers
# -------------------------------------------------------------------

def create_media_container(
    ig_user_id: str,
    access_token: str,
    video_url: str,
    caption: str = "",
) -> Optional[str]:
    """Step 1: Create media container (REELS)."""
    url = f"{GRAPH_BASE}/{ig_user_id}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": access_token,
    }

    print("📤 Creating media container...")
    print("   URL:", url)
    print("   Caption:", caption)

    try:
        r = requests.post(url, json=payload, timeout=60)
        print("   Status:", r.status_code)
        print("   Response:", r.text)
        r.raise_for_status()
        data = r.json()
        creation_id = data.get("id")
        print("   ✅ Container id:", creation_id)
        return creation_id
    except requests.exceptions.RequestException as e:
        print("   ❌ Failed to create container:", e)
        return None

def check_container_status(creation_id: str, access_token: str) -> str:
    url = f"{GRAPH_BASE}/{creation_id}"
    params = {"fields": "status_code", "access_token": access_token}
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        return r.json().get("status_code", "UNKNOWN")
    except Exception:
        return "ERROR"

def publish_media(
    ig_user_id: str,
    access_token: str,
    creation_id: str,
    max_attempts: int = 10,
    wait_seconds: int = 30,
) -> Optional[dict]:
    """Step 2: Publish container."""
    publish_url = f"{GRAPH_BASE}/{ig_user_id}/media_publish"
    payload = {"creation_id": creation_id, "access_token": access_token}

    for attempt in range(1, max_attempts + 1):
        print(f"📢 Publish attempt {attempt}/{max_attempts}...")
        status = check_container_status(creation_id, access_token)
        print("   Container status:", status)

        if status == "FINISHED":
            try:
                r = requests.post(publish_url, data=payload, timeout=60)
                print("   Publish status:", r.status_code)
                print("   Publish response:", r.text)
                if r.status_code == 200:
                    return r.json()
            except requests.exceptions.RequestException as e:
                print("   ❌ Publish error:", e)
        elif status == "ERROR":
            print("   ❌ Container has ERROR status, aborting publish.")
            return None

        wait = wait_seconds * attempt
        print(f"   ⏳ Waiting {wait}s...")
        time.sleep(wait)

    print("   ❌ Failed to publish after all attempts")
    return None

# -------------------------------------------------------------------
# Main pipeline
# -------------------------------------------------------------------

def pipeline(input_file: str):
    print("\n" + "=" * 60)
    print("  Instagram Reels Automation (Netlify)")
    print("=" * 60 + "\n")

    validate_env()
    check_dependencies()
    test_token()  # run /me test once at start

    input_path = Path(input_file)
    if not input_path.exists():
        print(f"❌ Input file not found: {input_file}")
        return

    print(f"📁 Input: {input_path.name}")
    print(f"📝 Title: {VIDEO_TITLE}")
    print(f"⏱️  Clip length: {CLIP_SECONDS}s\n")

    print("STEP 1: Slicing video...")
    parts = slice_video(input_path, PARTS_DIR, segment_sec=CLIP_SECONDS)
    if not parts:
        print("❌ No clips created. Exiting.")
        return

    print(f"\nSTEP 2: Adding overlay to {len(parts)} clips...")
    final_paths: List[Path] = []

    for i, part_path in enumerate(parts, start=1):
        final_path = FINAL_DIR / f"final_{i:03d}.mp4"
        result = overlay_and_encode(
            part_path,
            final_path,
            title=VIDEO_TITLE,
            part_num=i,
            width=VIDEO_WIDTH,
            height=VIDEO_HEIGHT,
            pad_top=PAD_TOP,
            pad_bottom=PAD_BOTTOM,
            top_fontsize=TOP_FONTSIZE,
            bottom_fontsize=BOTTOM_FONTSIZE,
        )
        if result:
            static_file = STATIC_DIR / final_path.name
            static_file.write_bytes(final_path.read_bytes())
            final_paths.append(static_file)

        try:
            part_path.unlink()
        except Exception:
            pass

    if not final_paths:
        print("❌ No encoded clips. Exiting.")
        return

    print(f"\n✅ {len(final_paths)} clips ready for upload\n")

    # STEP 3: Netlify base URL
    public_base = NETLIFY_BASE
    print(f"STEP 3: Using Netlify base URL: {public_base}")

    print(f"\nSTEP 4: Uploading {len(final_paths)} clips to Instagram...\n")
    success = 0

    for i, clip_path in enumerate(final_paths, start=1):
        print(f"\n--- Clip {i}/{len(final_paths)} ---")
        # assuming files served at https://site.netlify.app/final_001.mp4
        public_url = f"{public_base}/{clip_path.name}"
        base = f"{VIDEO_TITLE} Part {i}"
        hashtags = "#anime #animereels #reels #edit #fyp"
        caption = f"{base} {hashtags}"

        creation_id = create_media_container(IG_USER_ID, ACCESS_TOKEN, public_url, caption)
        if not creation_id:
            print(f"⚠️ Skipping clip {i} (container failed)")
            continue

        print("⏳ Waiting 60s before publish...")
        time.sleep(60)

        result = publish_media(IG_USER_ID, ACCESS_TOKEN, creation_id)
        if result:
            success += 1
            print(f"🎉 Clip {i} posted successfully!")
        else:
            print(f"⚠️ Clip {i} failed to publish")

        if i < len(final_paths):
            print("⏳ Waiting 30s before next clip...")
            time.sleep(30)

    print("\n" + "=" * 60)
    print("✅ Upload complete!")
    print(f"   Successful: {success}/{len(final_paths)}")
    print("=" * 60 + "\n")

    print("🧹 Cleaning up (Netlify mode, nothing to stop)...")
    print("✅ Done.\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUsage: python run.py <input_video.mp4>\n")
        sys.exit(1)

    try:
        pipeline(sys.argv[1])
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    except Exception as e:
        print("\n❌ FATAL ERROR:", e)
        import traceback
        traceback.print_exc()
        sys.exit(1)
