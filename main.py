from __future__ import annotations

import argparse
import html
import hashlib
import http.server
import json
import math
import mimetypes
import os
import random
import re
import secrets
import shutil
import struct
import subprocess
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone, tzinfo
from functools import lru_cache
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, unquote, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
IS_LANDSCAPE = False
IS_WHOLE_SURAH = False
DEFAULT_FPS = 30
DEFAULT_TARGET_DURATION = 60.0
AUTO_MIN_DURATION = 45.0
AUTO_DURATION_OVERSHOOT_TOLERANCE = 4.0
QURAN_API_BASE_URL = "https://api.quran.com/api/v4"
PUBLIC_TRANSLATION_API_BASE_URL = "https://api.alquran.cloud/v1"
DEFAULT_TRANSLATION_ID = 131
DEFAULT_PUBLIC_TRANSLATION_EDITION = "en.sahih"
DEFAULT_AUTO_COUNT = 1
DEFAULT_AUTO_STYLE_PRESET = "cinematic"
DEFAULT_AUTO_CHAPTER_MIN = 67
LOCAL_BACKGROUND_LIBRARY_DIRNAME = "backgroundPhoto"
BISMILLAH_ARABIC = "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ"
BISMILLAH_TRANSLATION = "In the name of Allah, the Most Compassionate, the Most Merciful."
AUTO_HISTORY_FILE = ".cache/auto_history.json"
AUTO_STYLE_PRESETS = (
    "cinematic",
)
AUTO_TITLE_HOOKS = {
    "calm": "تلاوة هادئة تريح الأعصاب",
    "reflect": "تلاوة خاشعة تريح القلب",
    "heart": "آيات تلامس القلوب",
    "reminder": "تلاوة هادئة تشرح الصدر",
}
AUTO_TITLE_TEMPLATES = {
    "hook_reference": "{reciter_name} | سورة {chapter_name} | تلاوة خاشعة تريح القلب | {hook}",
    "hook_reciter": "{reciter_name} | سورة {chapter_name} | {hook} | تلاوة خاشعة",
    "surah_focus": "{reciter_name} | سورة {chapter_name} كاملة | تلاوة خاشعة",
    "ayah_focus": "{reciter_name} | سورة {chapter_name} | تلاوة خاشعة تريح القلب",
}

ARABIC_RECITER_NAMES = {
    "Mishari Rashid al-`Afasy": "مشاري العفاسي",
    "Abdul Basit Abdus Samad": "عبد الباسط عبد الصمد",
    "Mahmoud Khalil Al-Husary": "محمود خليل الحصري",
    "Mohamed Siddiq El-Minshawi": "محمد صديق المنشاوي",
    "Abdurrahman As-Sudais": "عبد الرحمن السديس",
    "Saud Al-Shuraim": "سعود الشريم",
    "Maher Al Muaiqly": "ماهر المعيقلي",
    "Yasser Al-Dosari": "ياسر الدوسري",
    "Ahmed ibn Ali al-Ajamy": "أحمد بن علي العجمي",
    "Abu Bakr Ash-Shatri": "أبو بكر الشاطري",
    "Ali Al-Hudhaify": "علي الحذيفي",
    "Abdullah Awad Al-Juhany": "عبد الله الجهني",
}
AUTO_DESCRIPTION_HOOKS = {
    "pause": "Pause for a minute and listen to these verses with focus.",
    "calm": "A calm Quran recitation for quiet reflection.",
    "heart": "A short reminder to soften the heart and reset the mind.",
    "reflect": "Verses worth revisiting when you need perspective.",
}
AUTO_DESCRIPTION_TEMPLATES = {
    "meaning_first": "{hook_line}\n\nSurah: {chapter_name}\nAyat: {verse_reference}\nReciter: {reciter_name}\n\nMeaning:\n{translation_excerpt}\n\n{cta}",
    "reciter_first": "{hook_line}\n\nListen to {chapter_name} ({verse_reference}) recited by {reciter_name}.\n\nMeaning:\n{translation_excerpt}\n\n{cta}",
    "short_reflection": "{hook_line}\n\n{chapter_name} | {verse_reference}\nMeaning:\n{translation_excerpt}\n\n{cta}",
}
AUTO_CTA_LINES = {
    "share": "If this recitation brings you peace, share it with someone you care about.",
    "save": "Save this short so you can return to it when you need a quiet reminder.",
    "repeat": "Listen again, reflect slowly, and keep the Quran close to your day.",
    "comment": "If this verse touched you, leave a short reminder in the comments.",
}
AUTO_MIN_TARGET_SECONDS = 45.0
AUTO_MAX_TARGET_SECONDS = 90.0
AUTO_MIN_VERSES_COUNT = 70
LONG_SURAH_IDS = {
    2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
    15, 16, 17, 18, 19, 20, 21, 22, 23, 25, 26, 27, 28,
    33, 36, 37, 38, 39, 40, 43, 55, 56,
}
AUTO_MAX_WHOLE_SURAH_DURATION = 60.0
AUTO_STATIC_WHOLE_SURAH_MAX_QURAN_VERSES = 12
AUTO_MANY_SEGMENTS_THRESHOLD = 20
AUTO_RECENT_CHAPTER_WINDOW = 6
AUTO_RECENT_RECITER_WINDOW = 3
AUTO_RECENT_BACKGROUND_WINDOW = 6
AUTO_RECENT_STYLE_WINDOW = 2
AUTO_RECENT_TITLE_WINDOW = 3
AUTO_RECENT_METADATA_WINDOW = 4
AUTO_RECENT_SHOWCASE_START_WINDOW = 4
AUTO_DESCRIPTION_EXCERPT_CHARS = 220
DEFAULT_YOUTUBE_AUTO_SCHEDULE_PRESET = "ma_mena_prime"
DEFAULT_YOUTUBE_AUTO_SCHEDULE_TIMEZONE = "Africa/Casablanca"
DEFAULT_YOUTUBE_AUTO_SCHEDULE_BUFFER_MINUTES = 30
YOUTUBE_AUTO_SCHEDULE_PRESETS = {
    "ma_mena_prime": ("12:30", "18:30", "21:30"),
    "ma_mena_late": ("13:00", "19:30", "22:30"),
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
LOCAL_AUDIO_EXTENSIONS = (".mp3", ".m4a", ".ogg", ".wav", ".flac")
DEFAULT_CACHE_DIR = ".cache/downloads"
DEFAULT_DOWNLOAD_EXTENSIONS = {
    "audio": ".mp3",
    "background": ".mp4",
    "font": ".ttf",
}
CONTENT_TYPE_EXTENSIONS = {
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mp4": ".m4a",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "font/ttf": ".ttf",
    "font/otf": ".otf",
    "application/x-font-ttf": ".ttf",
    "application/x-font-otf": ".otf",
    "application/octet-stream": "",
}
VERSES_AUDIO_BASE_URL = "https://everyayah.com/data"
PROJECT_DIR = Path(__file__).resolve().parent
PROJECT_ARABIC_FONT_FILENAMES = (
    "quran_font.ttf",
    "alaem.ttf",
)
DEFAULT_ARABIC_FONT_URL = "https://raw.githubusercontent.com/googlefonts/noto-fonts/main/hinted/ttf/NotoSansArabic/NotoSansArabic-Regular.ttf"
DEFAULT_LATIN_FONT_URL = "https://raw.githubusercontent.com/googlefonts/noto-fonts/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf"
DEFAULT_FONT_URL_FALLBACKS = {
    "https://raw.githubusercontent.com/google/fonts/main/ofl/notosansarabic/NotoSansArabic-Regular.ttf": (
        DEFAULT_ARABIC_FONT_URL,
        "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansArabic/NotoSansArabic-Regular.ttf",
    ),
    DEFAULT_ARABIC_FONT_URL: (
        DEFAULT_ARABIC_FONT_URL,
        "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansArabic/NotoSansArabic-Regular.ttf",
    ),
    DEFAULT_LATIN_FONT_URL: (
        DEFAULT_LATIN_FONT_URL,
        "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf",
    ),
}
PEXELS_API_BASE_URL = "https://api.pexels.com/videos"
DEFAULT_PEXELS_API_KEY_FILE = ".secrets/pexels-api-key.txt"
PEXELS_NATURE_QUERIES = ("nature", "river mountains", "forest", "ocean waves", "rain forest", "sky clouds", "sunrise", "waterfall", "desert", "green nature")
SHOWCASE_STYLE = "showcase"
DEFAULT_BACKGROUND_URL = "https://upload.wikimedia.org/wikipedia/commons/6/65/Scenic_landscape.jpg"
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
DEFAULT_YOUTUBE_PRIVACY_STATUS = "private"
DEFAULT_YOUTUBE_CATEGORY_ID = "27"
DEFAULT_YOUTUBE_DEFAULT_LANGUAGE = "en"
DEFAULT_YOUTUBE_CLIENT_SECRETS_FILE = ".secrets/youtube-client-secret.json"
DEFAULT_YOUTUBE_TOKEN_FILE = ".secrets/youtube-token.json"
FACEBOOK_GRAPH_API_BASE_URL = "https://graph.facebook.com"
DEFAULT_FACEBOOK_API_VERSION = "v24.0"
DEFAULT_FACEBOOK_PAGE_CONFIG_FILE = ".secrets/facebook-page-config.json"
DEFAULT_FACEBOOK_VIDEO_STATE = "DRAFT"
FACEBOOK_VIDEO_STATE_CHOICES = (
    "PUBLISHED",
    "DRAFT",
)
FACEBOOK_STATUS_POLL_SECONDS = 10
FACEBOOK_STATUS_MAX_POLLS = 18
TIKTOK_OAUTH_AUTHORIZE_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_OAUTH_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_CREATOR_INFO_URL = "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"
TIKTOK_DIRECT_POST_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
TIKTOK_POST_STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
TIKTOK_UPLOAD_SCOPE = "video.publish"
DEFAULT_TIKTOK_PRIVACY_LEVEL = "SELF_ONLY"
DEFAULT_TIKTOK_CLIENT_CONFIG_FILE = ".secrets/tiktok-client-config.json"
DEFAULT_TIKTOK_TOKEN_FILE = ".secrets/tiktok-token.json"
DEFAULT_TIKTOK_REDIRECT_HOST = "127.0.0.1"
DEFAULT_TIKTOK_REDIRECT_PATH = "/callback/"
DEFAULT_AUTO_RECITER_LIBRARY_FILE = ".secrets/auto-reciters.json"
TIKTOK_PRIVACY_LEVEL_CHOICES = (
    "PUBLIC_TO_EVERYONE",
    "MUTUAL_FOLLOW_FRIENDS",
    "FOLLOWER_OF_CREATOR",
    "SELF_ONLY",
)
TIKTOK_ACCESS_TOKEN_REFRESH_BUFFER_SECONDS = 300
TIKTOK_AUTH_TIMEOUT_SECONDS = 300
TIKTOK_STATUS_POLL_SECONDS = 5
TIKTOK_STATUS_MAX_POLLS = 12
TIKTOK_SIMPLE_UPLOAD_MAX_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class VerseRecitationSource:
    relative_path: str
    reciter_name: str


@dataclass(frozen=True)
class WordSegment:
    arabic: str
    translation: str


@dataclass(frozen=True)
class TimedSegment:
    arabic: str
    translation: str
    start_time: float
    end_time: float


@dataclass(frozen=True)
class SegmentTextAsset:
    arabic_lines: list[Path]
    translation_lines: list[Path]


@dataclass(frozen=True)
class TimedSegmentTextAsset:
    arabic_lines: list[Path]
    translation_lines: list[Path]
    start_time: float
    end_time: float


@dataclass(frozen=True)
class AutoVerse:
    verse_key: str
    arabic: str
    translation: str
    audio_url: str
    audio_path: Path
    duration: float


@dataclass(frozen=True)
class AutoReciter:
    reciter_name: str
    recitation_id: int | None = None
    recitation_relative_path: str | None = None
    audio_base_url: str = VERSES_AUDIO_BASE_URL
    audio_base_dir: Path | None = None
    download_script: Path | None = None
    chapter_audio_files: dict[int, Path] = field(default_factory=dict)
    auto_detect_whole_surah_files: bool = False
    whole_surah_includes_basmala: bool = True
    attribution_lines: tuple[str, ...] = ()
    reciter_name_arabic: str | None = None
    showcase_only: bool = False


BUILTIN_VERSE_RECITATIONS = {
    "alafasy": VerseRecitationSource(
        relative_path="Alafasy_128kbps",
        reciter_name="Mishari Rashid al-`Afasy",
    ),
    "mishary": VerseRecitationSource(
        relative_path="Alafasy_128kbps",
        reciter_name="Mishari Rashid al-`Afasy",
    ),
    "mishari": VerseRecitationSource(
        relative_path="Alafasy_128kbps",
        reciter_name="Mishari Rashid al-`Afasy",
    ),
    "afasy": VerseRecitationSource(
        relative_path="Alafasy_128kbps",
        reciter_name="Mishari Rashid al-`Afasy",
    ),
    "abdulbaset_mujawwad": VerseRecitationSource(
        relative_path="Abdul_Basit_Mujawwad_128kbps",
        reciter_name="Abdul Basit Abdus Samad",
    ),
    "abdul_basit_mujawwad": VerseRecitationSource(
        relative_path="Abdul_Basit_Mujawwad_128kbps",
        reciter_name="Abdul Basit Abdus Samad",
    ),
    "husary": VerseRecitationSource(
        relative_path="Husary_128kbps",
        reciter_name="Mahmoud Khalil Al-Husary",
    ),
    "minshawi": VerseRecitationSource(
        relative_path="Minshawy_Murattal_128kbps",
        reciter_name="Mohamed Siddiq El-Minshawi",
    ),
    "sudais": VerseRecitationSource(
        relative_path="Abdurrahmaan_As-Sudais_192kbps",
        reciter_name="Abdurrahman As-Sudais",
    ),
    "shuraym": VerseRecitationSource(
        relative_path="Saood_ash-Shuraym_128kbps",
        reciter_name="Saud Al-Shuraim",
    ),
    "maher": VerseRecitationSource(
        relative_path="MaherAlMuaiqly128kbps",
        reciter_name="Maher Al Muaiqly",
    ),
    "yasser": VerseRecitationSource(
        relative_path="Yasser_Ad-Dussary_128kbps",
        reciter_name="Yasser Al-Dosari",
    ),
    "ajamy": VerseRecitationSource(
        relative_path="ahmed_ibn_ali_al_ajamy_128kbps",
        reciter_name="Ahmed ibn Ali al-Ajamy",
    ),
    "shatri": VerseRecitationSource(
        relative_path="Abu_Bakr_Ash-Shaatree_128kbps",
        reciter_name="Abu Bakr Ash-Shatri",
    ),
    "hudhaify": VerseRecitationSource(
        relative_path="Hudhaify_128kbps",
        reciter_name="Ali Al-Hudhaify",
    ),
    "juhany": VerseRecitationSource(
        relative_path="Abdullaah_3awwaad_Al-Juhaynee_128kbps",
        reciter_name="Abdullah Awad Al-Juhany",
    ),
}
WINDOWS_ARABIC_FONT_FALLBACKS = [
    Path("C:/Windows/Fonts/Candarab.ttf"),
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("C:/Windows/Fonts/tahoma.ttf"),
    Path("C:/Windows/Fonts/segoeui.ttf"),
]


@dataclass
class RenderConfig:
    audio_path: Path
    output_path: Path
    verse_text: str
    surah_name: str
    verse_reference: str
    translation: str | None = None
    reciter_name: str | None = None
    background_path: Path | None = None
    font_file: Path | None = None
    latin_font_file: Path | None = None
    brand_text: str = "shortQuran"
    title_text: str | None = None
    description_text: str | None = None
    fps: int = DEFAULT_FPS
    word_segments: list[WordSegment] | None = None
    timed_segments: list[TimedSegment] | None = None
    prefer_static_text_overlay: bool = False
    show_meta: bool = True
    show_brand: bool = True
    style_preset: str = "classic"
    auto_history_entry: dict[str, object] | None = None
    attribution_lines: tuple[str, ...] = ()
    facebook_credit_lines: tuple[str, ...] = ()
    arabic_surah_name: str | None = None
    arabic_reciter_name: str | None = None

    @classmethod
    def from_file(cls, config_path: Path) -> "RenderConfig":
        config_path = config_path.expanduser().resolve()
        payload = load_json_payload(config_path)
        return cls.from_payload(config_path.parent, payload)

    @classmethod
    def from_payload(cls, config_dir: Path, payload: dict[str, object]) -> "RenderConfig":
        cache_dir_value = payload.get("cache_dir", DEFAULT_CACHE_DIR)
        cache_dir = resolve_config_path(config_dir, cache_dir_value)
        verse_reference = resolve_verse_reference(payload)
        local_audio_path = resolve_optional_local_path(config_dir, payload.get("audio_path"))
        explicit_audio_url = normalize_optional_text(payload.get("audio_url"))
        generated_audio_url = None
        derived_reciter_name = None

        if explicit_audio_url is None and not (local_audio_path and local_audio_path.exists()):
            generated_audio_url, derived_reciter_name = resolve_generated_audio_url(payload)

        required_keys = ["output_path", "verse_text", "surah_name"]
        missing_keys = [key for key in required_keys if not payload.get(key)]
        if missing_keys:
            joined = ", ".join(missing_keys)
            raise ValueError(f"Missing required config fields: {joined}")

        audio_url_value = explicit_audio_url or generated_audio_url

        background_url_value = normalize_optional_text(payload.get("background_url"))
        local_background_path = resolve_optional_local_path(config_dir, payload.get("background_path"))
        library_background_path = None
        if background_url_value is None and local_background_path is None:
            library_background_path = choose_random_library_background(config_dir)
            if library_background_path is not None:
                print(f"Using local background from {library_background_path}")
            else:
                background_url_value = DEFAULT_BACKGROUND_URL

        font_url_value = normalize_optional_text(payload.get("font_url"))
        local_font_path = resolve_optional_local_path(config_dir, payload.get("font_file"))
        if font_url_value is None and local_font_path is None:
            local_font_path = find_project_arabic_font(config_dir)
            if local_font_path is None:
                font_url_value = DEFAULT_ARABIC_FONT_URL

        latin_font_url_value = normalize_optional_text(payload.get("latin_font_url"))
        local_latin_font_path = resolve_optional_local_path(config_dir, payload.get("latin_font_file"))
        if latin_font_url_value is None and local_latin_font_path is None:
            latin_font_url_value = DEFAULT_LATIN_FONT_URL

        audio_path = resolve_asset_path(
            config_dir=config_dir,
            cache_dir=cache_dir,
            local_value=payload.get("audio_path"),
            url_value=audio_url_value,
            asset_name="audio",
            required=True,
        )
        output_path = resolve_config_path(config_dir, payload["output_path"])
        background_path = library_background_path or resolve_asset_path(
            config_dir=config_dir,
            cache_dir=cache_dir,
            local_value=payload.get("background_path"),
            url_value=background_url_value,
            asset_name="background",
            required=False,
        )
        font_file = local_font_path or resolve_asset_path(
            config_dir=config_dir,
            cache_dir=cache_dir,
            local_value=payload.get("font_file"),
            url_value=font_url_value,
            asset_name="font",
            required=False,
        )
        latin_font_file = resolve_asset_path(
            config_dir=config_dir,
            cache_dir=cache_dir,
            local_value=payload.get("latin_font_file"),
            url_value=latin_font_url_value,
            asset_name="latin_font",
            required=False,
        )

        fps = int(payload.get("fps", DEFAULT_FPS))
        if fps <= 0:
            raise ValueError("fps must be greater than zero")

        verse_text = clean_quranic_text(require_non_empty_text(payload["verse_text"], "verse_text"))
        surah_name = require_non_empty_text(payload["surah_name"], "surah_name")
        reciter_name = str(payload["reciter_name"]).strip() if payload.get("reciter_name") else None
        if not reciter_name:
            reciter_name = derived_reciter_name
        word_segments = parse_word_segments(payload.get("word_segments"))
        show_meta = parse_optional_bool(payload.get("show_meta"), default=True)
        show_brand = parse_optional_bool(payload.get("show_brand"), default=True)
        style_preset = normalize_optional_text(payload.get("style_preset")) or "classic"

        return cls(
            audio_path=audio_path,
            output_path=output_path,
            verse_text=verse_text,
            translation=str(payload["translation"]).strip() if payload.get("translation") else None,
            surah_name=surah_name,
            verse_reference=verse_reference,
            reciter_name=reciter_name,
            background_path=background_path,
            font_file=font_file,
            latin_font_file=latin_font_file,
            brand_text=str(payload.get("brand_text", "shortQuran")).strip() or "shortQuran",
            title_text=str(payload["title_text"]).strip() if payload.get("title_text") else None,
            description_text=str(payload["description_text"]).strip() if payload.get("description_text") else None,
            fps=fps,
            word_segments=word_segments,
            show_meta=show_meta,
            show_brand=show_brand,
            style_preset=style_preset,
            attribution_lines=parse_string_lines(payload.get("attribution_lines"), context="render attribution_lines"),
        )


@dataclass(frozen=True)
class YouTubeUploadOptions:
    client_secrets_file: Path
    token_file: Path
    privacy_status: str = DEFAULT_YOUTUBE_PRIVACY_STATUS
    schedule_at: datetime | None = None
    auto_schedule_enabled: bool = False
    schedule_timezone: str = DEFAULT_YOUTUBE_AUTO_SCHEDULE_TIMEZONE
    schedule_slots: tuple[str, ...] = ()
    schedule_reference_at: datetime | None = None
    category_id: str = DEFAULT_YOUTUBE_CATEGORY_ID
    tags: tuple[str, ...] = ()
    default_language: str = DEFAULT_YOUTUBE_DEFAULT_LANGUAGE
    made_for_kids: bool = False


@dataclass(frozen=True)
class TikTokClientConfig:
    client_key: str
    client_secret: str
    redirect_host: str = DEFAULT_TIKTOK_REDIRECT_HOST
    redirect_path: str = DEFAULT_TIKTOK_REDIRECT_PATH


@dataclass(frozen=True)
class FacebookPageConfig:
    page_id: str
    page_access_token: str
    instagram_business_id: str | None = None
    api_version: str = DEFAULT_FACEBOOK_API_VERSION
    reciter_key: str | None = None
    recitation_relative_path: str | None = None
    reciter_name: str | None = None
    audio_base_url: str = VERSES_AUDIO_BASE_URL
    chapter_audio_overrides: dict[int, "FacebookChapterAudioOverride"] = field(default_factory=dict)
    credit_lines: tuple[str, ...] = ()


@dataclass(frozen=True)
class FacebookChapterAudioOverride:
    audio_path: Path | None = None
    audio_url: str | None = None
    reciter_name: str | None = None
    verse_durations: tuple[float, ...] = ()






def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a Quran short video from audio, text, and optional background media.")
    parser.add_argument("--config", help="Path to a JSON config file.")
    parser.add_argument("--auto", action="store_true", help="Generate a fully automatic Quran short without a config file.")
    parser.add_argument("--landscape", action="store_true", help="Generate video in landscape format (1920x1080).")
    parser.add_argument("--whole-surah", action="store_true", help="Generate a video for the whole surah without clipping.")
    parser.add_argument("--count", type=int, default=DEFAULT_AUTO_COUNT, help="How many automatic videos to generate.")
    parser.add_argument(
        "--target-seconds",
        type=float,
        default=DEFAULT_TARGET_DURATION,
        help="Target duration for automatic videos.",
    )
    parser.add_argument(
        "--auto-reciter-library-file",
        help="Optional JSON file that restricts automatic mode to a custom reciter library, for example .secrets/auto-reciters.json.",
    )
    parser.add_argument("--youtube-upload", action="store_true", help="Upload rendered videos to YouTube after each successful render.")
    parser.add_argument("--youtube-auth-only", action="store_true", help="Run the one-time YouTube OAuth flow, save the token file, and exit.")
    
    # Facebook & Instagram upload options
    parser.add_argument("--facebook-upload", action="store_true", help="Upload rendered videos to Facebook Page after each successful render.")
    parser.add_argument("--instagram-upload", action="store_true", help="Upload rendered videos to Instagram Reels after each successful render.")
    parser.add_argument("--facebook-page-config-file", help=f"Path to the Facebook Page (and Instagram ID) config JSON file. Defaults to {DEFAULT_FACEBOOK_PAGE_CONFIG_FILE}.")
    
    # TikTok upload options
    parser.add_argument("--tiktok-upload", action="store_true", help="Upload rendered videos to TikTok after each successful render.")
    parser.add_argument("--tiktok-client-config-file", help="Path to the TikTok API client config.")
    parser.add_argument("--tiktok-token-file", help="Path to the TikTok API token.")
    parser.add_argument(
        "--youtube-client-secrets-file",
        help="Path to the YouTube OAuth client secrets JSON file. Defaults to .secrets/youtube-client-secret.json or YOUTUBE_CLIENT_SECRETS_FILE.",
    )
    parser.add_argument(
        "--youtube-token-file",
        help="Path to the stored YouTube OAuth token JSON file. Defaults to .secrets/youtube-token.json or YOUTUBE_TOKEN_FILE.",
    )
    parser.add_argument(
        "--youtube-privacy-status",
        choices=("private", "unlisted", "public"),
        default=DEFAULT_YOUTUBE_PRIVACY_STATUS,
        help="Privacy status used for YouTube uploads.",
    )
    parser.add_argument(
        "--youtube-schedule-at",
        help="Optional ISO datetime for scheduled publish, for example 2026-04-10T18:00:00+01:00.",
    )
    parser.add_argument(
        "--youtube-auto-schedule",
        action="store_true",
        help="Automatically schedule YouTube uploads into the next available MA/MENA time slots.",
    )
    parser.add_argument(
        "--youtube-schedule-preset",
        choices=tuple(YOUTUBE_AUTO_SCHEDULE_PRESETS),
        default=DEFAULT_YOUTUBE_AUTO_SCHEDULE_PRESET,
        help="Preset slot pack used when --youtube-auto-schedule is enabled.",
    )
    parser.add_argument(
        "--youtube-schedule-timezone",
        default=DEFAULT_YOUTUBE_AUTO_SCHEDULE_TIMEZONE,
        help="IANA timezone used for automatic YouTube scheduling.",
    )
    parser.add_argument(
        "--youtube-schedule-slots",
        default="",
        help="Optional comma-separated publish slots like 12:30,18:30,21:30. Overrides the preset for automatic scheduling.",
    )
    parser.add_argument(
        "--youtube-category-id",
        default=DEFAULT_YOUTUBE_CATEGORY_ID,
        help="YouTube category id for uploads. Defaults to 27 (Education).",
    )
    parser.add_argument(
        "--youtube-tags",
        default="",
        help="Comma-separated extra YouTube tags, for example quran,shorts,islam.",
    )
    parser.add_argument(
        "--youtube-default-language",
        default=DEFAULT_YOUTUBE_DEFAULT_LANGUAGE,
        help="Default language metadata for YouTube uploads.",
    )
    parser.add_argument("--youtube-made-for-kids", action="store_true", help="Mark uploaded videos as made for kids.")
    return parser.parse_args()


def load_json_payload(config_path: Path) -> dict[str, object]:
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Config root must be a JSON object.")
    return payload


def load_render_configs(config_path: Path) -> list[RenderConfig]:
    config_path = config_path.expanduser().resolve()
    payload = load_json_payload(config_path)
    config_dir = config_path.parent
    jobs = payload.get("jobs")

    if jobs is None:
        return [RenderConfig.from_payload(config_dir, payload)]

    if not isinstance(jobs, list) or not jobs:
        raise ValueError("'jobs' must be a non-empty list of config objects.")

    shared_defaults = dict(payload)
    shared_defaults.pop("jobs", None)

    configs: list[RenderConfig] = []
    for index, job_payload in enumerate(jobs):
        if not isinstance(job_payload, dict):
            raise ValueError(f"'jobs[{index}]' must be an object.")

        merged_payload = dict(shared_defaults)
        merged_payload.update(job_payload)

        try:
            configs.append(RenderConfig.from_payload(config_dir, merged_payload))
        except Exception as error:  # noqa: BLE001
            raise ValueError(f"jobs[{index}]: {error}") from error

    return configs


def resolve_verse_reference(payload: dict[str, object]) -> str:
    if payload.get("verse_reference"):
        return require_non_empty_text(payload["verse_reference"], "verse_reference")

    surah_number = parse_optional_positive_int(payload.get("surah_number"), "surah_number")
    ayah_number = parse_optional_positive_int(payload.get("ayah_number"), "ayah_number")
    if surah_number is not None and ayah_number is not None:
        return f"{surah_number}:{ayah_number}"

    raise ValueError("Provide 'verse_reference' or both 'surah_number' and 'ayah_number' in the config file.")


def resolve_generated_audio_url(payload: dict[str, object]) -> tuple[str | None, str | None]:
    surah_number = parse_optional_positive_int(payload.get("surah_number"), "surah_number")
    ayah_number = parse_optional_positive_int(payload.get("ayah_number"), "ayah_number")

    if surah_number is None or ayah_number is None:
        return None, None

    explicit_relative_path = str(payload["recitation_relative_path"]).strip() if payload.get("recitation_relative_path") else ""
    if explicit_relative_path:
        return build_verse_audio_url(explicit_relative_path, surah_number, ayah_number), None

    reciter_key = str(payload["reciter_key"]).strip() if payload.get("reciter_key") else ""
    if not reciter_key:
        return None, None

    source = get_builtin_recitation_source(reciter_key)
    return build_verse_audio_url(source.relative_path, surah_number, ayah_number), source.reciter_name


def resolve_asset_path(
    *,
    config_dir: Path,
    cache_dir: Path,
    local_value: object,
    url_value: object,
    asset_name: str,
    required: bool,
) -> Path | None:
    local_path = resolve_optional_local_path(config_dir, local_value)

    if local_path and local_path.exists():
        return local_path

    url_text = str(url_value).strip() if url_value else ""
    if url_text:
        return download_asset(url_text, cache_dir / asset_name, asset_name)

    if local_path and not local_path.exists():
        raise FileNotFoundError(f"{asset_name.title()} file not found: {local_path}")

    if required:
        raise ValueError(f"Provide either '{asset_name}_path' or '{asset_name}_url' in the config file.")

    return None


def resolve_config_path(config_dir: Path, raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate
    return (config_dir / candidate).resolve()


def resolve_runtime_path(base_dir: Path, raw_path: str) -> Path:
    return resolve_config_path(base_dir, raw_path)


def normalize_optional_text(value: object) -> str | None:
    if value is None:
        return None

    cleaned = str(value).strip()
    return cleaned or None


def clean_quranic_text(text: str) -> str:
    if not text:
        return ""
    # Remove special Quranic tajweed marks only
    return re.sub(r"[\u06d6-\u06ed]", "", text)


def find_project_arabic_font(base_dir: Path | None = None) -> Path | None:
    search_roots: list[Path] = []
    if base_dir is not None:
        search_roots.append(base_dir.resolve())
    search_roots.append(PROJECT_DIR)

    seen_roots: set[Path] = set()
    for root in search_roots:
        if root in seen_roots:
            continue
        seen_roots.add(root)
        for font_name in PROJECT_ARABIC_FONT_FILENAMES:
            candidate = root / font_name
            if candidate.exists():
                return candidate.resolve()
    return None


def resolve_default_arabic_font_file(base_dir: Path, cache_dir: Path) -> Path:
    bundled_font = find_project_arabic_font(base_dir)
    if bundled_font is not None:
        return bundled_font
    return download_asset(DEFAULT_ARABIC_FONT_URL, cache_dir / "font", "font")







def parse_optional_datetime(value: object, *, field_name: str) -> datetime | None:
    normalized = normalize_optional_text(value)
    if normalized is None:
        return None

    cleaned_value = normalized.replace("Z", "+00:00")
    parsed_value = datetime.fromisoformat(cleaned_value)
    if parsed_value.tzinfo is None:
        parsed_value = parsed_value.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return parsed_value


def to_rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def resolve_schedule_timezone(timezone_name: str) -> ZoneInfo | tzinfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return datetime.now().astimezone().tzinfo or timezone.utc


def parse_schedule_slot(value: str) -> tuple[int, int]:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Schedule slot values cannot be empty.")

    match = re.fullmatch(r"(\d{1,2}):(\d{2})", cleaned)
    if not match:
        raise ValueError(f"Invalid schedule slot '{value}'. Use HH:MM format.")

    hour = int(match.group(1))
    minute = int(match.group(2))
    if hour not in range(24) or minute not in range(60):
        raise ValueError(f"Invalid schedule slot '{value}'. Use HH:MM format.")
    return hour, minute


def resolve_youtube_schedule_slots(
    raw_slots: object,
    *,
    preset_name: str,
) -> tuple[str, ...]:
    custom_slots = parse_csv_text_list(raw_slots)
    if custom_slots:
        return custom_slots
    return YOUTUBE_AUTO_SCHEDULE_PRESETS[preset_name]


def parse_csv_text_list(value: object) -> tuple[str, ...]:
    normalized = normalize_optional_text(value)
    if normalized is None:
        return ()
    return tuple(item for item in (chunk.strip() for chunk in normalized.split(",")) if item)


def parse_optional_bool(value: object, *, default: bool) -> bool:
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Cannot parse boolean value from '{value}'.")


def parse_word_segments(value: object) -> list[WordSegment] | None:
    if value is None:
        return None

    if not isinstance(value, list):
        raise ValueError("'word_segments' must be a list of objects")

    segments: list[WordSegment] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"'word_segments[{index}]' must be an object")

        arabic = require_non_empty_text(item.get("arabic", ""), f"word_segments[{index}].arabic")
        translation = require_non_empty_text(item.get("translation", ""), f"word_segments[{index}].translation")
        segments.append(WordSegment(arabic=arabic, translation=translation))

    return segments or None


def parse_optional_positive_int(value: object, field_name: str) -> int | None:
    if value is None:
        return None

    cleaned = str(value).strip()
    if not cleaned:
        return None

    parsed_value = int(cleaned)
    if parsed_value <= 0:
        raise ValueError(f"'{field_name}' must be greater than zero")
    return parsed_value


def resolve_optional_local_path(config_dir: Path, raw_path: object) -> Path | None:
    if raw_path is None:
        return None

    cleaned = str(raw_path).strip()
    if not cleaned:
        return None

    return resolve_config_path(config_dir, cleaned)


def resolve_auto_history_path(base_dir: Path) -> Path:
    return (base_dir / AUTO_HISTORY_FILE).resolve()


def load_auto_history(base_dir: Path) -> list[dict[str, object]]:
    history_path = resolve_auto_history_path(base_dir)
    if not history_path.exists():
        return []

    try:
        payload = json.loads(history_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(payload, list):
        return []

    return [item for item in payload if isinstance(item, dict)]


def save_auto_history(base_dir: Path, history_entries: list[dict[str, object]]) -> None:
    history_path = resolve_auto_history_path(base_dir)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(history_entries[-200:], indent=2, ensure_ascii=False), encoding="utf-8")


def append_auto_history_entry(base_dir: Path, history_entry: dict[str, object]) -> None:
    history_entries = load_auto_history(base_dir)
    history_entries.append(history_entry)
    save_auto_history(base_dir, history_entries)


def get_recent_history_values(
    history_entries: list[dict[str, object]],
    key: str,
    *,
    limit: int,
) -> list[str]:
    recent_values: list[str] = []
    for entry in reversed(history_entries):
        value = normalize_optional_text(entry.get(key))
        if value is None or value in recent_values:
            continue
        recent_values.append(value)
        if len(recent_values) >= limit:
            break
    return recent_values


def choose_balanced_history_value(
    candidates: tuple[str, ...] | list[str],
    history_entries: list[dict[str, object]],
    history_key: str,
    *,
    recent_limit: int,
) -> str:
    candidate_list = [candidate for candidate in candidates if candidate]
    if not candidate_list:
        raise ValueError(f"No candidates available for history key '{history_key}'.")

    recent_values = set(get_recent_history_values(history_entries, history_key, limit=recent_limit))
    counts = {candidate: 0 for candidate in candidate_list}
    for entry in history_entries:
        value = normalize_optional_text(entry.get(history_key))
        if value in counts:
            counts[value] += 1

    available_candidates = [candidate for candidate in candidate_list if candidate not in recent_values]
    preferred_candidates = available_candidates or candidate_list
    minimum_count = min(counts[candidate] for candidate in preferred_candidates)
    balanced_candidates = [
        candidate
        for candidate in preferred_candidates
        if counts[candidate] == minimum_count
    ]
    return random.choice(balanced_candidates)


def build_translation_excerpt(text: str | None, *, limit: int = AUTO_DESCRIPTION_EXCERPT_CHARS) -> str:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return "Listen, reflect, and revisit these verses."
    if len(cleaned) <= limit:
        return cleaned

    truncated = cleaned[:limit].rsplit(" ", maxsplit=1)[0].rstrip(" ,.;:-")
    return f"{truncated}..."


def build_auto_description(
    config: RenderConfig,
    *,
    description_template_key: str,
    description_hook_key: str,
    cta_key: str,
) -> str:
    hook_line = AUTO_DESCRIPTION_HOOKS[description_hook_key]
    cta_text = AUTO_CTA_LINES[cta_key]
    translation_excerpt = build_translation_excerpt(config.translation)
    description_body = AUTO_DESCRIPTION_TEMPLATES[description_template_key].format(
        hook_line=hook_line,
        chapter_name=config.surah_name,
        verse_reference=config.verse_reference,
        reciter_name=config.reciter_name or "Quran recitation",
        translation_excerpt=translation_excerpt,
        cta=cta_text,
    ).strip()
    hashtags_line = " ".join(build_youtube_hashtags(config))
    return f"{description_body}\n\n{hashtags_line}".strip()


def build_auto_combo_key(chapter_number: int, verse_start: int, verse_end: int, reciter_name: str) -> str:
    safe_reciter = sanitize_filename_part(reciter_name)
    return f"{chapter_number}:{verse_start}-{verse_end}:{safe_reciter}"


def choose_showcase_clip_window(
    *,
    history_entries: list[dict[str, object]],
    chapter_number: int,
    reciter_name: str,
    source_duration: float,
    clip_duration: float,
) -> tuple[float, float]:
    max_start = max(0.0, source_duration - clip_duration)
    if max_start <= 0.05:
        return 0.0, clip_duration

    candidate_count = min(12, max(5, int(max_start // 8.0) + 1))
    if candidate_count <= 1:
        return 0.0, clip_duration

    candidate_starts = [
        round((max_start * index) / (candidate_count - 1), 3)
        for index in range(candidate_count)
    ]

    recent_starts: list[float] = []
    for entry in reversed(history_entries):
        entry_chapter = entry.get("chapter_number")
        entry_reciter = normalize_optional_text(entry.get("reciter_name")) or ""
        entry_start = entry.get("clip_start_seconds")
        try:
            if int(entry_chapter or 0) != chapter_number:
                continue
            if entry_reciter != reciter_name:
                continue
            if entry_start is None:
                continue
            recent_starts.append(float(entry_start))
        except (TypeError, ValueError):
            continue
        if len(recent_starts) >= AUTO_RECENT_SHOWCASE_START_WINDOW:
            break

    minimum_spacing = max(8.0, clip_duration * 0.35)
    filtered_candidates = [
        start
        for start in candidate_starts
        if all(abs(start - recent_start) >= minimum_spacing for recent_start in recent_starts)
    ]
    non_zero_candidates = [start for start in filtered_candidates if start > 0.5]
    if non_zero_candidates:
        chosen_start = random.choice(non_zero_candidates)
    elif filtered_candidates:
        chosen_start = random.choice(filtered_candidates)
    else:
        fallback_candidates = [start for start in candidate_starts if start > 0.5]
        chosen_start = random.choice(fallback_candidates or candidate_starts)

    chosen_end = min(source_duration, chosen_start + clip_duration)
    chosen_start = max(0.0, chosen_end - clip_duration)
    return round(chosen_start, 3), round(chosen_end, 3)


def choose_auto_target_seconds(target_seconds: float, history_entries: list[dict[str, object]]) -> float:
    minimum = max(AUTO_MIN_TARGET_SECONDS, target_seconds - 6.0)
    maximum = min(AUTO_MAX_TARGET_SECONDS, target_seconds + 2.0)
    if minimum > maximum:
        minimum = maximum = max(AUTO_MIN_TARGET_SECONDS, min(AUTO_MAX_TARGET_SECONDS, target_seconds))

    stepped_options = [float(value) for value in range(int(round(minimum)), int(round(maximum)) + 1, 2)]
    if not stepped_options:
        stepped_options = [float(round(target_seconds))]

    recent_targets = {
        int(round(float(entry.get("target_seconds") or 0)))
        for entry in history_entries[-AUTO_RECENT_TITLE_WINDOW:]
        if entry.get("target_seconds") is not None
    }
    filtered_options = [option for option in stepped_options if int(round(option)) not in recent_targets]
    return random.choice(filtered_options or stepped_options)


def choose_auto_style_preset(history_entries: list[dict[str, object]]) -> str:
    return choose_balanced_history_value(
        list(AUTO_STYLE_PRESETS),
        history_entries,
        "style_preset",
        recent_limit=AUTO_RECENT_STYLE_WINDOW,
    )


def build_auto_title(
    *,
    chapter_name: str,
    verse_reference: str,
    verse_start: int,
    verse_end: int,
    reciter_name: str,
    history_entries: list[dict[str, object]],
) -> tuple[dict[str, str], str]:
    title_template_key = choose_balanced_history_value(
        list(AUTO_TITLE_TEMPLATES),
        history_entries,
        "title_template_key",
        recent_limit=AUTO_RECENT_TITLE_WINDOW,
    )
    title_hook_key = choose_balanced_history_value(
        list(AUTO_TITLE_HOOKS),
        history_entries,
        "title_hook_key",
        recent_limit=AUTO_RECENT_METADATA_WINDOW,
    )
    description_template_key = choose_balanced_history_value(
        list(AUTO_DESCRIPTION_TEMPLATES),
        history_entries,
        "description_template_key",
        recent_limit=AUTO_RECENT_TITLE_WINDOW,
    )
    description_hook_key = choose_balanced_history_value(
        list(AUTO_DESCRIPTION_HOOKS),
        history_entries,
        "description_hook_key",
        recent_limit=AUTO_RECENT_METADATA_WINDOW,
    )
    cta_key = choose_balanced_history_value(
        list(AUTO_CTA_LINES),
        history_entries,
        "cta_key",
        recent_limit=AUTO_RECENT_METADATA_WINDOW,
    )
    verse_range_label = str(verse_start) if verse_start == verse_end else f"{verse_start}-{verse_end}"
    hook_text = AUTO_TITLE_HOOKS[title_hook_key]
    title_text = AUTO_TITLE_TEMPLATES[title_template_key].format(
        chapter_name=chapter_name,
        verse_reference=verse_reference,
        verse_start=verse_start,
        verse_end=verse_end,
        verse_range_label=verse_range_label,
        reciter_name=reciter_name,
        hook=hook_text,
    )
    metadata_keys = {
        "title_template_key": title_template_key,
        "title_hook_key": title_hook_key,
        "title_hook_text": hook_text,
        "description_template_key": description_template_key,
        "description_hook_key": description_hook_key,
        "description_hook_text": AUTO_DESCRIPTION_HOOKS[description_hook_key],
        "cta_key": cta_key,
        "cta_text": AUTO_CTA_LINES[cta_key],
    }
    return metadata_keys, title_text


def is_cinematic_style(style_preset: str) -> bool:
    return style_preset in AUTO_STYLE_PRESETS or style_preset.startswith(f"{DEFAULT_AUTO_STYLE_PRESET}_")


def get_cinematic_variant(style_preset: str) -> str:
    if style_preset == "cinematic_compact":
        return "compact"
    if style_preset == "cinematic_spacious":
        return "spacious"
    return "default"


def build_youtube_upload_options(args: argparse.Namespace, base_dir: Path) -> YouTubeUploadOptions:
    client_secrets_raw = (
        normalize_optional_text(args.youtube_client_secrets_file)
        or normalize_optional_text(os.getenv("YOUTUBE_CLIENT_SECRETS_FILE"))
        or DEFAULT_YOUTUBE_CLIENT_SECRETS_FILE
    )
    token_file_raw = (
        normalize_optional_text(args.youtube_token_file)
        or normalize_optional_text(os.getenv("YOUTUBE_TOKEN_FILE"))
        or DEFAULT_YOUTUBE_TOKEN_FILE
    )
    schedule_at = parse_optional_datetime(args.youtube_schedule_at, field_name="youtube-schedule-at")
    auto_schedule_enabled = bool(args.youtube_auto_schedule) and schedule_at is None
    schedule_slots = resolve_youtube_schedule_slots(
        args.youtube_schedule_slots,
        preset_name=args.youtube_schedule_preset,
    )
    for slot in schedule_slots:
        parse_schedule_slot(slot)
    privacy_status = args.youtube_privacy_status
    if schedule_at is not None or auto_schedule_enabled:
        privacy_status = "private"

    return YouTubeUploadOptions(
        client_secrets_file=resolve_runtime_path(base_dir, client_secrets_raw),
        token_file=resolve_runtime_path(base_dir, token_file_raw),
        privacy_status=privacy_status,
        schedule_at=schedule_at,
        auto_schedule_enabled=auto_schedule_enabled,
        schedule_timezone=require_non_empty_text(args.youtube_schedule_timezone, "youtube-schedule-timezone"),
        schedule_slots=schedule_slots,
        schedule_reference_at=datetime.now(timezone.utc),
        category_id=require_non_empty_text(args.youtube_category_id, "youtube-category-id"),
        tags=parse_csv_text_list(args.youtube_tags),
        default_language=require_non_empty_text(args.youtube_default_language, "youtube-default-language"),
        made_for_kids=bool(args.youtube_made_for_kids),
    )


def resolve_auto_schedule_datetime(options: YouTubeUploadOptions, upload_index: int) -> datetime | None:
    if not options.auto_schedule_enabled:
        return options.schedule_at

    schedule_timezone = resolve_schedule_timezone(options.schedule_timezone)
    reference_time = (options.schedule_reference_at or datetime.now(timezone.utc)).astimezone(schedule_timezone)
    reference_time += timedelta(minutes=DEFAULT_YOUTUBE_AUTO_SCHEDULE_BUFFER_MINUTES)
    slot_values = [parse_schedule_slot(slot) for slot in options.schedule_slots]
    if not slot_values:
        return None

    scheduled_slots: list[datetime] = []
    candidate_date = reference_time.date()
    while len(scheduled_slots) < max(1, upload_index):
        for hour, minute in slot_values:
            candidate = datetime.combine(candidate_date, datetime.min.time(), tzinfo=schedule_timezone).replace(
                hour=hour,
                minute=minute,
            )
            if candidate < reference_time:
                continue
            scheduled_slots.append(candidate)
            if len(scheduled_slots) >= upload_index:
                break
        candidate_date += timedelta(days=1)

    return scheduled_slots[upload_index - 1]


def resolve_youtube_upload_options_for_index(
    options: YouTubeUploadOptions,
    *,
    upload_index: int,
) -> YouTubeUploadOptions:
    scheduled_at = resolve_auto_schedule_datetime(options, upload_index)
    privacy_status = "private" if scheduled_at is not None else options.privacy_status
    return replace(
        options,
        schedule_at=scheduled_at,
        privacy_status=privacy_status,
    )






def parse_facebook_chapter_audio_overrides(
    config_dir: Path,
    value: object,
) -> dict[int, FacebookChapterAudioOverride]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise RuntimeError("facebook chapter_audio_overrides must be a JSON object keyed by surah number.")

    overrides: dict[int, FacebookChapterAudioOverride] = {}
    for raw_key, raw_override in value.items():
        try:
            chapter_number = int(str(raw_key).strip())
        except ValueError as error:
            raise RuntimeError(f"Facebook chapter_audio_overrides key '{raw_key}' must be a surah number.") from error

        if chapter_number <= 0:
            raise RuntimeError("Facebook chapter_audio_overrides surah numbers must be greater than zero.")
        if not isinstance(raw_override, dict):
            raise RuntimeError(f"Facebook chapter_audio_overrides[{chapter_number}] must be a JSON object.")

        audio_path = resolve_optional_local_path(config_dir, raw_override.get("audio_path"))
        audio_url = normalize_optional_text(raw_override.get("audio_url"))
        if audio_path is None and audio_url is None:
            raise RuntimeError(
                f"Facebook chapter_audio_overrides[{chapter_number}] must include either audio_path or audio_url."
            )

        raw_durations = raw_override.get("verse_durations")
        if not isinstance(raw_durations, list) or not raw_durations:
            raise RuntimeError(
                f"Facebook chapter_audio_overrides[{chapter_number}] must include a non-empty verse_durations list."
            )

        verse_durations: list[float] = []
        for index, item in enumerate(raw_durations, start=1):
            try:
                duration = float(item)
            except (TypeError, ValueError) as error:
                raise RuntimeError(
                    f"Facebook chapter_audio_overrides[{chapter_number}].verse_durations[{index}] must be numeric."
                ) from error
            if duration <= 0:
                raise RuntimeError(
                    f"Facebook chapter_audio_overrides[{chapter_number}].verse_durations[{index}] must be > 0."
                )
            verse_durations.append(duration)

        overrides[chapter_number] = FacebookChapterAudioOverride(
            audio_path=audio_path,
            audio_url=audio_url,
            reciter_name=normalize_optional_text(raw_override.get("reciter_name")),
            verse_durations=tuple(verse_durations),
        )

    return overrides


def parse_string_lines(value: object, *, context: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        cleaned = " ".join(value.split()).strip()
        return (cleaned,) if cleaned else ()
    if not isinstance(value, list):
        raise RuntimeError(f"{context} must be either a string or a JSON array of strings.")

    lines: list[str] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, str):
            raise RuntimeError(f"{context}[{index}] must be a string.")
        cleaned = " ".join(item.split()).strip()
        if cleaned:
            lines.append(cleaned)
    return tuple(lines)


def load_tiktok_client_config(config_path: Path) -> TikTokClientConfig:
    if not config_path.exists():
        raise FileNotFoundError(
            f"TikTok client config file not found: {config_path}. "
            "Create a JSON file with client_key and client_secret from TikTok Developers."
        )

    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Failed to read TikTok client config from {config_path}: {error}") from error

    if not isinstance(payload, dict):
        raise RuntimeError(f"TikTok client config at {config_path} must be a JSON object.")

    redirect_host = normalize_optional_text(payload.get("redirect_host")) or DEFAULT_TIKTOK_REDIRECT_HOST
    redirect_path = normalize_optional_text(payload.get("redirect_path")) or DEFAULT_TIKTOK_REDIRECT_PATH
    if redirect_host not in {"127.0.0.1", "localhost"}:
        raise RuntimeError("TikTok redirect_host must be localhost or 127.0.0.1.")
    if not redirect_path.startswith("/"):
        redirect_path = f"/{redirect_path}"
    if not redirect_path.endswith("/"):
        redirect_path = f"{redirect_path}/"

    return TikTokClientConfig(
        client_key=require_non_empty_text(payload.get("client_key", ""), "tiktok client_key"),
        client_secret=require_non_empty_text(payload.get("client_secret", ""), "tiktok client_secret"),
        redirect_host=redirect_host,
        redirect_path=redirect_path,
    )




def request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    timeout: int = 60,
) -> dict[str, object]:
    request_headers = {
        "User-Agent": "shortQuran/1.0",
        "Accept": "application/json",
    }
    if headers:
        request_headers.update(headers)

    request = Request(url, data=data, headers=request_headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw_body = response.read()
    except HTTPError as error:
        raw_error_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Failed to call {url}: HTTP {error.code} {error.reason} - {raw_error_body}") from error
    except (OSError, URLError) as error:
        raise RuntimeError(f"Failed to call {url}: {error}") from error

    if not raw_body:
        return {}

    try:
        return json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Failed to decode JSON response from {url}: {error}") from error


def post_form_json(url: str, form_data: dict[str, object], *, timeout: int = 60) -> dict[str, object]:
    encoded_form = urlencode(form_data).encode("utf-8")
    return request_json(
        url,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=encoded_form,
        timeout=timeout,
    )


def post_json(url: str, payload: dict[str, object], *, headers: dict[str, str] | None = None, timeout: int = 60) -> dict[str, object]:
    encoded_payload = json.dumps(payload).encode("utf-8")
    merged_headers = {"Content-Type": "application/json; charset=UTF-8"}
    if headers:
        merged_headers.update(headers)
    return request_json(url, method="POST", headers=merged_headers, data=encoded_payload, timeout=timeout)


def normalize_tiktok_token_payload(payload: dict[str, object]) -> dict[str, object]:
    now_epoch = int(time.time())

    def get_optional_int(key: str) -> int | None:
        value = payload.get(key)
        if value is None:
            return None
        return int(value)

    normalized_payload = dict(payload)
    expires_in = get_optional_int("expires_in")
    refresh_expires_in = get_optional_int("refresh_expires_in")
    if expires_in is not None:
        normalized_payload["access_token_expires_at"] = now_epoch + expires_in
    if refresh_expires_in is not None:
        normalized_payload["refresh_token_expires_at"] = now_epoch + refresh_expires_in
    normalized_payload["saved_at"] = datetime.now(timezone.utc).isoformat()
    return normalized_payload


def load_tiktok_token_payload(token_path: Path) -> dict[str, object] | None:
    if not token_path.exists():
        return None

    try:
        payload = json.loads(token_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Failed to read TikTok token file {token_path}: {error}") from error

    if not isinstance(payload, dict):
        raise RuntimeError(f"TikTok token file {token_path} must contain a JSON object.")
    return payload


def save_tiktok_token_payload(token_path: Path, payload: dict[str, object]) -> None:
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def is_tiktok_access_token_valid(payload: dict[str, object]) -> bool:
    access_token = normalize_optional_text(payload.get("access_token"))
    expires_at = payload.get("access_token_expires_at")
    if access_token is None or expires_at is None:
        return False
    return int(expires_at) - TIKTOK_ACCESS_TOKEN_REFRESH_BUFFER_SECONDS > int(time.time())


def refresh_tiktok_access_token(options: TikTokUploadOptions, client_config: TikTokClientConfig, token_payload: dict[str, object]) -> dict[str, object]:
    refresh_token = normalize_optional_text(token_payload.get("refresh_token"))
    if refresh_token is None:
        raise RuntimeError("TikTok token file is missing a refresh_token. Run '--tiktok-auth-only' again.")

    refreshed_payload = post_form_json(
        TIKTOK_OAUTH_TOKEN_URL,
        {
            "client_key": client_config.client_key,
            "client_secret": client_config.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
    )
    if normalize_optional_text(refreshed_payload.get("error")):
        raise RuntimeError(
            "TikTok token refresh failed: "
            f"{refreshed_payload.get('error')} - {refreshed_payload.get('error_description', '')}".strip()
        )

    normalized_payload = normalize_tiktok_token_payload(refreshed_payload)
    save_tiktok_token_payload(options.token_file, normalized_payload)
    return normalized_payload


def create_tiktok_callback_server(
    *,
    redirect_host: str,
    redirect_path: str,
) -> tuple[http.server.HTTPServer, dict[str, str]]:
    callback_result: dict[str, str] = {}

    class TikTokOAuthHandler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            return

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path != redirect_path:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not found.")
                return

            params = parse_qs(parsed.query)
            for key in ("code", "state", "error", "error_description"):
                if params.get(key):
                    callback_result[key] = params[key][0]

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"You can close this tab now.")

    server = http.server.HTTPServer((redirect_host, 0), TikTokOAuthHandler)
    server.timeout = 1
    return server, callback_result


def get_tiktok_credentials(options: TikTokUploadOptions, *, interactive: bool) -> dict[str, object]:
    client_config = load_tiktok_client_config(options.client_config_file)
    token_payload = load_tiktok_token_payload(options.token_file)

    if token_payload and is_tiktok_access_token_valid(token_payload):
        return token_payload

    if token_payload and normalize_optional_text(token_payload.get("refresh_token")):
        refreshed_payload = refresh_tiktok_access_token(options, client_config, token_payload)
        if is_tiktok_access_token_valid(refreshed_payload):
            return refreshed_payload

    if not interactive:
        raise RuntimeError(
            "TikTok token file is missing or expired. Run '--tiktok-auth-only' once on a machine with a browser "
            "to generate a refresh token before using unattended uploads."
        )

    state = secrets.token_urlsafe(24)
    code_verifier = secrets.token_urlsafe(64)[:96]
    code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).hexdigest()

    callback_server, callback_result = create_tiktok_callback_server(
        redirect_host=client_config.redirect_host,
        redirect_path=client_config.redirect_path,
    )
    try:
        redirect_uri = f"http://{client_config.redirect_host}:{callback_server.server_port}{client_config.redirect_path}"
        authorize_url = (
            f"{TIKTOK_OAUTH_AUTHORIZE_URL}?"
            f"{urlencode({'client_key': client_config.client_key, 'response_type': 'code', 'scope': TIKTOK_UPLOAD_SCOPE, 'redirect_uri': redirect_uri, 'state': state, 'code_challenge': code_challenge, 'code_challenge_method': 'S256'})}"
        )
        print(f"Open this URL in your browser to authorize TikTok posting access: {authorize_url}")

        deadline = time.time() + TIKTOK_AUTH_TIMEOUT_SECONDS
        while time.time() < deadline:
            callback_server.handle_request()
            if callback_result:
                break
    finally:
        callback_server.server_close()

    if not callback_result:
        raise TimeoutError("Timed out waiting for the TikTok OAuth callback.")
    if callback_result.get("error"):
        raise RuntimeError(
            "TikTok authorization failed: "
            f"{callback_result.get('error')} - {callback_result.get('error_description', '')}".strip()
        )
    if callback_result.get("state") != state:
        raise RuntimeError("TikTok authorization failed because the returned state did not match.")

    authorization_code = normalize_optional_text(callback_result.get("code"))
    if authorization_code is None:
        raise RuntimeError("TikTok authorization callback did not include a code.")

    token_payload = post_form_json(
        TIKTOK_OAUTH_TOKEN_URL,
        {
            "client_key": client_config.client_key,
            "client_secret": client_config.client_secret,
            "code": authorization_code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        },
    )
    if normalize_optional_text(token_payload.get("error")):
        raise RuntimeError(
            "TikTok token exchange failed: "
            f"{token_payload.get('error')} - {token_payload.get('error_description', '')}".strip()
        )

    normalized_payload = normalize_tiktok_token_payload(token_payload)
    save_tiktok_token_payload(options.token_file, normalized_payload)
    return normalized_payload


def require_tiktok_api_success(payload: dict[str, object], context: str) -> dict[str, object]:
    error_payload = payload.get("error")
    if isinstance(error_payload, dict):
        error_code = normalize_optional_text(error_payload.get("code")) or "unknown_error"
        error_message = normalize_optional_text(error_payload.get("message")) or ""
        if error_code.lower() != "ok":
            raise RuntimeError(f"TikTok {context} failed: {error_code} - {error_message}".strip())

    data_payload = payload.get("data")
    if not isinstance(data_payload, dict):
        raise RuntimeError(f"TikTok {context} failed: missing response data.")
    return data_payload


def query_tiktok_creator_info(access_token: str) -> dict[str, object]:
    payload = post_json(
        TIKTOK_CREATOR_INFO_URL,
        {},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    return require_tiktok_api_success(payload, "creator info query")


def resolve_tiktok_privacy_level(requested_level: str, creator_info: dict[str, object]) -> str:
    options = [
        option
        for option in (
            normalize_optional_text(option)
            for option in creator_info.get("privacy_level_options", [])
            if isinstance(creator_info.get("privacy_level_options"), list)
        )
        if option is not None
    ]
    if not options:
        raise RuntimeError("TikTok creator info did not return any privacy_level_options.")
    if requested_level in options:
        return requested_level
    if DEFAULT_TIKTOK_PRIVACY_LEVEL in options:
        print(
            f"TikTok privacy level '{requested_level}' is not available for this account. "
            f"Falling back to '{DEFAULT_TIKTOK_PRIVACY_LEVEL}'."
        )
        return DEFAULT_TIKTOK_PRIVACY_LEVEL
    print(f"TikTok privacy level '{requested_level}' is not available. Falling back to '{options[0]}'.")
    return options[0]


def merge_credit_lines(*groups: tuple[str, ...]) -> tuple[str, ...]:
    lines: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for line in group:
            normalized = line.strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            lines.append(line.strip())
    return tuple(lines)


def build_tiktok_caption(config: RenderConfig) -> str:
    lines = [build_youtube_title(config).replace(" #Shorts", "")]
    if config.reciter_name:
        lines.append(f"Reciter: {config.reciter_name}")
    if config.attribution_lines:
        lines.extend(["", *config.attribution_lines])
    hashtags = " ".join(build_youtube_hashtags(config))
    if hashtags:
        lines.extend(["", hashtags])
    return "\n".join(lines)[:2200].strip()


def build_facebook_reel_title(config: RenderConfig) -> str:
    return build_youtube_title(config).replace(" #Shorts", "")[:255].strip()


def build_facebook_reel_description(config: RenderConfig, page_config: FacebookPageConfig) -> str:
    lines = []
    
    # 1. Main Title / Hook
    title = getattr(config, 'quran_arabic_name', None)
    if not title:
        # Fallback to standard
        title = getattr(config, 'surah_name', '')
    
    # 2. Arabic Metadata
    lines.append(f"سورة: {title}")
    lines.append(f"الآيات: {config.verse_reference}")
    
    if config.reciter_name:
        lines.append(f"القارئ: {config.reciter_name}")
        
    if config.verse_text:
        lines.extend(["", config.verse_text.strip()])
    
    facebook_credit_lines = merge_credit_lines(config.attribution_lines, config.facebook_credit_lines)
    if facebook_credit_lines:
        lines.extend(["", *facebook_credit_lines])
        
    # Standard Hashtags per user request
    hashtags = "#قرآن #تلاوة #تلاوات_خاشعة #قرآن_كريم #القرآن_الكريم #quran #islam #quranrecitation"
    lines.extend(["", hashtags])
    
    return "\n".join(lines).strip()


def build_facebook_graph_url(api_version: str, path: str, params: dict[str, object]) -> str:
    return f"{FACEBOOK_GRAPH_API_BASE_URL}/{api_version}/{path}?{urlencode(params)}"


def require_facebook_api_success(payload: dict[str, object], context: str) -> dict[str, object]:
    error_payload = payload.get("error")
    if isinstance(error_payload, dict):
        error_code = normalize_optional_text(error_payload.get("code")) or "unknown_error"
        error_message = normalize_optional_text(error_payload.get("message")) or ""
        raise RuntimeError(f"Facebook {context} failed: {error_code} - {error_message}".strip())
    return payload




def fetch_facebook_reel_status(page_config: FacebookPageConfig, video_id: str) -> dict[str, object]:
    payload = request_json(
        build_facebook_graph_url(
            page_config.api_version,
            video_id,
            {
                "fields": "status",
                "access_token": page_config.page_access_token,
            },
        ),
        timeout=60,
    )
    payload = require_facebook_api_success(payload, "status fetch")
    status_payload = payload.get("status")
    if not isinstance(status_payload, dict):
        return {}
    return status_payload


def summarize_facebook_reel_status(status_payload: dict[str, object]) -> str:
    video_status = (normalize_optional_text(status_payload.get("video_status")) or "unknown").upper()
    processing_progress = status_payload.get("processing_progress")
    if isinstance(processing_progress, (int, float)) and video_status == "PROCESSING":
        return f"{video_status} ({int(processing_progress)}%)"
    return video_status


def is_facebook_reel_status_terminal(status_payload: dict[str, object]) -> bool:
    phase_statuses: list[str] = []
    for phase_key in ("uploading_phase", "processing_phase", "publishing_phase"):
        phase_payload = status_payload.get(phase_key)
        if isinstance(phase_payload, dict):
            phase_status = normalize_optional_text(phase_payload.get("status"))
            if phase_status:
                phase_statuses.append(phase_status.lower())
    if any(status in {"error", "failed"} for status in phase_statuses):
        raise RuntimeError(f"Facebook Reel status failed: {status_payload}")

    video_status = normalize_optional_text(status_payload.get("video_status")) or ""
    video_status_lower = video_status.lower()
    if video_status_lower in {"error", "failed"}:
        raise RuntimeError(f"Facebook Reel processing failed: {status_payload}")
    if video_status_lower in {"published", "ready", "complete"}:
        return True
    if "complete" in phase_statuses and all(status == "complete" for status in phase_statuses if status):
        return True
    return False


def poll_facebook_reel_status(page_config: FacebookPageConfig, video_id: str) -> dict[str, object]:
    latest_status: dict[str, object] = {}
    for _ in range(FACEBOOK_STATUS_MAX_POLLS):
        latest_status = fetch_facebook_reel_status(page_config, video_id)
        if latest_status and is_facebook_reel_status_terminal(latest_status):
            return latest_status
        time.sleep(FACEBOOK_STATUS_POLL_SECONDS)
    return latest_status


def upload_video_to_facebook(
    video_path: Path,
    config: RenderConfig,
    options: object,
    page_config: FacebookPageConfig,
) -> dict[str, str]:
    import subprocess
    import json
    
    print(f"Initializing Facebook Video Upload for {video_path.name}")
    description = build_facebook_reel_description(config, page_config)
    upload_url = f"{FACEBOOK_GRAPH_API_BASE_URL}/{page_config.api_version}/{page_config.page_id}/videos"
    
    command = [
        "curl", "-s", "-X", "POST", upload_url,
        "-F", f"access_token={page_config.page_access_token}",
        "-F", f"description={description}",
        "-F", f"source=@{video_path.absolute().as_posix()}"
    ]
    
    print(f"Uploading to {upload_url} via CURL")
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    
    if result.returncode != 0:
        raise RuntimeError(f"CURL upload failed: {result.stderr}")
        
    try:
        response_data = json.loads(result.stdout)
    except Exception as e:
        raise RuntimeError(f"Failed to parse Facebook response: {result.stdout}") from e
        
    if "error" in response_data:
        raise RuntimeError(f"Facebook API Error: {response_data['error']}")
        
    video_id = str(response_data.get("id", ""))
    if not video_id:
        raise RuntimeError(f"Missing video ID in response: {response_data}")
        
    return {
        "video_id": video_id,
        "status": "PUBLISHED",
        "video_state": "PUBLISHED",
        "watch_url": f"https://www.facebook.com/watch/?v={video_id}"
    }





def fetch_tiktok_publish_status(access_token: str, publish_id: str) -> dict[str, object]:
    payload = post_json(
        TIKTOK_POST_STATUS_URL,
        {"publish_id": publish_id},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    return require_tiktok_api_success(payload, "status fetch")


def poll_tiktok_publish_status(access_token: str, publish_id: str) -> dict[str, object]:
    latest_status: dict[str, object] = {}
    for _ in range(TIKTOK_STATUS_MAX_POLLS):
        latest_status = fetch_tiktok_publish_status(access_token, publish_id)
        status_value = normalize_optional_text(latest_status.get("status")) or ""
        public_post_ids = latest_status.get("publicaly_available_post_id")
        if isinstance(public_post_ids, list) and public_post_ids:
            return latest_status
        if status_value.upper() == "FAILED":
            return latest_status
        time.sleep(TIKTOK_STATUS_POLL_SECONDS)
    return latest_status




def import_youtube_client_modules() -> tuple[object, object, object, object, object]:
    try:
        from google.auth.transport.requests import Request as GoogleAuthRequest
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build as google_build
        from googleapiclient.http import MediaFileUpload
    except ModuleNotFoundError as error:  # noqa: BLE001
        raise RuntimeError(
            "YouTube upload support needs google-api-python-client, google-auth-oauthlib, and google-auth-httplib2."
        ) from error

    return Credentials, GoogleAuthRequest, InstalledAppFlow, google_build, MediaFileUpload


def get_youtube_credentials(options: YouTubeUploadOptions, *, interactive: bool) -> object:
    Credentials, GoogleAuthRequest, InstalledAppFlow, _, _ = import_youtube_client_modules()
    credentials = None

    if options.token_file.exists():
        credentials = Credentials.from_authorized_user_file(str(options.token_file), [YOUTUBE_UPLOAD_SCOPE])

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(GoogleAuthRequest())
        options.token_file.parent.mkdir(parents=True, exist_ok=True)
        options.token_file.write_text(credentials.to_json(), encoding="utf-8")

    if credentials and credentials.valid:
        return credentials

    if not options.client_secrets_file.exists():
        raise FileNotFoundError(
            f"YouTube client secrets file not found: {options.client_secrets_file}. "
            "Create it in Google Cloud Console and place it in the expected path."
        )

    if not interactive:
        raise RuntimeError(
            "YouTube token file is missing or expired. Run '--youtube-auth-only' once on a machine with a browser "
            "to generate a refresh token before using unattended uploads."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(options.client_secrets_file), [YOUTUBE_UPLOAD_SCOPE])
    credentials = flow.run_local_server(
        host="localhost",
        port=0,
        authorization_prompt_message="Open this URL in your browser to authorize YouTube upload access: {url}",
        success_message="YouTube authorization completed. You can close this tab now.",
        open_browser=False,
    )
    options.token_file.parent.mkdir(parents=True, exist_ok=True)
    options.token_file.write_text(credentials.to_json(), encoding="utf-8")
    return credentials


def build_youtube_title(config: RenderConfig) -> str:
    surah_label = normalize_optional_text(config.surah_name) or "Quran"
    verse_label = normalize_optional_text(config.verse_reference) or ""
    reciter_label = normalize_optional_text(config.reciter_name) or ""
    hook_title = normalize_optional_text(config.title_text)

    def append_distinct_segment(base_value: str, segment: str, *, max_length: int) -> str:
        cleaned_segment = " ".join(segment.split()).strip()
        if not cleaned_segment:
            return base_value
        if cleaned_segment.lower() in base_value.lower():
            return base_value
        candidate = f"{base_value} | {cleaned_segment}"
        return candidate if len(candidate) <= max_length else base_value

    if hook_title:
        base_title = hook_title
    else:
        base_title = f"{surah_label} | {verse_label}" if verse_label else surah_label
        base_title = append_distinct_segment(base_title, reciter_label, max_length=92)

    shorts_suffix = " #Shorts"
    if not globals().get('IS_LANDSCAPE') and "#shorts" not in base_title.lower() and len(base_title) + len(shorts_suffix) <= 100:
        base_title += shorts_suffix
    return base_title[:100].strip()


def build_youtube_hashtags(config: RenderConfig) -> list[str]:
    surah_label = normalize_optional_text(config.surah_name) or "Quran"
    surah_base = re.sub(r"(?i)^surah\s+", "", surah_label).strip() or surah_label
    reciter_label = normalize_optional_text(config.reciter_name) or ""

    def make_hashtag(value: str, *, prefix: str = "", limit_words: int = 4) -> str | None:
        words = re.findall(r"[A-Za-z0-9]+", value)
        if prefix:
            words = re.findall(r"[A-Za-z0-9]+", prefix) + words
        if not words:
            return None
        token = "".join(word[:1].upper() + word[1:] for word in words[:limit_words])
        return f"#{token}" if token else None

    raw_hashtags = [
        "#shorts",
        "#quran",
        "#quranrecitation",
        "#qurantilawat",
        "#qurantranslation",
        "#القرآن_الكريم",
        "#القرآن",
        make_hashtag(surah_base, prefix="Surah"),
        make_hashtag(reciter_label),
    ]
    deduped_hashtags: list[str] = []
    for hashtag in raw_hashtags:
        cleaned_hashtag = normalize_optional_text(hashtag)
        if cleaned_hashtag is None:
            continue
        if cleaned_hashtag.lower() in {existing.lower() for existing in deduped_hashtags}:
            continue
        deduped_hashtags.append(cleaned_hashtag)
    return deduped_hashtags[:10]


def build_youtube_tags(config: RenderConfig, extra_tags: tuple[str, ...]) -> list[str]:
    surah_label = normalize_optional_text(config.surah_name) or ""
    surah_base = re.sub(r"(?i)^surah\s+", "", surah_label).strip()
    reciter_label = normalize_optional_text(config.reciter_name) or ""
    raw_tags = [
        "quran",
        "shorts",
        "quran shorts",
        "quran recitation",
        "islam",
        "islamic shorts",
        config.surah_name,
        surah_base,
        config.verse_reference,
        f"{surah_base} quran" if surah_base else "",
        reciter_label,
        *(hashtag.lstrip("#") for hashtag in build_youtube_hashtags(config)),
        *extra_tags,
    ]
    deduped_tags: list[str] = []
    for tag in raw_tags:
        cleaned_tag = " ".join(str(tag).split()).strip()
        if not cleaned_tag:
            continue
        normalized = cleaned_tag.lower()
        if normalized in {existing.lower() for existing in deduped_tags}:
            continue
        deduped_tags.append(cleaned_tag[:30])
    return deduped_tags[:12]


def build_youtube_description(config: RenderConfig) -> str:
    custom_description = normalize_optional_text(config.description_text)
    if custom_description:
        return custom_description

    hashtags_line = " ".join(build_youtube_hashtags(config))
    lines = [
        build_youtube_title(config).replace(" #Shorts", ""),
        "",
        f"Surah: {config.surah_name}",
        f"Ayat: {config.verse_reference}",
    ]
    if config.reciter_name:
        lines.append(f"Reciter: {config.reciter_name}")
    if config.verse_text:
        lines.extend(["", "Arabic:", config.verse_text.strip()])
    if config.translation:
        lines.extend(["", "Meaning:", config.translation.strip()])
    if config.attribution_lines:
        lines.extend(["", *config.attribution_lines])
    lines.extend(["", "Listen, reflect, and share khayr.", "", hashtags_line])
    return "\n".join(lines).strip()


def generate_youtube_thumbnail(config: RenderConfig) -> Path | None:
    thumbnail_path = config.output_path.with_suffix(".jpg")
    if thumbnail_path.exists():
        return thumbnail_path

    bg_path = config.background_path
    if not bg_path or not bg_path.exists():
        return None

    arabic_surah = config.arabic_surah_name or config.surah_name
    arabic_reciter = ARABIC_RECITER_NAMES.get(config.reciter_name, config.reciter_name) if config.reciter_name else ""
    
    ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: SurahName,Noto Naskh Arabic,180,&Hffffff,&Hffffff,&Haa000000,&H66000000,1,0,0,0,100,100,0,0,1,0,18,5,0,0,250,1
Style: ReciterName,Noto Naskh Arabic,90,&Hffffff,&Hffffff,&Haa000000,&H66000000,1,0,0,0,100,100,0,0,1,0,12,5,0,0,650,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:05.00,SurahName,,0,0,0,,سورة {arabic_surah}
Dialogue: 0,0:00:00.00,0:00:05.00,ReciterName,,0,0,0,,بصوت {arabic_reciter}
"""
    ass_path = config.output_path.parent / f"{config.output_path.stem}_thumb.ass"
    ass_path.write_text(ass_content, encoding="utf-8-sig")

    ass_path_str = str(ass_path).replace('\\\\', '/').replace(':', '\\\\:')
    
    cmd = [
        "ffmpeg", "-y", "-i", str(bg_path),
        "-vframes", "1",
        "-vf", f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,ass='{ass_path_str}'",
        str(thumbnail_path)
    ]
    import subprocess
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError:
        pass
        
    try:
        ass_path.unlink(missing_ok=True)
    except Exception:
        pass
        
    return thumbnail_path if thumbnail_path.exists() else None


def upload_video_to_youtube(
    *,
    video_path: Path,
    config: RenderConfig,
    options: YouTubeUploadOptions,
    interactive_auth: bool,
) -> dict[str, str]:
    _, _, _, google_build, MediaFileUpload = import_youtube_client_modules()
    credentials = get_youtube_credentials(options, interactive=interactive_auth)
    youtube = google_build("youtube", "v3", credentials=credentials, cache_discovery=False)

    snippet = {
        "title": build_youtube_title(config),
        "description": build_youtube_description(config),
        "tags": build_youtube_tags(config, options.tags),
        "categoryId": options.category_id,
        "defaultLanguage": options.default_language,
    }
    status = {
        "privacyStatus": options.privacy_status,
        "selfDeclaredMadeForKids": options.made_for_kids,
    }
    if options.schedule_at is not None:
        status["publishAt"] = to_rfc3339(options.schedule_at)
        status["privacyStatus"] = "private"

    request = youtube.videos().insert(
        part="snippet,status",
        body={"snippet": snippet, "status": status},
        media_body=MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4"),
    )

    response = None
    while response is None:
        _, response = request.next_chunk()

    video_id = str(response["id"])

    print(f"Generating and uploading custom thumbnail for video {video_id}...")
    try:
        thumbnail_path = generate_youtube_thumbnail(config)
        if thumbnail_path and thumbnail_path.exists():
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumbnail_path), mimetype='image/jpeg', chunksize=-1, resumable=True)
            ).execute()
            print("Custom thumbnail uploaded successfully!")
        else:
            print("Failed to generate custom thumbnail.")
    except Exception as e:
        print(f"Error uploading thumbnail: {e}")

    return {
        "video_id": video_id,
        "watch_url": f"https://www.youtube.com/watch?v={video_id}",
        "privacy_status": status["privacyStatus"],
        "publish_at": status.get("publishAt", ""),
    }


def iter_background_library_dirs(base_dir: Path) -> list[Path]:
    desktop_dir = Path.home() / "Desktop"
    downloads_dir = Path.home() / "Downloads"
    candidates: list[Path] = [
        base_dir / LOCAL_BACKGROUND_LIBRARY_DIRNAME,
        base_dir / "inputs" / LOCAL_BACKGROUND_LIBRARY_DIRNAME,
        base_dir.parent / LOCAL_BACKGROUND_LIBRARY_DIRNAME,
        desktop_dir / LOCAL_BACKGROUND_LIBRARY_DIRNAME,
        downloads_dir / LOCAL_BACKGROUND_LIBRARY_DIRNAME,
    ]

    for search_root in (desktop_dir, downloads_dir):
        if not search_root.exists() or not search_root.is_dir():
            continue
        for child in search_root.iterdir():
            if child.is_dir():
                candidates.append(child / LOCAL_BACKGROUND_LIBRARY_DIRNAME)

    return candidates


def list_background_library_assets(base_dir: Path) -> list[Path]:
    supported_extensions = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
    assets: list[Path] = []
    seen_dirs: set[Path] = set()

    for library_dir in iter_background_library_dirs(base_dir):
        resolved_library_dir = library_dir.resolve()
        if resolved_library_dir in seen_dirs:
            continue
        seen_dirs.add(resolved_library_dir)

        if not resolved_library_dir.exists() or not resolved_library_dir.is_dir():
            continue

        assets.extend(
            candidate.resolve()
            for candidate in sorted(resolved_library_dir.rglob("*"))
            if candidate.is_file() and candidate.suffix.lower() in supported_extensions
        )

    return assets


def choose_random_library_background(base_dir: Path, *, excluded_paths: set[str] | None = None) -> Path | None:
    assets = list_background_library_assets(base_dir)
    if not assets:
        return None

    normalized_excluded = {str(Path(path).resolve()) for path in (excluded_paths or set())}
    filtered_assets = [asset for asset in assets if str(asset.resolve()) not in normalized_excluded]
    return random.choice(filtered_assets or assets)


def require_non_empty_text(value: object, field_name: str) -> str:
    cleaned = str(value).strip()
    if cleaned:
        return cleaned
    raise ValueError(f"'{field_name}' cannot be empty")


def normalize_reciter_key(value: str) -> str:
    normalized_characters = []
    for character in value.lower():
        if character.isalnum():
            normalized_characters.append(character)
        else:
            normalized_characters.append("_")

    collapsed = "".join(normalized_characters)
    while "__" in collapsed:
        collapsed = collapsed.replace("__", "_")
    return collapsed.strip("_")


def normalize_lookup_text(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


@lru_cache(maxsize=64)
def list_local_audio_library_files(base_dir_str: str) -> tuple[str, ...]:
    base_dir = Path(base_dir_str)
    if not base_dir.exists():
        return ()
    return tuple(
        str(candidate)
        for candidate in sorted(base_dir.rglob("*"))
        if candidate.is_file() and candidate.suffix.lower() in LOCAL_AUDIO_EXTENSIONS
    )


def candidate_matches_ayah(stem: str, ayah_number: int) -> bool:
    escaped_number = re.escape(str(ayah_number))
    lower_stem = stem.lower()
    patterns = (
        rf"(?:ayah|aya)\s*0*{escaped_number}(?!\d)",
        rf"(?<!\d)0*{escaped_number}(?!\d)$",
    )
    return any(re.search(pattern, lower_stem) for pattern in patterns)


def find_named_local_audio_file(
    base_dir: Path,
    *,
    chapter_number: int,
    chapter_name: str,
    ayah_number: int,
) -> Path | None:
    chapter_token = normalize_lookup_text(chapter_name)
    chapter_number_token = f"{chapter_number:03d}"
    candidate_files = list_local_audio_library_files(str(base_dir.resolve()))
    for candidate_str in candidate_files:
        candidate = Path(candidate_str)
        try:
            relative_candidate = candidate.relative_to(base_dir)
        except ValueError:
            relative_candidate = candidate

        lookup_parts = [normalize_lookup_text(part) for part in relative_candidate.parts[:-1]]
        stem_lookup = normalize_lookup_text(candidate.stem)
        chapter_match = any(
            token and (chapter_token in token or token in {chapter_token, chapter_number_token, str(chapter_number)})
            for token in lookup_parts
        )
        if not chapter_match and chapter_token:
            chapter_match = chapter_token in stem_lookup
        if not chapter_match:
            continue
        if candidate_matches_ayah(candidate.stem, ayah_number):
            return candidate
    return None


def local_audio_chapter_available(reciter: AutoReciter, *, chapter_number: int, chapter_name: str) -> bool:
    if reciter.audio_base_dir is None or reciter.recitation_id is not None:
        return False

    base_dir = reciter.audio_base_dir
    if reciter.recitation_relative_path:
        base_dir = base_dir / reciter.recitation_relative_path
    if not base_dir.exists():
        return False

    verse_code = f"{chapter_number:03d}001"
    for extension in LOCAL_AUDIO_EXTENSIONS:
        if (base_dir / f"{verse_code}{extension}").exists():
            return True
    return find_named_local_audio_file(
        base_dir,
        chapter_number=chapter_number,
        chapter_name=chapter_name,
        ayah_number=1,
    ) is not None


def get_auto_reciter_whole_surah_files(reciter: AutoReciter) -> dict[int, Path]:
    discovered_files = {
        chapter_number: audio_path
        for chapter_number, audio_path in reciter.chapter_audio_files.items()
        if audio_path.exists()
    }
    if not reciter.auto_detect_whole_surah_files or reciter.audio_base_dir is None:
        return discovered_files

    base_dir = reciter.audio_base_dir
    if reciter.recitation_relative_path:
        base_dir = base_dir / reciter.recitation_relative_path
    if not base_dir.exists():
        return discovered_files

    for extension in LOCAL_AUDIO_EXTENSIONS:
        for candidate in base_dir.glob(f"*{extension}"):
            if not candidate.is_file():
                continue
            stem = candidate.stem.strip()
            if not re.fullmatch(r"\d{3}", stem):
                continue
            discovered_files.setdefault(int(stem), candidate)
    return discovered_files


def ensure_auto_reciter_source_material(reciter: AutoReciter) -> None:
    if reciter.download_script is None:
        return

    if get_auto_reciter_whole_surah_files(reciter):
        return

    if reciter.audio_base_dir is not None:
        base_dir = reciter.audio_base_dir
        if reciter.recitation_relative_path:
            base_dir = base_dir / reciter.recitation_relative_path
        if base_dir.exists() and not reciter.showcase_only:
            for extension in LOCAL_AUDIO_EXTENSIONS:
                if any(base_dir.rglob(f"*{extension}")):
                    return

    print(f"[AutoReciter] Downloading source audio for {reciter.reciter_name}...")
    try:
        subprocess.run([sys.executable, str(reciter.download_script)], check=True)
    except subprocess.CalledProcessError as error:
        raise RuntimeError(
            f"Failed to download source audio for '{reciter.reciter_name}' using {reciter.download_script}. "
            "Make sure the downloader script works and that required tools like yt-dlp are installed."
        ) from error


def list_auto_reciter_downloadable_chapters(reciter: AutoReciter) -> dict[int, dict[str, object]]:
    if reciter.download_script is None:
        return {}

    try:
        process = subprocess.run(
            [sys.executable, str(reciter.download_script), "--list-json"],
            capture_output=True,
            check=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.CalledProcessError:
        return {}

    try:
        payload = json.loads(process.stdout)
    except json.JSONDecodeError:
        return {}

    if not isinstance(payload, dict):
        return {}

    discovered: dict[int, dict[str, object]] = {}
    for raw_key, raw_value in payload.items():
        try:
            chapter_number = int(str(raw_key).strip())
        except ValueError:
            continue
        if not isinstance(raw_value, dict):
            continue
        discovered[chapter_number] = raw_value
    return discovered


def ensure_auto_reciter_chapter_audio(reciter: AutoReciter, *, chapter_number: int) -> Path | None:
    whole_surah_files = get_auto_reciter_whole_surah_files(reciter)
    existing_audio = whole_surah_files.get(chapter_number)
    if existing_audio is not None and existing_audio.exists():
        return existing_audio

    if reciter.download_script is None:
        return None

    try:
        subprocess.run([sys.executable, str(reciter.download_script), str(chapter_number)], check=True)
    except subprocess.CalledProcessError as error:
        raise RuntimeError(
            f"Failed to download chapter {chapter_number} for '{reciter.reciter_name}' using {reciter.download_script}."
        ) from error

    refreshed_audio = get_auto_reciter_whole_surah_files(reciter).get(chapter_number)
    if refreshed_audio is not None and refreshed_audio.exists():
        return refreshed_audio
    return None


def get_builtin_recitation_source(reciter_key: str) -> VerseRecitationSource:
    normalized_key = normalize_reciter_key(reciter_key)
    source = BUILTIN_VERSE_RECITATIONS.get(normalized_key)
    if source:
        return source

    available_keys = ", ".join(sorted({"alafasy", "abdulbaset_mujawwad"}))
    raise ValueError(
        f"Unsupported reciter_key '{reciter_key}'. Use one of: {available_keys}, "
        "or provide 'recitation_relative_path' directly."
    )


def resolve_drawtext_font_file(font_file: Path | None) -> Path | None:
    target = font_file
    if target is None:
        target = find_project_arabic_font()
    if not target and sys.platform.startswith("win"):
        for candidate in WINDOWS_ARABIC_FONT_FALLBACKS:
            if candidate.exists():
                target = candidate
                break

    if target:
        return target.resolve()
    return None


def ensure_binary(binary_name: str) -> None:
    resolve_binary_command(binary_name)


@lru_cache(maxsize=None)
def resolve_binary_command(binary_name: str) -> str:
    command_in_path = shutil.which(binary_name)
    if command_in_path:
        return command_in_path

    if sys.platform.startswith("win"):
        fallback_path = find_windows_binary(binary_name)
        if fallback_path:
            return str(fallback_path)

    raise FileNotFoundError(
        f"'{binary_name}' was not found in PATH. Install FFmpeg and make sure both ffmpeg and ffprobe are available."
    )


def find_windows_binary(binary_name: str) -> Path | None:
    executable_name = f"{binary_name}.exe"
    fallback_candidates = [
        Path.home() / "AppData/Local/Microsoft/WinGet/Links" / executable_name,
        Path("C:/ffmpeg/bin") / executable_name,
        Path("C:/Program Files/ffmpeg/bin") / executable_name,
        Path("C:/Program Files/WinGet/Links") / executable_name,
    ]

    for candidate in fallback_candidates:
        if candidate.exists():
            return candidate

    packages_root = Path.home() / "AppData/Local/Microsoft/WinGet/Packages"
    if not packages_root.exists():
        return None

    package_patterns = [
        "Gyan.FFmpeg_*",
        "Gyan.FFmpeg.Shared_*",
    ]

    for package_pattern in package_patterns:
        for package_dir in sorted(packages_root.glob(package_pattern), reverse=True):
            build_dirs = sorted(package_dir.glob("ffmpeg-*"), reverse=True)
            for build_dir in build_dirs:
                candidate = build_dir / "bin" / executable_name
                if candidate.exists():
                    return candidate

    return None


def pad_audio_to_duration(
    audio_path: Path,
    *,
    target_seconds: float,
    ffmpeg_command: str,
    ffprobe_command: str,
) -> Path:
    if target_seconds <= 0:
        return audio_path
    duration = probe_duration(audio_path, ffprobe_command)
    if duration >= (target_seconds - 0.05):
        return audio_path

    padded_path = audio_path.with_name(f"{audio_path.stem}-pad{audio_path.suffix}")
    pad_duration = max(0.0, target_seconds - duration)
    filter_chain = f"apad=pad_dur={pad_duration:.3f},atrim=0:{target_seconds:.3f}"
    command = [
        ffmpeg_command,
        "-y",
        "-i",
        str(audio_path),
        "-filter_complex",
        filter_chain,
        "-t",
        f"{target_seconds:.3f}",
        str(padded_path),
    ]
    run_command(command)
    return padded_path


def build_verse_audio_url(
    relative_path: str,
    surah_number: int,
    ayah_number: int,
    *,
    base_url: str = VERSES_AUDIO_BASE_URL,
) -> str:
    cleaned_relative_path = relative_path.strip().strip("/")
    if not cleaned_relative_path:
        raise ValueError("'recitation_relative_path' cannot be empty")

    cleaned_base_url = require_non_empty_text(base_url, "audio_base_url").rstrip("/")
    verse_code = f"{surah_number:03d}{ayah_number:03d}.mp3"
    return f"{cleaned_base_url}/{cleaned_relative_path}/{verse_code}"


VERSE_REFERENCE_RANGE_PATTERN = re.compile(r"^\s*(\d+)\s*:\s*(\d+)(?:\s*-\s*(\d+))?\s*$")


def parse_verse_reference_range(verse_reference: str) -> tuple[int, int, int]:
    match = VERSE_REFERENCE_RANGE_PATTERN.fullmatch(verse_reference.strip())
    if match is None:
        raise ValueError(
            "Facebook audio overrides require a numeric verse_reference like '99:1' or '99:1-8'."
        )

    chapter_number = int(match.group(1))
    verse_start = int(match.group(2))
    verse_end = int(match.group(3) or verse_start)
    if verse_end < verse_start:
        raise ValueError("verse_reference range cannot end before it starts.")
    return chapter_number, verse_start, verse_end


def resolve_facebook_recitation_source(page_config: FacebookPageConfig) -> tuple[str, str | None] | None:
    explicit_relative_path = normalize_optional_text(page_config.recitation_relative_path)
    if explicit_relative_path:
        return explicit_relative_path, normalize_optional_text(page_config.reciter_name)

    reciter_key = normalize_optional_text(page_config.reciter_key)
    if reciter_key is None:
        return None

    source = get_builtin_recitation_source(reciter_key)
    return source.relative_path, normalize_optional_text(page_config.reciter_name) or source.reciter_name


def build_facebook_timed_segments(
    config: RenderConfig,
    verse_durations: list[float],
) -> list[TimedSegment] | None:
    if config.timed_segments is None:
        return None

    if len(config.timed_segments) != len(verse_durations):
        raise RuntimeError(
            "Facebook audio override requires one timed segment per verse so timings can be rebuilt cleanly."
        )

    rebuilt_segments: list[TimedSegment] = []
    cursor = 0.0
    for template_segment, duration in zip(config.timed_segments, verse_durations):
        rebuilt_segments.append(
            TimedSegment(
                arabic=template_segment.arabic,
                translation=template_segment.translation,
                start_time=cursor,
                end_time=cursor + duration,
            )
        )
        cursor += duration
    return rebuilt_segments


def resolve_facebook_override_audio_path(
    chapter_override: FacebookChapterAudioOverride,
    *,
    cache_dir: Path,
) -> Path:
    if chapter_override.audio_path is not None:
        if not chapter_override.audio_path.exists():
            raise FileNotFoundError(f"Facebook chapter audio file not found: {chapter_override.audio_path}")
        return chapter_override.audio_path
    if chapter_override.audio_url is not None:
        return download_asset(chapter_override.audio_url, cache_dir / "facebook_chapter_audio", "audio")
    raise RuntimeError("Facebook chapter audio override is missing both audio_path and audio_url.")


def trim_audio_segment(
    input_path: Path,
    output_path: Path,
    *,
    start_time: float,
    end_time: float,
    ffmpeg_command: str,
) -> Path:
    if end_time <= start_time:
        raise RuntimeError("Facebook chapter audio timings produced an empty clip.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg_command,
        "-y",
        "-ss",
        f"{start_time:.3f}",
        "-to",
        f"{end_time:.3f}",
        "-i",
        str(input_path),
        "-vn",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(output_path),
    ]
    subprocess.run(command, check=True)
    return output_path


def build_facebook_render_config_from_chapter_audio(
    config: RenderConfig,
    *,
    chapter_override: FacebookChapterAudioOverride,
    chapter_number: int,
    verse_start: int,
    verse_end: int,
    base_dir: Path,
    credit_lines: tuple[str, ...] = (),
) -> RenderConfig:
    if verse_end > len(chapter_override.verse_durations):
        raise RuntimeError(
            f"Facebook chapter_audio_overrides[{chapter_number}] does not cover verse {verse_end}."
        )

    cache_dir = (base_dir / DEFAULT_CACHE_DIR).resolve()
    ffmpeg_command = resolve_binary_command("ffmpeg")
    chapter_audio_path = resolve_facebook_override_audio_path(chapter_override, cache_dir=cache_dir)
    verse_durations = list(chapter_override.verse_durations[verse_start - 1 : verse_end])
    clip_start = sum(chapter_override.verse_durations[: verse_start - 1])
    clip_end = sum(chapter_override.verse_durations[:verse_end])
    facebook_audio_path = cache_dir / "compiled_audio" / f"{config.output_path.stem}-facebook-audio.m4a"
    facebook_output_path = config.output_path.with_name(f"{config.output_path.stem}-facebook{config.output_path.suffix}")
    trim_audio_segment(
        chapter_audio_path,
        facebook_audio_path,
        start_time=clip_start,
        end_time=clip_end,
        ffmpeg_command=ffmpeg_command,
    )

    return replace(
        config,
        audio_path=facebook_audio_path,
        output_path=facebook_output_path,
        reciter_name=chapter_override.reciter_name or config.reciter_name,
        timed_segments=build_facebook_timed_segments(config, verse_durations),
        facebook_credit_lines=credit_lines,
    )


def build_facebook_render_config(
    config: RenderConfig,
    *,
    page_config: FacebookPageConfig,
    base_dir: Path,
) -> RenderConfig:
    merged_credit_lines = merge_credit_lines(config.facebook_credit_lines, page_config.credit_lines)
    try:
        chapter_number, verse_start, verse_end = parse_verse_reference_range(config.verse_reference)
    except ValueError:
        # Showcase/full-surah clips already have their audio prepared locally, so
        # Facebook should reuse that clip instead of requiring verse-by-verse
        # override timings.
        return replace(config, facebook_credit_lines=merged_credit_lines)

    chapter_override = page_config.chapter_audio_overrides.get(chapter_number)
    if chapter_override is not None:
        return build_facebook_render_config_from_chapter_audio(
            config,
            chapter_override=chapter_override,
            chapter_number=chapter_number,
            verse_start=verse_start,
            verse_end=verse_end,
            base_dir=base_dir,
            credit_lines=page_config.credit_lines,
        )

    recitation_source = resolve_facebook_recitation_source(page_config)
    if recitation_source is None:
        return replace(config, facebook_credit_lines=merged_credit_lines)

    relative_path, override_reciter_name = recitation_source
    cache_dir = (base_dir / DEFAULT_CACHE_DIR).resolve()
    ffmpeg_command = resolve_binary_command("ffmpeg")
    ffprobe_command = resolve_binary_command("ffprobe")
    verse_audio_paths: list[Path] = []
    verse_durations: list[float] = []

    for ayah_number in range(verse_start, verse_end + 1):
        audio_url = build_verse_audio_url(
            relative_path,
            chapter_number,
            ayah_number,
            base_url=page_config.audio_base_url,
        )
        audio_path = download_asset(audio_url, cache_dir / "facebook_audio", "audio")
        verse_audio_paths.append(audio_path)
        verse_durations.append(probe_duration(audio_path, ffprobe_command))

    facebook_audio_path = cache_dir / "compiled_audio" / f"{config.output_path.stem}-facebook-audio.m4a"
    concatenate_audio_files(verse_audio_paths, facebook_audio_path, ffmpeg_command)
    facebook_output_path = config.output_path.with_name(f"{config.output_path.stem}-facebook{config.output_path.suffix}")

    return replace(
        config,
        audio_path=facebook_audio_path,
        output_path=facebook_output_path,
        reciter_name=override_reciter_name or config.reciter_name,
        timed_segments=build_facebook_timed_segments(config, verse_durations),
        facebook_credit_lines=merged_credit_lines,
    )


def sanitize_filename_part(value: str) -> str:
    safe_characters = []
    for character in value.lower():
        if character.isalnum():
            safe_characters.append(character)
        elif character in {"-", "_"}:
            safe_characters.append(character)
        else:
            safe_characters.append("-")

    cleaned = "".join(safe_characters).strip("-")
    return cleaned or "asset"


def get_extension_from_url(url: str) -> str:
    path = Path(unquote(urlparse(url).path))
    suffix = path.suffix.lower()
    if suffix and len(suffix) <= 10:
        return suffix
    return ""


def get_extension_from_content_type(content_type: str, asset_name: str) -> str:
    normalized = content_type.split(";", maxsplit=1)[0].strip().lower()
    if normalized in CONTENT_TYPE_EXTENSIONS:
        return CONTENT_TYPE_EXTENSIONS[normalized]

    guessed = mimetypes.guess_extension(normalized)
    if guessed:
        return guessed

    return DEFAULT_DOWNLOAD_EXTENSIONS[asset_name]


def download_asset(url: str, cache_dir: Path, asset_name: str) -> Path:
    candidate_urls = (url,)
    if asset_name == "font":
        candidate_urls = DEFAULT_FONT_URL_FALLBACKS.get(url, (url,))

    cache_dir.mkdir(parents=True, exist_ok=True)

    for candidate_url in candidate_urls:
        asset_hash = hashlib.sha1(candidate_url.encode("utf-8")).hexdigest()[:12]
        existing_matches = sorted(cache_dir.glob(f"{asset_name}-*-{asset_hash}.*"))
        if existing_matches:
            return existing_matches[0]

    errors: list[str] = []
    for candidate_url in candidate_urls:
        parsed_url = urlparse(candidate_url)
        source_name = Path(unquote(parsed_url.path)).stem or asset_name
        safe_name = sanitize_filename_part(source_name)
        request = Request(candidate_url, headers={"User-Agent": "shortQuran/1.0"})
        asset_hash = hashlib.sha1(candidate_url.encode("utf-8")).hexdigest()[:12]

        try:
            print(f"Downloading {asset_name} from {candidate_url}")
            with urlopen(request, timeout=60) as response:
                content_type = response.headers.get_content_type()
                extension = get_extension_from_url(candidate_url) or get_extension_from_content_type(content_type, asset_name)
                target_path = cache_dir / f"{asset_name}-{safe_name}-{asset_hash}{extension}"
                temp_path = target_path.with_suffix(f"{target_path.suffix}.part")

                with temp_path.open("wb") as temp_file:
                    shutil.copyfileobj(response, temp_file)

                temp_path.replace(target_path)
                return target_path
        except (OSError, URLError) as error:
            errors.append(f"{candidate_url}: {error}")

    raise RuntimeError(f"Failed to download {asset_name}. Tried: {' | '.join(errors)}")


def build_quran_api_url(path: str, query: dict[str, object] | None = None) -> str:
    normalized_query = {}
    for key, value in (query or {}).items():
        if value is None:
            continue
        normalized_query[key] = value

    query_string = urlencode(normalized_query, doseq=True)
    if query_string:
        return f"{QURAN_API_BASE_URL}{path}?{query_string}"
    return f"{QURAN_API_BASE_URL}{path}"


def fetch_json(url: str) -> dict[str, object]:
    request = Request(
        url,
        headers={
            "User-Agent": "shortQuran/1.0",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Failed to fetch JSON from {url}: {error}") from error


def fetch_quran_api_json(path: str, query: dict[str, object] | None = None) -> dict[str, object]:
    return fetch_json(build_quran_api_url(path, query))


def fetch_public_translation_map(
    chapter_number: int,
    *,
    edition: str = DEFAULT_PUBLIC_TRANSLATION_EDITION,
) -> dict[str, str]:
    payload = fetch_json(f"{PUBLIC_TRANSLATION_API_BASE_URL}/surah/{chapter_number}/{edition}")
    data = payload.get("data")
    if not isinstance(data, dict):
        return {}

    ayahs = data.get("ayahs")
    if not isinstance(ayahs, list):
        return {}

    translation_map: dict[str, str] = {}
    for ayah in ayahs:
        if not isinstance(ayah, dict):
            continue

        verse_number = ayah.get("numberInSurah")
        if verse_number is None:
            continue

        text = normalize_optional_text(ayah.get("text"))
        if text is None:
            continue

        translation_map[f"{chapter_number}:{int(verse_number)}"] = clean_translation_text(text)

    return translation_map


def clean_translation_text(text: str) -> str:
    without_tags = re.sub(r"<[^>]+>", "", text)
    cleaned = html.unescape(without_tags)
    cleaned = re.sub(r"\[[^\]]+\]", "", cleaned)
    return " ".join(cleaned.split())


def normalize_audio_download_url(url: str) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"{VERSES_AUDIO_BASE_URL}{url.lstrip('/')}"


def get_verse_number_from_key(verse_key: str) -> int:
    _, _, verse_number = verse_key.partition(":")
    return int(verse_number)


def parse_int_fallback(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        cleaned = re.sub(r"\D", "", value)
        if cleaned:
            return int(cleaned)
    return 0


def fetch_auto_chapters() -> list[dict[str, object]]:
    payload = fetch_quran_api_json("/chapters")
    chapters = payload.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        raise RuntimeError("Quran API did not return any chapters.")
    return chapters


def chapter_meets_minimum_verses(chapter: dict[str, object], minimum_verses: int) -> bool:
    chapter_id = parse_int_fallback(
        chapter.get("id")
        or chapter.get("chapter_id")
        or chapter.get("chapter_number")
    )
    verses_count = parse_int_fallback(
        chapter.get("verses_count")
        or chapter.get("verses")
    )

    if verses_count:
        return verses_count >= minimum_verses
    if chapter_id in LONG_SURAH_IDS:
        return True
    return False


def fetch_auto_reciters() -> list[AutoReciter]:
    reciters: list[AutoReciter] = []
    for key, source in BUILTIN_VERSE_RECITATIONS.items():
        reciters.append(AutoReciter(
            reciter_name=source.reciter_name,
            recitation_id=None,
            recitation_relative_path=source.relative_path,
            audio_base_url=VERSES_AUDIO_BASE_URL,
        ))
    return reciters


def fetch_all_chapter_verses(
    chapter_number: int,
    *,
    verses_count: int,
    translation_id: int,
) -> list[dict[str, object]]:
    verse_pages = max(1, math.ceil(verses_count / 50))
    verses: list[dict[str, object]] = []
    for page in range(1, verse_pages + 1):
        verses.extend(fetch_chapter_verses_page(chapter_number, page=page, translation_id=translation_id))
    return verses


def chapter_starts_with_basmala(chapter_number: int) -> bool:
    return chapter_number not in {1, 9}


def load_auto_reciters_from_library(library_path: Path) -> list[AutoReciter]:
    if not library_path.exists():
        raise FileNotFoundError(f"Auto reciter library file not found: {library_path}")

    try:
        payload = json.loads(library_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Failed to read auto reciter library from {library_path}: {error}") from error

    if not isinstance(payload, dict):
        raise RuntimeError(f"Auto reciter library at {library_path} must be a JSON object.")

    raw_reciters = payload.get("reciters")
    if not isinstance(raw_reciters, list) or not raw_reciters:
        raise RuntimeError("Auto reciter library must include a non-empty 'reciters' array.")

    reciters: list[AutoReciter] = []
    for index, item in enumerate(raw_reciters, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(f"auto reciters[{index}] must be a JSON object.")

        reciter_name = require_non_empty_text(item.get("name", ""), f"auto reciters[{index}].name")
        recitation_relative_path = normalize_optional_text(item.get("recitation_relative_path"))
        recitation_id_value = item.get("recitation_id")
        recitation_id = int(recitation_id_value) if recitation_id_value is not None else None
        audio_base_url = normalize_optional_text(item.get("audio_base_url")) or VERSES_AUDIO_BASE_URL
        audio_base_dir = resolve_optional_local_path(library_path.parent, item.get("audio_base_dir"))
        download_script = resolve_optional_local_path(library_path.parent, item.get("download_script"))
        if download_script is not None and not download_script.exists():
            raise FileNotFoundError(
                f"auto reciters[{index}].download_script was not found: {download_script}"
            )
        raw_auto_detect_whole_surah_files = item.get("auto_detect_whole_surah_files")
        if raw_auto_detect_whole_surah_files is None:
            auto_detect_whole_surah_files = False
        elif isinstance(raw_auto_detect_whole_surah_files, bool):
            auto_detect_whole_surah_files = raw_auto_detect_whole_surah_files
        else:
            raise RuntimeError(f"auto reciters[{index}].auto_detect_whole_surah_files must be true or false.")
        raw_whole_surah_includes_basmala = item.get("whole_surah_includes_basmala")
        if raw_whole_surah_includes_basmala is None:
            whole_surah_includes_basmala = True
        elif isinstance(raw_whole_surah_includes_basmala, bool):
            whole_surah_includes_basmala = raw_whole_surah_includes_basmala
        else:
            raise RuntimeError(f"auto reciters[{index}].whole_surah_includes_basmala must be true or false.")
        raw_chapter_audio_files = item.get("chapter_audio_files")
        chapter_audio_files: dict[int, Path] = {}
        if raw_chapter_audio_files is not None:
            if not isinstance(raw_chapter_audio_files, dict):
                raise RuntimeError(f"auto reciters[{index}].chapter_audio_files must be a JSON object.")
            for raw_key, raw_value in raw_chapter_audio_files.items():
                try:
                    chapter_number = int(str(raw_key).strip())
                except ValueError as error:
                    raise RuntimeError(
                        f"auto reciters[{index}].chapter_audio_files key '{raw_key}' must be a surah number."
                    ) from error
                chapter_audio_path = resolve_optional_local_path(library_path.parent, raw_value)
                if chapter_audio_path is None:
                    raise RuntimeError(
                        f"auto reciters[{index}].chapter_audio_files[{chapter_number}] must point to a local file."
                    )
                if not chapter_audio_path.exists():
                    raise FileNotFoundError(
                        f"auto reciters[{index}].chapter_audio_files[{chapter_number}] was not found: {chapter_audio_path}"
                    )
                chapter_audio_files[chapter_number] = chapter_audio_path
        attribution_lines = parse_string_lines(
            item.get("attribution_lines"),
            context=f"auto reciters[{index}].attribution_lines",
        )
        reciter_name_arabic = normalize_optional_text(item.get("reciter_name_arabic"))
        showcase_only = bool(item.get("showcase_only", False))

        has_whole_surah_source = bool(chapter_audio_files) or (auto_detect_whole_surah_files and audio_base_dir is not None)

        if not showcase_only and recitation_id is None and recitation_relative_path is None and not chapter_audio_files:
            raise RuntimeError(
                f"auto reciters[{index}] must include recitation_id, recitation_relative_path, or chapter_audio_files."
            )
        if showcase_only and not has_whole_surah_source:
            raise RuntimeError(
                f"auto reciters[{index}] with showcase_only=true must include chapter_audio_files or auto-detected whole-surah files."
            )

        reciters.append(
            AutoReciter(
                reciter_name=reciter_name,
                recitation_id=recitation_id,
                recitation_relative_path=recitation_relative_path,
                audio_base_url=audio_base_url,
                audio_base_dir=audio_base_dir,
                download_script=download_script,
                chapter_audio_files=chapter_audio_files,
                auto_detect_whole_surah_files=auto_detect_whole_surah_files,
                whole_surah_includes_basmala=whole_surah_includes_basmala,
                attribution_lines=attribution_lines,
                reciter_name_arabic=reciter_name_arabic,
                showcase_only=showcase_only,
            )
        )

    return reciters


def fetch_pexels_nature_video(cache_dir: Path, pexels_api_key: str) -> Path | None:
    """Fetch a random nature video from Pexels API and cache it locally."""
    query = random.choice(PEXELS_NATURE_QUERIES)
    orientation = 'landscape' if globals().get('IS_LANDSCAPE') else 'portrait'
    url = f"{PEXELS_API_BASE_URL}/search?query={query.replace(' ', '+')}&per_page=15&orientation={orientation}"
    try:
        request = Request(url, headers={"Authorization": pexels_api_key, "User-Agent": "shortQuran/1.0"})
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as error:  # noqa: BLE001
        print(f"[Pexels] Failed to search videos: {error}")
        return None

    videos = payload.get("videos")
    if not isinstance(videos, list) or not videos:
        print(f"[Pexels] No videos found for query: {query}")
        return None

    # Filter to portrait/tall videos only, pick random
    tall_videos = [v for v in videos if isinstance(v, dict) and int(v.get("height", 0)) >= int(v.get("width", 1))]
    chosen = random.choice(tall_videos or videos)
    video_files = chosen.get("video_files") if isinstance(chosen, dict) else None
    if not isinstance(video_files, list) or not video_files:
        return None

    # Prefer HD (1080p) portrait files
    sorted_files = sorted(
        [f for f in video_files if isinstance(f, dict) and f.get("link")],
        key=lambda f: abs(int(f.get("height", 0)) - 1920),
    )
    chosen_file = sorted_files[0] if sorted_files else None
    if chosen_file is None:
        return None

    video_url = str(chosen_file["link"])
    video_id = str(chosen.get("id", "unknown"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached_path = cache_dir / f"pexels_{video_id}.mp4"
    if cached_path.exists():
        print(f"[Pexels] Using cached video: {cached_path.name}")
        return cached_path

    print(f"[Pexels] Downloading nature video: {video_id} ({query})")
    try:
        request = Request(video_url, headers={"User-Agent": "shortQuran/1.0"})
        with urlopen(request, timeout=60) as response:
            cached_path.write_bytes(response.read())
        print(f"[Pexels] Saved to {cached_path.name}")
        return cached_path
    except Exception as error:  # noqa: BLE001
        print(f"[Pexels] Failed to download video: {error}")
        if cached_path.exists():
            cached_path.unlink()
        return None


def load_pexels_api_key(base_dir: Path) -> str | None:
    """Load Pexels API key from .secrets/pexels-api-key.txt"""
    key_path = (base_dir / DEFAULT_PEXELS_API_KEY_FILE).resolve()
    if not key_path.exists():
        return None
    key = key_path.read_text(encoding="utf-8").strip()
    return key or None


def finalize_showcase_render_config(
    *,
    base_dir: Path,
    index: int,
    history_entries: list[dict[str, object]],
    chapter_number: int,
    chapter_name: str,
    arabic_surah_name: str,
    reciter: AutoReciter,
    audio_path: Path,
    target_seconds: float,
    ffmpeg_command: str,
    ffprobe_command: str,
) -> RenderConfig:
    """Build a showcase-style RenderConfig capped to the requested short duration."""
    cache_dir = (base_dir / DEFAULT_CACHE_DIR).resolve()
    output_dir = (base_dir / "outputs").resolve()

    source_duration = probe_duration(audio_path, ffprobe_command)
    clipped_duration = min(source_duration, max(1.0, target_seconds))
    output_audio_path = audio_path
    clip_start_seconds = 0.0
    clip_end_seconds = clipped_duration
    if source_duration > clipped_duration + 0.05:
        clip_start_seconds, clip_end_seconds = choose_showcase_clip_window(
            history_entries=history_entries,
            chapter_number=chapter_number,
            reciter_name=reciter.reciter_name,
            source_duration=source_duration,
            clip_duration=clipped_duration,
        )
        output_audio_path = cache_dir / "compiled_audio" / build_auto_output_path(
            cache_dir / "compiled_audio",
            chapter_number=chapter_number,
            verse_start=1,
            verse_end=0,
            chapter_name=chapter_name,
            reciter_name=reciter.reciter_name,
            index=index,
        ).with_suffix(".m4a").name
        trim_audio_segment(
            audio_path,
            output_audio_path,
            start_time=clip_start_seconds,
            end_time=clip_end_seconds,
            ffmpeg_command=ffmpeg_command,
        )
    combo_key = f"{chapter_number}:showcase:{sanitize_filename_part(reciter.reciter_name)}"
    output_path = build_auto_output_path(
        output_dir,
        chapter_number=chapter_number,
        verse_start=1,
        verse_end=0,
        chapter_name=chapter_name,
        reciter_name=reciter.reciter_name,
        index=index,
    )

    # Prefer user-provided local backgrounds first, then fall back to Pexels/default.
    background_path: Path | None = None
    used_background_paths = {
        normalize_optional_text(entry.get("background_path"))
        for entry in history_entries
        if isinstance(entry, dict)
    }
    background_path = choose_random_library_background(
        base_dir,
        excluded_paths={path for path in used_background_paths if path},
    )
    if background_path is None:
        pexels_key = load_pexels_api_key(base_dir)
        if pexels_key:
            pexels_cache = cache_dir / "pexels"
            background_path = fetch_pexels_nature_video(pexels_cache, pexels_key)
    if background_path is None:
        background_path = download_asset(DEFAULT_BACKGROUND_URL, cache_dir / "background", "background")

    font_file = resolve_default_arabic_font_file(base_dir, cache_dir)
    latin_font_file = download_asset(DEFAULT_LATIN_FONT_URL, cache_dir / "font", "font")

    import random
    hook_template_key = random.choice(list(AUTO_TITLE_HOOKS))
    hook_text = AUTO_TITLE_HOOKS[hook_template_key]
    arabic_reciter = ARABIC_RECITER_NAMES.get(reciter.reciter_name, reciter.reciter_name)
    title_text = f"{hook_text} | سورة {arabic_surah_name} كاملة | {arabic_reciter}"
    history_entry = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "combo_key": combo_key,
        "chapter_number": chapter_number,
        "chapter_name": chapter_name,
        "verse_reference": f"{chapter_number}:full",
        "reciter_name": reciter.reciter_name,
        "attribution_lines": list(reciter.attribution_lines),
        "background_path": str(background_path.resolve()) if background_path is not None else "",
        "style_preset": SHOWCASE_STYLE,
        "title_text": title_text,
        "planned_duration_seconds": round(clipped_duration, 2),
        "source_duration_seconds": round(source_duration, 2),
        "clip_start_seconds": round(clip_start_seconds, 2),
        "clip_end_seconds": round(clip_end_seconds, 2),
        "output_path": str(output_path),
    }

    return RenderConfig(
        audio_path=output_audio_path,
        output_path=output_path,
        verse_text="",
        surah_name=chapter_name,
        verse_reference=f"{chapter_number}:full",
        translation=None,
        reciter_name=reciter.reciter_name,
        background_path=background_path,
        font_file=font_file,
        latin_font_file=latin_font_file,
        brand_text="shortQuran",
        title_text=title_text,
        fps=DEFAULT_FPS,
        timed_segments=None,
        prefer_static_text_overlay=False,
        show_meta=False,
        show_brand=False,
        style_preset=SHOWCASE_STYLE,
        auto_history_entry=history_entry,
        attribution_lines=reciter.attribution_lines,
        arabic_surah_name=arabic_surah_name,
        arabic_reciter_name=reciter.reciter_name_arabic,
    )


def fetch_chapter_verses_page(
    chapter_number: int,
    *,
    page: int,
    translation_id: int,
) -> list[dict[str, object]]:
    payload = fetch_quran_api_json(
        f"/verses/by_chapter/{chapter_number}",
        {
            "page": page,
            "per_page": 50,
            "translations": translation_id,
            "words": "false",
            "fields": "text_uthmani",
        },
    )
    verses = payload.get("verses")
    if not isinstance(verses, list):
        raise RuntimeError(f"Invalid verse payload returned for chapter {chapter_number}.")
    return verses


def fetch_chapter_audio_page(chapter_number: int, *, page: int, recitation_id: int) -> dict[str, str]:
    payload = fetch_quran_api_json(
        f"/recitations/{recitation_id}/by_chapter/{chapter_number}",
        {
            "page": page,
            "per_page": 50,
        },
    )
    audio_files = payload.get("audio_files")
    if not isinstance(audio_files, list):
        raise RuntimeError(f"Invalid audio payload returned for chapter {chapter_number}.")

    audio_map: dict[str, str] = {}
    for item in audio_files:
        if not isinstance(item, dict):
            continue
        verse_key = normalize_optional_text(item.get("verse_key"))
        audio_url = normalize_optional_text(item.get("url"))
        if verse_key and audio_url:
            audio_map[verse_key] = normalize_audio_download_url(audio_url)

    return audio_map


def resolve_auto_reciter_audio_source(
    reciter: AutoReciter,
    *,
    chapter_number: int,
    chapter_name: str,
    ayah_number: int,
) -> tuple[str | None, Path | None]:
    if reciter.recitation_id is not None:
        return None, None

    if reciter.recitation_relative_path is None:
        raise RuntimeError(f"Automatic reciter '{reciter.reciter_name}' is missing recitation_relative_path.")

    verse_code = f"{chapter_number:03d}{ayah_number:03d}"
    if reciter.audio_base_dir is not None:
        base_dir = reciter.audio_base_dir
        if reciter.recitation_relative_path:
            base_dir = base_dir / reciter.recitation_relative_path
        for extension in LOCAL_AUDIO_EXTENSIONS:
            candidate = base_dir / f"{verse_code}{extension}"
            if candidate.exists():
                return None, candidate
        named_candidate = find_named_local_audio_file(
            base_dir,
            chapter_number=chapter_number,
            chapter_name=chapter_name,
            ayah_number=ayah_number,
        )
        if named_candidate is not None:
            return None, named_candidate
        raise FileNotFoundError(
            f"Could not find local audio for {verse_code} under {base_dir} for reciter '{reciter.reciter_name}'."
        )

    return (
        build_verse_audio_url(
            reciter.recitation_relative_path,
            chapter_number,
            ayah_number,
            base_url=reciter.audio_base_url,
        ),
        None,
    )


def concatenate_audio_files(audio_paths: list[Path], output_path: Path, ffmpeg_command: str) -> Path:
    if not audio_paths:
        raise ValueError("No audio files were provided for concatenation.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="quran-audio-") as temp_folder:
        list_file = Path(temp_folder) / "concat.txt"
        entries = "\n".join(f"file '{audio_path.as_posix()}'" for audio_path in audio_paths)
        write_text_asset(list_file, entries)
        command = [
            ffmpeg_command,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-vn",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(output_path),
        ]
        subprocess.run(command, check=True)

    return output_path


def probe_duration(media_path: Path, ffprobe_command: str) -> float:
    command = [
        ffprobe_command,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(media_path),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return float(result.stdout.strip())


def estimate_whole_surah_verse_durations(
    verse_payloads: list[dict[str, object]],
    *,
    total_duration: float,
) -> list[float]:
    if not verse_payloads:
        raise ValueError("Whole-surah duration estimation requires at least one verse.")
    if total_duration <= 0:
        raise ValueError("Whole-surah duration estimation requires a positive duration.")

    weights: list[float] = []
    for verse_payload in verse_payloads:
        arabic = clean_quranic_text(normalize_optional_text(verse_payload.get("text_uthmani")) or "")
        word_count = len([word for word in arabic.split() if word.strip()])
        weights.append(float(max(word_count, 1)))

    total_weight = sum(weights) or float(len(weights))
    consumed = 0.0
    durations: list[float] = []
    for index, weight in enumerate(weights):
        if index == len(weights) - 1:
            duration = max(0.25, total_duration - consumed)
        else:
            duration = total_duration * (weight / total_weight)
            consumed += duration
        durations.append(duration)

    return durations


def estimate_intro_duration(
    *,
    total_duration: float,
    verse_payloads: list[dict[str, object]],
    intro_word_count: int,
) -> float:
    if total_duration <= 0:
        raise ValueError("Intro duration estimation requires a positive duration.")
    if intro_word_count <= 0:
        return 0.0

    verse_word_total = 0
    for verse_payload in verse_payloads:
        arabic = clean_quranic_text(normalize_optional_text(verse_payload.get("text_uthmani")) or "")
        verse_word_total += max(len([word for word in arabic.split() if word.strip()]), 1)

    total_weight = intro_word_count + max(verse_word_total, 1)
    estimated = total_duration * (intro_word_count / total_weight)
    return max(0.6, min(estimated, max(1.2, total_duration * 0.18)))


def whole_surah_duration_supported(audio_path: Path, ffprobe_command: str) -> bool:
    return probe_duration(audio_path, ffprobe_command) > 0


def build_auto_output_path(
    output_dir: Path,
    *,
    chapter_number: int,
    verse_start: int,
    verse_end: int,
    chapter_name: str,
    reciter_name: str,
    index: int,
) -> Path:
    verse_range = f"{verse_start:03d}" if verse_start == verse_end else f"{verse_start:03d}-{verse_end:03d}"
    chapter_slug = sanitize_filename_part(chapter_name)[:18].strip("-") or "surah"
    reciter_slug = sanitize_filename_part(reciter_name)[:18].strip("-") or "reciter"
    filename = f"auto-{index + 1:02d}-{chapter_number:03d}-{verse_range}-{chapter_slug}-{reciter_slug}.mp4"
    return output_dir / filename


def extract_translation_text(verse_payload: dict[str, object]) -> str:
    translations = verse_payload.get("translations")
    if not isinstance(translations, list) or not translations:
        return ""

    first_translation = translations[0]
    if not isinstance(first_translation, dict):
        return ""

    raw_text = normalize_optional_text(first_translation.get("text"))
    if raw_text is None:
        return ""
    return clean_translation_text(raw_text)


def collect_auto_verses(
    *,
    chapter_number: int,
    chapter_name: str,
    verses_count: int,
    reciter: AutoReciter,
    translation_id: int,
    translation_map: dict[str, str],
    target_seconds: float,
    cache_dir: Path,
    ffprobe_command: str,
) -> list[AutoVerse]:
    if verses_count <= 0:
        raise ValueError("Chapter does not contain any verses.")

    minimum_duration = min(AUTO_MIN_DURATION, max(10.0, target_seconds * 0.68))
    estimated_verses_needed = max(3, int(target_seconds // 6) + 1)
    max_start = max(1, verses_count - estimated_verses_needed + 1)
    effective_ceiling = target_seconds + AUTO_DURATION_OVERSHOOT_TOLERANCE

    is_whole_surah = globals().get('IS_WHOLE_SURAH')

    # Build a list of start positions to attempt.  When the first random pick
    # lands near the chapter end the audio may be too short; instead of
    # immediately failing (which wastes an outer retry) we try a few earlier
    # start positions first and fall back to ayah 1 on the last attempt.
    if is_whole_surah:
        start_candidates = [1]
    else:
        first_pick = random.randint(1, max_start)
        start_candidates = [first_pick]
        for _ in range(2):
            alt = random.randint(1, max_start)
            if alt not in start_candidates:
                start_candidates.append(alt)
        if 1 not in start_candidates:
            start_candidates.append(1)

    verses_cache: dict[int, list[dict[str, object]]] = {}
    audio_cache: dict[int, dict[str, str]] = {}
    best_verses: list[AutoVerse] = []
    best_duration = 0.0

    for start_ayah in start_candidates:
        current_ayah = start_ayah
        selected_verses: list[AutoVerse] = []
        total_duration = 0.0

        while current_ayah <= verses_count:
            page = ((current_ayah - 1) // 50) + 1
            if page not in verses_cache:
                verses_cache[page] = fetch_chapter_verses_page(chapter_number, page=page, translation_id=translation_id)
                if reciter.recitation_id is not None:
                    audio_cache[page] = fetch_chapter_audio_page(
                        chapter_number,
                        page=page,
                        recitation_id=reciter.recitation_id,
                    )
                else:
                    audio_cache[page] = {}

            verse_key = f"{chapter_number}:{current_ayah}"
            verse_payload = next((item for item in verses_cache[page] if item.get("verse_key") == verse_key), None)
            if verse_payload is None:
                raise RuntimeError(f"Could not find verse data for {verse_key}.")

            local_audio_path: Path | None = None
            audio_url = audio_cache[page].get(verse_key)
            if not audio_url and reciter.recitation_id is None:
                audio_url, local_audio_path = resolve_auto_reciter_audio_source(
                    reciter,
                    chapter_number=chapter_number,
                    chapter_name=chapter_name,
                    ayah_number=current_ayah,
                )
            if not audio_url and local_audio_path is None:
                raise RuntimeError(f"Could not find audio URL for {verse_key} with reciter {reciter.reciter_name}.")

            arabic = clean_quranic_text(require_non_empty_text(verse_payload.get("text_uthmani", ""), f"text_uthmani for {verse_key}"))
            translation = extract_translation_text(verse_payload) or translation_map.get(verse_key, "")
            audio_path = local_audio_path or download_asset(audio_url, cache_dir / "audio", "audio")
            duration = probe_duration(audio_path, ffprobe_command)

            if not is_whole_surah and selected_verses and (total_duration + duration) > effective_ceiling:
                break

            selected_verses.append(
                AutoVerse(
                    verse_key=verse_key,
                    arabic=arabic,
                    translation=translation,
                    audio_url=audio_url,
                    audio_path=audio_path,
                    duration=duration,
                )
            )
            total_duration += duration
            current_ayah += 1

            if not is_whole_surah and total_duration >= target_seconds:
                break

        if not selected_verses:
            continue

        candidate_duration = sum(verse.duration for verse in selected_verses)
        if candidate_duration >= minimum_duration:
            return selected_verses

        # Keep track of the best attempt in case none individually pass.
        if candidate_duration > best_duration:
            best_verses = selected_verses
            best_duration = candidate_duration

    # If the best attempt across all start positions still falls short, accept
    # it when it is at least 75 % of the minimum (a lenient fallback) to avoid
    # crashing the entire workflow over a small shortfall.
    if best_verses:
        lenient_floor = minimum_duration * 0.75
        if best_duration >= lenient_floor:
            return best_verses

    if not best_verses:
        raise RuntimeError("Automatic verse selection returned no verses.")

    raise RuntimeError("Selected verses are too short for the requested automatic render.")


def collect_auto_whole_surah_verses(
    *,
    chapter_number: int,
    verses_count: int,
    whole_surah_audio_path: Path,
    whole_surah_includes_basmala: bool,
    translation_id: int,
    target_seconds: float,
    ffprobe_command: str,
) -> tuple[list[AutoVerse], Path, float, float]:
    if not whole_surah_audio_path.exists():
        raise FileNotFoundError(
            f"Whole-surah audio for chapter {chapter_number} was not found: {whole_surah_audio_path}"
        )

    verse_payloads = [
        verse
        for verse in fetch_all_chapter_verses(
            chapter_number,
            verses_count=verses_count,
            translation_id=translation_id,
        )
        if isinstance(verse, dict)
    ]
    verse_payloads.sort(key=lambda verse: get_verse_number_from_key(str(verse.get("verse_key") or f"{chapter_number}:0")))
    if not verse_payloads:
        raise RuntimeError(f"Could not load verse payloads for chapter {chapter_number}.")

    translation_map = fetch_public_translation_map(chapter_number)
    total_duration = probe_duration(whole_surah_audio_path, ffprobe_command)
    include_basmala = whole_surah_includes_basmala and chapter_starts_with_basmala(chapter_number)
    basmala_duration = 0.0
    if include_basmala:
        basmala_duration = estimate_intro_duration(
            total_duration=total_duration,
            verse_payloads=verse_payloads,
            intro_word_count=len(BISMILLAH_ARABIC.split()),
        )

    remaining_duration = max(0.25, total_duration - basmala_duration)
    verse_durations = estimate_whole_surah_verse_durations(verse_payloads, total_duration=remaining_duration)
    quran_verses: list[AutoVerse] = []
    for verse_payload, verse_duration in zip(verse_payloads, verse_durations):
        verse_key = require_non_empty_text(verse_payload.get("verse_key", ""), f"verse_key for chapter {chapter_number}")
        arabic = clean_quranic_text(require_non_empty_text(verse_payload.get("text_uthmani", ""), f"text_uthmani for {verse_key}"))
        translation = extract_translation_text(verse_payload) or translation_map.get(verse_key, "")
        quran_verses.append(
            AutoVerse(
                verse_key=verse_key,
                arabic=arabic,
                translation=translation,
                audio_url="",
                audio_path=whole_surah_audio_path,
                duration=verse_duration,
            )
        )

    basmala_verse: AutoVerse | None = None
    if include_basmala and basmala_duration > 0:
        basmala_verse = AutoVerse(
            verse_key=f"{chapter_number}:0",
            arabic=BISMILLAH_ARABIC,
            translation=BISMILLAH_TRANSLATION,
            audio_url="",
            audio_path=whole_surah_audio_path,
            duration=basmala_duration,
        )

    if globals().get('IS_WHOLE_SURAH'):
        clipped_verses = quran_verses[:]
        if basmala_verse is not None:
            clipped_verses.insert(0, basmala_verse)
        return clipped_verses, whole_surah_audio_path, 0.0, total_duration

    minimum_duration = min(AUTO_MIN_DURATION, max(10.0, target_seconds * 0.68))
    start_offsets: list[float] = []
    cursor = basmala_duration
    for verse in quran_verses:
        start_offsets.append(cursor)
        cursor += verse.duration

    candidate_starts = list(range(len(quran_verses)))
    if len(candidate_starts) > 1:
        non_zero_starts = candidate_starts[1:]
        random.shuffle(non_zero_starts)
        candidate_starts = non_zero_starts + [0]

    clipped_verses: list[AutoVerse] = []
    clipped_duration = 0.0
    clip_start_time = 0.0
    clip_end_time = 0.0
    for start_index in candidate_starts:
        current_verses: list[AutoVerse] = []
        current_duration = 0.0
        if start_index == 0 and basmala_verse is not None:
            current_verses.append(basmala_verse)
            current_duration += basmala_duration

        for verse in quran_verses[start_index:]:
            if (
                current_verses
                and current_duration >= minimum_duration
                and (current_duration + verse.duration) > (target_seconds + AUTO_DURATION_OVERSHOOT_TOLERANCE)
            ):
                break
            current_verses.append(verse)
            current_duration += verse.duration
            if current_duration >= target_seconds:
                break

        if len(current_verses) > 1:
            trimmed_duration = current_duration - current_verses[-1].duration
            if (
                trimmed_duration >= minimum_duration
                and abs(trimmed_duration - target_seconds) < abs(current_duration - target_seconds)
                and any(get_verse_number_from_key(verse.verse_key) > 0 for verse in current_verses[:-1])
            ):
                current_verses.pop()
                current_duration = trimmed_duration

        if not current_verses or not any(get_verse_number_from_key(verse.verse_key) > 0 for verse in current_verses):
            continue
        if current_duration < minimum_duration:
            continue

        quran_verse_count = len([verse for verse in current_verses if get_verse_number_from_key(verse.verse_key) > 0])
        while quran_verse_count > AUTO_STATIC_WHOLE_SURAH_MAX_QURAN_VERSES and len(current_verses) > 1:
            removed_verse = current_verses.pop()
            current_duration = max(0.0, current_duration - removed_verse.duration)
            quran_verse_count = len([verse for verse in current_verses if get_verse_number_from_key(verse.verse_key) > 0])
            if current_duration < minimum_duration:
                break

        if current_duration < minimum_duration:
            continue

        display_verses = list(current_verses)
        if 0 < start_index <= 2:
            opening_context: list[AutoVerse] = []
            if basmala_verse is not None:
                opening_context.append(basmala_verse)
            opening_context.extend(quran_verses[:start_index])
            existing_verse_keys = {verse.verse_key for verse in display_verses}
            display_verses = [verse for verse in opening_context if verse.verse_key not in existing_verse_keys] + display_verses

        clip_start_time = 0.0 if start_index == 0 and include_basmala else start_offsets[start_index]
        clip_end_time = clip_start_time + current_duration
        if 0 < start_index <= 2:
            # Whole-surah audio intros often flow into the first verses, so keep
            # the clip anchored at the real start of the surah for early excerpts.
            opening_lead_in = start_offsets[start_index]
            clip_start_time = 0.0
            clip_end_time = min(total_duration, opening_lead_in + current_duration)
        clipped_verses = display_verses
        clipped_duration = current_duration
        break

    if not clipped_verses:
        raise RuntimeError("Whole-surah automatic selection returned no usable verses.")

    return clipped_verses, whole_surah_audio_path, clip_start_time, clip_end_time


def finalize_auto_render_config(
    *,
    base_dir: Path,
    index: int,
    history_entries: list[dict[str, object]],
    chapter_number: int,
    chapter_name: str,
    arabic_surah_name: str,
    reciter: AutoReciter,
    selected_verses: list[AutoVerse],
    selected_target_seconds: float,
    ffmpeg_command: str,
    ffprobe_command: str,
    source_audio_path: Path | None = None,
    source_start_time: float | None = None,
    source_end_time: float | None = None,
    allow_repeat_combo: bool = False,
) -> RenderConfig:
    cache_dir = (base_dir / DEFAULT_CACHE_DIR).resolve()
    output_dir = (base_dir / "outputs").resolve()

    reference_verses = [verse for verse in selected_verses if get_verse_number_from_key(verse.verse_key) > 0]
    if not reference_verses:
        raise RuntimeError("Automatic render configuration requires at least one Quran verse segment.")

    verse_start = get_verse_number_from_key(reference_verses[0].verse_key)
    verse_end = get_verse_number_from_key(reference_verses[-1].verse_key)
    verse_reference = f"{chapter_number}:{verse_start}" if verse_start == verse_end else f"{chapter_number}:{verse_start}-{verse_end}"
    combo_key = build_auto_combo_key(chapter_number, verse_start, verse_end, reciter.reciter_name)
    known_combo_keys = {
        normalize_optional_text(entry.get("combo_key")) or ""
        for entry in history_entries
    }
    if combo_key in known_combo_keys and not allow_repeat_combo:
        raise RuntimeError(f"Automatic mode selected a repeated combination: {combo_key}")

    if source_audio_path is None:
        audio_output = cache_dir / "compiled_audio" / build_auto_output_path(
            cache_dir / "compiled_audio",
            chapter_number=chapter_number,
            verse_start=verse_start,
            verse_end=verse_end,
            chapter_name=chapter_name,
            reciter_name=reciter.reciter_name,
            index=index,
        ).with_suffix(".m4a").name
        concatenate_audio_files([verse.audio_path for verse in selected_verses], audio_output, ffmpeg_command)
    else:
        if source_end_time is not None:
            audio_output = cache_dir / "compiled_audio" / build_auto_output_path(
                cache_dir / "compiled_audio",
                chapter_number=chapter_number,
                verse_start=verse_start,
                verse_end=verse_end,
                chapter_name=chapter_name,
                reciter_name=reciter.reciter_name,
                index=index,
            ).with_suffix(".m4a").name
            trim_audio_segment(
                source_audio_path,
                audio_output,
                start_time=max(0.0, source_start_time or 0.0),
                end_time=source_end_time,
                ffmpeg_command=ffmpeg_command,
            )
        else:
            audio_output = source_audio_path

    audio_duration = probe_duration(audio_output, ffprobe_command)
    if not globals().get('IS_WHOLE_SURAH') and audio_duration > (selected_target_seconds + 0.05):
        trimmed_output = cache_dir / "compiled_audio" / f"{audio_output.stem}-trim{audio_output.suffix}"
        trim_audio_segment(
            audio_output,
            trimmed_output,
            start_time=0.0,
            end_time=selected_target_seconds,
            ffmpeg_command=ffmpeg_command,
        )
        audio_output = trimmed_output

    use_static_source_audio = source_audio_path is not None
    timed_segments: list[TimedSegment] = []
    cursor = 0.0
    for verse in selected_verses:
        timed_segments.append(
            TimedSegment(
                arabic=verse.arabic,
                translation=verse.translation,
                start_time=cursor,
                end_time=cursor + verse.duration,
            )
        )
        cursor += verse.duration

    used_background_paths = {
        normalize_optional_text(entry.get("background_path"))
        for entry in history_entries
        if isinstance(entry, dict)
    }
    background_path = choose_random_library_background(
        base_dir,
        excluded_paths={path for path in used_background_paths if path},
    )
    if background_path is not None:
        print(f"Using local background from {background_path}")
    else:
        background_path = download_asset(DEFAULT_BACKGROUND_URL, cache_dir / "background", "background")
    
    font_file = resolve_default_arabic_font_file(base_dir, cache_dir)

    latin_font_file = download_asset(DEFAULT_LATIN_FONT_URL, cache_dir / "latin_font", "latin_font")
    style_preset = choose_auto_style_preset(history_entries)
    metadata_keys, title_text = build_auto_title(
        chapter_name=arabic_surah_name,
        verse_reference=verse_reference,
        verse_start=verse_start,
        verse_end=verse_end,
        reciter_name=ARABIC_RECITER_NAMES.get(reciter.reciter_name, reciter.reciter_name),
        history_entries=history_entries,
    )
    output_path = build_auto_output_path(
        output_dir,
        chapter_number=chapter_number,
        verse_start=verse_start,
        verse_end=verse_end,
        chapter_name=chapter_name,
        reciter_name=reciter.reciter_name,
        index=index,
    )
    history_entry = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "combo_key": combo_key,
        "chapter_number": chapter_number,
        "chapter_name": chapter_name,
        "verse_reference": verse_reference,
        "verse_start": verse_start,
        "verse_end": verse_end,
        "reciter_name": reciter.reciter_name,
        "attribution_lines": list(reciter.attribution_lines),
        "background_path": str(background_path.resolve()) if background_path is not None else "",
        "style_preset": style_preset,
        "title_text": title_text,
        "target_seconds": selected_target_seconds,
        "planned_duration_seconds": round(
            max(0.0, (source_end_time or 0.0) - max(0.0, source_start_time or 0.0))
            if use_static_source_audio and source_end_time is not None
            else cursor,
            2,
        ),
        "output_path": str(output_path),
    }
    history_entry.update(metadata_keys)
    history_entry["metadata_variant_key"] = (
        f"{metadata_keys['title_template_key']}|{metadata_keys['title_hook_key']}|"
        f"{metadata_keys['description_template_key']}|{metadata_keys['description_hook_key']}|"
        f"{metadata_keys['cta_key']}"
    )
    history_entry["experiment_bucket"] = (
        f"{style_preset}|{metadata_keys['title_template_key']}|{metadata_keys['description_template_key']}"
    )

    config = RenderConfig(
        audio_path=audio_output,
        output_path=output_path,
        verse_text=" ".join(verse.arabic for verse in selected_verses),
        surah_name=chapter_name,
        verse_reference=verse_reference,
        translation=" ".join(filter(None, (verse.translation for verse in selected_verses))) or None,
        reciter_name=reciter.reciter_name,
        background_path=background_path,
        font_file=font_file,
        latin_font_file=latin_font_file,
        brand_text="shortQuran",
        title_text=title_text,
        description_text=None,
        fps=DEFAULT_FPS,
        timed_segments=timed_segments or None,
        prefer_static_text_overlay=False,
        show_meta=True,
        show_brand=False,
        style_preset=style_preset,
        auto_history_entry=history_entry,
        attribution_lines=reciter.attribution_lines,
        arabic_surah_name=arabic_surah_name,
        arabic_reciter_name=ARABIC_RECITER_NAMES.get(reciter.reciter_name, reciter.reciter_name),
    )
    config.description_text = build_auto_description(
        config,
        description_template_key=metadata_keys["description_template_key"],
        description_hook_key=metadata_keys["description_hook_key"],
        cta_key=metadata_keys["cta_key"],
    )
    history_entry["description_text"] = config.description_text
    return config


def build_auto_render_config(
    *,
    base_dir: Path,
    index: int,
    target_seconds: float,
    history_entries: list[dict[str, object]],
    translation_id: int,
    chapters: list[dict[str, object]],
    reciters: list[AutoReciter],
    ffmpeg_command: str,
    ffprobe_command: str,
) -> RenderConfig:
    last_error: Exception | None = None

    for _ in range(30):
        recent_reciters = set(
            get_recent_history_values(
                history_entries,
                "reciter_name",
                limit=AUTO_RECENT_RECITER_WINDOW,
            )
        )
        available_reciters = [
            reciter_candidate
            for reciter_candidate in reciters
            if reciter_candidate.reciter_name not in recent_reciters
        ]
        reciter = random.choice(available_reciters or reciters)

        recent_chapter_values = get_recent_history_values(
            history_entries,
            "chapter_number",
            limit=AUTO_RECENT_CHAPTER_WINDOW,
        )
        recent_chapter_ids = {int(value) for value in recent_chapter_values if value.isdigit()}
        candidate_chapters = chapters
        whole_surah_files = get_auto_reciter_whole_surah_files(reciter)
        downloadable_chapters = list_auto_reciter_downloadable_chapters(reciter)
        if reciter.showcase_only and whole_surah_files:
            # Showcase mode: bypass the 60s duration limit - use full surah audio
            supported_chapter_ids = {
                chapter_id
                for chapter_id, audio_path in whole_surah_files.items()
                if audio_path.exists()
            }
            supported_chapter_ids.update(downloadable_chapters)
            candidate_chapters = [
                chapter
                for chapter in chapters
                if int(chapter.get("id") or 0) in supported_chapter_ids
            ]
            if not candidate_chapters:
                last_error = RuntimeError(
                    f"Showcase reciter '{reciter.reciter_name}' does not have any usable whole-surah files."
                )
                continue
        elif reciter.showcase_only and downloadable_chapters:
            supported_chapter_ids = set(downloadable_chapters)
            candidate_chapters = [
                chapter
                for chapter in chapters
                if int(chapter.get("id") or 0) in supported_chapter_ids
            ]
            if not candidate_chapters:
                last_error = RuntimeError(
                    f"Showcase reciter '{reciter.reciter_name}' does not have any downloadable whole-surah files."
                )
                continue
        elif whole_surah_files:
            supported_chapter_ids = {
                chapter_id
                for chapter_id, audio_path in whole_surah_files.items()
                if audio_path.exists() and whole_surah_duration_supported(audio_path, ffprobe_command)
            }
            candidate_chapters = [
                chapter
                for chapter in chapters
                if int(chapter.get("id") or 0) in supported_chapter_ids
            ]
            if not candidate_chapters:
                last_error = RuntimeError(
                    f"Automatic reciter '{reciter.reciter_name}' does not have any usable whole-surah files."
                )
                continue
        elif reciter.audio_base_dir is not None and reciter.recitation_id is None:
            candidate_chapters = [
                chapter
                for chapter in chapters
                if local_audio_chapter_available(
                    reciter,
                    chapter_number=int(chapter.get("id") or 0),
                    chapter_name=normalize_optional_text(chapter.get("name_simple")) or f"Surah {int(chapter.get('id') or 0)}",
                )
            ]
            if not candidate_chapters:
                last_error = RuntimeError(
                    f"Automatic reciter '{reciter.reciter_name}' does not have any usable verse-by-verse local files."
                )
                continue
        available_chapters = [
            chapter
            for chapter in candidate_chapters
            if int(chapter.get("id") or 0) not in recent_chapter_ids
        ]
        chapter = random.choice(available_chapters or candidate_chapters)
        chapter_number = int(chapter.get("id") or 0)
        verses_count = int(chapter.get("verses_count") or 0)
        chapter_name = normalize_optional_text(chapter.get("name_simple")) or f"Surah {chapter_number}"
        arabic_surah_name = normalize_optional_text(chapter.get("name_arabic")) or chapter_name
        if chapter_number <= 0 or verses_count <= 0:
            continue

        selected_target_seconds = target_seconds
        if not reciter.showcase_only and target_seconds < 60:
            selected_target_seconds = choose_auto_target_seconds(target_seconds, history_entries)
        try:
            if reciter.showcase_only and not globals().get('IS_WHOLE_SURAH'):
                showcase_audio_path = whole_surah_files.get(chapter_number)
                if showcase_audio_path is None:
                    showcase_audio_path = ensure_auto_reciter_chapter_audio(reciter, chapter_number=chapter_number)
                if showcase_audio_path is None:
                    raise RuntimeError(
                        f"Showcase reciter '{reciter.reciter_name}' does not define audio for chapter {chapter_number}."
                    )
                return finalize_showcase_render_config(
                    base_dir=base_dir,
                    index=index,
                    history_entries=history_entries,
                    chapter_number=chapter_number,
                    chapter_name=chapter_name,
                    arabic_surah_name=arabic_surah_name,
                    reciter=reciter,
                    audio_path=showcase_audio_path,
                    target_seconds=selected_target_seconds,
                    ffmpeg_command=ffmpeg_command,
                    ffprobe_command=ffprobe_command,
                )
            ensure_auto_reciter_source_material(reciter)
            whole_surah_files = get_auto_reciter_whole_surah_files(reciter)
            if whole_surah_files:
                whole_surah_audio_path = whole_surah_files.get(chapter_number)
                if whole_surah_audio_path is None:
                    raise RuntimeError(
                        f"Automatic reciter '{reciter.reciter_name}' does not define whole-surah audio for chapter {chapter_number}."
                    )
                selected_verses, whole_surah_audio_path, whole_surah_clip_start, whole_surah_clip_end = collect_auto_whole_surah_verses(
                    chapter_number=chapter_number,
                    verses_count=verses_count,
                    whole_surah_audio_path=whole_surah_audio_path,
                    whole_surah_includes_basmala=reciter.whole_surah_includes_basmala,
                    translation_id=translation_id,
                    target_seconds=selected_target_seconds,
                    ffprobe_command=ffprobe_command,
                )
                return finalize_auto_render_config(
                    base_dir=base_dir,
                    index=index,
                    history_entries=history_entries,
                    chapter_number=chapter_number,
                    chapter_name=chapter_name,
                    arabic_surah_name=arabic_surah_name,
                    reciter=reciter,
                    selected_verses=selected_verses,
                    selected_target_seconds=selected_target_seconds,
                    ffmpeg_command=ffmpeg_command,
                    ffprobe_command=ffprobe_command,
                    source_audio_path=whole_surah_audio_path,
                    source_start_time=whole_surah_clip_start,
                    source_end_time=whole_surah_clip_end,
                    allow_repeat_combo=True,
                )

            translation_map = fetch_public_translation_map(chapter_number)
            selected_verses = collect_auto_verses(
                chapter_number=chapter_number,
                chapter_name=chapter_name,
                verses_count=verses_count,
                reciter=reciter,
                translation_id=translation_id,
                translation_map=translation_map,
                target_seconds=selected_target_seconds,
                cache_dir=(base_dir / DEFAULT_CACHE_DIR).resolve(),
                ffprobe_command=ffprobe_command,
            )
            return finalize_auto_render_config(
                base_dir=base_dir,
                index=index,
                history_entries=history_entries,
                chapter_number=chapter_number,
                chapter_name=chapter_name,
                arabic_surah_name=arabic_surah_name,
                reciter=reciter,
                selected_verses=selected_verses,
                selected_target_seconds=selected_target_seconds,
                ffmpeg_command=ffmpeg_command,
                ffprobe_command=ffprobe_command,
            )
        except Exception as error:  # noqa: BLE001
            last_error = error
            continue

    if last_error is not None:
        raise RuntimeError(f"Automatic render generation failed: {last_error}") from last_error
    raise RuntimeError("Automatic render generation failed before any chapter could be selected.")


def build_auto_render_configs(
    base_dir: Path,
    *,
    count: int,
    target_seconds: float,
    auto_reciter_library_file: str | None = None,
) -> list[RenderConfig]:
    if count <= 0:
        raise ValueError("'count' must be greater than zero.")
    if target_seconds <= 0:
        raise ValueError("'target-seconds' must be greater than zero.")
    if target_seconds < 60:
        target_seconds = 60.0

    ffmpeg_command = resolve_binary_command("ffmpeg")
    ffprobe_command = resolve_binary_command("ffprobe")
    all_chapters = fetch_auto_chapters()
    if not all_chapters:
        raise RuntimeError("No chapters are available for automatic cinematic mode.")
    explicit_library_file_raw = normalize_optional_text(auto_reciter_library_file) or normalize_optional_text(
        os.getenv("AUTO_RECITER_LIBRARY_FILE")
    )
    library_file_raw = explicit_library_file_raw or DEFAULT_AUTO_RECITER_LIBRARY_FILE
    library_path = resolve_runtime_path(base_dir, library_file_raw)
    if explicit_library_file_raw and not library_path.exists():
        raise FileNotFoundError(f"Auto reciter library file not found: {library_path}")
    reciters = load_auto_reciters_from_library(library_path) if library_path.exists() else fetch_auto_reciters()
    if any(
        reciter.chapter_audio_files
        or reciter.auto_detect_whole_surah_files
        or (reciter.audio_base_dir is not None and reciter.recitation_id is None)
        for reciter in reciters
    ):
        chapters = all_chapters
    else:
        chapters = [
            chapter
            for chapter in all_chapters
            if int(chapter.get("id") or 0) >= DEFAULT_AUTO_CHAPTER_MIN
        ]
    chapters = [
        chapter
        for chapter in chapters
        if chapter_meets_minimum_verses(chapter, AUTO_MIN_VERSES_COUNT)
    ]
    if not chapters:
        chapters = [
            chapter
            for chapter in all_chapters
            if parse_int_fallback(
                chapter.get("id")
                or chapter.get("chapter_id")
                or chapter.get("chapter_number")
            ) in LONG_SURAH_IDS
        ]
    if not chapters:
        raise RuntimeError(
            "No chapters are available for automatic cinematic mode after enforcing the minimum verse count."
        )
    history_entries = load_auto_history(base_dir)
    configs: list[RenderConfig] = []
    planned_history_entries = list(history_entries)

    for index in range(count):
        config = build_auto_render_config(
            base_dir=base_dir,
            index=index,
            target_seconds=target_seconds,
            history_entries=planned_history_entries,
            translation_id=DEFAULT_TRANSLATION_ID,
            chapters=chapters,
            reciters=reciters,
            ffmpeg_command=ffmpeg_command,
            ffprobe_command=ffprobe_command,
        )
        configs.append(config)
        if config.auto_history_entry is not None:
            planned_history_entries.append(config.auto_history_entry)

    return configs


def wrap_text(text: str, width: int) -> str:
    cleaned = " ".join(text.split())
    return textwrap.fill(cleaned, width=width, break_long_words=False, break_on_hyphens=False)


def estimate_arabic_word_units(word: str) -> int:
    base_letters = re.sub(r"[\u0640\u064b-\u065f\u0670]", "", word)
    return max(1, len(base_letters))


def wrap_arabic_text(text: str, words_per_line: int, *, max_line_units: int | None = None) -> str:
    words = [word for word in text.split() if word.strip()]
    if not words:
        return ""

    lines: list[str] = []
    current_words: list[str] = []
    current_units = 0

    for word in words:
        word_units = estimate_arabic_word_units(word)
        projected_units = current_units + word_units + (1 if current_words else 0)
        hit_word_limit = len(current_words) >= words_per_line
        hit_width_limit = max_line_units is not None and current_words and projected_units > max_line_units

        if current_words and (hit_word_limit or hit_width_limit):
            lines.append(" ".join(current_words))
            current_words = [word]
            current_units = word_units
            continue

        current_words.append(word)
        current_units = projected_units

    if current_words:
        lines.append(" ".join(current_words))

    return "\n".join(lines)


def choose_arabic_words_per_line(text: str, *, is_cinematic: bool) -> int:
    return 12


def choose_arabic_line_unit_budget(text: str, *, is_cinematic: bool) -> int:
    return 55


def measure_arabic_line_units(text: str) -> int:
    max_units = 0
    for line in text.splitlines():
        line_units = sum(estimate_arabic_word_units(word) for word in line.split())
        max_units = max(max_units, line_units)
    return max_units


def build_wrapped_arabic_text(text: str, *, is_cinematic: bool) -> str:
    return wrap_arabic_text(
        text,
        words_per_line=choose_arabic_words_per_line(text, is_cinematic=is_cinematic),
        max_line_units=choose_arabic_line_unit_budget(text, is_cinematic=is_cinematic),
    )


def resolve_arabic_text_metrics(line_count: int, *, is_cinematic: bool, max_line_units: int) -> tuple[int, int]:
    if not is_cinematic:
        font_size, line_spacing = 88, 24
    elif line_count >= 7:
        font_size, line_spacing = 88, 28
    elif line_count == 6:
        font_size, line_spacing = 94, 30
    elif line_count >= 5:
        font_size, line_spacing = 100, 32
    elif line_count == 4:
        font_size, line_spacing = 110, 30
    elif line_count == 3:
        font_size, line_spacing = 120, 28
    else:
        font_size, line_spacing = 140, 24

    if max_line_units >= 22:
        font_size -= 16
    elif max_line_units >= 20:
        font_size -= 12
    elif max_line_units >= 18:
        font_size -= 8
    elif max_line_units >= 16:
        font_size -= 4

    return max(76 if is_cinematic else 70, font_size), line_spacing


def resolve_translation_text_metrics(line_count: int, *, is_cinematic: bool) -> tuple[int, int]:
    if not is_cinematic:
        if line_count >= 7:
            return 30, 10
        if line_count >= 5:
            return 34, 10
        return 40, 14

    if line_count >= 7:
        return 38, 10
    if line_count >= 5:
        return 44, 12
    if line_count >= 4:
        return 50, 12
    return 56, 14


def resolve_text_stack_positions(
    *,
    arabic_block_height: int,
    translation_line_count: int,
    translation_font_size: int,
    translation_line_spacing: int,
    is_cinematic: bool,
    preferred_arabic_top: float,
    preferred_translation_top: float,
) -> tuple[int, int]:
    if globals().get('IS_LANDSCAPE'):
        top_margin = 150 if is_cinematic else 100
        bottom_margin = 150 if is_cinematic else 100
    else:
        top_margin = 260 if is_cinematic else 200
        bottom_margin = 320 if is_cinematic else 300
        preferred_translation_top += 80

    if translation_line_count <= 0:
        max_arabic_top = VIDEO_HEIGHT - bottom_margin - arabic_block_height
        if max_arabic_top < top_margin:
            centered_top = max(40.0, (VIDEO_HEIGHT - arabic_block_height) / 2)
            return int(round(centered_top)), int(round(preferred_translation_top))

        arabic_top = min(max(preferred_arabic_top, top_margin), max_arabic_top)
        return int(round(arabic_top)), int(round(preferred_translation_top))

    translation_block_height = (translation_line_count * (translation_font_size + translation_line_spacing)) - translation_line_spacing
    minimum_gap = 90 if is_cinematic else 70

    arabic_top = preferred_arabic_top
    translation_top = max(preferred_translation_top, arabic_top + arabic_block_height + minimum_gap)
    max_translation_top = VIDEO_HEIGHT - bottom_margin - translation_block_height

    if translation_top > max_translation_top:
        shift_up = translation_top - max_translation_top
        arabic_top = max(top_margin, arabic_top - shift_up)
        translation_top = max(preferred_translation_top, arabic_top + arabic_block_height + minimum_gap)
        translation_top = min(translation_top, max_translation_top)

    return int(round(arabic_top)), int(round(translation_top))


def resolve_minimalist_arabic_layout(text_lines: list[str]) -> tuple[int, int, int]:
    font_size, line_spacing = resolve_arabic_text_metrics(
        len(text_lines),
        is_cinematic=False,
        max_line_units=measure_arabic_line_units("\n".join(text_lines)),
    )
    block_height = (len(text_lines) * (font_size + line_spacing)) - line_spacing
    top_y, _ = resolve_text_stack_positions(
        arabic_block_height=block_height,
        translation_line_count=0,
        translation_font_size=0,
        translation_line_spacing=0,
        is_cinematic=False,
        preferred_arabic_top=880,
        preferred_translation_top=0,
    )
    return font_size, line_spacing, top_y


def write_text_asset(path: Path, content: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as text_file:
        text_file.write(content)


def escape_filter_path(path: Path) -> str:
    return path.as_posix().replace(":", r"\:").replace("'", r"\'")


def resolve_font_family_name(font_file: Path | None) -> str | None:
    if font_file is None or not font_file.exists():
        return None

    fallback_names = {
        "quran_font": "Noto Naskh Arabic",
        "alaem": "ALAEM",
        "amiri-bold": "Amiri",
        "amiri-regular": "Amiri",
        "notosansarabic-regular": "Noto Sans Arabic",
    }

    try:
        with font_file.open("rb") as font_stream:
            header = font_stream.read(12)
            if len(header) < 12:
                return fallback_names.get(font_file.stem.lower())

            _, table_count, _, _, _ = struct.unpack(">IHHHH", header)
            name_table_offset = None
            name_table_length = None

            for _ in range(table_count):
                record = font_stream.read(16)
                if len(record) < 16:
                    break
                table_tag, _, table_offset, table_length = struct.unpack(">4sIII", record)
                if table_tag == b"name":
                    name_table_offset = table_offset
                    name_table_length = table_length
                    break

            if name_table_offset is None or name_table_length is None:
                return fallback_names.get(font_file.stem.lower())

            font_stream.seek(name_table_offset)
            name_table = font_stream.read(name_table_length)
            if len(name_table) < 6:
                return fallback_names.get(font_file.stem.lower())

            _, record_count, string_offset = struct.unpack(">HHH", name_table[:6])
            best_match: tuple[tuple[int, int, int], str] | None = None

            for index in range(record_count):
                record_offset = 6 + (index * 12)
                record_end = record_offset + 12
                if record_end > len(name_table):
                    break

                platform_id, _, language_id, name_id, value_length, value_offset = struct.unpack(
                    ">HHHHHH",
                    name_table[record_offset:record_end],
                )
                if name_id not in {1, 16}:
                    continue

                value_start = string_offset + value_offset
                value_end = value_start + value_length
                if value_end > len(name_table):
                    continue

                raw_value = name_table[value_start:value_end]
                if platform_id == 3:
                    decoded_value = raw_value.decode("utf-16-be", errors="ignore")
                elif platform_id == 1:
                    decoded_value = raw_value.decode("mac_roman", errors="ignore")
                else:
                    continue

                family_name = decoded_value.strip().strip("\x00")
                if not family_name:
                    continue

                sort_key = (
                    0 if name_id == 16 else 1,
                    0 if platform_id == 3 else 1,
                    0 if language_id in {0, 0x0409} else 1,
                )
                if best_match is None or sort_key < best_match[0]:
                    best_match = (sort_key, family_name)

            if best_match is not None:
                return best_match[1]
    except OSError:
        return fallback_names.get(font_file.stem.lower())

    return fallback_names.get(font_file.stem.lower())


def format_ass_timestamp(seconds: float) -> str:
    total_centiseconds = max(0, int(round(seconds * 100)))
    hours, remainder = divmod(total_centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    whole_seconds, centiseconds = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{centiseconds:02d}"


def escape_ass_text(text: str) -> str:
    return (
        text.replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\n", r"\N")
    )


def read_text_lines(text_paths: list[Path]) -> list[str]:
    lines: list[str] = []
    for text_path in text_paths:
        line = text_path.read_text(encoding="utf-8").strip()
        if line:
            lines.append(line)
    return lines


def build_ass_dialogue(
    text_lines: list[str],
    *,
    start_time: float,
    end_time: float,
    font_size: int,
    line_spacing: int,
    top_y: float,
) -> str:
    ass_text = escape_ass_text("\n".join(text_lines))
    override = (
        f"{{\\an8\\q1\\pos({VIDEO_WIDTH // 2},{top_y})"
        f"\\fs{font_size}\\bord10\\shad0}}"
    )
    return (
        "Dialogue: 0,"
        f"{format_ass_timestamp(start_time)},{format_ass_timestamp(end_time)},"
        f"Arabic,,0,0,0,,{override}{ass_text}"
    )


def write_fontconfig_file(temp_dir: Path, font_dirs: list[Path]) -> Path:
    unique_dirs: list[Path] = []
    seen_dirs: set[Path] = set()

    for font_dir in font_dirs:
        resolved_dir = font_dir.resolve()
        if resolved_dir in seen_dirs or not resolved_dir.exists():
            continue
        seen_dirs.add(resolved_dir)
        unique_dirs.append(resolved_dir)

    cache_dir = temp_dir / "fontconfig-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    xml_lines = [
        "<?xml version=\"1.0\"?>",
        "<!DOCTYPE fontconfig SYSTEM \"fonts.dtd\">",
        "<fontconfig>",
    ]
    for font_dir in unique_dirs:
        xml_lines.append(f"  <dir>{html.escape(font_dir.as_posix())}</dir>")
    xml_lines.append(f"  <cachedir>{html.escape(cache_dir.as_posix())}</cachedir>")
    xml_lines.append("</fontconfig>")

    fontconfig_path = temp_dir / "fonts.conf"
    write_text_asset(fontconfig_path, "\n".join(xml_lines))
    return fontconfig_path


def create_arabic_ass_file(
    config: RenderConfig,
    duration: float,
    temp_dir: Path,
    text_assets: dict[str, list[Path]],
    segment_assets: list[SegmentTextAsset],
    timed_segment_assets: list[TimedSegmentTextAsset],
) -> Path | None:
    resolved_font_file = resolve_drawtext_font_file(config.font_file)
    font_family = resolve_font_family_name(resolved_font_file)
    if resolved_font_file is None or font_family is None:
        return None

    is_cinematic = is_cinematic_style(config.style_preset)
    cinematic_variant = get_cinematic_variant(config.style_preset)
    cinematic_arabic_offset = 180 if cinematic_variant == "compact" else 140 if cinematic_variant == "spacious" else 160
    if globals().get('IS_LANDSCAPE'):
        cinematic_translation_top = 800 if cinematic_variant == "compact" else 840 if cinematic_variant == "spacious" else 820
    else:
        cinematic_translation_top = 980 if cinematic_variant == "compact" else 1020 if cinematic_variant == "spacious" else 1000

    use_timed_segment_overlays = bool(timed_segment_assets) and not config.prefer_static_text_overlay
    use_segment_overlays = bool(segment_assets) and not config.prefer_static_text_overlay

    dialogues: list[str] = []

    if config.style_preset == "minimalist_info":
        if timed_segment_assets:
            for segment_asset in timed_segment_assets:
                verse_lines = read_text_lines(segment_asset.arabic_lines)
                if not verse_lines:
                    continue

                arabic_font_size, arabic_line_spacing, arabic_top = resolve_minimalist_arabic_layout(verse_lines)
                dialogues.append(
                    build_ass_dialogue(
                        verse_lines,
                        start_time=segment_asset.start_time,
                        end_time=segment_asset.end_time,
                        font_size=arabic_font_size,
                        line_spacing=arabic_line_spacing,
                        top_y=arabic_top,
                    )
                )
        elif segment_assets:
            intro_padding = 0.45
            outro_padding = 0.45
            available_duration = max(1.0, duration - intro_padding - outro_padding)
            segment_duration = available_duration / len(segment_assets)

            for index, segment_asset in enumerate(segment_assets):
                verse_lines = read_text_lines(segment_asset.arabic_lines)
                if not verse_lines:
                    continue

                start_time = intro_padding + (index * segment_duration)
                end_time = duration - outro_padding if index == len(segment_assets) - 1 else start_time + segment_duration
                arabic_font_size, arabic_line_spacing, arabic_top = resolve_minimalist_arabic_layout(verse_lines)
                dialogues.append(
                    build_ass_dialogue(
                        verse_lines,
                        start_time=start_time,
                        end_time=end_time,
                        font_size=arabic_font_size,
                        line_spacing=arabic_line_spacing,
                        top_y=arabic_top,
                    )
                )
        else:
            verse_lines = read_text_lines(text_assets.get("verse", []))
            if verse_lines:
                arabic_font_size, arabic_line_spacing, arabic_top = resolve_minimalist_arabic_layout(verse_lines)
                dialogues.append(
                    build_ass_dialogue(
                        verse_lines,
                        start_time=0.0,
                        end_time=duration,
                        font_size=arabic_font_size,
                        line_spacing=arabic_line_spacing,
                        top_y=arabic_top,
                    )
                )
    elif use_timed_segment_overlays:
        for segment_asset in timed_segment_assets:
            verse_lines = read_text_lines(segment_asset.arabic_lines)
            if not verse_lines:
                continue

            arabic_font_size, arabic_line_spacing = resolve_arabic_text_metrics(
                len(verse_lines),
                is_cinematic=is_cinematic,
                max_line_units=measure_arabic_line_units("\n".join(verse_lines)),
            )
            translation_font_size, translation_line_spacing = resolve_translation_text_metrics(
                len(segment_asset.translation_lines),
                is_cinematic=is_cinematic,
            )
            arabic_block_height = (len(verse_lines) * (arabic_font_size + arabic_line_spacing)) - arabic_line_spacing
            preferred_arabic_top = ((VIDEO_HEIGHT - arabic_block_height) / 2) - (cinematic_arabic_offset if is_cinematic else 100)
            arabic_top, _ = resolve_text_stack_positions(
                arabic_block_height=arabic_block_height,
                translation_line_count=len(segment_asset.translation_lines),
                translation_font_size=translation_font_size,
                translation_line_spacing=translation_line_spacing,
                is_cinematic=is_cinematic,
                preferred_arabic_top=preferred_arabic_top,
                preferred_translation_top=cinematic_translation_top if is_cinematic else VIDEO_HEIGHT - (250 if globals().get('IS_LANDSCAPE') else 500),
            )
            dialogues.append(
                build_ass_dialogue(
                    verse_lines,
                    start_time=segment_asset.start_time,
                    end_time=segment_asset.end_time,
                    font_size=arabic_font_size,
                    line_spacing=arabic_line_spacing,
                    top_y=arabic_top,
                )
            )
    elif use_segment_overlays:
        intro_padding = 0.45
        outro_padding = 0.45
        available_duration = max(1.0, duration - intro_padding - outro_padding)
        segment_duration = available_duration / len(segment_assets)

        for index, segment_asset in enumerate(segment_assets):
            verse_lines = read_text_lines(segment_asset.arabic_lines)
            if not verse_lines:
                continue

            start_time = intro_padding + (index * segment_duration)
            end_time = duration - outro_padding if index == len(segment_assets) - 1 else start_time + segment_duration
            arabic_font_size, arabic_line_spacing = resolve_arabic_text_metrics(
                len(verse_lines),
                is_cinematic=is_cinematic,
                max_line_units=measure_arabic_line_units("\n".join(verse_lines)),
            )
            translation_font_size, translation_line_spacing = resolve_translation_text_metrics(
                len(segment_asset.translation_lines),
                is_cinematic=is_cinematic,
            )
            arabic_block_height = (len(verse_lines) * (arabic_font_size + arabic_line_spacing)) - arabic_line_spacing
            preferred_arabic_top = ((VIDEO_HEIGHT - arabic_block_height) / 2) - (cinematic_arabic_offset if is_cinematic else 100)
            arabic_top, _ = resolve_text_stack_positions(
                arabic_block_height=arabic_block_height,
                translation_line_count=len(segment_asset.translation_lines),
                translation_font_size=translation_font_size,
                translation_line_spacing=translation_line_spacing,
                is_cinematic=is_cinematic,
                preferred_arabic_top=preferred_arabic_top,
                preferred_translation_top=cinematic_translation_top if is_cinematic else VIDEO_HEIGHT - (250 if globals().get('IS_LANDSCAPE') else 500),
            )
            dialogues.append(
                build_ass_dialogue(
                    verse_lines,
                    start_time=start_time,
                    end_time=end_time,
                    font_size=arabic_font_size,
                    line_spacing=arabic_line_spacing,
                    top_y=arabic_top,
                )
            )
    else:
        verse_lines = read_text_lines(text_assets.get("verse", []))
        if verse_lines:
            verse_font_size, verse_line_spacing = resolve_arabic_text_metrics(
                len(verse_lines),
                is_cinematic=is_cinematic,
                max_line_units=measure_arabic_line_units("\n".join(verse_lines)),
            )
            translation_font_size, translation_line_spacing = resolve_translation_text_metrics(
                len(text_assets.get("translation", [])),
                is_cinematic=is_cinematic,
            )
            verse_block_height = (len(verse_lines) * (verse_font_size + verse_line_spacing)) - verse_line_spacing
            preferred_verse_top = ((VIDEO_HEIGHT - verse_block_height) / 2) - (cinematic_arabic_offset if is_cinematic else 110)
            verse_top, _ = resolve_text_stack_positions(
                arabic_block_height=verse_block_height,
                translation_line_count=len(text_assets.get("translation", [])),
                translation_font_size=translation_font_size,
                translation_line_spacing=translation_line_spacing,
                is_cinematic=is_cinematic,
                preferred_arabic_top=preferred_verse_top,
                preferred_translation_top=cinematic_translation_top if is_cinematic else VIDEO_HEIGHT - (220 if globals().get('IS_LANDSCAPE') else 470),
            )
            dialogues.append(
                build_ass_dialogue(
                    verse_lines,
                    start_time=0.0,
                    end_time=duration,
                    font_size=verse_font_size,
                    line_spacing=verse_line_spacing,
                    top_y=verse_top,
                )
            )

    if not dialogues:
        return None

    ass_lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "ScaledBorderAndShadow: yes",
        f"PlayResX: {VIDEO_WIDTH}",
        f"PlayResY: {VIDEO_HEIGHT}",
        "WrapStyle: 1",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Arabic,{font_family},110,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,10,0,5,50,50,50,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    ass_lines.extend(dialogues)

    ass_path = temp_dir / "arabic_overlay.ass"
    write_text_asset(ass_path, "\n".join(ass_lines))
    return ass_path


def create_translation_ass_file(
    config: RenderConfig,
    duration: float,
    temp_dir: Path,
    timed_segment_assets: list[TimedSegmentTextAsset],
) -> Path | None:
    """Create an ASS subtitle file for translation overlays.

    This is used when there are many timed segments (e.g. 128 verses for a
    whole surah) to avoid creating hundreds of chained drawtext filters in
    the ffmpeg filter_complex which would crash the render.
    """
    if not timed_segment_assets:
        return None
    if len(timed_segment_assets) < AUTO_MANY_SEGMENTS_THRESHOLD:
        return None

    is_cinematic = is_cinematic_style(config.style_preset)
    cinematic_variant = get_cinematic_variant(config.style_preset)
    cinematic_arabic_offset = 180 if cinematic_variant == "compact" else 140 if cinematic_variant == "spacious" else 160
    if globals().get('IS_LANDSCAPE'):
        cinematic_translation_top = 800 if cinematic_variant == "compact" else 840 if cinematic_variant == "spacious" else 820
    else:
        cinematic_translation_top = 980 if cinematic_variant == "compact" else 1020 if cinematic_variant == "spacious" else 1000

    resolved_font_file = resolve_drawtext_font_file(config.latin_font_file or config.font_file)
    font_family = resolve_font_family_name(resolved_font_file)
    if font_family is None:
        font_family = "Sans"

    dialogues: list[str] = []
    for segment_asset in timed_segment_assets:
        translation_lines = read_text_lines(segment_asset.translation_lines)
        if not translation_lines:
            continue

        translation_font_size, translation_line_spacing = resolve_translation_text_metrics(
            len(segment_asset.translation_lines),
            is_cinematic=is_cinematic,
        )
        arabic_font_size, arabic_line_spacing = resolve_arabic_text_metrics(
            len(segment_asset.arabic_lines),
            is_cinematic=is_cinematic,
            max_line_units=measure_arabic_line_units(
                "\n".join(path.read_text(encoding="utf-8") for path in segment_asset.arabic_lines)
            ),
        )
        arabic_block_height = (len(segment_asset.arabic_lines) * (arabic_font_size + arabic_line_spacing)) - arabic_line_spacing
        preferred_arabic_top = ((VIDEO_HEIGHT - arabic_block_height) / 2) - (cinematic_arabic_offset if is_cinematic else 100)
        _, translation_top = resolve_text_stack_positions(
            arabic_block_height=arabic_block_height,
            translation_line_count=len(segment_asset.translation_lines),
            translation_font_size=translation_font_size,
            translation_line_spacing=translation_line_spacing,
            is_cinematic=is_cinematic,
            preferred_arabic_top=preferred_arabic_top,
            preferred_translation_top=cinematic_translation_top if is_cinematic else VIDEO_HEIGHT - (250 if globals().get('IS_LANDSCAPE') else 500),
        )
        ass_text = escape_ass_text("\n".join(translation_lines))
        override = (
            f"{{\\an8\\q1\\pos({VIDEO_WIDTH // 2},{translation_top})"
            f"\\fs{translation_font_size}\\bord8\\shad0}}"
        )
        dialogues.append(
            "Dialogue: 0,"
            f"{format_ass_timestamp(segment_asset.start_time)},{format_ass_timestamp(segment_asset.end_time)},"
            f"Translation,,0,0,0,,{override}{ass_text}"
        )

    if not dialogues:
        return None

    ass_lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "ScaledBorderAndShadow: yes",
        f"PlayResX: {VIDEO_WIDTH}",
        f"PlayResY: {VIDEO_HEIGHT}",
        "WrapStyle: 1",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Translation,{font_family},36,&H00FCF8FA,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,8,0,5,50,50,50,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    ass_lines.extend(dialogues)

    ass_path = temp_dir / "translation_overlay.ass"
    write_text_asset(ass_path, "\n".join(ass_lines))
    return ass_path


def build_ass_filter(
    input_label: str,
    output_label: str,
    *,
    ass_path: Path,
    font_dir: Path | None,
) -> str:
    options = [f"filename='{escape_filter_path(ass_path)}'"]
    if font_dir is not None:
        options.append(f"fontsdir='{escape_filter_path(font_dir)}'")
    return f"[{input_label}]ass={':'.join(options)}[{output_label}]"


def prepare_ass_font_dir(font_file: Path | None, temp_dir: Path) -> Path | None:
    if font_file is None or not font_file.exists():
        return None

    ass_font_dir = temp_dir / "ass-fonts"
    ass_font_dir.mkdir(parents=True, exist_ok=True)
    copied_font_path = ass_font_dir / font_file.name
    if not copied_font_path.exists():
        shutil.copy2(font_file, copied_font_path)
    return ass_font_dir


def build_render_environment(config: RenderConfig, temp_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    font_dirs: list[Path] = [PROJECT_DIR]

    for font_path in {
        resolve_drawtext_font_file(config.font_file),
        resolve_drawtext_font_file(config.latin_font_file),
    }:
        if font_path is not None:
            font_dirs.append(font_path.parent)

    if sys.platform.startswith("win"):
        font_dirs.append(Path("C:/Windows/Fonts"))

    fontconfig_path = write_fontconfig_file(temp_dir, font_dirs)
    env["FONTCONFIG_FILE"] = str(fontconfig_path)
    env["FONTCONFIG_PATH"] = str(temp_dir)
    env["FC_CONFIG_DIR"] = str(temp_dir)
    return env


def build_drawtext_filter(
    input_label: str,
    output_label: str,
    *,
    text_path: Path,
    y_expression: str,
    font_size: int,
    font_color: str,
    box_color: str | None,
    alpha_expression: str,
    font_file: Path | None,
    line_spacing: int = 12,
    box_border: int = 26,
    border_width: int = 2,
    border_color: str = "0x000000cc",
    shadow_x: int = 0,
    shadow_y: int = 8,
    shadow_color: str = "0x000000bb",
) -> str:
    resolved_font_file = resolve_drawtext_font_file(font_file)
    font_part = (
        f"fontfile='{escape_filter_path(resolved_font_file)}'"
        if resolved_font_file
        else "font='Arial'"
    )

    box_part = ""
    if box_color:
        box_part = f"box=1:boxcolor={box_color}:boxborderw={box_border}:"

    return (
        f"[{input_label}]drawtext="
        f"{font_part}:"
        f"textfile='{escape_filter_path(text_path)}':"
        f"reload=0:"
        f"fontcolor={font_color}:"
        f"fontsize={font_size}:"
        f"line_spacing={line_spacing}:"
        f"text_shaping=1:"
        f"fix_bounds=1:"
        f"{box_part}"
        f"borderw={border_width}:"
        f"bordercolor={border_color}:"
        f"shadowx={shadow_x}:"
        f"shadowy={shadow_y}:"
        f"shadowcolor={shadow_color}:"
        f"x=(w-text_w)/2:"
        f"y={y_expression}:"
        f"alpha='{alpha_expression}'"
        f"[{output_label}]"
    )


def build_text_block_filters(
    *,
    input_label: str,
    output_prefix: str,
    text_paths: list[Path],
    top_y: float,
    font_size: int,
    font_color: str,
    box_color: str | None,
    alpha_expression: str,
    font_file: Path | None,
    line_spacing: int,
    box_border: int,
    border_width: int = 2,
    border_color: str = "0x000000cc",
    shadow_x: int = 0,
    shadow_y: int = 8,
    shadow_color: str = "0x000000bb",
) -> list[str]:
    filters: list[str] = []
    previous_label = input_label
    line_height = font_size + line_spacing

    for index, text_path in enumerate(text_paths):
        output_label = f"{output_prefix}_{index}"
        y_position = int(round(top_y + (index * line_height)))
        filters.append(
            build_drawtext_filter(
                previous_label,
                output_label,
                text_path=text_path,
                y_expression=str(y_position),
                font_size=font_size,
                font_color=font_color,
                box_color=box_color,
                alpha_expression=alpha_expression,
                font_file=font_file,
                line_spacing=line_spacing,
                box_border=box_border,
                border_width=border_width,
                border_color=border_color,
                shadow_x=shadow_x,
                shadow_y=shadow_y,
                shadow_color=shadow_color,
            )
        )
        previous_label = output_label

    return filters


def build_alpha_expression(duration: float) -> str:
    fade_in = min(0.35, max(0.12, duration * 0.04))
    fade_out = min(0.5, max(0.18, duration * 0.07))
    fade_out_start = max(fade_in, duration - fade_out)

    return (
        f"if(lt(t,{fade_in:.2f}),t/{fade_in:.2f},"
        f"if(lt(t,{fade_out_start:.2f}),1,"
        f"if(lt(t,{duration:.2f}),({duration:.2f}-t)/{fade_out:.2f},0)))"
    )


def build_timed_alpha_expression(start_time: float, end_time: float) -> str:
    block_duration = max(0.2, end_time - start_time)
    fade_duration = min(0.35, max(0.12, block_duration * 0.18))
    full_opacity_start = start_time + fade_duration
    fade_out_start = end_time - fade_duration

    return (
        f"if(lt(t,{start_time:.2f}),0,"
        f"if(lt(t,{full_opacity_start:.2f}),(t-{start_time:.2f})/{fade_duration:.2f},"
        f"if(lt(t,{fade_out_start:.2f}),1,"
        f"if(lt(t,{end_time:.2f}),({end_time:.2f}-t)/{fade_duration:.2f},0))))"
    )


def detect_background_kind(background_path: Path | None) -> str:
    if background_path is None:
        return "generated"

    extension = background_path.suffix.lower()
    if extension in IMAGE_EXTENSIONS:
        return "image"
    if extension in VIDEO_EXTENSIONS:
        return "video"

    raise ValueError(
        "Unsupported background format. Use an image (.jpg, .png, .webp) or video (.mp4, .mov, .mkv, .webm)."
    )


def build_line_files(temp_dir: Path, prefix: str, text: str) -> list[Path]:
    line_paths: list[Path] = []

    for index, line in enumerate(text.splitlines()):
        if not line.strip():
            continue
        line_path = temp_dir / f"{prefix}_{index}.txt"
        write_text_asset(line_path, line)
        line_paths.append(line_path)

    return line_paths


def build_arabic_line_files(temp_dir: Path, prefix: str, text: str) -> list[Path]:
    return build_line_files(temp_dir, prefix, text)

def create_text_assets(config: RenderConfig, temp_dir: Path) -> dict[str, list[Path]]:
    is_cinematic = is_cinematic_style(config.style_preset)
    is_showcase = config.style_preset == SHOWCASE_STYLE
    is_minimalist = config.style_preset == "minimalist_info"

    if is_showcase:
        # Showcase: show surah name (Arabic + English) + reciter name (Arabic + English), no verse
        arabic_surah = config.arabic_surah_name or config.surah_name
        english_surah = config.surah_name
        arabic_reciter = config.arabic_reciter_name or ""
        english_reciter = config.reciter_name or ""

        # Verse slot = Arabic surah name (large, Arabic font)
        verse_text = "\n".join(filter(None, [arabic_surah, arabic_reciter]))
        # Translation slot = English surah + reciter info
        reciter_line = " ".join(filter(None, [arabic_reciter, f"· {english_reciter}" if english_reciter else ""])).strip()
        translation_text = "\n".join(filter(None, [english_surah, english_reciter]))

        brand_text = wrap_text(config.brand_text, width=24) if config.show_brand else ""
        assets = {
            "meta": [],
            "verse": build_arabic_line_files(temp_dir, "verse", verse_text),
            "brand": build_line_files(temp_dir, "brand", brand_text),
        }
        if translation_text:
            assets["translation"] = build_line_files(temp_dir, "translation", translation_text)
        return assets

    if is_minimalist:
        assets = {
            "meta": [],
            "surah": build_line_files(temp_dir, "surah", config.surah_name),
            "ayah": build_line_files(temp_dir, "ayah", f"Ayat {config.verse_reference}"),
            "brand": build_line_files(temp_dir, "brand", wrap_text(config.brand_text, width=24) if config.show_brand else ""),
            "verse": build_arabic_line_files(temp_dir, "verse", build_wrapped_arabic_text(config.verse_text, is_cinematic=False)),
        }
        
        if config.arabic_surah_name:
            assets["arabic_surah"] = build_arabic_line_files(temp_dir, "arabic_surah", config.arabic_surah_name)
            
        return assets

    title_value = config.title_text or f"{config.surah_name} | {config.verse_reference}"
    meta_text = ""
    if config.show_meta:
        if is_cinematic:
            meta_value = config.surah_name
            if config.reciter_name:
                meta_value = f"{config.surah_name} • {config.reciter_name}"
        else:
            meta_value = title_value
            if config.reciter_name:
                meta_value = f"{title_value}\nReciter: {config.reciter_name}"
        meta_text = wrap_text(meta_value, width=24 if is_cinematic else 36)

    verse_text = build_wrapped_arabic_text(config.verse_text, is_cinematic=is_cinematic)
    translation_text = wrap_text(config.translation, width=30 if is_cinematic else 34) if config.translation else ""
    brand_text = wrap_text(config.brand_text, width=24 if is_cinematic else 32) if config.show_brand else ""

    assets = {
        "meta": build_arabic_line_files(temp_dir, "meta", meta_text),
        "verse": build_arabic_line_files(temp_dir, "verse", verse_text),
        "brand": build_line_files(temp_dir, "brand", brand_text),
    }

    if translation_text:
        assets["translation"] = build_line_files(temp_dir, "translation", translation_text)

    return assets


def create_segment_assets(config: RenderConfig, temp_dir: Path) -> list[SegmentTextAsset]:
    if not config.word_segments:
        return []

    is_cinematic = is_cinematic_style(config.style_preset)
    segment_assets: list[SegmentTextAsset] = []
    for index, segment in enumerate(config.word_segments):
        arabic_text = build_wrapped_arabic_text(segment.arabic, is_cinematic=is_cinematic)
        translation_text = wrap_text(segment.translation, width=40 if is_cinematic else 45)
        segment_assets.append(
            SegmentTextAsset(
                arabic_lines=build_arabic_line_files(temp_dir, f"segment_arabic_{index}", arabic_text),
                translation_lines=build_line_files(temp_dir, f"segment_translation_{index}", translation_text),
            )
        )

    return segment_assets


def create_timed_segment_assets(config: RenderConfig, temp_dir: Path) -> list[TimedSegmentTextAsset]:
    if not config.timed_segments:
        return []

    is_cinematic = is_cinematic_style(config.style_preset)
    timed_assets: list[TimedSegmentTextAsset] = []
    for index, segment in enumerate(config.timed_segments):
        arabic_text = build_wrapped_arabic_text(segment.arabic, is_cinematic=is_cinematic)
        translation_text = wrap_text(segment.translation, width=40 if is_cinematic else 45)
        timed_assets.append(
            TimedSegmentTextAsset(
                arabic_lines=build_arabic_line_files(temp_dir, f"timed_segment_arabic_{index}", arabic_text),
                translation_lines=build_line_files(temp_dir, f"timed_segment_translation_{index}", translation_text),
                start_time=segment.start_time,
                end_time=segment.end_time,
            )
        )

    return timed_assets


def get_last_layer_label(prefix: str, text_paths: list[Path], fallback_label: str) -> str:
    if not text_paths:
        return fallback_label
    return f"{prefix}_{len(text_paths) - 1}"


def build_filter_complex(
    config: RenderConfig,
    duration: float,
    background_kind: str,
    text_assets: dict[str, list[Path]],
    segment_assets: list[SegmentTextAsset],
    timed_segment_assets: list[TimedSegmentTextAsset],
    arabic_ass_path: Path | None,
    arabic_ass_font_dir: Path | None,
    translation_ass_path: Path | None = None,
) -> str:
    is_cinematic = is_cinematic_style(config.style_preset)
    cinematic_variant = get_cinematic_variant(config.style_preset)
    cinematic_meta_top = 78 if cinematic_variant == "compact" else 112 if cinematic_variant == "spacious" else 92
    cinematic_meta_font_size = 26 if cinematic_variant == "compact" else 30 if cinematic_variant == "spacious" else 28
    cinematic_arabic_offset = 180 if cinematic_variant == "compact" else 140 if cinematic_variant == "spacious" else 160
    if globals().get('IS_LANDSCAPE'):
        cinematic_translation_top = 800 if cinematic_variant == "compact" else 840 if cinematic_variant == "spacious" else 820
    else:
        cinematic_translation_top = 980 if cinematic_variant == "compact" else 1020 if cinematic_variant == "spacious" else 1000
    cinematic_image_blur = 4 if cinematic_variant == "compact" else 2 if cinematic_variant == "spacious" else 3
    cinematic_video_blur = 3 if cinematic_variant == "compact" else 1 if cinematic_variant == "spacious" else 2
    cinematic_overlay_alpha = "0.30" if cinematic_variant == "compact" else "0.18" if cinematic_variant == "spacious" else "0.24"
    cinematic_brightness = "-0.08" if cinematic_variant == "compact" else "-0.02" if cinematic_variant == "spacious" else "-0.05"
    cinematic_video_brightness = "-0.10" if cinematic_variant == "compact" else "-0.03" if cinematic_variant == "spacious" else "-0.06"

    if background_kind == "image":
        if is_cinematic:
            base_filter = (
                f"[0:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
                "x='max(0,min(in_w-out_w,(in_w-out_w)/2+sin(n/90)*16))':"
                "y='max(0,min(in_h-out_h,(in_h-out_h)/2+cos(n/120)*12))',"
                "format=yuv420p,"
                f"eq=saturation=1.05:brightness={cinematic_brightness},"
                f"gblur=sigma={cinematic_image_blur},"
                "vignette=PI/8,"
                f"drawbox=x=0:y=0:w=iw:h=ih:color=black@{cinematic_overlay_alpha}:t=fill"
                "[base]"
            )
        else:
            base_filter = (
                f"[0:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},format=yuv420p,"
                "eq=saturation=1.12:brightness=-0.05,"
                "drawbox=x=0:y=0:w=iw:h=ih:color=black@0.24:t=fill"
                "[base]"
            )
    elif background_kind == "video":
        if is_cinematic:
            base_filter = (
                f"[0:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},format=yuv420p,"
                f"eq=saturation=1.02:brightness={cinematic_video_brightness},"
                f"gblur=sigma={cinematic_video_blur},"
                "vignette=PI/8,"
                f"drawbox=x=0:y=0:w=iw:h=ih:color=black@{cinematic_overlay_alpha}:t=fill"
                "[base]"
            )
        else:
            base_filter = (
                f"[0:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},format=yuv420p,"
                "eq=saturation=1.10:brightness=-0.06,"
                "drawbox=x=0:y=0:w=iw:h=ih:color=black@0.28:t=fill"
                "[base]"
            )
    else:
        if is_cinematic:
            base_filter = (
                "[0:v]format=yuv420p,"
                "drawbox=x=-120:y=180:w=640:h=640:color=0x275c88@0.18:t=fill,"
                "drawbox=x=440:y=1220:w=760:h=440:color=0x497a58@0.16:t=fill,"
                "drawbox=x=0:y=0:w=iw:h=ih:color=0x05070a@0.24:t=fill,"
                "gblur=sigma=52,"
                "eq=saturation=1.02:brightness=-0.03,"
                "vignette=PI/7"
                "[base]"
            )
        else:
            base_filter = (
                "[0:v]format=yuv420p,"
                "drawbox=x=-120:y=220:w=640:h=640:color=0x2f6f5e@0.28:t=fill,"
                "drawbox=x=420:y=1080:w=760:h=520:color=0x7a8f3b@0.18:t=fill,"
                "drawbox=x=150:y=1460:w=520:h=360:color=0x365c9a@0.16:t=fill,"
                "gblur=sigma=70,"
                "eq=saturation=1.12:brightness=-0.02,"
                "noise=alls=3:allf=t,"
                "vignette=PI/6"
                "[base]"
            )

    is_minimalist = config.style_preset == "minimalist_info"
    alpha_expression = build_alpha_expression(duration)
    filters = [base_filter]
    resolved_arabic_font = resolve_drawtext_font_file(config.font_file)
    arabic_font_dir = arabic_ass_font_dir or (resolved_arabic_font.parent if resolved_arabic_font is not None else None)
    
    if is_minimalist:
        # Full screen darkening overlay
        box_filter = "[base]drawbox=x=0:y=0:w=iw:h=ih:color=black@0.45:t=fill[bg_dark]"
        
        filters.extend([box_filter])
        previous_label = "bg_dark"
        
        ar_surah = text_assets.get("arabic_surah", [])
        if ar_surah:
            filters.extend(build_text_block_filters(
                input_label=previous_label, output_prefix="ar_surah", text_paths=ar_surah,
                top_y=500, font_size=150, font_color="0xffffff", box_color=None, alpha_expression=alpha_expression,
                font_file=config.font_file, line_spacing=10, box_border=0, border_width=0, shadow_y=12, shadow_color="0x000000dd", shadow_x=0
            ))
            previous_label = f"ar_surah_{len(ar_surah)-1}"
            
        en_surah_base = (VIDEO_HEIGHT - 350) if globals().get('IS_LANDSCAPE') else 600
        en_surah_offset = (VIDEO_HEIGHT - 280) if globals().get('IS_LANDSCAPE') else 680
        ayah_base = (VIDEO_HEIGHT - 220) if globals().get('IS_LANDSCAPE') else 710
        ayah_offset = (VIDEO_HEIGHT - 170) if globals().get('IS_LANDSCAPE') else 790

        filters.extend(build_text_block_filters(
            input_label=previous_label, output_prefix="en_surah", text_paths=text_assets["surah"],
            top_y=en_surah_offset if ar_surah else en_surah_base, font_size=75, font_color="0xf8fafc", box_color=None, alpha_expression=alpha_expression,
            font_file=config.latin_font_file or config.font_file, line_spacing=10, box_border=0, border_width=0, shadow_y=8, shadow_color="0x000000cc", shadow_x=0
        ))
        previous_label = "en_surah_0"
        
        filters.extend(build_text_block_filters(
            input_label=previous_label, output_prefix="ayah", text_paths=text_assets["ayah"],
            top_y=ayah_offset if ar_surah else ayah_base, font_size=45, font_color="0x90e0ef", box_color=None, alpha_expression=alpha_expression,
            font_file=config.latin_font_file or config.font_file, line_spacing=10, box_border=0, border_width=0, shadow_y=6, shadow_color="0x000000aa", shadow_x=0
        ))
        previous_label = "ayah_0"

        verse = text_assets.get("verse", [])
        if verse:
            if arabic_ass_path is not None:
                filters.append(
                    build_ass_filter(
                        previous_label,
                        "arabic_ass_layer",
                        ass_path=arabic_ass_path,
                        font_dir=arabic_font_dir,
                    )
                )
                previous_label = "arabic_ass_layer"
            elif timed_segment_assets:
                for index, segment_asset in enumerate(timed_segment_assets):
                    segment_alpha = build_timed_alpha_expression(segment_asset.start_time, segment_asset.end_time)
                    arabic_font_size, arabic_line_spacing, arabic_top = resolve_minimalist_arabic_layout(
                        read_text_lines(segment_asset.arabic_lines)
                    )
                    arabic_prefix = f"minimalist_timed_arabic_{index}"
                    filters.extend(
                        build_text_block_filters(
                            input_label=previous_label,
                            output_prefix=arabic_prefix,
                            text_paths=segment_asset.arabic_lines,
                            top_y=arabic_top,
                            font_size=arabic_font_size,
                            font_color="0xffffff",
                            box_color=None,
                            alpha_expression=segment_alpha,
                            font_file=config.font_file,
                            line_spacing=arabic_line_spacing,
                            box_border=0,
                            border_width=10,
                            border_color="black",
                            shadow_y=0,
                            shadow_color="0x00000000",
                            shadow_x=0,
                        )
                    )
                    previous_label = get_last_layer_label(arabic_prefix, segment_asset.arabic_lines, previous_label)
            elif segment_assets:
                intro_padding = 0.45
                outro_padding = 0.45
                available_duration = max(1.0, duration - intro_padding - outro_padding)
                segment_duration = available_duration / len(segment_assets)

                for index, segment_asset in enumerate(segment_assets):
                    start_time = intro_padding + (index * segment_duration)
                    end_time = duration - outro_padding if index == len(segment_assets) - 1 else start_time + segment_duration
                    segment_alpha = build_timed_alpha_expression(start_time, end_time)
                    arabic_font_size, arabic_line_spacing, arabic_top = resolve_minimalist_arabic_layout(
                        read_text_lines(segment_asset.arabic_lines)
                    )
                    arabic_prefix = f"minimalist_segment_arabic_{index}"
                    filters.extend(
                        build_text_block_filters(
                            input_label=previous_label,
                            output_prefix=arabic_prefix,
                            text_paths=segment_asset.arabic_lines,
                            top_y=arabic_top,
                            font_size=arabic_font_size,
                            font_color="0xffffff",
                            box_color=None,
                            alpha_expression=segment_alpha,
                            font_file=config.font_file,
                            line_spacing=arabic_line_spacing,
                            box_border=0,
                            border_width=10,
                            border_color="black",
                            shadow_y=0,
                            shadow_color="0x00000000",
                            shadow_x=0,
                        )
                    )
                    previous_label = get_last_layer_label(arabic_prefix, segment_asset.arabic_lines, previous_label)
            else:
                arabic_font_size, arabic_line_spacing, arabic_top = resolve_minimalist_arabic_layout(read_text_lines(verse))
                filters.extend(build_text_block_filters(
                    input_label=previous_label, output_prefix="verse", text_paths=verse,
                    top_y=arabic_top, font_size=arabic_font_size, font_color="0xffffff", box_color=None, alpha_expression=alpha_expression,
                    font_file=config.font_file, line_spacing=arabic_line_spacing, box_border=0, border_width=10, border_color="black", shadow_y=0, shadow_color="0x00000000", shadow_x=0
                ))
                previous_label = f"verse_{len(verse)-1}"
        
        if text_assets["brand"]:
            filters.extend(build_text_block_filters(
                input_label=previous_label, output_prefix="brand", text_paths=text_assets["brand"],
                top_y=1750, font_size=32, font_color="0x90e0ef", box_color=None, alpha_expression=alpha_expression,
                font_file=config.latin_font_file or config.font_file, line_spacing=10, box_border=0, border_width=0, shadow_y=2, shadow_color="0x00000088", shadow_x=0
            ))
            previous_label = "brand_0"
            
        filters.append(f"[{previous_label}]copy[vout]")
        return ";".join(filters)

    use_timed_segment_overlays = bool(timed_segment_assets) and not config.prefer_static_text_overlay
    use_segment_overlays = bool(segment_assets) and not config.prefer_static_text_overlay

    meta_font_size = (
        max(22, cinematic_meta_font_size - 2)
        if is_cinematic and config.prefer_static_text_overlay
        else cinematic_meta_font_size if is_cinematic else 48
    )
    meta_line_spacing = 8 if is_cinematic else 12
    filters.extend(
        build_text_block_filters(
            input_label="base_waves" if is_minimalist else "base",
            output_prefix="meta_layer",
            text_paths=text_assets["meta"],
            top_y=cinematic_meta_top if is_cinematic else 140,
            font_size=meta_font_size,
            font_color="0xf8fafccc" if is_cinematic else "0xffd166",
            box_color=None,
            alpha_expression=alpha_expression,
            font_file=config.latin_font_file or (None if is_cinematic else config.font_file),
            line_spacing=meta_line_spacing,
            box_border=0,
            border_width=1,
            border_color="0x00000066" if is_cinematic else "0x2a1a00dd",
            shadow_x=0,
            shadow_y=4 if is_cinematic else 6,
            shadow_color="0x000000aa",
        )
    )
    previous_label = get_last_layer_label("meta_layer", text_assets["meta"], "base_waves" if is_minimalist else "base")

    if arabic_ass_path is not None:
        filters.append(
            build_ass_filter(
                previous_label,
                "arabic_ass_layer",
                ass_path=arabic_ass_path,
                font_dir=arabic_font_dir,
            )
        )
        previous_label = "arabic_ass_layer"

    if use_timed_segment_overlays:
        if translation_ass_path is not None:
            # Efficient path: use ASS subtitle files for both Arabic and
            # translation overlays.  This avoids creating hundreds of chained
            # drawtext filters which would crash ffmpeg for long surahs.
            if arabic_ass_path is not None:
                # Arabic already handled by ASS above; nothing to do here.
                pass
            else:
                for index, segment_asset in enumerate(timed_segment_assets):
                    segment_alpha = build_timed_alpha_expression(segment_asset.start_time, segment_asset.end_time)
                    arabic_font_size, arabic_line_spacing = resolve_arabic_text_metrics(
                        len(segment_asset.arabic_lines),
                        is_cinematic=is_cinematic,
                        max_line_units=measure_arabic_line_units("\n".join(path.read_text(encoding="utf-8") for path in segment_asset.arabic_lines)),
                    )
                    translation_font_size, translation_line_spacing = resolve_translation_text_metrics(
                        len(segment_asset.translation_lines),
                        is_cinematic=is_cinematic,
                    )
                    arabic_block_height = (len(segment_asset.arabic_lines) * (arabic_font_size + arabic_line_spacing)) - arabic_line_spacing
                    preferred_arabic_top = ((VIDEO_HEIGHT - arabic_block_height) / 2) - (cinematic_arabic_offset if is_cinematic else 100)
                    arabic_top, _ = resolve_text_stack_positions(
                        arabic_block_height=arabic_block_height,
                        translation_line_count=len(segment_asset.translation_lines),
                        translation_font_size=translation_font_size,
                        translation_line_spacing=translation_line_spacing,
                        is_cinematic=is_cinematic,
                        preferred_arabic_top=preferred_arabic_top,
                        preferred_translation_top=cinematic_translation_top if is_cinematic else VIDEO_HEIGHT - (250 if globals().get('IS_LANDSCAPE') else 500),
                    )
                    arabic_prefix = f"timed_segment_arabic_layer_{index}"
                    filters.extend(
                        build_text_block_filters(
                            input_label=previous_label,
                            output_prefix=arabic_prefix,
                            text_paths=segment_asset.arabic_lines,
                            top_y=arabic_top,
                            font_size=arabic_font_size,
                            font_color="white",
                            box_color=None,
                            alpha_expression=segment_alpha,
                            font_file=config.font_file,
                            line_spacing=arabic_line_spacing,
                            box_border=0,
                            border_width=10,
                            border_color="black",
                            shadow_x=0,
                            shadow_y=0,
                            shadow_color="0x00000000",
                        )
                    )
                    previous_label = get_last_layer_label(arabic_prefix, segment_asset.arabic_lines, previous_label)

            # Render translations using ASS subtitle overlay.
            trans_ass_font_dir = arabic_ass_font_dir
            if config.latin_font_file and config.latin_font_file != config.font_file:
                latin_font_dir = prepare_ass_font_dir(resolve_drawtext_font_file(config.latin_font_file), translation_ass_path.parent)
                if latin_font_dir is not None:
                    trans_ass_font_dir = latin_font_dir
            filters.append(
                build_ass_filter(
                    previous_label,
                    "translation_ass_layer",
                    ass_path=translation_ass_path,
                    font_dir=trans_ass_font_dir,
                )
            )
            previous_label = "translation_ass_layer"
        else:
            # Standard path for few segments: use drawtext filters.
            for index, segment_asset in enumerate(timed_segment_assets):
                segment_alpha = build_timed_alpha_expression(segment_asset.start_time, segment_asset.end_time)

                arabic_font_size, arabic_line_spacing = resolve_arabic_text_metrics(
                    len(segment_asset.arabic_lines),
                    is_cinematic=is_cinematic,
                    max_line_units=measure_arabic_line_units("\n".join(path.read_text(encoding="utf-8") for path in segment_asset.arabic_lines)),
                )
                translation_font_size, translation_line_spacing = resolve_translation_text_metrics(
                    len(segment_asset.translation_lines),
                    is_cinematic=is_cinematic,
                )
                arabic_block_height = (len(segment_asset.arabic_lines) * (arabic_font_size + arabic_line_spacing)) - arabic_line_spacing
                preferred_arabic_top = ((VIDEO_HEIGHT - arabic_block_height) / 2) - (cinematic_arabic_offset if is_cinematic else 100)
                arabic_top, translation_top = resolve_text_stack_positions(
                    arabic_block_height=arabic_block_height,
                    translation_line_count=len(segment_asset.translation_lines),
                    translation_font_size=translation_font_size,
                    translation_line_spacing=translation_line_spacing,
                    is_cinematic=is_cinematic,
                    preferred_arabic_top=preferred_arabic_top,
                    preferred_translation_top=cinematic_translation_top if is_cinematic else VIDEO_HEIGHT - (250 if globals().get('IS_LANDSCAPE') else 500),
                )
                if arabic_ass_path is None:
                    arabic_prefix = f"timed_segment_arabic_layer_{index}"

                    filters.extend(
                        build_text_block_filters(
                            input_label=previous_label,
                            output_prefix=arabic_prefix,
                            text_paths=segment_asset.arabic_lines,
                            top_y=arabic_top,
                            font_size=arabic_font_size,
                            font_color="white",
                            box_color=None,
                            alpha_expression=segment_alpha,
                            font_file=config.font_file,
                            line_spacing=arabic_line_spacing,
                            box_border=0,
                            border_width=10,
                            border_color="black",
                            shadow_x=0,
                            shadow_y=0,
                            shadow_color="0x00000000",
                        )
                    )
                    previous_label = get_last_layer_label(arabic_prefix, segment_asset.arabic_lines, previous_label)

                translation_prefix = f"timed_segment_translation_layer_{index}"
                filters.extend(
                    build_text_block_filters(
                        input_label=previous_label,
                        output_prefix=translation_prefix,
                        text_paths=segment_asset.translation_lines,
                        top_y=translation_top,
                        font_size=translation_font_size,
                        font_color="0xf8fafc",
                        box_color=None if is_cinematic else "0x00000022",
                        alpha_expression=segment_alpha,
                        font_file=config.latin_font_file or (None if is_cinematic else config.font_file),
                        line_spacing=translation_line_spacing,
                        box_border=0,
                        border_width=8,
                        border_color="black",
                        shadow_x=0,
                        shadow_y=0,
                        shadow_color="0x00000000",
                    )
                )
                previous_label = get_last_layer_label(translation_prefix, segment_asset.translation_lines, previous_label)
    elif use_segment_overlays:
        intro_padding = 0.45
        outro_padding = 0.45
        available_duration = max(1.0, duration - intro_padding - outro_padding)
        segment_duration = available_duration / len(segment_assets)

        for index, segment_asset in enumerate(segment_assets):
            start_time = intro_padding + (index * segment_duration)
            end_time = duration - outro_padding if index == len(segment_assets) - 1 else start_time + segment_duration
            segment_alpha = build_timed_alpha_expression(start_time, end_time)

            arabic_font_size, arabic_line_spacing = resolve_arabic_text_metrics(
                len(segment_asset.arabic_lines),
                is_cinematic=is_cinematic,
                max_line_units=measure_arabic_line_units("\n".join(path.read_text(encoding="utf-8") for path in segment_asset.arabic_lines)),
            )
            translation_font_size, translation_line_spacing = resolve_translation_text_metrics(
                len(segment_asset.translation_lines),
                is_cinematic=is_cinematic,
            )
            arabic_block_height = (len(segment_asset.arabic_lines) * (arabic_font_size + arabic_line_spacing)) - arabic_line_spacing
            preferred_arabic_top = ((VIDEO_HEIGHT - arabic_block_height) / 2) - (cinematic_arabic_offset if is_cinematic else 100)
            arabic_top, translation_top = resolve_text_stack_positions(
                arabic_block_height=arabic_block_height,
                translation_line_count=len(segment_asset.translation_lines),
                translation_font_size=translation_font_size,
                translation_line_spacing=translation_line_spacing,
                is_cinematic=is_cinematic,
                preferred_arabic_top=preferred_arabic_top,
                preferred_translation_top=cinematic_translation_top if is_cinematic else VIDEO_HEIGHT - (250 if globals().get('IS_LANDSCAPE') else 500),
            )
            if arabic_ass_path is None:
                arabic_prefix = f"segment_arabic_layer_{index}"

                filters.extend(
                    build_text_block_filters(
                        input_label=previous_label,
                        output_prefix=arabic_prefix,
                        text_paths=segment_asset.arabic_lines,
                        top_y=arabic_top,
                        font_size=arabic_font_size,
                        font_color="white",
                        box_color=None,
                        alpha_expression=segment_alpha,
                        font_file=config.font_file,
                        line_spacing=arabic_line_spacing,
                        box_border=0,
                        border_width=10,
                        border_color="black",
                        shadow_x=0,
                        shadow_y=0,
                        shadow_color="0x00000000",
                    )
                )
                previous_label = get_last_layer_label(arabic_prefix, segment_asset.arabic_lines, previous_label)

            translation_prefix = f"segment_translation_layer_{index}"
            filters.extend(
                build_text_block_filters(
                    input_label=previous_label,
                    output_prefix=translation_prefix,
                    text_paths=segment_asset.translation_lines,
                    top_y=translation_top,
                    font_size=translation_font_size,
                    font_color="0xf8fafc",
                    box_color=None if is_cinematic else "0x00000022",
                    alpha_expression=segment_alpha,
                    font_file=config.latin_font_file or (None if is_cinematic else config.font_file),
                    line_spacing=translation_line_spacing,
                    box_border=0,
                    border_width=8,
                    border_color="black",
                    shadow_x=0,
                    shadow_y=0,
                    shadow_color="0x00000000",
                )
            )
            previous_label = get_last_layer_label(translation_prefix, segment_asset.translation_lines, previous_label)
    else:
        verse_font_size, verse_line_spacing = resolve_arabic_text_metrics(
            len(text_assets["verse"]),
            is_cinematic=is_cinematic,
            max_line_units=measure_arabic_line_units("\n".join(path.read_text(encoding="utf-8") for path in text_assets["verse"])),
        )
        translation_font_size, translation_line_spacing = resolve_translation_text_metrics(
            len(text_assets.get("translation", [])),
            is_cinematic=is_cinematic,
        )
        verse_block_height = (len(text_assets["verse"]) * (verse_font_size + verse_line_spacing)) - verse_line_spacing
        preferred_verse_top = ((VIDEO_HEIGHT - verse_block_height) / 2) - (cinematic_arabic_offset if is_cinematic else 110)
        verse_top, translation_top = resolve_text_stack_positions(
            arabic_block_height=verse_block_height,
            translation_line_count=len(text_assets.get("translation", [])),
            translation_font_size=translation_font_size,
            translation_line_spacing=translation_line_spacing,
            is_cinematic=is_cinematic,
            preferred_arabic_top=preferred_verse_top,
            preferred_translation_top=cinematic_translation_top if is_cinematic else VIDEO_HEIGHT - (220 if globals().get('IS_LANDSCAPE') else 470),
        )
        if arabic_ass_path is None:
            filters.extend(
                build_text_block_filters(
                    input_label=previous_label,
                    output_prefix="verse_layer",
                    text_paths=text_assets["verse"],
                    top_y=verse_top,
                    font_size=verse_font_size,
                    font_color="white",
                    box_color=None,
                    alpha_expression=alpha_expression,
                    font_file=config.font_file,
                    line_spacing=verse_line_spacing,
                    box_border=0,
                    border_width=10,
                    border_color="black",
                    shadow_x=0,
                    shadow_y=0,
                    shadow_color="0x00000000",
                )
            )
            previous_label = get_last_layer_label("verse_layer", text_assets["verse"], previous_label)

        if "translation" in text_assets:
            filters.extend(
                build_text_block_filters(
                    input_label=previous_label,
                    output_prefix="translation_layer",
                    text_paths=text_assets["translation"],
                    top_y=translation_top,
                    font_size=translation_font_size,
                    font_color="0xf8fafc",
                    box_color=None if is_cinematic and config.prefer_static_text_overlay else "0x02061766" if is_cinematic else None,
                    alpha_expression=alpha_expression,
                    font_file=config.latin_font_file or (None if is_cinematic else config.font_file),
                    line_spacing=translation_line_spacing,
                    box_border=0,
                    border_width=8,
                    border_color="black",
                    shadow_x=0,
                    shadow_y=0,
                    shadow_color="0x00000000",
                )
            )
            previous_label = get_last_layer_label("translation_layer", text_assets["translation"], previous_label)

    brand_font_size = 22 if is_cinematic else 28
    brand_line_spacing = 8
    filters.extend(
        build_text_block_filters(
            input_label=previous_label,
            output_prefix="brand_layer",
            text_paths=text_assets["brand"],
            top_y=VIDEO_HEIGHT - (110 if is_cinematic else 150),
            font_size=brand_font_size,
            font_color="0x90e0ef",
            box_color=None,
            alpha_expression=alpha_expression,
            font_file=config.latin_font_file or config.font_file,
            line_spacing=brand_line_spacing,
            box_border=0,
            border_width=1,
            border_color="0x082f49cc",
            shadow_x=0,
            shadow_y=4,
            shadow_color="0x00000088",
        )
    )
    if text_assets["brand"]:
        last_brand_label = f"brand_layer_{len(text_assets['brand']) - 1}"
        filters.append(f"[{last_brand_label}]copy[vout]")
    else:
        filters.append(f"[{previous_label}]copy[vout]")

    return ";".join(filters)


def build_command(config: RenderConfig, duration: float, temp_dir: Path, ffmpeg_command: str) -> list[str]:
    background_kind = detect_background_kind(config.background_path)
    text_assets = create_text_assets(config, temp_dir)
    segment_assets = create_segment_assets(config, temp_dir)
    timed_segment_assets = create_timed_segment_assets(config, temp_dir)
    arabic_ass_path = create_arabic_ass_file(
        config,
        duration,
        temp_dir,
        text_assets,
        segment_assets,
        timed_segment_assets,
    )
    translation_ass_path = create_translation_ass_file(
        config,
        duration,
        temp_dir,
        timed_segment_assets,
    )
    arabic_ass_font_dir = prepare_ass_font_dir(resolve_drawtext_font_file(config.font_file), temp_dir)

    command: list[str] = [ffmpeg_command, "-y"]

    if background_kind == "generated":
        command.extend(
            [
                "-f",
                "lavfi",
                "-i",
                f"color=c=#0f172a:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:r={config.fps}",
            ]
        )
    elif background_kind == "image":
        command.extend(["-loop", "1", "-framerate", str(config.fps), "-i", str(config.background_path)])
    else:
        command.extend(["-stream_loop", "-1", "-i", str(config.background_path)])

    command.extend(["-i", str(config.audio_path)])

    filter_complex = build_filter_complex(
        config,
        duration,
        background_kind,
        text_assets,
        segment_assets,
        timed_segment_assets,
        arabic_ass_path,
        arabic_ass_font_dir,
        translation_ass_path=translation_ass_path,
    )

    audio_fade_start = max(0.0, duration - 0.8)
    audio_filter = f"afade=t=in:st=0:d=0.4,afade=t=out:st={audio_fade_start:.2f}:d=0.8"

    filter_script_path = temp_dir / "filter_script.txt"
    filter_script_path.write_text(filter_complex, encoding="utf-8")

    command.extend(
        [
            "-filter_complex_script",
            str(filter_script_path),
            "-map",
            "[vout]",
            "-map",
            "1:a:0",
            "-af",
            audio_filter,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(config.fps),
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-shortest",
            str(config.output_path),
        ]
    )

    return command


def render_video(config: RenderConfig) -> None:
    ffmpeg_command = resolve_binary_command("ffmpeg")
    ffprobe_command = resolve_binary_command("ffprobe")

    duration = probe_duration(config.audio_path, ffprobe_command)
    config.output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="quran-short-") as temp_folder:
        temp_dir = Path(temp_folder)
        command = build_command(config, duration, temp_dir, ffmpeg_command)
        render_env = build_render_environment(config, temp_dir)
        subprocess.run(command, check=True, env=render_env)


def load_facebook_page_config(path: Path) -> FacebookPageConfig:
    import json
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return FacebookPageConfig(
        page_id=data["page_id"],
        page_access_token=data["access_token"],
        instagram_business_id=data.get("instagram_business_id") or data.get("instagram_id"),
        api_version=data.get("api_version", DEFAULT_FACEBOOK_API_VERSION),
        reciter_key=data.get("reciter_key"),
        recitation_relative_path=data.get("recitation_relative_path"),
        reciter_name=data.get("reciter_name"),
        audio_base_url=data.get("audio_base_url", VERSES_AUDIO_BASE_URL),
        credit_lines=tuple(data.get("credit_lines", [])),
    )


def upload_video_to_instagram_reel(
    video_path: Path,
    config: RenderConfig,
    page_config: FacebookPageConfig,
) -> str:
    import subprocess
    import json
    import time

    if not page_config.instagram_business_id:
        raise ValueError("Instagram Business ID is required for Instagram uploads.")

    print(f"Initializing Instagram Reel Upload for {video_path.name}")
    caption = build_facebook_reel_description(config, page_config)
    
    # 1. Initialize Upload / Create Media Container
    init_url = f"{FACEBOOK_GRAPH_API_BASE_URL}/{page_config.api_version}/{page_config.instagram_business_id}/media"
    
    # Note: Instagram API requires a public URL or a direct file upload via multipart/form-data for sessions.
    # For Reels, we can use the same pattern as Facebook.
    command_init = [
        "curl", "-s", "-X", "POST", init_url,
        "-F", f"access_token={page_config.page_access_token}",
        "-F", "media_type=REELS",
        "-F", f"caption={caption}",
        "-F", f"video=@{video_path.absolute().as_posix()}"
    ]
    
    print(f"Uploading media container to {init_url}...")
    result_init = subprocess.run(command_init, capture_output=True, text=True, check=False)
    
    if result_init.returncode != 0:
        raise RuntimeError(f"CURL Instagram init failed: {result_init.stderr}")
        
    try:
        init_data = json.loads(result_init.stdout)
    except Exception as e:
        raise RuntimeError(f"Failed to parse Instagram response: {result_init.stdout}") from e
        
    if "error" in init_data:
        raise RuntimeError(f"Instagram API Error (Init): {init_data['error']}")
        
    container_id = str(init_data.get("id", ""))
    if not container_id:
        raise RuntimeError(f"No container ID returned from Instagram: {init_data}")

    # 2. Poll for status (Instagram requires the container to be 'FINISHED' before publishing)
    status_url = f"{FACEBOOK_GRAPH_API_BASE_URL}/{page_config.api_version}/{container_id}"
    print(f"Waiting for Instagram to process container {container_id}...")
    
    for _ in range(30): # Poll for 5 minutes max
        status_res = subprocess.run([
            "curl", "-s", "-G", status_url,
            "-d", f"access_token={page_config.page_access_token}",
            "-d", "fields=status_code"
        ], capture_output=True, text=True, check=False)
        
        try:
            status_data = json.loads(status_res.stdout)
            status_code = status_data.get("status_code", "")
            if status_code == "FINISHED":
                print("Instagram processing complete.")
                break
            if status_code == "ERROR":
                raise RuntimeError(f"Instagram processing failed: {status_data}")
            print(f"Status: {status_code}. Sleeping 10s...")
        except:
            print("Error checking status, retrying...")
            
        time.sleep(10)
    else:
        raise TimeoutError("Instagram took too long to process the video.")

    # 3. Publish
    publish_url = f"{FACEBOOK_GRAPH_API_BASE_URL}/{page_config.api_version}/{page_config.instagram_business_id}/media_publish"
    command_publish = [
        "curl", "-s", "-X", "POST", publish_url,
        "-F", f"access_token={page_config.page_access_token}",
        "-F", f"creation_id={container_id}"
    ]
    
    print(f"Publishing Reel {container_id}...")
    result_publish = subprocess.run(command_publish, capture_output=True, text=True, check=False)
    
    try:
        publish_data = json.loads(result_publish.stdout)
        if "error" in publish_data:
             raise RuntimeError(f"Instagram API Error (Publish): {publish_data['error']}")
        print(f"Successfully published to Instagram! Media ID: {publish_data.get('id')}")
        return str(publish_data.get("id"))
    except Exception as e:
        raise RuntimeError(f"Failed to publish Instagram reel: {result_publish.stdout}") from e


def main() -> int:
    global IS_LANDSCAPE, IS_WHOLE_SURAH, VIDEO_WIDTH, VIDEO_HEIGHT
    args = parse_args()
    if args.landscape:
        IS_LANDSCAPE = True
        VIDEO_WIDTH = 1920
        VIDEO_HEIGHT = 1080
    if args.whole_surah:
        IS_WHOLE_SURAH = True

    configs: list[RenderConfig] = []
    base_dir = Path.cwd()
    youtube_options = None
    facebook_options = object() if args.facebook_upload else None
    facebook_page_config = None
    tiktok_options = None
    try:
        if args.youtube_upload or args.youtube_auth_only:
            youtube_options = build_youtube_upload_options(args, base_dir)
        if args.youtube_auth_only:
            if youtube_options is None:
                raise RuntimeError("YouTube upload options could not be built.")
            get_youtube_credentials(youtube_options, interactive=True)
            print(f"YouTube token saved to {youtube_options.token_file}")
            return 0
            
        if args.facebook_upload or args.instagram_upload:
            fb_config_path = base_dir / (args.facebook_page_config_file or DEFAULT_FACEBOOK_PAGE_CONFIG_FILE)
            if not fb_config_path.exists():
                raise FileNotFoundError(f"Facebook/Instagram config file missing: {fb_config_path}")
            facebook_page_config = load_facebook_page_config(fb_config_path)

        use_auto_mode = args.auto or not args.config
        if use_auto_mode:
            configs = build_auto_render_configs(
                base_dir,
                count=args.count,
                target_seconds=args.target_seconds,
                auto_reciter_library_file=args.auto_reciter_library_file,
            )
        else:
            config_path = Path(args.config).expanduser()
            if not config_path.exists():
                print(f"Config file not found: {config_path}", file=sys.stderr)
                return 1
            configs = load_render_configs(config_path)

        total_configs = len(configs)

        for index, config in enumerate(configs, start=1):
            if total_configs > 1:
                print(
                    f"[{index}/{total_configs}] Rendering {config.surah_name} "
                    f"({config.verse_reference}) -> {config.output_path.name}"
                )
            try:
                render_video(config)
                youtube_upload_result = None
                facebook_upload_result = None
                instagram_upload_result = None
                tiktok_upload_result = None
                if youtube_options is not None and args.youtube_upload:
                    resolved_youtube_options = resolve_youtube_upload_options_for_index(
                        youtube_options,
                        upload_index=index,
                    )
                    print(f"Uploading to YouTube: {config.output_path.name}")
                    if resolved_youtube_options.schedule_at is not None:
                        print(
                            "YouTube publish slot: "
                            f"{resolved_youtube_options.schedule_at.astimezone(resolve_schedule_timezone(resolved_youtube_options.schedule_timezone)).isoformat()}"
                        )
                    youtube_upload_result = upload_video_to_youtube(
                        video_path=config.output_path,
                        config=config,
                        options=resolved_youtube_options,
                        interactive_auth=False,
                    )
                    print(
                        "Uploaded to YouTube: "
                        f"{youtube_upload_result['watch_url']} "
                        f"({youtube_upload_result['privacy_status']})"
                    )
                if facebook_options is not None and args.facebook_upload:
                    facebook_render_config = config
                    if facebook_page_config is not None:
                        facebook_render_config = build_facebook_render_config(
                            config,
                            page_config=facebook_page_config,
                            base_dir=base_dir,
                        )
                        if facebook_render_config is not config:
                            print(f"Rendering Facebook-specific version: {facebook_render_config.output_path.name}")
                            render_video(facebook_render_config)
                    print(f"Uploading to Facebook Page: {facebook_render_config.output_path.name}")
                    facebook_upload_result = upload_video_to_facebook(
                        video_path=facebook_render_config.output_path,
                        config=facebook_render_config,
                        options=facebook_options,
                        page_config=facebook_page_config,
                    )
                    facebook_message = (
                        f"Uploaded to Facebook: video_id={facebook_upload_result['video_id']} "
                        f"({facebook_upload_result['video_state']}, {facebook_upload_result['status']})"
                    )
                    if facebook_upload_result["watch_url"]:
                        facebook_message += f" {facebook_upload_result['watch_url']}"
                    print(facebook_message)
                if facebook_page_config is not None and args.instagram_upload:
                    if facebook_page_config.instagram_business_id:
                        print(f"Uploading to Instagram Reels: {config.output_path.name}")
                        instagram_video_id = upload_video_to_instagram_reel(
                            video_path=config.output_path,
                            config=config,
                            page_config=facebook_page_config,
                        )
                        print(f"Uploaded to Instagram: media_id={instagram_video_id}")
                    else:
                        print("Skipping Instagram upload: instagram_business_id missing in config.")
                if tiktok_options is not None and args.tiktok_upload:
                    print(f"Uploading to TikTok: {config.output_path.name}")
                    tiktok_upload_result = upload_video_to_tiktok(
                        video_path=config.output_path,
                        config=config,
                        options=tiktok_options,
                        interactive_auth=False,
                    )
                    tiktok_message = (
                        f"Uploaded to TikTok: publish_id={tiktok_upload_result['publish_id']} "
                        f"({tiktok_upload_result['privacy_level']}, {tiktok_upload_result['status']})"
                    )
                    if tiktok_upload_result["watch_url"]:
                        tiktok_message += f" {tiktok_upload_result['watch_url']}"
                    print(tiktok_message)
                if config.auto_history_entry is not None:
                    config.auto_history_entry["rendered_at"] = datetime.now(timezone.utc).isoformat()
                    if youtube_upload_result is not None:
                        config.auto_history_entry["youtube_video_id"] = youtube_upload_result["video_id"]
                        config.auto_history_entry["youtube_watch_url"] = youtube_upload_result["watch_url"]
                        config.auto_history_entry["youtube_privacy_status"] = youtube_upload_result["privacy_status"]
                        if youtube_upload_result.get("publish_at"):
                            config.auto_history_entry["youtube_publish_at"] = youtube_upload_result["publish_at"]
                            config.auto_history_entry["youtube_schedule_timezone"] = (
                                resolved_youtube_options.schedule_timezone
                                if youtube_options is not None
                                else DEFAULT_YOUTUBE_AUTO_SCHEDULE_TIMEZONE
                            )
                        config.auto_history_entry["uploaded_at"] = datetime.now(timezone.utc).isoformat()
                    if facebook_upload_result is not None:
                        config.auto_history_entry["facebook_video_id"] = facebook_upload_result["video_id"]
                        config.auto_history_entry["facebook_status"] = facebook_upload_result["status"]
                        config.auto_history_entry["facebook_video_state"] = facebook_upload_result["video_state"]
                        if facebook_page_config is not None:
                            facebook_recitation_source = resolve_facebook_recitation_source(facebook_page_config)
                            if facebook_recitation_source is not None:
                                config.auto_history_entry["facebook_reciter_name"] = (
                                    facebook_page_config.reciter_name
                                    or facebook_recitation_source[1]
                                    or config.reciter_name
                                    or ""
                                )
                        if facebook_upload_result["watch_url"]:
                            config.auto_history_entry["facebook_watch_url"] = facebook_upload_result["watch_url"]
                    if tiktok_upload_result is not None:
                        config.auto_history_entry["tiktok_publish_id"] = tiktok_upload_result["publish_id"]
                        config.auto_history_entry["tiktok_status"] = tiktok_upload_result["status"]
                        config.auto_history_entry["tiktok_privacy_level"] = tiktok_upload_result["privacy_level"]
                        if tiktok_upload_result["watch_url"]:
                            config.auto_history_entry["tiktok_watch_url"] = tiktok_upload_result["watch_url"]
                    append_auto_history_entry(base_dir, config.auto_history_entry)
            except Exception as error:  # noqa: BLE001
                raise RuntimeError(
                    f"Render {index}/{total_configs} failed for "
                    f"{config.surah_name} ({config.verse_reference}): {error}"
                ) from error
    except Exception as error:  # noqa: BLE001
        print(f"Error: {error}", file=sys.stderr)
        return 1

    if len(configs) == 1:
        print(f"Video created successfully: {configs[0].output_path}")
    else:
        print(f"Created {len(configs)} videos successfully:")
        for config in configs:
            print(f"- {config.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
