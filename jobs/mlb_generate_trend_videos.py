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

The first INTRO_BADGE_SECONDS (2s) also burn in an away-team/"VS"/home-team
badge — team-colored bars (api/utils/team_colors.py) across the vertical
middle of the frame — so the matchup is identifiable without having to add
it by hand in TikTok's/Instagram's own cover editor after uploading.

Produces two videos per game — one for the standard "script" (gambling terms
allowed) and one for "script_tiktok" (sanitized) — since they're worded
differently and may end up on different platforms.

Requires:
- ffmpeg on PATH (`brew install ffmpeg`)
- TTS_ENGINE=edge (default, see below) — edge-tts (`pip install edge-tts`,
  >=7.3.0 — earlier versions 403 against Microsoft's current token scheme,
  see below), free, uses Microsoft Edge's neural voices via an unofficial
  API. No API key needed, but because it's unofficial/reverse-engineered,
  it's prone to breaking whenever Microsoft changes something server-side —
  it 403'd outright from 2026-10-12 until upstream shipped a fix (Sec-MS-GEC
  v2 token support, edge-tts 7.3.0, released 2026-10-13); as of 2026-10-30
  it's working again, but the project's own issue tracker shows this is a
  recurring pattern, not a one-off. synthesize_voiceover() below handles
  this by catching ANY edge-tts failure and automatically re-synthesizing
  that voiceover with piper instead — no manual TTS_ENGINE flip needed when
  edge has a bad day; piper is the automatic backup, not something you have
  to remember to switch to.
- piper-tts (`pip install piper-tts`) plus a downloaded .onnx voice model —
  required regardless of TTS_ENGINE, since it's always the fallback when
  TTS_ENGINE=edge, and used directly when TTS_ENGINE=piper. Runs fully
  offline, no API/network dependency at all. piper_voices/ is gitignored
  (models run ~100-200MB each) — fetch the default voice with:
    mkdir -p piper_voices && cd piper_voices
    curl -sL -o en_US-ryan-high.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/en_US-ryan-high.onnx"
    curl -sL -o en_US-ryan-high.onnx.json "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/en_US-ryan-high.onnx.json"
  Browse https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US for
  other voices.
- Set TTS_ENGINE=piper to skip edge-tts entirely (fully offline, no network
  dependency at all) — e.g. if edge-tts is in one of its down spells for an
  extended stretch and you'd rather not pay the per-voiceover fallback delay.

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

from shared_utils import convert_team_name
from api.utils.team_colors import get_team_colors

SCRIPTS_ROOT = Path(__file__).resolve().parent.parent / "output" / "scripts"
SCREENSHOTS_ROOT = Path(__file__).resolve().parent.parent / "output" / "screenshots"
AUDIO_ROOT = Path(__file__).resolve().parent.parent / "output" / "audio"
VIDEOS_ROOT = Path(__file__).resolve().parent.parent / "output" / "videos"

# Which TTS engine to use — "edge" (default: Microsoft Edge's neural voices,
# free, better-sounding than piper — see synthesize_voiceover, which
# automatically falls back to piper on any edge-tts failure, so this stays
# the default despite edge-tts's unofficial/reverse-engineered API being
# prone to breaking when Microsoft changes something server-side, as it did
# 2026-10-12 and again in mid-October; piper's offline model is the backup,
# not the primary) or "piper" (skip edge entirely, offline-only).
TTS_ENGINE = os.getenv("TTS_ENGINE", "edge")

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

# --- intro team/VS badge (first INTRO_BADGE_SECONDS of every video) ---
# Rendered as a PNG via Pillow and composited in with ffmpeg's "overlay"
# filter, rather than ffmpeg's own "drawtext"/"drawbox" filters — this
# machine's Homebrew ffmpeg build has no freetype support (confirmed via
# `ffmpeg -filters`/a direct run: "No such filter: 'drawtext'"), so drawtext
# isn't actually available here regardless of filter syntax. Pillow sidesteps
# that entirely and gives pixel-level control (anti-aliased text, proper
# centering via textbbox) that drawtext's own layout primitives don't.
#
# A fixed system font rather than anything bundled in the repo — fine since
# this whole pipeline is already tied to this one Mac (local dev server,
# launchd schedule, etc.), same assumption the rest of the jobs make.
INTRO_BADGE_FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
INTRO_BADGE_SECONDS = 2
INTRO_BADGE_BAR_HEIGHT = 110      # px, each of the two team bars
INTRO_BADGE_BAR_MARGIN_X = 40     # px, left/right inset from the video edges
INTRO_BADGE_FONT_SIZE = 40
INTRO_BADGE_VS_SIZE = (130, 70)   # px, (width, height) of the center VS badge
INTRO_BADGE_VS_FONT_SIZE = 34
INTRO_BADGE_VS_BG = "black"
INTRO_BADGE_VS_FG = "white"
# A white outline around each bar/the VS badge so the boundary between them
# stays visible even when two teams share (or nearly share) a primary color
# — e.g. the Blackhawks and Bruins are both black — which would otherwise
# merge the away/home bars and the VS badge into one indistinguishable block.
INTRO_BADGE_BORDER_COLOR = "white"
INTRO_BADGE_BORDER_WIDTH = 4


def _badge_layout():
    """Pixel geometry shared by the PNG renderer and (if ever needed again)
    anything else that wants to know where the badge sits on the frame."""
    mid_y = VIDEO_HEIGHT // 2
    bar_w = VIDEO_WIDTH - 2 * INTRO_BADGE_BAR_MARGIN_X
    away_y0 = mid_y - INTRO_BADGE_BAR_HEIGHT
    home_y0 = mid_y
    vs_w, vs_h = INTRO_BADGE_VS_SIZE
    vs_x0 = (VIDEO_WIDTH - vs_w) // 2
    vs_y0 = mid_y - vs_h // 2
    return bar_w, away_y0, home_y0, vs_x0, vs_y0, vs_w, vs_h


def render_badge_png(sport, away_team, home_team, out_path):
    """Render the away-team/VS/home-team badge to a transparent PNG at
    out_path — team-colored bars stacked across the vertical middle of the
    frame (api/utils/team_colors.py; sports without curated colors —
    currently NCAAF/NCAAB — get that module's neutral slate/white fallback).
    """
    from PIL import Image, ImageDraw, ImageFont

    away_colors = get_team_colors(sport, convert_team_name(away_team))
    home_colors = get_team_colors(sport, convert_team_name(home_team))
    bar_w, away_y0, home_y0, vs_x0, vs_y0, vs_w, vs_h = _badge_layout()

    img = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(INTRO_BADGE_FONT, INTRO_BADGE_FONT_SIZE)
    vs_font = ImageFont.truetype(INTRO_BADGE_FONT, INTRO_BADGE_VS_FONT_SIZE)

    def centered_text(text, font, color, box_x0, box_y0, box_w, box_h):
        # textbbox's own (left, top) offset isn't (0, 0) for most fonts —
        # subtract it too, or "centered" text drifts off-center by a few px.
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        x = box_x0 + (box_w - (right - left)) / 2 - left
        y = box_y0 + (box_h - (bottom - top)) / 2 - top
        draw.text((x, y), text, font=font, fill=color)

    draw.rectangle(
        [INTRO_BADGE_BAR_MARGIN_X, away_y0, INTRO_BADGE_BAR_MARGIN_X + bar_w, away_y0 + INTRO_BADGE_BAR_HEIGHT],
        fill=away_colors["primary"], outline=INTRO_BADGE_BORDER_COLOR, width=INTRO_BADGE_BORDER_WIDTH,
    )
    draw.rectangle(
        [INTRO_BADGE_BAR_MARGIN_X, home_y0, INTRO_BADGE_BAR_MARGIN_X + bar_w, home_y0 + INTRO_BADGE_BAR_HEIGHT],
        fill=home_colors["primary"], outline=INTRO_BADGE_BORDER_COLOR, width=INTRO_BADGE_BORDER_WIDTH,
    )
    draw.rectangle(
        [vs_x0, vs_y0, vs_x0 + vs_w, vs_y0 + vs_h],
        fill=INTRO_BADGE_VS_BG, outline=INTRO_BADGE_BORDER_COLOR, width=INTRO_BADGE_BORDER_WIDTH,
    )

    centered_text(away_team.upper(), font, away_colors["secondary"], INTRO_BADGE_BAR_MARGIN_X, away_y0, bar_w, INTRO_BADGE_BAR_HEIGHT)
    centered_text(home_team.upper(), font, home_colors["secondary"], INTRO_BADGE_BAR_MARGIN_X, home_y0, bar_w, INTRO_BADGE_BAR_HEIGHT)
    centered_text("VS", vs_font, INTRO_BADGE_VS_FG, vs_x0, vs_y0, vs_w, vs_h)

    img.save(out_path)
    return out_path


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
        return out_path

    # TTS_ENGINE == "edge" (default): try the better-sounding neural voice
    # first, but never let an edge-tts outage (unofficial API, breaks
    # whenever Microsoft changes something server-side — see TTS_ENGINE's
    # comment) take the whole daily pipeline down. Fall back to piper
    # automatically and keep going rather than failing the video.
    try:
        asyncio.run(_synthesize_edge(text, TTS_VOICE, TTS_RATE, out_path))
    except Exception as e:
        print(f"  [TTS] edge-tts failed ({e}); falling back to piper for this voiceover.")
        _synthesize_piper(text, out_path)
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


def render_multi_scene_video(scenes, audio_path, out_path, total_duration, badge=None):
    """scenes: list of {"image": Path, "kind": "zoom_out" | "static"}, played
    back-to-back in order, each taking an equal share of total_duration, with
    an xfade slide transition between consecutive scenes.

    badge: optional (sport, away_team, home_team) tuple — when given, burns
    in the intro team/VS badge (see intro_badge_filter) over the first
    INTRO_BADGE_SECONDS of the final concatenated output.
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

    badge_parts = []
    badge_png = None
    audio_input_index = n
    if badge:
        sport, away_team, home_team = badge
        badge_png = out_path.with_name(f".badge_{out_path.stem}.png")
        render_badge_png(sport, away_team, home_team, badge_png)
        badge_input_index = n
        audio_input_index = n + 1
        inputs += ["-loop", "1", "-i", str(badge_png)]
        badge_parts.append(
            f"[{chain}][{badge_input_index}:v]overlay=0:0:"
            f"enable='between(t\\,0\\,{INTRO_BADGE_SECONDS})'[vbadge]"
        )
        chain = "vbadge"

    filter_complex = ";".join(filter_parts + xfade_parts + badge_parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-i", str(audio_path),
        "-filter_complex", filter_complex,
        "-map", f"[{chain}]", "-map", f"{audio_input_index}:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-t", f"{total_duration:.3f}",
        "-shortest",
        str(out_path),
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    finally:
        if badge_png is not None:
            badge_png.unlink(missing_ok=True)
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

    matchup = game["matchup"]
    # Falls back to "mlb" for older script JSONs written before "sport" was
    # stored in the payload, matching the same fallback used elsewhere
    # (e.g. mlb_generate_trend_video_screenshots.py's capture_game).
    badge = (game.get("sport", "mlb"), matchup["away_team"], matchup["home_team"])
    render_multi_scene_video(scenes, audio_path, video_path, duration, badge=badge)
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
