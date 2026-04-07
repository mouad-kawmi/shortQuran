"""
Download Omar Hisham Al Arabi whole-surah recitations from his official channel.

This script scans the public video list of the official Omar Hisham Al Arabi
YouTube channel, tries to map videos to specific surahs, and downloads the
best whole-surah candidate for each supported chapter.

Usage:
    pip install yt-dlp
    python download_cfq_omar_hisham.py
    python download_cfq_omar_hisham.py 67 91 99
    python download_cfq_omar_hisham.py --list

Terms of use referenced by this project:
  - Credit the reciter (Omar Hisham Al Arabi)
  - Include in description: "Collected From: https://sites.google.com/view/copyrightfreequran"
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from main import fetch_auto_chapters, normalize_lookup_text

OUTPUT_DIR = Path(__file__).parent / "licensed-audio" / "cfq" / "omar-hisham"
CHANNEL_VIDEOS_URL = "https://www.youtube.com/@OmarHishamAlArabi/videos"
YT_DLP_CMD = [sys.executable, "-m", "yt_dlp"]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PREFERRED_VIDEO_IDS = {
    5: "zCq60_RN9Oo",
    44: "A9Qwm3Q4AnU",
    55: "onW92LviAwE",
    67: "1506LDptsdI",
    75: "VRNNUWq36Mw",
    76: "JRn8Xc41nUI",
    89: "_1y9c3Jvwhw",
    91: "RV2CkTctMzc",
    99: "bUdjMar2cLk",
    100: "xrl5rE4o32c",
}

IGNORE_TITLE_HINTS = (
    "dua",
    "ruqya",
    "ruqyah",
    "ayat",
    "ayatulkursi",
    "ayatulkursifull",
    "1hour",
    "1000",
    "x10",
    "x100",
    "shortsurahs",
    "juzzamma",
    "juzz",
    "quls",
    "laylatulqadr",
    "lailatulqadr",
)

COMBO_TITLE_HINTS = (
    "alfalaq",
    "annas",
    "alnaas",
    "fatiha",
    "baqarah",
    "yaseenarrahman",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download Omar Hisham Al Arabi audio files used by the project."
    )
    parser.add_argument(
        "chapters",
        metavar="CHAPTER",
        nargs="*",
        type=int,
        help="Optional chapter numbers to download (defaults to all supported chapters discovered on the channel).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List surah videos discovered on the channel and exit.",
    )
    parser.add_argument(
        "--list-json",
        action="store_true",
        help="Print discovered surah videos as JSON and exit.",
    )
    return parser.parse_args()


def check_yt_dlp() -> bool:
    try:
        subprocess.run(YT_DLP_CMD + ["--version"], capture_output=True, check=True, text=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def build_chapter_aliases() -> dict[int, dict[str, object]]:
    chapters = fetch_auto_chapters()
    catalog: dict[int, dict[str, object]] = {}
    for raw_chapter in chapters:
        chapter_number = int(raw_chapter.get("id") or 0)
        chapter_name = str(raw_chapter.get("name_simple") or "").strip()
        chapter_name_arabic = str(raw_chapter.get("name_arabic") or "").strip()
        if chapter_number <= 0 or not chapter_name:
            continue

        aliases = {
            normalize_lookup_text(chapter_name),
            normalize_lookup_text(chapter_name_arabic),
            normalize_lookup_text(chapter_name.replace("-", " ")),
            normalize_lookup_text(chapter_name.replace("'", "")),
            normalize_lookup_text(chapter_name.replace("`", "")),
        }

        lowered = chapter_name.lower()
        for prefix in ("al-", "ad-", "ar-", "as-", "ash-", "at-", "az-", "an-"):
            if lowered.startswith(prefix):
                stripped_aliases = (
                    normalize_lookup_text(chapter_name[len(prefix) :]),
                    normalize_lookup_text(chapter_name.replace(prefix, "", 1)),
                )
                for stripped_alias in stripped_aliases:
                    if len(stripped_alias) >= 4:
                        aliases.add(stripped_alias)

        catalog[chapter_number] = {
            "surah_name": chapter_name,
            "aliases": {alias for alias in aliases if alias},
        }
    return catalog


def load_channel_entries() -> list[dict[str, object]]:
    process = subprocess.run(
        YT_DLP_CMD + ["--flat-playlist", "--dump-single-json", CHANNEL_VIDEOS_URL],
        capture_output=True,
        check=True,
        text=True,
    )
    payload = json.loads(process.stdout)
    entries = payload.get("entries")
    return [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []


def title_should_be_ignored(normalized_title: str) -> bool:
    if any(hint in normalized_title for hint in IGNORE_TITLE_HINTS):
        return True
    # Exclude common multi-surah combinations where one chapter cannot safely
    # represent the whole audio file for showcase mode.
    if "ikhlas" in normalized_title and any(hint in normalized_title for hint in ("falaq", "naas", "nas")):
        return True
    if any(hint in normalized_title for hint in COMBO_TITLE_HINTS):
        return True
    return False


def score_channel_entry(
    *,
    chapter_number: int,
    matched_alias: str,
    entry_id: str,
    normalized_title: str,
    duration_seconds: float,
) -> int:
    score = len(matched_alias)
    has_surah_marker = "surah" in normalized_title or "sura" in normalized_title or "سورة" in normalized_title
    if has_surah_marker:
        score += 4
    elif PREFERRED_VIDEO_IDS.get(chapter_number) != entry_id:
        score -= 100
    if "omarhisham" in normalized_title:
        score += 4
    if duration_seconds >= 45:
        score += 1
    if duration_seconds > 4000:
        score -= 20
    if title_should_be_ignored(normalized_title):
        score -= 1000
    preferred_video_id = PREFERRED_VIDEO_IDS.get(chapter_number)
    if preferred_video_id and entry_id == preferred_video_id:
        score += 100
    return score


def discover_surah_videos(entries: list[dict[str, object]]) -> dict[int, dict[str, object]]:
    chapter_catalog = build_chapter_aliases()
    discovered: dict[int, dict[str, object]] = {}

    for entry in entries:
        entry_id = str(entry.get("id") or "").strip()
        raw_title = str(entry.get("title") or "").strip()
        normalized_title = normalize_lookup_text(raw_title)
        if not entry_id or not normalized_title or title_should_be_ignored(normalized_title):
            continue

        matched_chapters: list[tuple[int, str]] = []
        for chapter_number, chapter_info in chapter_catalog.items():
            aliases = chapter_info["aliases"]
            longest_alias = ""
            for alias in aliases:
                if alias and alias in normalized_title and len(alias) > len(longest_alias):
                    longest_alias = alias
            if longest_alias:
                matched_chapters.append((chapter_number, longest_alias))

        if len(matched_chapters) != 1:
            continue

        chapter_number, matched_alias = matched_chapters[0]
        duration_seconds = float(entry.get("duration") or 0.0)
        score = score_channel_entry(
            chapter_number=chapter_number,
            matched_alias=matched_alias,
            entry_id=entry_id,
            normalized_title=normalized_title,
            duration_seconds=duration_seconds,
        )
        if score <= 0:
            continue

        current = discovered.get(chapter_number)
        candidate = {
            "surah_name": chapter_catalog[chapter_number]["surah_name"],
            "video_id": entry_id,
            "title": raw_title,
            "duration_seconds": duration_seconds,
            "score": score,
        }
        if current is None or int(candidate["score"]) > int(current["score"]):
            discovered[chapter_number] = candidate

    return discovered


def download_audio(video_id: str, output_path: Path, surah_name: str) -> bool:
    if output_path.exists():
        print(f"  [SKIP] {output_path.name} already exists")
        return True

    url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"  [DOWNLOAD] {surah_name} -> {output_path.name}")
    print(f"    URL: {url}")

    try:
        subprocess.run(
            YT_DLP_CMD
            + [
                "--extract-audio",
                "--audio-format",
                "mp3",
                "--audio-quality",
                "0",
                "--output",
                str(output_path.with_suffix(".%(ext)s")),
                "--no-playlist",
                url,
            ],
            check=True,
        )
        if output_path.exists():
            print(f"  [OK] {output_path.name}")
            return True
        print(f"  [WARN] File not found after download: {output_path}")
        return False
    except subprocess.CalledProcessError as error:
        print(f"  [ERROR] Failed to download {surah_name}: {error}")
        return False


def print_discovered_videos(discovered_videos: dict[int, dict[str, object]]) -> None:
    print("Discovered whole-surah videos on Omar Hisham's official channel:")
    for chapter_number in sorted(discovered_videos):
        item = discovered_videos[chapter_number]
        duration_seconds = float(item["duration_seconds"])
        print(
            f"  {chapter_number:03d} | {item['surah_name']} | {item['video_id']} | "
            f"{int(round(duration_seconds))}s | {item['title']}"
        )


def discovered_videos_to_json_payload(discovered_videos: dict[int, dict[str, object]]) -> str:
    payload = {
        str(chapter_number): {
            "surah_name": str(item["surah_name"]),
            "video_id": str(item["video_id"]),
            "title": str(item["title"]),
            "duration_seconds": float(item["duration_seconds"]),
        }
        for chapter_number, item in sorted(discovered_videos.items())
    }
    return json.dumps(payload, ensure_ascii=False)


def main() -> None:
    args = parse_args()

    if not check_yt_dlp():
        print("ERROR: yt-dlp is not installed!")
        print("Install it with: pip install yt-dlp")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        channel_entries = load_channel_entries()
        discovered_videos = discover_surah_videos(channel_entries)
    except subprocess.CalledProcessError as error:
        print(f"ERROR: Failed to inspect Omar Hisham's channel: {error}")
        sys.exit(1)
    except json.JSONDecodeError as error:
        print(f"ERROR: Failed to parse Omar Hisham channel feed: {error}")
        sys.exit(1)

    if args.list_json:
        print(discovered_videos_to_json_payload(discovered_videos))
        return

    print("=" * 60)
    print("Omar Hisham Channel Audio Downloader")
    print("=" * 60)
    print()

    if args.list:
        print_discovered_videos(discovered_videos)
        print()
        print(f"Total supported surah videos: {len(discovered_videos)}")
        return

    requested_chapters = args.chapters or sorted(discovered_videos)
    unsupported_chapters = [chapter for chapter in requested_chapters if chapter not in discovered_videos]
    if unsupported_chapters:
        joined = ", ".join(str(chapter) for chapter in unsupported_chapters)
        print(f"ERROR: Unsupported chapter(s): {joined}")
        print(f"Supported chapters right now: {', '.join(f'{chapter:03d}' for chapter in sorted(discovered_videos))}")
        sys.exit(1)

    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Surahs to download: {len(requested_chapters)}")
    print()

    success_count = 0
    fail_count = 0

    for surah_number in requested_chapters:
        item = discovered_videos[surah_number]
        surah_name = str(item["surah_name"])
        video_id = str(item["video_id"])
        output_path = OUTPUT_DIR / f"{surah_number:03d}.mp3"
        print(f"Surah {surah_number} ({surah_name}):")
        if download_audio(video_id, output_path, surah_name):
            success_count += 1
        else:
            fail_count += 1
        print()

    print("=" * 60)
    print(f"Done! {success_count} downloaded, {fail_count} failed")
    print(f"Files saved to: {OUTPUT_DIR}")
    print()
    print("REMINDER - When using this audio, add to your description:")
    print("  Recitation credit: Omar Hisham Al Arabi")
    print("  Collected From: https://sites.google.com/view/copyrightfreequran")
    print("=" * 60)


if __name__ == "__main__":
    main()
