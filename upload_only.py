# upload_only.py

import os
import re
import sys
import time
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

import requests
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")
GRAPH_BASE = os.getenv("GRAPH_BASE", "https://graph.facebook.com/v24.0")
PORT = int(os.getenv("PORT", "8000"))

BASE_DIR = Path.cwd()
PUBLIC_DIR = BASE_DIR / "public"   # yahin final_*.mp4 hain
CLOUDFLARED_CMD = os.getenv("CLOUDFLARED_CMD", "cloudflared")


def start_fastapi_server(port: int = 8000) -> subprocess.Popen:
    app_py = BASE_DIR / "_temp_fastapi_upload_app.py"
    app_py.write_text(
        "from fastapi import FastAPI\n"
        "from fastapi.staticfiles import StaticFiles\n\n"
        "app = FastAPI()\n"
        "app.mount('/files', StaticFiles(directory='public'), name='files')\n"
    )
    cmd = [
        sys.executable, "-m", "uvicorn",
        "_temp_fastapi_upload_app:app",
        "--host", "0.0.0.0",
        "--port", str(port),
        "--log-level", "warning",
    ]
    print(f"Starting FastAPI upload server on port {port}...")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    time.sleep(3)
    print(f"  Server running at http://localhost:{port}")
    return proc


def start_cloudflared(port: int = 8000, timeout: int = 30) -> Optional[Tuple[subprocess.Popen, str]]:
    cmd = [CLOUDFLARED_CMD, "tunnel", "--url", f"http://localhost:{port}"]
    print("Starting cloudflared tunnel for upload...")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

    url = None
    start_time = time.time()
    pattern = re.compile(r"https?://[\w\-\.]+trycloudflare\.com")

    while time.time() - start_time < timeout:
        if proc.stdout is None:
            break
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                print("  cloudflared exited early.")
                break
            time.sleep(0.1)
            continue
        print("cloudflared:", line.strip())
        m = pattern.search(line)
        if m:
            url = m.group(0)
            break

    if not url:
        print("  Failed to get public URL from cloudflared.")
        return None
    print("  Public URL:", url)
    return proc, url


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

    files: List[Path] = sorted(PUBLIC_DIR.glob("final_*.mp4"))
    if not files:
        print("No final_*.mp4 found in public/ for upload.")
        sys.exit(0)

    print(f"Found {len(files)} clips to upload from public/")

    # start server + tunnel
    fastapi_proc = start_fastapi_server(PORT)
    cf = start_cloudflared(PORT, timeout=30)
    if not cf:
        print("Cloudflared tunnel failed; aborting uploads.")
        fastapi_proc.terminate()
        return
    cf_proc, public_base = cf

    success = 0
    for idx, f in enumerate(files, start=1):
        print(f"\n--- Clip {idx}/{len(files)} :: {f.name} ---")
        public_url = f"{public_base}/files/{f.name}"
        # Caption pattern: Title Part X ... (title .env se lo, ya file naam se)
        title = os.getenv("VIDEO_TITLE", "Video")
        base = f"{title} Part {idx}"
        hashtags = "#anime #animereels #reels #edit #fyp"
        caption = f"{base} {hashtags}"

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
            time.sleep(30)

    print(f"\nDone. Success: {success}/{len(files)}")

    # cleanup
    print("Stopping server and tunnel...")
    try:
        fastapi_proc.terminate()
    except Exception:
        pass
    try:
        cf_proc.terminate()
    except Exception:
        pass
    print("Cleanup complete.")


if __name__ == "__main__":
    main()
