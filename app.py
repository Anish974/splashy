# # # #!/usr/bin/env python3
# # # """
# # # Instagram Reels Automation — Single-file Python Script (Debug Version)
# # # ----------------------------------------------------------------------
# # # Features:
# # # 1) Slice input video into N-second segments
# # # 2) Add cinematic text overlay (top title + bottom part number)
# # # 3) Add padding: top and bottom (black bars)
# # # 4) Start FastAPI static server for edited clips
# # # 5) Start Cloudflare Tunnel to expose server publicly
# # # 6) Upload clips to Instagram Reels via Graph API
# # # 7) Memory-efficient processing (one clip at a time)

# # # Requirements:
# # #     pip install fastapi uvicorn python-dotenv requests
# # #     apt-get install ffmpeg

# # # .env file (same folder):
# # #     ACCESS_TOKEN=IGAA...your_instagram_token
# # #     IG_USER_ID=17841473514094554
# # #     VIDEO_TITLE=Suzume
# # #     CLIP_SECONDS=30
# # #     PORT=8000
# # # """

# # # import os
# # # import re
# # # import sys
# # # import time
# # # import math
# # # import subprocess
# # # from pathlib import Path
# # # from typing import List, Optional, Tuple

# # # import requests
# # # from dotenv import load_dotenv

# # # # --- Load environment variables ---
# # # load_dotenv()

# # # # Required
# # # ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
# # # IG_USER_ID = os.getenv("IG_USER_ID")

# # # # Optional with defaults
# # # VIDEO_TITLE = os.getenv("VIDEO_TITLE", "Video")
# # # CLIP_SECONDS = int(os.getenv("CLIP_SECONDS", "30"))
# # # FONTFILE = os.getenv("FONTFILE", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
# # # PORT = int(os.getenv("PORT", "8000"))
# # # GRAPH_BASE = os.getenv("GRAPH_BASE", "https://graph.facebook.com/v24.0")
# # # TOP_FONTSIZE = int(os.getenv("TOP_FONTSIZE", "80"))
# # # BOTTOM_FONTSIZE = int(os.getenv("BOTTOM_FONTSIZE", "70"))
# # # VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", "1080"))
# # # VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", "1920"))
# # # PAD_TOP = int(os.getenv("PAD_TOP", "200"))
# # # PAD_BOTTOM = int(os.getenv("PAD_BOTTOM", "200"))

# # # # --- Directories ---
# # # BASE_DIR = Path.cwd()
# # # PARTS_DIR = BASE_DIR / "parts"
# # # FINAL_DIR = BASE_DIR / "final"
# # # STATIC_DIR = BASE_DIR / "public"

# # # for d in (PARTS_DIR, FINAL_DIR, STATIC_DIR):
# # #     d.mkdir(exist_ok=True)

# # # # -------------------------------------------------------------------
# # # # Utility / debug helpers
# # # # -------------------------------------------------------------------

# # # def check_dependencies():
# # #     """Check if required tools are installed."""
# # #     try:
# # #         subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
# # #     except Exception:
# # #         print("❌ ERROR: ffmpeg not found. Install with: apt-get install ffmpeg")
# # #         sys.exit(1)

# # #     try:
# # #         subprocess.run(["cloudflared", "--version"], capture_output=True, check=True)
# # #     except Exception:
# # #         print("⚠️ WARNING: cloudflared not found. You can still run local tests but not upload via public URL.")


# # # def validate_env():
# # #     """Validate required environment variables."""
# # #     print(f"DEBUG ACCESS_TOKEN prefix: {str(ACCESS_TOKEN)[:10] if ACCESS_TOKEN else 'None'}")
# # #     print(f"DEBUG IG_USER_ID: {IG_USER_ID}")

# # #     if not ACCESS_TOKEN:
# # #         print("❌ ERROR: ACCESS_TOKEN not set in .env")
# # #         sys.exit(1)

# # #     if not IG_USER_ID:
# # #         print("❌ ERROR: IG_USER_ID not set in .env")
# # #         sys.exit(1)

# # #     if not ACCESS_TOKEN.startswith("IGAA"):
# # #         print("⚠️ WARNING: ACCESS_TOKEN does not start with 'IGAA'. "
# # #               "Instagram media upload usually requires an IG user token.")


# # # def test_token():
# # #     """Quick self‑test: call /me with current token, print result."""
# # #     url = f"{GRAPH_BASE}/me"
# # #     params = {
# # #         "fields": "id,username",
# # #         "access_token": ACCESS_TOKEN,
# # #     }
# # #     print("\n=== TOKEN SELF-TEST: GET /me?fields=id,username ===")
# # #     print("Request URL:", url)
# # #     try:
# # #         r = requests.get(url, params=params, timeout=20)
# # #         print("Status:", r.status_code)
# # #         print("Response:", r.text)
# # #     except Exception as e:
# # #         print("❌ /me test failed:", e)
# # #     print("=== END SELF-TEST ===\n")


# # # # -------------------------------------------------------------------
# # # # FFmpeg helpers
# # # # -------------------------------------------------------------------

# # # def ffprobe_duration(path: Path) -> float:
# # #     cmd = [
# # #         "ffprobe", "-v", "error",
# # #         "-show_entries", "format=duration",
# # #         "-of", "default=noprint_wrappers=1:nokey=1",
# # #         str(path)
# # #     ]
# # #     try:
# # #         out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
# # #         return float(out)
# # #     except Exception as e:
# # #         print(f"❌ Error getting video duration: {e}")
# # #         return 0.0


# # # def slice_video(input_path: Path, out_dir: Path, segment_sec: int = 30) -> List[Path]:
# # #     duration = ffprobe_duration(input_path)
# # #     if duration == 0:
# # #         print("❌ Could not determine video duration")
# # #         return []

# # #     num_clips = math.ceil(duration / segment_sec)
# # #     parts: List[Path] = []

# # #     print("\n📹 Video Info:")
# # #     print(f"   Duration: {duration:.2f}s")
# # #     print(f"   Creating {num_clips} clips of {segment_sec}s each\n")

# # #     for i in range(num_clips):
# # #         start = i * segment_sec
# # #         out = out_dir / f"part_{i:03d}.mp4"
# # #         cmd = [
# # #             "ffmpeg", "-y",
# # #             "-ss", str(start),
# # #             "-i", str(input_path),
# # #             "-t", str(segment_sec),
# # #             "-c", "copy",
# # #             "-avoid_negative_ts", "make_zero",
# # #             str(out)
# # #         ]
# # #         print(f"✂️  Slicing clip {i+1}/{num_clips}...")
# # #         try:
# # #             subprocess.run(cmd, check=True, capture_output=True)
# # #             parts.append(out)
# # #             print(f"   ✅ Created: {out.name}")
# # #         except subprocess.CalledProcessError as e:
# # #             print(f"   ❌ Failed to slice clip {i+1}: {e.stderr.decode()}")
# # #     return parts


# # # def overlay_and_encode(
# # #     input_path: Path,
# # #     output_path: Path,
# # #     title: str,
# # #     part_num: int,
# # #     width: int = 1080,
# # #     height: int = 1920,
# # #     pad_top: int = 250,
# # #     pad_bottom: int = 250,
# # #     top_fontsize: int = 150,
# # #     bottom_fontsize: int = 70,
# # # ) -> Optional[Path]:
# # #     # Escape for FFmpeg
# # #     title_escaped = title.replace("'", r"\'").replace(":", r"\:")
# # #     part_text_escaped = f"Part {part_num}".replace(":", r"\:")
# # #     fontfile = FONTFILE.replace("\\", "/")

# # #     content_height = height - pad_top - pad_bottom

# # #     video_filter = (
# # #         # scale into content area respecting aspect ratio
# # #         f"scale="
# # #         f"w='if(gt(a,{width}/{content_height}),{width},-2)':"
# # #         f"h='if(gt(a,{width}/{content_height}),-2,{content_height})',"
# # #         # pad to full size, video centered between top/bottom bars
# # #         f"pad=width={width}:height={height}:"
# # #         f"x=(ow-iw)/2:"
# # #         f"y={pad_top}+(oh-{pad_top}-{pad_bottom}-ih)/2:color=black,"
# # #         # top title
# # #         f"drawtext=fontfile='{fontfile}':text='{title_escaped}':"
# # #         f"fontsize={top_fontsize}:fontcolor=white:x=(w-text_w)/2:y=80:"
# # #         f"box=1:boxcolor=black:boxborderw=30,"
# # #         # bottom part label
# # #         f"drawtext=fontfile='{fontfile}':text='{part_text_escaped}':"
# # #         f"fontsize={bottom_fontsize}:fontcolor=white:"
# # #         f"x=(w-text_w)/2:y=h-{300+bottom_fontsize}:"
# # #         f"box=1:boxcolor=black:boxborderw=30"
# # #     )

# # #     cmd = [
# # #         "ffmpeg", "-y",
# # #         "-i", str(input_path),
# # #         "-vf", video_filter,
# # #         "-c:v", "libx264",
# # #         "-preset", "medium",
# # #         "-crf", "23",
# # #         "-profile:v", "high",
# # #         "-level", "4.0",
# # #         "-pix_fmt", "yuv420p",
# # #         "-c:a", "aac",
# # #         "-b:a", "128k",
# # #         "-ar", "44100",
# # #         "-movflags", "+faststart",
# # #         str(output_path),
# # #     ]

# # #     print(f"🎬 Encoding clip {part_num} with overlay...")
# # #     try:
# # #         subprocess.run(cmd, check=True, capture_output=True)
# # #         print(f"   ✅ Encoded: {output_path.name}")
# # #         return output_path
# # #     except subprocess.CalledProcessError as e:
# # #         print(f"   ❌ Encoding failed: {e.stderr.decode()}")
# # #         return None

# # # # -------------------------------------------------------------------
# # # # Server helpers
# # # # -------------------------------------------------------------------

# # # def start_fastapi_server(port: int = 8000) -> subprocess.Popen:
# # #     app_py = BASE_DIR / "_temp_fastapi_app.py"
# # #     app_py.write_text(
# # #         "from fastapi import FastAPI\n"
# # #         "from fastapi.staticfiles import StaticFiles\n"
# # #         "import os\n\n"
# # #         "app = FastAPI()\n"
# # #         "app.mount('/files', StaticFiles(directory='public'), name='files')\n\n"
# # #         "@app.get('/')\n"
# # #         "async def root():\n"
# # #         "    return {'status': 'ok', 'message': 'Static file server running'}\n\n"
# # #         "@app.get('/health')\n"
# # #         "async def health():\n"
# # #         "    files = os.listdir('public')\n"
# # #         "    return {'status': 'healthy', 'files': files}\n"
# # #     )

# # #     cmd = [
# # #         sys.executable, "-m", "uvicorn",
# # #         "_temp_fastapi_app:app",
# # #         "--host", "0.0.0.0",
# # #         "--port", str(port),
# # #         "--log-level", "warning",
# # #     ]

# # #     proc = subprocess.Popen(
# # #         cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
# # #     )
# # #     print(f"🌐 FastAPI server starting on port {port}...")
# # #     time.sleep(3)
# # #     print(f"   ✅ Server running at http://localhost:{port}")
# # #     return proc


# # # def start_cloudflared(port: int = 8000, timeout: int = 30) -> Optional[Tuple[subprocess.Popen, str]]:
# # #     cmd = ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"]
# # #     print("☁️  Starting Cloudflare Tunnel...")
# # #     proc = subprocess.Popen(
# # #         cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
# # #     )

# # #     url = None
# # #     start_time = time.time()
# # #     pattern = re.compile(r"https://[\w\-]+\.trycloudflare\.com")

# # #     while time.time() - start_time < timeout:
# # #         if proc.stdout is None:
# # #             break
# # #         line = proc.stdout.readline()
# # #         if not line:
# # #             if proc.poll() is not None:
# # #                 print("   ❌ cloudflared process terminated")
# # #                 break
# # #             time.sleep(0.1)
# # #             continue

# # #         m = pattern.search(line)
# # #         if m:
# # #             url = m.group(0)
# # #             print(f"   ✅ Public URL: {url}")
# # #             return proc, url

# # #     print("   ❌ Failed to get public URL from cloudflared")
# # #     return None

# # # # -------------------------------------------------------------------
# # # # Instagram API helpers
# # # # -------------------------------------------------------------------

# # # def create_media_container(
# # #     ig_user_id: str,
# # #     access_token: str,
# # #     video_url: str,
# # #     caption: str = "",
# # # ) -> Optional[str]:
# # #     """Step 1: Create media container (REELS)."""
# # #     url = f"{GRAPH_BASE}/{ig_user_id}/media"
# # #     payload = {
# # #         "media_type": "REELS",
# # #         "video_url": video_url,
# # #         "caption": caption,
# # #         "access_token": access_token,
# # #     }

# # #     print("📤 Creating media container...")
# # #     print("   URL:", url)
# # #     print("   Payload (truncated token):", {**payload, "access_token": access_token[:12] + "..."})

# # #     try:
# # #         # use JSON body, clearer debugging
# # #         r = requests.post(url, json=payload, timeout=30)
# # #         print("   Status:", r.status_code)
# # #         print("   Response:", r.text)
# # #         r.raise_for_status()
# # #         data = r.json()
# # #         creation_id = data.get("id")
# # #         print("   ✅ Container id:", creation_id)
# # #         return creation_id
# # #     except requests.exceptions.RequestException as e:
# # #         print("   ❌ Failed to create container:", e)
# # #         return None


# # # def check_container_status(creation_id: str, access_token: str) -> str:
# # #     url = f"{GRAPH_BASE}/{creation_id}"
# # #     params = {"fields": "status_code", "access_token": access_token}
# # #     try:
# # #         r = requests.get(url, params=params, timeout=10)
# # #         r.raise_for_status()
# # #         return r.json().get("status_code", "UNKNOWN")
# # #     except Exception:
# # #         return "ERROR"


# # # def publish_media(
# # #     ig_user_id: str,
# # #     access_token: str,
# # #     creation_id: str,
# # #     max_attempts: int = 10,
# # #     wait_seconds: int = 30,
# # # ) -> Optional[dict]:
# # #     """Step 2: Publish container."""
# # #     publish_url = f"{GRAPH_BASE}/{ig_user_id}/media_publish"
# # #     payload = {"creation_id": creation_id, "access_token": access_token}

# # #     for attempt in range(1, max_attempts + 1):
# # #         print(f"📢 Publish attempt {attempt}/{max_attempts}...")
# # #         status = check_container_status(creation_id, access_token)
# # #         print("   Container status:", status)

# # #         if status == "FINISHED":
# # #             try:
# # #                 r = requests.post(publish_url, data=payload, timeout=30)
# # #                 print("   Publish status:", r.status_code)
# # #                 print("   Publish response:", r.text)
# # #                 if r.status_code == 200:
# # #                     return r.json()
# # #             except requests.exceptions.RequestException as e:
# # #                 print("   ❌ Publish error:", e)
# # #         elif status == "ERROR":
# # #             print("   ❌ Container has ERROR status, aborting publish.")
# # #             return None

# # #         wait = wait_seconds * attempt
# # #         print(f"   ⏳ Waiting {wait}s...")
# # #         time.sleep(wait)

# # #     print("   ❌ Failed to publish after all attempts")
# # #     return None

# # # # -------------------------------------------------------------------
# # # # Main pipeline
# # # # -------------------------------------------------------------------

# # # def pipeline(input_file: str):
# # #     print("\n" + "=" * 60)
# # #     print("  Instagram Reels Automation (Debug)")
# # #     print("=" * 60 + "\n")

# # #     validate_env()
# # #     check_dependencies()
# # #     test_token()  # run /me test once at start

# # #     input_path = Path(input_file)
# # #     if not input_path.exists():
# # #         print(f"❌ Input file not found: {input_file}")
# # #         return

# # #     print(f"📁 Input: {input_path.name}")
# # #     print(f"📝 Title: {VIDEO_TITLE}")
# # #     print(f"⏱️  Clip length: {CLIP_SECONDS}s\n")

# # #     print("STEP 1: Slicing video...")
# # #     parts = slice_video(input_path, PARTS_DIR, segment_sec=CLIP_SECONDS)
# # #     if not parts:
# # #         print("❌ No clips created. Exiting.")
# # #         return

# # #     print(f"\nSTEP 2: Adding overlay to {len(parts)} clips...")
# # #     final_paths: List[Path] = []

# # #     for i, part_path in enumerate(parts, start=1):
# # #         final_path = FINAL_DIR / f"final_{i:03d}.mp4"
# # #         result = overlay_and_encode(
# # #             part_path,
# # #             final_path,
# # #             title=VIDEO_TITLE,
# # #             part_num=i,
# # #             width=VIDEO_WIDTH,
# # #             height=VIDEO_HEIGHT,
# # #             pad_top=PAD_TOP,
# # #             pad_bottom=PAD_BOTTOM,
# # #             top_fontsize=TOP_FONTSIZE,
# # #             bottom_fontsize=BOTTOM_FONTSIZE,
# # #         )
# # #         if result:
# # #             static_file = STATIC_DIR / final_path.name
# # #             static_file.write_bytes(final_path.read_bytes())
# # #             final_paths.append(static_file)

# # #         # free space
# # #         try:
# # #             part_path.unlink()
# # #         except Exception:
# # #             pass

# # #     if not final_paths:
# # #         print("❌ No encoded clips. Exiting.")
# # #         return

# # #     print(f"\n✅ {len(final_paths)} clips ready for upload\n")

# # #     print("STEP 3: Starting web server...")
# # #     fastapi_proc = start_fastapi_server(PORT)

# # #     print("\nSTEP 4: Starting Cloudflare tunnel...")
# # #     cf = start_cloudflared(PORT, timeout=30)
# # #     if not cf:
# # #         print("❌ Could not create public tunnel, stopping before upload.")
# # #         fastapi_proc.terminate()
# # #         return

# # #     cf_proc, public_base = cf

# # #     print(f"\nSTEP 5: Uploading {len(final_paths)} clips to Instagram...\n")
# # #     success = 0

# # #     for i, clip_path in enumerate(final_paths, start=1):
# # #         print(f"\n--- Clip {i}/{len(final_paths)} ---")
# # #         public_url = f"{public_base}/files/{clip_path.name}"
# # #         caption = f"{VIDEO_TITLE} - Part {i} 🎬 #automation #reels"

# # #         creation_id = create_media_container(IG_USER_ID, ACCESS_TOKEN, public_url, caption)
# # #         if not creation_id:
# # #             print(f"⚠️ Skipping clip {i} (container failed)")
# # #             continue

# # #         print("⏳ Waiting 60s before publish...")
# # #         time.sleep(60)

# # #         result = publish_media(IG_USER_ID, ACCESS_TOKEN, creation_id)
# # #         if result:
# # #             success += 1
# # #             print(f"🎉 Clip {i} posted successfully!")
# # #         else:
# # #             print(f"⚠️ Clip {i} failed to publish")

# # #         if i < len(final_paths):
# # #             print("⏳ Waiting 30s before next clip...")
# # #             time.sleep(30)

# # #     print("\n" + "=" * 60)
# # #     print("✅ Upload complete!")
# # #     print(f"   Successful: {success}/{len(final_paths)}")
# # #     print("=" * 60 + "\n")

# # #     print("🧹 Cleaning up...")
# # #     fastapi_proc.terminate()
# # #     cf_proc.terminate()
# # #     print("✅ Done.\n")


# # # if __name__ == "__main__":
# # #     if len(sys.argv) < 2:
# # #         print("\nUsage: python insta_reels_automation_debug.py <input_video.mp4>\n")
# # #         sys.exit(1)

# # #     try:
# # #         pipeline(sys.argv[1])
# # #     except KeyboardInterrupt:
# # #         print("\nInterrupted by user.")
# # #     except Exception as e:
# # #         print("\n❌ FATAL ERROR:", e)
# # #         import traceback
# # #         traceback.print_exc()
# # #         sys.exit(1)




# # """
# # Insta Reels Automation — single-file Python script
# # -------------------------------------------------
# # What it does (all-automated, local-only, no S3):
# # 1) Slice an input video into N-second segments using ffmpeg
# # 2) Add text overlay to each segment (ffmpeg drawtext)
# # 3) Start a FastAPI static file server that serves the edited clips
# # 4) Start a Cloudflare Tunnel (cloudflared) to expose the server publicly
# #    (cloudflared produces a public URL like https://abcd.trycloudflare.com)
# # 5) For each clip, provide the public URL to Instagram Graph API:
# #    - POST /{ig_user_id}/media  (media_type=REELS, video_url=...)
# #    - wait/poll then POST /{ig_user_id}/media_publish (creation_id=...)

# # Prereqs (install before running):
# # - Python 3.10+
# # - ffmpeg (on PATH)
# # - cloudflared (on PATH) - https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/
# # - Instagram Business/Creator account + Facebook Page + Graph API setup
# #   (ACCESS_TOKEN must have instagram_content_publish and related scopes)

# # Python packages:
# #     pip install fastapi uvicorn python-dotenv requests

# # Usage:
# #     1) Create a .env file next to this script with the following vars:
# #        ACCESS_TOKEN=EAA...        # your long-lived IG token
# #        IG_USER_ID=178...          # your IG user id
# #        CLIP_SECONDS=30            # length in seconds for each clip
# #        FONTFILE=/path/to/font.ttf # optional, path to a ttf font for drawtext
# #        PORT=8000                  # port for local FastAPI server

# #     2) Run:
# #        python app.py input.mp4

# # Notes & limitations:
# # - Your machine must be online and reachable by cloudflared (it will open a tunnel).
# # - cloudflared returns a random trycloudflare domain unless you register/tunnel config; the script parses the generated URL.
# # - Keep cloudflared open while the uploads run. The script manages starting/stopping cloudflared for you.
# # - Instagram Graph API requires the video URL to be accessible by Instagram servers; ensure firewall allows outgoing traffic.
# # - Tokens expire; refresh as needed.

# # """

# # import os
# # import re
# # import sys
# # import time
# # import math
# # import shlex
# # import signal
# # import subprocess
# # from pathlib import Path
# # from typing import List, Optional
# # from dotenv import load_dotenv
# # import requests

# # # load env
# # load_dotenv()
# # ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
# # IG_USER_ID = os.getenv("IG_USER_ID")
# # CLIP_SECONDS = int(os.getenv("CLIP_SECONDS" , "30"))
# # FONTFILE = os.getenv("FONTFILE", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
# # PORT = int(os.getenv("PORT", "8000"))

# # GRAPH_BASE = os.getenv("GRAPH_BASE", "https://graph.facebook.com/v19.0")

# # # directories
# # BASE_DIR = Path.cwd()
# # PARTS_DIR = BASE_DIR / "parts"
# # FINAL_DIR = BASE_DIR / "final"
# # STATIC_DIR = BASE_DIR / "public"

# # for d in (PARTS_DIR, FINAL_DIR, STATIC_DIR):
# #     d.mkdir(exist_ok=True)

# # # --- utils: ffmpeg helpers ---

# # def ffprobe_duration(path: Path) -> float:
# #     cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
# #            "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
# #     out = subprocess.check_output(cmd).decode().strip()
# #     return float(out)


# # def slice_video(input_path: Path, out_dir: Path, segment_sec: int = 30) -> List[Path]:
# #     duration = ffprobe_duration(input_path)
# #     num = math.ceil(duration / segment_sec)
# #     parts = []
# #     print(f"Video duration: {duration:.2f}s -> creating {num} parts of up to {segment_sec}s each")
# #     for i in range(num):
# #         start = i * segment_sec
# #         out = out_dir / f"part_{i}.mp4"
# #         # use -ss + -t with copy for speed; re-encode later
# #         cmd = [
# #             "ffmpeg", "-y",
# #             "-ss", str(start), "-i", str(input_path),
# #             "-t", str(segment_sec),
# #             "-c", "copy",
# #             str(out)
# #         ]
# #         print("Running:", " ".join(shlex.quote(c) for c in cmd))
# #         subprocess.check_call(cmd)
# #         parts.append(out)
# #     return parts


# # def overlay_and_encode(input_path: Path, output_path: Path, text: str, width: int = 1080, height: int = 1920, fontsize: int = 48):
# #     # escape text for ffmpeg drawtext
# #     text_escaped = text.replace("%", "\\%").replace(":", "\\:")
# #     pos = "x=(w-text_w)/2:y=h-(text_h*2)"
# #     vf = (
# #         f"scale=w={width}:h={height}:force_original_aspect_ratio=decrease," \
# #         f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,drawtext=fontfile='{FONTFILE}':text='{text_escaped}':"
# #         f"fontcolor=white:fontsize={fontsize}:box=1:boxcolor=black@0.5:boxborderw=10:{pos}"
# #     )
# #     cmd = [
# #         "ffmpeg", "-y", "-i", str(input_path),
# #         "-vf", vf,
# #         "-c:v", "libx264", "-preset", "fast", "-profile:v", "high", "-level", "4.0",
# #         "-pix_fmt", "yuv420p",
# #         "-c:a", "aac", "-b:a", "128k",
# #         "-movflags", "+faststart",
# #         str(output_path)
# #     ]
# #     print("Encoding:", output_path.name)
# #     subprocess.check_call(cmd)
# #     return output_path

# # # --- start static file server (FastAPI) ---

# # def start_fastapi_server(port: int = 8000):
# #     """Starts a FastAPI static server in a subprocess using uvicorn."""
# #     # create a minimal app file on the fly
# #     app_py = BASE_DIR / "_temp_fastapi_app.py"
# #     app_py.write_text(f"""
# # from fastapi import FastAPI
# # from fastapi.staticfiles import StaticFiles
# # app = FastAPI()
# # app.mount('/', StaticFiles(directory='public', html=False), name='public')

# # # uvicorn will run this module
# # """)
# #     cmd = [sys.executable, "-m", "uvicorn", "_temp_fastapi_app:app", "--host", "0.0.0.0", "--port", str(port), "--log-level", "info"]
# #     print("Starting FastAPI server on port", port)
# #     proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
# #     # don't block; return process handle
# #     return proc

# # # --- cloudflared tunnel ---

# # CLOUDFLARED_CMD = os.getenv("CLOUDFLARED_CMD", "cloudflared")


# # def start_cloudflared(port: int = 8000, timeout: int = 20) -> Optional[subprocess.Popen]:
# #     """Start cloudflared and return the process and the public URL it exposes.
# #     This uses `cloudflared tunnel --url http://localhost:{port}` which prints a line with the public url.
# #     """
# #     cmd = [CLOUDFLARED_CMD, "tunnel", "--url", f"http://localhost:{port}"]
# #     print("Starting cloudflared tunnel...")
# #     proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
# #     url = None
# #     start = time.time()
# #     pattern = re.compile(r"https?://[\w\-\.]+trycloudflare\.com")
# #     # read lines until we find the url or timeout
# #     while True:
# #         if proc.stdout is None:
# #             break
# #         line = proc.stdout.readline()
# #         if not line:
# #             if proc.poll() is not None:
# #                 break
# #             time.sleep(0.1)
# #             if time.time() - start > timeout:
# #                 break
# #             continue
# #         print("cloudflared:", line.strip())
# #         m = pattern.search(line)
# #         if m:
# #             url = m.group(0)
# #             break
# #         if time.time() - start > timeout:
# #             break
# #     if url is None:
# #         print("Failed to get public URL from cloudflared output. Check cloudflared installation and network.")
# #         # still return proc so caller can inspect logs
# #         return proc
# #     print("Public URL:", url)
# #     return proc, url

# # # --- Instagram Graph API helpers ---

# # def create_media_container(ig_user_id: str, access_token: str, video_url: str, caption: str = "") -> str:
# #     url = f"{GRAPH_BASE}/{ig_user_id}/media"
# #     payload = {
# #         "media_type": "REELS",
# #         "video_url": video_url,
# #         "caption": caption,
# #         "access_token": access_token
# #     }
# #     r = requests.post(url, data=payload)
# #     try:
# #         r.raise_for_status()
# #     except Exception as e:
# #         print("create_media_container failed:", r.status_code, r.text)
# #         raise
# #     j = r.json()
# #     return j.get("id")


# # def publish_media(ig_user_id: str, access_token: str, creation_id: str, wait_seconds: int = 60, max_attempts: int = 6):
# #     publish_url = f"{GRAPH_BASE}/{ig_user_id}/media_publish"
# #     payload = {"creation_id": creation_id, "access_token": access_token}
# #     for attempt in range(max_attempts):
# #         print(f"Attempting publish (attempt {attempt+1}/{max_attempts})...")
# #         r = requests.post(publish_url, data=payload)
# #         if r.status_code == 200:
# #             print("Published successfully:", r.text)
# #             return r.json()
# #         else:
# #             # common cause: still processing; wait and retry
# #             print("publish returned:", r.status_code, r.text)
# #             sleep = wait_seconds * (1 + attempt)
# #             print(f"Waiting {sleep}s before retrying...")
# #             time.sleep(sleep)
# #     r.raise_for_status()
# #     return r.json()

# # # --- orchestration ---

# # def pipeline(input_file: str):
# #     if not ACCESS_TOKEN or not IG_USER_ID:
# #         print("ERROR: ACCESS_TOKEN and IG_USER_ID must be set in .env")
# #         return

# #     input_path = Path(input_file)
# #     if not input_path.exists():
# #         print("Input file not found:", input_file)
# #         return

# #     # 1) slice
# #     parts = slice_video(input_path, PARTS_DIR, segment_sec=CLIP_SECONDS)

# #     # 2) re-encode + overlay
# #     final_paths = []
# #     for i, p in enumerate(parts):
# #         final = FINAL_DIR / f"final_{i}.mp4"
# #         text = f"Clip {i+1}"
# #         overlay_and_encode(p, final, text=text)
# #         # copy to public folder for serving
# #         target = STATIC_DIR / final.name
# #         # overwrite
# #         target.write_bytes(final.read_bytes())
# #         final_paths.append(final)

# #     # 3) start fastapi server
# #     fastapi_proc = start_fastapi_server(port=PORT)
# #     time.sleep(2)

# #     # 4) start cloudflared and obtain url
# #     cf = start_cloudflared(port=PORT, timeout=20)
# #     if not cf:
# #         print("Cloudflared did not start correctly; exiting. Check installation and try again.")
# #         # cleanup
# #         fastapi_proc.terminate()
# #         return
# #     if isinstance(cf, tuple):
# #         cf_proc, public_base = cf
# #     else:
# #         # no url available
# #         cf_proc = cf
# #         public_base = None

# #     if public_base is None:
# #         print("Could not determine public URL. Dumping cloudflared logs (first 2000 chars):")
# #         if cf_proc and cf_proc.stdout:
# #             print(cf_proc.stdout.read(2000))
# #         fastapi_proc.terminate()
# #         if cf_proc:
# #             cf_proc.terminate()
# #         return

# #     # 5) for each final clip, publish to IG
# #     for i, final in enumerate(final_paths):
# #         public_path = f"{public_base}/{final.name}"
# #         caption = f"Auto clip {i+1}"
# #         print("Creating container for", public_path)
# #         try:
# #             creation_id = create_media_container(IG_USER_ID, ACCESS_TOKEN, public_path, caption=caption)
# #         except Exception as e:
# #             print("Failed to create media container for", public_path)
# #             continue
# #         # polite wait
# #         print("Waiting 30s before publish to give IG time to fetch/process")
# #         time.sleep(30)
# #         try:
# #             res = publish_media(IG_USER_ID, ACCESS_TOKEN, creation_id, wait_seconds=30, max_attempts=6)
# #             print("Publish response:", res)
# #         except Exception as e:
# #             print("Publish failed for", public_path, "error:", e)

# #     # cleanup: stop services
# #     print("Done. Cleaning up: terminating processes.")
# #     try:
# #         fastapi_proc.terminate()
# #     except Exception:
# #         pass
# #     try:
# #         cf_proc.terminate()
# #     except Exception:
# #         pass


# # if __name__ == '__main__':
# #     if len(sys.argv) < 2:
# #         print("Usage: python insta_reels_automation.py input.mp4")
# #         sys.exit(1)
# #     input_file = sys.argv[1]
# #     try:
# #         pipeline(input_file)
# #     except KeyboardInterrupt:
# #         print("Interrupted by user. Exiting.")
# #         sys.exit(0)

# #!/usr/bin/env python3
# """
# Instagram Reels Automation — Single-file Python Script (Debug Version)
# ----------------------------------------------------------------------
# Features:
# 1) Slice input video into N-second segments
# 2) Add cinematic text overlay (top title + bottom part number)
# 3) Add padding: top and bottom (black bars)
# 4) Start FastAPI static server for edited clips
# 5) Start Cloudflare Tunnel to expose server publicly
# 6) Upload clips to Instagram Reels via Graph API
# 7) Memory-efficient processing (one clip at a time)
# """

# import os
# import re
# import sys
# import time
# import math
# import shlex
# import subprocess
# from pathlib import Path
# from typing import List, Optional, Tuple

# import requests
# from dotenv import load_dotenv

# # --- Load environment variables ---
# load_dotenv()

# # Required
# ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
# IG_USER_ID = os.getenv("IG_USER_ID")

# # Optional with defaults
# VIDEO_TITLE = os.getenv("VIDEO_TITLE", "Video")
# CLIP_SECONDS = int(os.getenv("CLIP_SECONDS", "30"))
# FONTFILE = os.getenv("FONTFILE", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
# PORT = int(os.getenv("PORT", "8000"))
# GRAPH_BASE = os.getenv("GRAPH_BASE", "https://graph.facebook.com/v24.0")
# TOP_FONTSIZE = int(os.getenv("TOP_FONTSIZE", "90"))
# BOTTOM_FONTSIZE = int(os.getenv("BOTTOM_FONTSIZE", "80"))
# VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", "1080"))
# VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", "1920"))
# PAD_TOP = int(os.getenv("PAD_TOP", "200"))
# PAD_BOTTOM = int(os.getenv("PAD_BOTTOM", "200"))

# # --- Directories ---
# BASE_DIR = Path.cwd()
# PARTS_DIR = BASE_DIR / "parts"
# FINAL_DIR = BASE_DIR / "final"
# STATIC_DIR = BASE_DIR / "public"

# for d in (PARTS_DIR, FINAL_DIR, STATIC_DIR):
#     d.mkdir(exist_ok=True)

# # -------------------------------------------------------------------
# # Utility / debug helpers
# # -------------------------------------------------------------------

# def check_dependencies():
#     """Check if required tools are installed."""
#     try:
#         subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
#     except Exception:
#         print("❌ ERROR: ffmpeg not found. Install with: apt-get install ffmpeg")
#         sys.exit(1)

#     try:
#         subprocess.run(["cloudflared", "--version"], capture_output=True, check=True)
#     except Exception:
#         print("⚠️ WARNING: cloudflared not found. You can still run local tests but not upload via public URL.")

# def validate_env():
#     """Validate required environment variables."""
#     print(f"DEBUG ACCESS_TOKEN prefix: {str(ACCESS_TOKEN)[:10] if ACCESS_TOKEN else 'None'}")
#     print(f"DEBUG IG_USER_ID: {IG_USER_ID}")

#     if not ACCESS_TOKEN:
#         print("❌ ERROR: ACCESS_TOKEN not set in .env")
#         sys.exit(1)

#     if not IG_USER_ID:
#         print("❌ ERROR: IG_USER_ID not set in .env")
#         sys.exit(1)

# def test_token():
#     """Quick self‑test: call /me with current token, print result."""
#     url = f"{GRAPH_BASE}/me"
#     params = {
#         "fields": "id,username",
#         "access_token": ACCESS_TOKEN,
#     }
#     print("\n=== TOKEN SELF-TEST: GET /me?fields=id,username ===")
#     print("Request URL:", url)
#     try:
#         r = requests.get(url, params=params, timeout=20)
#         print("Status:", r.status_code)
#         print("Response:", r.text)
#     except Exception as e:
#         print("❌ /me test failed:", e)
#     print("=== END SELF-TEST ===\n")

# # -------------------------------------------------------------------
# # FFmpeg helpers
# # -------------------------------------------------------------------

# def ffprobe_duration(path: Path) -> float:
#     cmd = [
#         "ffprobe", "-v", "error",
#         "-show_entries", "format=duration",
#         "-of", "default=noprint_wrappers=1:nokey=1",
#         str(path)
#     ]
#     try:
#         out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
#         return float(out)
#     except Exception as e:
#         print(f"❌ Error getting video duration: {e}")
#         return 0.0

# def slice_video(input_path: Path, out_dir: Path, segment_sec: int = 30) -> List[Path]:
#     duration = ffprobe_duration(input_path)
#     if duration == 0:
#         print("❌ Could not determine video duration")
#         return []

#     num_clips = math.ceil(duration / segment_sec)
#     parts: List[Path] = []

#     print("\n📹 Video Info:")
#     print(f"   Duration: {duration:.2f}s")
#     print(f"   Creating {num_clips} clips of {segment_sec}s each\n")

#     for i in range(num_clips):
#         start = i * segment_sec
#         out = out_dir / f"part_{i:03d}.mp4"
#         cmd = [
#             "ffmpeg", "-y",
#             "-ss", str(start),
#             "-i", str(input_path),
#             "-t", str(segment_sec),
#             "-c", "copy",
#             "-avoid_negative_ts", "make_zero",
#             str(out)
#         ]
#         print(f"✂️  Slicing clip {i+1}/{num_clips}...")
#         try:
#             subprocess.run(cmd, check=True, capture_output=True)
#             parts.append(out)
#             print(f"   ✅ Created: {out.name}")
#         except subprocess.CalledProcessError as e:
#             print(f"   ❌ Failed to slice clip {i+1}: {e.stderr.decode()}")
#     return parts

# # --------- UPDATED OVERLAY FUNCTION (TITLE TOP, PART BOTTOM) ---------

# def overlay_and_encode(
#     input_path: Path,
#     output_path: Path,
#     title: str,
#     part_num: int,
#     width: int = VIDEO_WIDTH,
#     height: int = VIDEO_HEIGHT,
#     pad_top: int = PAD_TOP,
#     pad_bottom: int = PAD_BOTTOM,
#     top_fontsize: int = TOP_FONTSIZE,
#     bottom_fontsize: int = BOTTOM_FONTSIZE,
# ) -> Optional[Path]:
#     # Escape for FFmpeg
#     title_escaped = title.replace("'", r"\'").replace(":", r"\:")
#     part_text_escaped = f"Part {part_num}".replace("'", r"\'").replace(":", r"\:")
#     fontfile = FONTFILE.replace("\\", "/")

#     content_height = height - pad_top - pad_bottom

#     video_filter = (
#         # scale into content area respecting aspect ratio
#         f"scale="
#         f"w='if(gt(a,{width}/{content_height}),{width},-2)':"
#         f"h='if(gt(a,{width}/{content_height}),-2,{content_height})',"
#         # pad to full size, video centered between top/bottom bars
#         f"pad=width={width}:height={height}:"
#         f"x=(ow-iw)/2:"
#         f"y={pad_top}+(oh-{pad_top}-{pad_bottom}-ih)/2:color=black,"
#         # TOP TITLE (upper bar, center)
#         f"drawtext=fontfile='{fontfile}':text='{title_escaped}':"
#         f"fontsize={top_fontsize}:fontcolor=white:"
#         f"x=(w-text_w)/2:"
#         f"y={pad_top*1.8}-text_h/2:"
#         f"box=1:boxcolor=black@1:boxborderw=30,"
#         # BOTTOM PART LABEL (lower bar, center)
#         f"drawtext=fontfile='{fontfile}':text='{part_text_escaped}':"
#         f"fontsize={bottom_fontsize}:fontcolor=white:"
#         f"x=(w-text_w)/2:"
#         f"y=h-{pad_bottom*1.8}-text_h/2:"
#         f"box=1:boxcolor=black@1:boxborderw=30"
#     )

#     cmd = [
#         "ffmpeg", "-y",
#         "-i", str(input_path),
#         "-vf", video_filter,
#         "-c:v", "libx264",
#         "-preset", "medium",
#         "-crf", "23",
#         "-profile:v", "high",
#         "-level", "4.0",
#         "-pix_fmt", "yuv420p",
#         "-c:a", "aac",
#         "-b:a", "128k",
#         "-ar", "44100",
#         "-movflags", "+faststart",
#         str(output_path),
#     ]

#     print(f"🎬 Encoding clip {part_num} with overlay...")
#     try:
#         subprocess.run(cmd, check=True, capture_output=True)
#         print(f"   ✅ Encoded: {output_path.name}")
#         return output_path
#     except subprocess.CalledProcessError as e:
#         print(f"   ❌ Encoding failed: {e.stderr.decode()}")
#         return None

# # -------------------------------------------------------------------
# # Server helpers
# # -------------------------------------------------------------------

# def start_fastapi_server(port: int = 8000) -> subprocess.Popen:
#     app_py = BASE_DIR / "_temp_fastapi_app.py"
#     app_py.write_text(
#         "from fastapi import FastAPI\n"
#         "from fastapi.staticfiles import StaticFiles\n"
#         "import os\n\n"
#         "app = FastAPI()\n"
#         "app.mount('/files', StaticFiles(directory='public'), name='files')\n\n"
#         "@app.get('/')\n"
#         "async def root():\n"
#         "    return {'status': 'ok', 'message': 'Static file server running'}\n\n"
#         "@app.get('/health')\n"
#         "async def health():\n"
#         "    files = os.listdir('public')\n"
#         "    return {'status': 'healthy', 'files': files}\n"
#     )

#     cmd = [
#         sys.executable, "-m", "uvicorn",
#         "_temp_fastapi_app:app",
#         "--host", "0.0.0.0",
#         "--port", str(port),
#         "--log-level", "warning",
#     ]

#     proc = subprocess.Popen(
#         cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
#     )
#     print(f"🌐 FastAPI server starting on port {port}...")
#     time.sleep(3)
#     print(f"   ✅ Server running at http://localhost:{port}")
#     return proc

# def start_cloudflared(port: int = 8000, timeout: int = 30) -> Optional[Tuple[subprocess.Popen, str]]:
#     cmd = ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"]
#     print("☁️  Starting Cloudflare Tunnel...")
#     proc = subprocess.Popen(
#         cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
#     )

#     url = None
#     start_time = time.time()
#     pattern = re.compile(r"https://[\w\-]+\.trycloudflare\.com")

#     while time.time() - start_time < timeout:
#         if proc.stdout is None:
#             break
#         line = proc.stdout.readline()
#         if not line:
#             if proc.poll() is not None:
#                 print("   ❌ cloudflared process terminated")
#                 break
#             time.sleep(0.1)
#             continue

#         m = pattern.search(line)
#         if m:
#             url = m.group(0)
#             print(f"   ✅ Public URL: {url}")
#             return proc, url

#     print("   ❌ Failed to get public URL from cloudflared")
#     return None

# # -------------------------------------------------------------------
# # Instagram API helpers
# # -------------------------------------------------------------------

# def create_media_container(
#     ig_user_id: str,
#     access_token: str,
#     video_url: str,
#     caption: str = "",
# ) -> Optional[str]:
#     """Step 1: Create media container (REELS)."""
#     url = f"{GRAPH_BASE}/{ig_user_id}/media"
#     payload = {
#         "media_type": "REELS",
#         "video_url": video_url,
#         "caption": caption,
#         "access_token": access_token,
#     }

#     print("📤 Creating media container...")
#     print("   URL:", url)
#     print("   Caption:", caption)

#     try:
#         r = requests.post(url, json=payload, timeout=30)
#         print("   Status:", r.status_code)
#         print("   Response:", r.text)
#         r.raise_for_status()
#         data = r.json()
#         creation_id = data.get("id")
#         print("   ✅ Container id:", creation_id)
#         return creation_id
#     except requests.exceptions.RequestException as e:
#         print("   ❌ Failed to create container:", e)
#         return None

# def check_container_status(creation_id: str, access_token: str) -> str:
#     url = f"{GRAPH_BASE}/{creation_id}"
#     params = {"fields": "status_code", "access_token": access_token}
#     try:
#         r = requests.get(url, params=params, timeout=10)
#         r.raise_for_status()
#         return r.json().get("status_code", "UNKNOWN")
#     except Exception:
#         return "ERROR"

# def publish_media(
#     ig_user_id: str,
#     access_token: str,
#     creation_id: str,
#     max_attempts: int = 10,
#     wait_seconds: int = 30,
# ) -> Optional[dict]:
#     """Step 2: Publish container."""
#     publish_url = f"{GRAPH_BASE}/{ig_user_id}/media_publish"
#     payload = {"creation_id": creation_id, "access_token": access_token}

#     for attempt in range(1, max_attempts + 1):
#         print(f"📢 Publish attempt {attempt}/{max_attempts}...")
#         status = check_container_status(creation_id, access_token)
#         print("   Container status:", status)

#         if status == "FINISHED":
#             try:
#                 r = requests.post(publish_url, data=payload, timeout=30)
#                 print("   Publish status:", r.status_code)
#                 print("   Publish response:", r.text)
#                 if r.status_code == 200:
#                     return r.json()
#             except requests.exceptions.RequestException as e:
#                 print("   ❌ Publish error:", e)
#         elif status == "ERROR":
#             print("   ❌ Container has ERROR status, aborting publish.")
#             return None

#         wait = wait_seconds * attempt
#         print(f"   ⏳ Waiting {wait}s...")
#         time.sleep(wait)

#     print("   ❌ Failed to publish after all attempts")
#     return None

# # -------------------------------------------------------------------
# # Main pipeline
# # -------------------------------------------------------------------

# def pipeline(input_file: str):
#     print("\n" + "=" * 60)
#     print("  Instagram Reels Automation (Debug)")
#     print("=" * 60 + "\n")

#     validate_env()
#     check_dependencies()
#     test_token()  # run /me test once at start

#     input_path = Path(input_file)
#     if not input_path.exists():
#         print(f"❌ Input file not found: {input_file}")
#         return

#     print(f"📁 Input: {input_path.name}")
#     print(f"📝 Title: {VIDEO_TITLE}")
#     print(f"⏱️  Clip length: {CLIP_SECONDS}s\n")

#     print("STEP 1: Slicing video...")
#     parts = slice_video(input_path, PARTS_DIR, segment_sec=CLIP_SECONDS)
#     if not parts:
#         print("❌ No clips created. Exiting.")
#         return

#     print(f"\nSTEP 2: Adding overlay to {len(parts)} clips...")
#     final_paths: List[Path] = []

#     for i, part_path in enumerate(parts, start=1):
#         final_path = FINAL_DIR / f"final_{i:03d}.mp4"
#         result = overlay_and_encode(
#             part_path,
#             final_path,
#             title=VIDEO_TITLE,
#             part_num=i,
#             width=VIDEO_WIDTH,
#             height=VIDEO_HEIGHT,
#             pad_top=PAD_TOP,
#             pad_bottom=PAD_BOTTOM,
#             top_fontsize=TOP_FONTSIZE,
#             bottom_fontsize=BOTTOM_FONTSIZE,
#         )
#         if result:
#             static_file = STATIC_DIR / final_path.name
#             static_file.write_bytes(final_path.read_bytes())
#             final_paths.append(static_file)

#         try:
#             part_path.unlink()
#         except Exception:
#             pass

#     if not final_paths:
#         print("❌ No encoded clips. Exiting.")
#         return

#     print(f"\n✅ {len(final_paths)} clips ready for upload\n")

#     print("STEP 3: Starting web server...")
#     fastapi_proc = start_fastapi_server(PORT)

#     print("\nSTEP 4: Starting Cloudflare tunnel...")
#     cf = start_cloudflared(PORT, timeout=30)
#     if not cf:
#         print("❌ Could not create public tunnel, stopping before upload.")
#         fastapi_proc.terminate()
#         return

#     cf_proc, public_base = cf

#     print(f"\nSTEP 5: Uploading {len(final_paths)} clips to Instagram...\n")
#     success = 0

#     for i, clip_path in enumerate(final_paths, start=1):
#         print(f"\n--- Clip {i}/{len(final_paths)} ---")
#         public_url = f"{public_base}/files/{clip_path.name}"
#         base = f"{VIDEO_TITLE} Part {i}"
#         hashtags = "#anime #animereels #reels #edit #fyp"
#         caption = f"{base} {hashtags}"

#         creation_id = create_media_container(IG_USER_ID, ACCESS_TOKEN, public_url, caption)
#         if not creation_id:
#             print(f"⚠️ Skipping clip {i} (container failed)")
#             continue

#         print("⏳ Waiting 60s before publish...")
#         time.sleep(60)

#         result = publish_media(IG_USER_ID, ACCESS_TOKEN, creation_id)
#         if result:
#             success += 1
#             print(f"🎉 Clip {i} posted successfully!")
#         else:
#             print(f"⚠️ Clip {i} failed to publish")

#         if i < len(final_paths):
#             print("⏳ Waiting 30s before next clip...")
#             time.sleep(30)

#     print("\n" + "=" * 60)
#     print("✅ Upload complete!")
#     print(f"   Successful: {success}/{len(final_paths)}")
#     print("=" * 60 + "\n")

#     print("🧹 Cleaning up...")
#     fastapi_proc.terminate()
#     cf_proc.terminate()
#     print("✅ Done.\n")

# if __name__ == "__main__":
#     if len(sys.argv) < 2:
#         print("\nUsage: python app.py <input_video.mp4>\n")
#         sys.exit(1)

#     try:
#         pipeline(sys.argv[1])
#     except KeyboardInterrupt:
#         print("\nInterrupted by user.")
#     except Exception as e:
#         print("\n❌ FATAL ERROR:", e)
#         import traceback
#         traceback.print_exc()
#         sys.exit(1)





"""
Instagram Reels Automation — Single-file Python Script (Debug Version)
----------------------------------------------------------------------
Features:
1) Slice input video into N-second segments
2) Add cinematic text overlay (top title + bottom part number)
3) Add padding: top and bottom (black bars)
4) Start FastAPI static server for edited clips
5) Start Cloudflare Tunnel to expose server publicly
6) Upload clips to Instagram Reels via Graph API
7) Memory-efficient processing (one clip at a time)
"""

import os
import re
import sys
import time
import math
import shlex
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

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
PORT = int(os.getenv("PORT", "8000"))
GRAPH_BASE = os.getenv("GRAPH_BASE", "https://graph.facebook.com/v24.0")
TOP_FONTSIZE = int(os.getenv("TOP_FONTSIZE", "90"))
BOTTOM_FONTSIZE = int(os.getenv("BOTTOM_FONTSIZE", "80"))
VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", "1080"))
VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", "1920"))
PAD_TOP = int(os.getenv("PAD_TOP", "200"))
PAD_BOTTOM = int(os.getenv("PAD_BOTTOM", "200"))
EPISODE_NUMBER = int(os.getenv("EPISODE_NUMBER", "1"))  # NEW

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

    try:
        subprocess.run(["cloudflared", "--version"], capture_output=True, check=True)
    except Exception:
        print("⚠️ WARNING: cloudflared not found. You can still run local tests but not upload via public URL.")

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

# --------- UPDATED OVERLAY FUNCTION (TITLE TOP, E# P# BOTTOM) ---------

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
    part_label = f"E{EPISODE_NUMBER} P{part_num}"     # E1 P1, E1 P2, ...
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
# Server helpers
# -------------------------------------------------------------------

def start_fastapi_server(port: int = 8000) -> subprocess.Popen:
    app_py = BASE_DIR / "_temp_fastapi_app.py"
    app_py.write_text(
        "from fastapi import FastAPI\n"
        "from fastapi.staticfiles import StaticFiles\n"
        "import os\n\n"
        "app = FastAPI()\n"
        "app.mount('/files', StaticFiles(directory='public'), name='files')\n\n"
        "@app.get('/')\n"
        "async def root():\n"
        "    return {'status': 'ok', 'message': 'Static file server running'}\n\n"
        "@app.get('/health')\n"
        "async def health():\n"
        "    files = os.listdir('public')\n"
        "    return {'status': 'healthy', 'files': files}\n"
    )

    cmd = [
        sys.executable, "-m", "uvicorn",
        "_temp_fastapi_app:app",
        "--host", "0.0.0.0",
        "--port", str(port),
        "--log-level", "warning",
    ]

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    print(f"🌐 FastAPI server starting on port {port}...")
    time.sleep(3)
    print(f"   ✅ Server running at http://localhost:{port}")
    return proc

def start_cloudflared(port: int = 8000, timeout: int = 30) -> Optional[Tuple[subprocess.Popen, str]]:
    cmd = ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"]
    print("☁️  Starting Cloudflare Tunnel...")
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
    )

    url = None
    start_time = time.time()
    pattern = re.compile(r"https://[\w\-]+\.trycloudflare\.com")

    while time.time() - start_time < timeout:
        if proc.stdout is None:
            break
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                print("   ❌ cloudflared process terminated")
                break
            time.sleep(0.1)
            continue

        m = pattern.search(line)
        if m:
            url = m.group(0)
            print(f"   ✅ Public URL: {url}")
            return proc, url

    print("   ❌ Failed to get public URL from cloudflared")
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
        r = requests.post(url, json=payload, timeout=30)
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
        r = requests.get(url, params=params, timeout=10)
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
                r = requests.post(publish_url, data=payload, timeout=30)
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
    print("  Instagram Reels Automation (Debug)")
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

    print("STEP 3: Starting web server...")
    fastapi_proc = start_fastapi_server(PORT)

    print("\nSTEP 4: Starting Cloudflare tunnel...")
    cf = start_cloudflared(PORT, timeout=30)
    if not cf:
        print("❌ Could not create public tunnel, stopping before upload.")
        fastapi_proc.terminate()
        return

    cf_proc, public_base = cf

    print(f"\nSTEP 5: Uploading {len(final_paths)} clips to Instagram...\n")
    success = 0

    for i, clip_path in enumerate(final_paths, start=1):
        print(f"\n--- Clip {i}/{len(final_paths)} ---")
        public_url = f"{public_base}/files/{clip_path.name}"
        base = f"{VIDEO_TITLE} Part {i}"
        hashtags = "#anime #animereels #reels #edit #fyp"
        caption = f"{base} {hashtags}"

        creation_id = create_media_container(IG_USER_ID, ACCESS_TOKEN, public_url, caption)
        if not creation_id:
            print(f"⚠️ Skipping clip {i} (container failed)")
            continue

        print("⏳ Waiting 60s before publish...")
        time.sleep(20)

        result = publish_media(IG_USER_ID, ACCESS_TOKEN, creation_id)
        if result:
            success += 1
            print(f"🎉 Clip {i} posted successfully!")
        else:
            print(f"⚠️ Clip {i} failed to publish")

        if i < len(final_paths):
            print("⏳ Waiting 30s before next clip...")
            time.sleep(5)

    print("\n" + "=" * 60)
    print("✅ Upload complete!")
    print(f"   Successful: {success}/{len(final_paths)}")
    print("=" * 60 + "\n")

    print("🧹 Cleaning up...")
    fastapi_proc.terminate()
    cf_proc.terminate()
    print("✅ Done.\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUsage: python app.py <input_video.mp4>\n")
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
