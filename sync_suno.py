"""Weekly sync of the public @biology_tunes Suno profile into biologytunes_database_v2.json.

- Updates play/like counts and missing metadata for existing songs.
- Adds newly published songs (classification fields get defaults and
  `_needs_classification: true` so they can be tagged later).
- Never deletes songs, and never touches hand-made classification fields.
- Appends a snapshot of plays/likes to stats_history.json for the dashboard.

Suno has no official API. The script opens the profile in a headless browser
(so Cloudflare/cookies behave like a normal visit) and reads the same JSON
endpoint the page itself uses.
"""
import asyncio
import json
import sys
from datetime import datetime, timezone

from playwright.async_api import async_playwright

HANDLE = "biology_tunes"
DB_PATH = "biologytunes_database_v2.json"
HISTORY_PATH = "stats_history.json"
PROFILE_URL = f"https://suno.com/@{HANDLE}?page=songs"
API_URL = ("https://studio-api.prod.suno.com/api/profiles/" + HANDLE +
           "?page={page}&playlists_sort_by=created_at&clips_sort_by=created_at")
MAX_PAGES = 60


async def fetch_clips():
    clips = {}
    captured = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"))
        page = await context.new_page()

        async def on_response(resp):
            if "/api/profiles/" in resp.url and resp.ok:
                try:
                    captured.append(await resp.json())
                except Exception:
                    pass
        page.on("response", on_response)

        try:
            await page.goto(PROFILE_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(8000)

            # Page through the profile endpoint until it runs dry.
            for n in range(1, MAX_PAGES + 1):
                resp = await context.request.get(API_URL.format(page=n), timeout=30000)
                if not resp.ok:
                    print(f"API page {n}: HTTP {resp.status}")
                    break
                data = await resp.json()
                batch = data.get("clips") or []
                new = [c for c in batch if c.get("id") not in clips]
                for c in batch:
                    clips[c["id"]] = c
                print(f"API page {n}: {len(batch)} clips ({len(new)} new)")
                if not batch or not new:
                    break
        finally:
            await browser.close()

    # Fall back to whatever the page loaded on its own.
    for data in captured:
        for c in data.get("clips") or []:
            clips.setdefault(c["id"], c)

    return [c for c in clips.values()
            if c.get("is_public", True) and (c.get("handle") in (None, HANDLE))]


def model_of(c):
    v = c.get("major_model_version") or ""
    return v if v.startswith("v") else (f"v{v}" if v else None)


def new_song(c):
    meta = c.get("metadata") or {}
    sid = c["id"]
    return {
        "id": sid,
        "title": (c.get("title") or "").strip(),
        "status": c.get("status", "complete"),
        "play_count": 0,
        "upvote_count": 0,
        "created_at": c.get("created_at") or "",
        "audio_url": c.get("audio_url") or f"https://cdn1.suno.ai/{sid}.mp3",
        "image_url": c.get("image_large_url") or c.get("image_url"),
        "video_url": c.get("video_url"),
        "model_version": model_of(c),
        "model_name": c.get("model_name"),
        "duration": round(meta.get("duration") or 0),
        "tags": meta.get("tags") or "",
        "prompt": meta.get("prompt"),
        "type": meta.get("type", "gen"),
        "url": f"https://suno.com/song/{sid}",
        "language": "en",
        "version_group": None,
        "is_primary_version": True,
        "musical_genre": [],
        "primary_theme": "other",
        "secondary_themes": [],
        "is_biology": None,
        "humor_level": "none",
        "academic_level": "none",
        "full_lyrics": meta.get("prompt"),
        "caption": c.get("caption") or "",
        "display_tags": meta.get("tags") or "",
        "_needs_classification": True,
        "_sync_source": "weekly_profile_sync",
    }


def merge(db, clips):
    by_id = {s["id"]: s for s in db["songs"]}
    added = []
    for c in clips:
        s = by_id.get(c["id"])
        if s is None:
            s = new_song(c)
            db["songs"].append(s)
            by_id[s["id"]] = s
            added.append(s["title"])
        meta = c.get("metadata") or {}
        s["play_count"] = c.get("play_count") or s.get("play_count") or 0
        s["upvote_count"] = c.get("upvote_count") or s.get("upvote_count") or 0
        # Fill gaps only; never overwrite curated values.
        if not s.get("created_at") and c.get("created_at"):
            s["created_at"] = c["created_at"]
        if not s.get("duration") and meta.get("duration"):
            s["duration"] = round(meta["duration"])
        if not s.get("tags") and meta.get("tags"):
            s["tags"] = meta["tags"]
        if not s.get("model_version") and model_of(c):
            s["model_version"] = model_of(c)
        if not s.get("image_url") and (c.get("image_large_url") or c.get("image_url")):
            s["image_url"] = c.get("image_large_url") or c.get("image_url")
    return added


def snapshot(db, now):
    songs = db["songs"]
    return {
        "date": now[:10],
        "songs": len(songs),
        "plays": sum(s.get("play_count") or 0 for s in songs),
        "likes": sum(s.get("upvote_count") or 0 for s in songs),
        "per_song": {s["id"]: [s.get("play_count") or 0, s.get("upvote_count") or 0] for s in songs},
    }


def main():
    with open(DB_PATH, encoding="utf-8") as f:
        db = json.load(f)

    clips = asyncio.run(fetch_clips())
    print(f"Fetched {len(clips)} public clips")
    # Guard against a broken scrape wiping out counts.
    if len(clips) < 0.5 * len(db["songs"]):
        sys.exit(f"Only {len(clips)} clips fetched vs {len(db['songs'])} known; aborting without changes.")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    added = merge(db, clips)
    db["metadata"]["total_songs"] = len(db["songs"])
    db["metadata"]["last_synced"] = now
    if added:
        db["metadata"].setdefault("sync_notes", []).append(
            f"{now[:10]}: Weekly sync added {len(added)} songs: {', '.join(added)}")

    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    try:
        with open(HISTORY_PATH, encoding="utf-8") as f:
            history = json.load(f)
    except FileNotFoundError:
        history = {"snapshots": []}
    snap = snapshot(db, now)
    history["snapshots"] = [h for h in history["snapshots"] if h["date"] != snap["date"]] + [snap]
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Done: {len(db['songs'])} songs, {len(added)} new, {snap['plays']} plays, {snap['likes']} likes")


if __name__ == "__main__":
    main()
