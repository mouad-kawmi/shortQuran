"""
Download Mahmud Huzaifa's Copyright Free Quran (CFQ) audio from YouTube.

Usage:
    pip install yt-dlp
    python download_cfq_mahmud_huzaifa.py

Terms of use (from https://sites.google.com/view/copyrightfreequran):
  - Credit the reciter (Mahmud Huzaifa) in your video
  - Include in description: "Collected From: https://sites.google.com/view/copyrightfreequran"
  - Monetisation is allowed if you follow these rules
"""

import subprocess
import sys
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "licensed-audio" / "cfq" / "mahmud-huzaifa"

# YouTube video IDs found on the Mahmud Huzaifa page of copyrightfreequran
# Channel: Truth of Ummah
VIDEOS = {
    # surah_number: (youtube_video_id, surah_name)
    67: ("SyfyqXvU_oA", "Al-Mulk"),
    78: ("cKwkTMQNRUY", "An-Naba"),
    79: ("4o-BVSAXaFM", "An-Naziat"),
    56: ("ChWWftSw5dY", "Al-Waqiah"),
    72: ("IBdNfyOuhv8", "Al-Jinn"),
    69: ("oTpHC1pFYE4", "Al-Haaqqa"),
    75: ("ZMpw8XUTq8w", "Al-Qiyamah"),
    73: ("oW0NXAcj-Pc", "Al-Muzammil"),
    # Additional videos found on the page - may be other surahs or duplicates
    # Uncomment if needed:
    # 0: ("jaO9YiRJXyU", "Unknown1"),
    # 0: ("PytW77qyYHk", "Unknown2"),
    # 0: ("ljrNPuyniww", "Unknown3"),
    # 0: ("FY5J62cDShw", "Unknown4"),
    # 0: ("n34hT8H67Fc", "Unknown5"),
}


YT_DLP_CMD = [sys.executable, "-m", "yt_dlp"]


def check_yt_dlp():
    """Check if yt-dlp is installed."""
    try:
        subprocess.run(YT_DLP_CMD + ["--version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def download_audio(video_id: str, output_path: Path, surah_name: str) -> bool:
    """Download audio from a YouTube video as MP3."""
    if output_path.exists():
        print(f"  [SKIP] {output_path.name} already exists")
        return True

    url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"  [DOWNLOAD] {surah_name} -> {output_path.name}")
    print(f"    URL: {url}")

    try:
        subprocess.run(
            YT_DLP_CMD + [
                "--extract-audio",
                "--audio-format", "mp3",
                "--audio-quality", "0",  # best quality
                "--output", str(output_path.with_suffix(".%(ext)s")),
                "--no-playlist",
                url,
            ],
            check=True,
        )
        if output_path.exists():
            print(f"  [OK] {output_path.name}")
            return True
        else:
            print(f"  [WARN] File not found after download: {output_path}")
            return False
    except subprocess.CalledProcessError as e:
        print(f"  [ERROR] Failed to download {surah_name}: {e}")
        print(f"    The video might be private or unavailable.")
        return False


def main():
    print("=" * 60)
    print("CFQ Mahmud Huzaifa Audio Downloader")
    print("=" * 60)
    print()

    if not check_yt_dlp():
        print("ERROR: yt-dlp is not installed!")
        print("Install it with: pip install yt-dlp")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Surahs to download: {len(VIDEOS)}")
    print()

    success_count = 0
    fail_count = 0

    for surah_number, (video_id, surah_name) in sorted(VIDEOS.items()):
        # Name files like: 067.mp3, 078.mp3, etc. (matching omar-hisham pattern)
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
    print('  Reciter: Mahmud Huzaifa')
    print('  Collected From: https://sites.google.com/view/copyrightfreequran')
    print("=" * 60)


if __name__ == "__main__":
    main()
