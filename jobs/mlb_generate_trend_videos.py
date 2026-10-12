"""
MLB Trend Video Assembler

Step 3 of the trend-video pipeline (after mlb_generate_trend_video_scripts.py
and mlb_generate_trend_video_screenshots.py). For every script JSON that has
matching screenshots, synthesizes a spoken voiceover and renders a vertical
(1080x1920) video split into three equal scenes, each holding for one third
of the voiceover's length:

1. hero.png       — zoom-out Ken Burns effect (starts zoomed in, eases out
                     to the full trend card over the first 2.5s, then holds)
2. home_last5.png — home team's last-5-home-games table
3. away_last5.png — away team's last-5-away-games table

Scenes 2 and 3 slide in from the previous scene (ffmpeg's xfade transition).

Produces two videos per game — one for the standard "script" (gambling terms
allowed) and one for "script_tiktok" (sanitized) — since they're worded
differently and may end up on different platforms.

Requires:
- ffmpeg on PATH (`brew install ffmpeg`)
- TTS_ENGINE=piper (default, see below) — piper-tts (`pip install piper-tts`)
  plus a downloaded .onnx voice model. Runs fully offline, no API/network
  dependency at all. piper_voices/ is gitignored (models run ~100-200MB
  each) — fetch the default voice with:
    mkdir -p piper_voices && cd piper_voices
    curl -sL -o en_US-ryan-high.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/en_US-ryan-high.onnx"
    curl -sL -o en_US-ryan-high.onnx.json "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/en_US-ryan-high.onnx.json"
  Browse https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US for
  other voices.
- TTS_ENGINE=edge (the original engine, kept as a fallback option) —
  edge-tts (`pip install edge-tts`), free, uses Microsoft Edge's neural
  voices via an unofficial API. No API key, but that API started rejecting
  all requests with a 403 on 2026-10-12 with no fix available upstream —
  this is exactly the kind of outage risk piper's offline model avoids.

Usage:
    venv/bin/python jobs/mlb_generate_trend_videos.py [YYYY-MM-DD]

Output:
    output/audio/<date>/<game_id>.mp3          (voiceover, standard script)
    output/audio/<date>/<game_id>_tiktok.mp3    (voiceover, tiktok script)
    output/videos/<date>/<game_id>.mp4          (standard video)
    output/videos/<date>/<game_id>_tiktok.mp4   (tiktok video)
"""

import os
import sys
import json
import asyncio
import subprocess
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

SCRIPTS_ROOT = Path(__file__).resolve().parent.parent / "output" / "scripts"
SCREENSHOTS_ROOT = Path(__file__).resolve().parent.parent / "output" / "screenshots"
AUDIO_ROOT = Path(__file__).resolve().parent.parent / "output" / "audio"
VIDEOS_ROOT = Path(__file__).resolve().parent.parent / "output" / "videos"

# Which TTS engine to use — "piper" (offline, default since edge-tts's
# 2026-10-12 outage) or "edge" (the original, free but outage-prone).
TTS_ENGINE = os.getenv("TTS_ENGINE", "piper")

# --- edge-tts settings (only used when TTS_ENGINE=edge) ---
# "Reliable, Authority" — reads as a confident sports analyst. Swap via env
# var without touching code; run `edge-tts --list-voices` for the full list.
TTS_VOICE = os.getenv("TTS_VOICE", "en-US-ChristopherNeural")
# edge-tts's native prosody rate — speeds up the voice itself (not a
# post-process time-stretch), so pitch stays natural. "+0%" is the neutral
# speaking pace edge-tts defaults to; bump this to tighten up the pacing.
TTS_RATE = os.getenv("TTS_RATE", "+20%")

# --- piper settings (only used when TTS_ENGINE=piper) ---
# en_US-ryan-high picked after comparing several candidates by ear — see
# piper_voices/ for other downloaded models. length_scale is piper's speed
# control (smaller = faster; inverse of a plain multiplier) — 0.8333 =
# 1/1.2, matching edge-tts's previous "+20%" rate by ear.
PIPER_VOICE_PATH = os.getenv(
    "PIPER_VOICE_PATH",
    str(Path(__file__).resolve().parent.parent / "piper_voices" / "en_US-ryan-high.onnx"),
)
PIPER_LENGTH_SCALE = os.getenv("PIPER_LENGTH_SCALE", "0.8333")

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30
# End-of-zoom scale — 1.0 = no zoom, 1.3 = 30% zoomed in by the final frame.
ZOOM_TARGET = 1.3
# The zoom+pan "settle" plays out over this many seconds at the start of the
# video, then holds still for the rest of the (much longer) narration — a
# zoom spread over the full ~100s runtime is too gradual to read as motion.
EFFECT_SECONDS = 2.5
# How far the pan drifts in from, as a fraction of the (upscaled) frame's
# width/height — settles to 0 (centered) by the end of the effect window.
PAN_X_FRACTION = 0.025
PAN_Y_FRACTION = 0.02

# Transition between the 3 scenes. xfade's slide transitions "consume"
# SLIDE_DURATION seconds from each side of the cut, so each scene's own clip
# is rendered slightly longer than a plain 1/3 split to compensate — see
# render_multi_scene_video's per_scene calculation.
SLIDE_TRANSITION = "slideleft"
SLIDE_DURATION = 0.6


def load_games(date_str):
    date_dir = SCRIPTS_ROOT / date_str
    if not date_dir.exists():
        return []
    games = []
    for path in sorted(date_dir.glob("*.json")):
        with open(path) as f:
            data = json.load(f)
        if not data.get("matchup"):
            continue
        games.append(data)
    return games


async def _synthesize_edge(text, voice, rate, out_path):
    import edge_tts

    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(str(out_path))


def _synthesize_piper(text, out_path):
    # piper only writes wav directly; render to a temp .wav next to the
    # real destination, then transcode to .mp3 (matching what the rest of
    # the pipeline — ffprobe duration checks, ffmpeg muxing — expects) and
    # clean up the intermediate file.
    wav_path = out_path.with_suffix(".wav")
    subprocess.run(
        [sys.executable, "-m", "piper", "-m", PIPER_VOICE_PATH,
         "--length-scale", PIPER_LENGTH_SCALE, "-f", str(wav_path)],
        input=text, text=True, check=True, capture_output=True,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav_path), "-q:a", "2", str(out_path)],
        check=True, capture_output=True,
    )
    wav_path.unlink(missing_ok=True)


def synthesize_voiceover(text, out_path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if TTS_ENGINE == "piper":
        _synthesize_piper(text, out_path)
    else:
        asyncio.run(_synthesize_edge(text, TTS_VOICE, TTS_RATE, out_path))
    return out_path


def get_audio_duration(audio_path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def _zoom_out_filter(scene_frames):
    # Ken Burns "settle": upscale the still first so zoompan has sub-pixel
    # headroom to zoom out of without blockiness, then zoom+pan out over
    # EFFECT_SECONDS — starts zoomed in on ZOOM_TARGET and eases back to the
    # full screenshot (using zoompan's per-frame "on" counter, not its
    # self-referential "zoom" accumulator, since we need it to hold exactly
    # at 1.0 rather than keep creeping for the rest of the scene).
    effect_frames = max(min(int(EFFECT_SECONDS * FPS), scene_frames), 1)
    zoom_range = ZOOM_TARGET - 1.0
    zoom_expr = f"if(lte(on,{effect_frames}),{ZOOM_TARGET}-{zoom_range}*on/{effect_frames},1.0)"
    settle = f"(1-min(on/{effect_frames},1))"  # 1 -> 0 over the effect window, then stays 0
    x_expr = f"iw/2-(iw/zoom/2)+(iw*{PAN_X_FRACTION})*{settle}"
    y_expr = f"ih/2-(ih/zoom/2)+(ih*{PAN_Y_FRACTION})*{settle}"
    return (
        f"scale=8000:-1,"
        f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':"
        f"d={scene_frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={FPS}"
    )


def _static_filter(per_scene_duration):
    # Whole-panel shots (data tables) are a very different aspect ratio than
    # the vertical canvas — scale to fit width and letterbox top/bottom on
    # white (matches the site's background) rather than cropping, so the
    # full table stays readable instead of losing rows/columns off-frame.
    return (
        f"scale={VIDEO_WIDTH}:-1,"
        f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:0:(oh-ih)/2:color=white,"
        f"fps={FPS},trim=duration={per_scene_duration:.3f},setpts=PTS-STARTPTS"
    )


def render_multi_scene_video(scenes, audio_path, out_path, total_duration):
    """scenes: list of {"image": Path, "kind": "zoom_out" | "static"}, played
    back-to-back in order, each taking an equal share of total_duration, with
    an xfade slide transition between consecutive scenes.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = len(scenes)
    t = SLIDE_DURATION
    # Each scene is rendered a bit longer than a plain 1/3 split so that,
    # after the (n-1) transitions each "eat" t seconds of overlap, the final
    # concatenated output still lands exactly on total_duration.
    per_scene = (total_duration + (n - 1) * t) / n
    scene_frames = max(int(round(per_scene * FPS)), 1)

    inputs = []
    filter_parts = []
    for i, scene in enumerate(scenes):
        inputs += ["-loop", "1", "-i", str(scene["image"])]
        body = _zoom_out_filter(scene_frames) if scene["kind"] == "zoom_out" else _static_filter(per_scene)
        filter_parts.append(f"[{i}:v]{body}[v{i}]")

    xfade_parts = []
    chain = "v0"
    running_offset = per_scene - t
    for i in range(1, n):
        out_label = f"vx{i}"
        xfade_parts.append(
            f"[{chain}][v{i}]xfade=transition={SLIDE_TRANSITION}:duration={t}:offset={running_offset:.3f}[{out_label}]"
        )
        chain = out_label
        running_offset += per_scene - t

    filter_complex = ";".join(filter_parts + xfade_parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-i", str(audio_path),
        "-filter_complex", filter_complex,
        "-map", f"[{chain}]", "-map", f"{n}:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-t", f"{total_duration:.3f}",
        "-shortest",
        str(out_path),
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    return out_path


def build_variant(game, date_str, script_key, suffix):
    game_id = game["game_id"]

    # Idempotent: a rerun for a date that's already produced this exact
    # video (e.g. catching up other games in the same batch that failed
    # earlier) shouldn't re-synthesize audio and re-render it from scratch.
    video_path = VIDEOS_ROOT / date_str / f"{game_id}{suffix}.mp4"
    if video_path.exists():
        return video_path, None

    script_data = (game.get(script_key) or {})
    text = script_data.get("script")
    if not text:
        return None, f"no '{script_key}' text in script JSON"

    shot_dir = SCREENSHOTS_ROOT / date_str / game_id
    scenes = [
        {"image": shot_dir / "hero.png", "kind": "zoom_out"},
        {"image": shot_dir / "home_last5.png", "kind": "static"},
        {"image": shot_dir / "away_last5.png", "kind": "static"},
    ]
    missing = [str(s["image"]) for s in scenes if not s["image"].exists()]
    if missing:
        return None, f"missing screenshot(s) {missing} — run mlb_generate_trend_video_screenshots.py first"

    audio_path = AUDIO_ROOT / date_str / f"{game_id}{suffix}.mp3"
    synthesize_voiceover(text, audio_path)
    duration = get_audio_duration(audio_path)

    render_multi_scene_video(scenes, audio_path, video_path, duration)
    return video_path, None


def run(date_str=None):
    from datetime import datetime
    import pytz

    if not date_str:
        date_str = datetime.now(pytz.timezone("US/Eastern")).strftime("%Y-%m-%d")

    games = load_games(date_str)
    print(f"Found {len(games)} script(s) for {date_str}")
    if not games:
        return

    ok, failed = 0, 0
    for game in games:
        label = f"{game['matchup']['away_team']} @ {game['matchup']['home_team']}"

        for script_key, suffix, tag in (("script", "", "standard"), ("script_tiktok", "_tiktok", "tiktok")):
            try:
                video_path, err = build_variant(game, date_str, script_key, suffix)
                if err:
                    failed += 1
                    print(f"  [SKIP] {label} ({tag}): {err}")
                else:
                    ok += 1
                    print(f"  [OK] {label} ({tag}) -> {video_path}")
            except subprocess.CalledProcessError as e:
                failed += 1
                print(f"  [FAILED] {label} ({tag}): ffmpeg error: {e.stderr[-500:] if e.stderr else e}")
            except Exception as e:
                failed += 1
                print(f"  [FAILED] {label} ({tag}): {e}")

    print(f"\nDone. videos_generated={ok} failed={failed}")


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run(date_arg)
