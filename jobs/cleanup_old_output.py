"""
Cleanup Old Trend-Video Output

Deletes per-date output subfolders (output/videos/<date>, output/screenshots/<date>,
output/audio/<date>) older than RETENTION_DAYS (default 7) so the daily trend-video
pipeline's output doesn't pile up unbounded on disk. These three are the heavy,
purely-intermediate/output artifacts (screenshots + voiceover audio feed into the
final video; the video itself has already been uploaded to YouTube and emailed out
by the time its folder is a week old) — output/scripts (tiny JSON, a few MB total)
and the output/emailed and output/youtube_uploads tracking markers are left alone,
since those are small and some jobs use them to avoid reprocessing the same game.

Only subfolders exactly matching YYYY-MM-DD are touched — never any other file or
directory under output/, so an unexpected name is simply skipped rather than risking
deleting something unrelated.

Meant to run as the final step of scripts/run_daily_trend_video_pipeline.sh, once per
day after that day's video has already been rendered/uploaded/emailed. Safe to also
run by hand any time.

Usage:
    venv/bin/python jobs/cleanup_old_output.py [--days N] [--dry-run]
"""

import argparse
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path

OUTPUT_ROOT = Path(__file__).resolve().parent.parent / "output"
PRUNE_SUBDIRS = ("videos", "screenshots", "audio")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DEFAULT_RETENTION_DAYS = 7


def _dir_size(path):
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def run(retention_days=DEFAULT_RETENTION_DAYS, dry_run=False):
    cutoff = datetime.now().date() - timedelta(days=retention_days)
    total_freed = 0
    total_deleted = 0

    for sub in PRUNE_SUBDIRS:
        root = OUTPUT_ROOT / sub
        if not root.exists():
            continue
        for date_dir in sorted(root.iterdir()):
            if not date_dir.is_dir() or not DATE_RE.match(date_dir.name):
                continue
            try:
                folder_date = datetime.strptime(date_dir.name, "%Y-%m-%d").date()
            except ValueError:
                continue
            if folder_date >= cutoff:
                continue

            size = _dir_size(date_dir)
            total_freed += size
            total_deleted += 1
            action = "[DRY RUN] Would delete" if dry_run else "Deleting"
            print(f"{action} {date_dir.relative_to(OUTPUT_ROOT.parent)}/ ({size / 1e6:.1f} MB)")
            if not dry_run:
                shutil.rmtree(date_dir)

    verb = "Would free" if dry_run else "Freed"
    print(f"\n{verb} {total_freed / 1e6:.1f} MB across {total_deleted} folder(s) (retention: {retention_days} days, cutoff: {cutoff}).")
    return total_deleted, total_freed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=DEFAULT_RETENTION_DAYS, help="Retention window in days (default: 7)")
    parser.add_argument("--dry-run", action="store_true", help="List what would be deleted without deleting anything")
    args = parser.parse_args()
    run(retention_days=args.days, dry_run=args.dry_run)
