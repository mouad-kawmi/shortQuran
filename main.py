from __future__ import annotations

import argparse
import html
import hashlib
import http.server
import json
import mimetypes
import os
import random
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, unquote, urlparse
from urllib.request import Request, urlopen

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
DEFAULT_FPS = 30
DEFAULT_TARGET_DURATION = 60.0
AUTO_MIN_DURATION = 48.0
AUTO_DURATION_OVERSHOOT_TOLERANCE = 8.0
QURAN_API_BASE_URL = "https://api.quran.com/api/v4"
PUBLIC_TRANSLATION_API_BASE_URL = "https://api.alquran.cloud/v1"
DEFAULT_TRANSLATION_ID = 131
DEFAULT_PUBLIC_TRANSLATION_EDITION = "en.sahih"
DEFAULT_AUTO_COUNT = 1
DEFAULT_AUTO_STYLE_PRESET = "cinematic"
DEFAULT_AUTO_CHAPTER_MIN = 67
LOCAL_BACKGROUND_LIBRARY_DIRNAME = "backgroundPhoto"
AUTO_HISTORY_FILE = ".cache/auto_history.json"
AUTO_STYLE_PRESETS = (
    "cinematic",
    "cinematic_compact",
    "cinematic_spacious",
)
AUTO_TITLE_TEMPLATES = {
    "reference": "{chapter_name} | {verse_reference}",
    "reciter": "{chapter_name} Recitation | {reciter_name}",
    "focus": "Quran Short | {chapter_name}",
    "ayah": "{chapter_name} | Ayat {verse_range_label}",
}
AUTO_MIN_TARGET_SECONDS = 46.0
AUTO_MAX_TARGET_SECONDS = 64.0
AUTO_RECENT_CHAPTER_WINDOW = 6
AUTO_RECENT_RECITER_WINDOW = 3
AUTO_RECENT_BACKGROUND_WINDOW = 6
AUTO_RECENT_STYLE_WINDOW = 2
AUTO_RECENT_TITLE_WINDOW = 3

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
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
VERSES_AUDIO_BASE_URL = "https://verses.quran.foundation/"
DEFAULT_ARABIC_FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/amiri/Amiri-Regular.ttf"
DEFAULT_BACKGROUND_URL = "https://upload.wikimedia.org/wikipedia/commons/6/65/Scenic_landscape.jpg"
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
DEFAULT_YOUTUBE_PRIVACY_STATUS = "private"
DEFAULT_YOUTUBE_CATEGORY_ID = "27"
DEFAULT_YOUTUBE_DEFAULT_LANGUAGE = "en"
DEFAULT_YOUTUBE_CLIENT_SECRETS_FILE = ".secrets/youtube-client-secret.json"
DEFAULT_YOUTUBE_TOKEN_FILE = ".secrets/youtube-token.json"
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
    recitation_id: int
    reciter_name: str


BUILTIN_VERSE_RECITATIONS = {
    "alafasy": VerseRecitationSource(
        relative_path="Alafasy/mp3",
        reciter_name="Mishari Rashid al-`Afasy",
    ),
    "mishary": VerseRecitationSource(
        relative_path="Alafasy/mp3",
        reciter_name="Mishari Rashid al-`Afasy",
    ),
    "mishari": VerseRecitationSource(
        relative_path="Alafasy/mp3",
        reciter_name="Mishari Rashid al-`Afasy",
    ),
    "afasy": VerseRecitationSource(
        relative_path="Alafasy/mp3",
        reciter_name="Mishari Rashid al-`Afasy",
    ),
    "abdulbaset_mujawwad": VerseRecitationSource(
        relative_path="AbdulBaset/Mujawwad/mp3",
        reciter_name="Abdul Basit Abdus Samad",
    ),
    "abdul_basit_mujawwad": VerseRecitationSource(
        relative_path="AbdulBaset/Mujawwad/mp3",
        reciter_name="Abdul Basit Abdus Samad",
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
    brand_text: str = "shortQuran"
    title_text: str | None = None
    fps: int = DEFAULT_FPS
    word_segments: list[WordSegment] | None = None
    timed_segments: list[TimedSegment] | None = None
    show_meta: bool = True
    show_brand: bool = True
    style_preset: str = "classic"
    auto_history_entry: dict[str, object] | None = None

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
            font_url_value = DEFAULT_ARABIC_FONT_URL

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
        font_file = resolve_asset_path(
            config_dir=config_dir,
            cache_dir=cache_dir,
            local_value=payload.get("font_file"),
            url_value=font_url_value,
            asset_name="font",
            required=False,
        )

        fps = int(payload.get("fps", DEFAULT_FPS))
        if fps <= 0:
            raise ValueError("fps must be greater than zero")

        verse_text = require_non_empty_text(payload["verse_text"], "verse_text")
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
            brand_text=str(payload.get("brand_text", "shortQuran")).strip() or "shortQuran",
            title_text=str(payload["title_text"]).strip() if payload.get("title_text") else None,
            fps=fps,
            word_segments=word_segments,
            show_meta=show_meta,
            show_brand=show_brand,
            style_preset=style_preset,
        )


@dataclass(frozen=True)
class YouTubeUploadOptions:
    client_secrets_file: Path
    token_file: Path
    privacy_status: str = DEFAULT_YOUTUBE_PRIVACY_STATUS
    schedule_at: datetime | None = None
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
class TikTokUploadOptions:
    client_config_file: Path
    token_file: Path
    privacy_level: str = DEFAULT_TIKTOK_PRIVACY_LEVEL
    disable_comment: bool = False
    disable_duet: bool = False
    disable_stitch: bool = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a Quran short video from audio, text, and optional background media.")
    parser.add_argument("--config", help="Path to a JSON config file.")
    parser.add_argument("--auto", action="store_true", help="Generate a fully automatic Quran short without a config file.")
    parser.add_argument("--count", type=int, default=DEFAULT_AUTO_COUNT, help="How many automatic videos to generate.")
    parser.add_argument(
        "--target-seconds",
        type=float,
        default=DEFAULT_TARGET_DURATION,
        help="Target duration for automatic videos.",
    )
    parser.add_argument("--youtube-upload", action="store_true", help="Upload rendered videos to YouTube after each successful render.")
    parser.add_argument("--youtube-auth-only", action="store_true", help="Run the one-time YouTube OAuth flow, save the token file, and exit.")
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
    parser.add_argument("--tiktok-upload", action="store_true", help="Upload rendered videos to TikTok after each successful render.")
    parser.add_argument("--tiktok-auth-only", action="store_true", help="Run the one-time TikTok OAuth flow, save the token file, and exit.")
    parser.add_argument(
        "--tiktok-client-config-file",
        help="Path to the TikTok client config JSON file. Defaults to .secrets/tiktok-client-config.json or TIKTOK_CLIENT_CONFIG_FILE.",
    )
    parser.add_argument(
        "--tiktok-token-file",
        help="Path to the stored TikTok OAuth token JSON file. Defaults to .secrets/tiktok-token.json or TIKTOK_TOKEN_FILE.",
    )
    parser.add_argument(
        "--tiktok-privacy-level",
        choices=TIKTOK_PRIVACY_LEVEL_CHOICES,
        default=DEFAULT_TIKTOK_PRIVACY_LEVEL,
        help="TikTok privacy level for direct posts. Unaudited TikTok apps can only post to private accounts.",
    )
    parser.add_argument("--tiktok-disable-comment", action="store_true", help="Disable comments on TikTok uploads.")
    parser.add_argument("--tiktok-disable-duet", action="store_true", help="Disable duets on TikTok uploads.")
    parser.add_argument("--tiktok-disable-stitch", action="store_true", help="Disable stitch on TikTok uploads.")
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


def build_auto_combo_key(chapter_number: int, verse_start: int, verse_end: int, reciter_name: str) -> str:
    safe_reciter = sanitize_filename_part(reciter_name)
    return f"{chapter_number}:{verse_start}-{verse_end}:{safe_reciter}"


def choose_auto_target_seconds(target_seconds: float, history_entries: list[dict[str, object]]) -> float:
    minimum = max(AUTO_MIN_TARGET_SECONDS, target_seconds - 12.0)
    maximum = min(AUTO_MAX_TARGET_SECONDS, target_seconds + 4.0)
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
    recent_styles = get_recent_history_values(
        history_entries,
        "style_preset",
        limit=AUTO_RECENT_STYLE_WINDOW,
    )
    available_styles = [preset for preset in AUTO_STYLE_PRESETS if preset not in recent_styles]
    return random.choice(available_styles or list(AUTO_STYLE_PRESETS))


def build_auto_title(
    *,
    chapter_name: str,
    verse_reference: str,
    verse_start: int,
    verse_end: int,
    reciter_name: str,
    history_entries: list[dict[str, object]],
) -> tuple[str, str]:
    recent_templates = get_recent_history_values(
        history_entries,
        "title_template_key",
        limit=AUTO_RECENT_TITLE_WINDOW,
    )
    available_templates = [
        template_key
        for template_key in AUTO_TITLE_TEMPLATES
        if template_key not in recent_templates
    ]
    template_key = random.choice(available_templates or list(AUTO_TITLE_TEMPLATES))
    verse_range_label = str(verse_start) if verse_start == verse_end else f"{verse_start}-{verse_end}"
    title_text = AUTO_TITLE_TEMPLATES[template_key].format(
        chapter_name=chapter_name,
        verse_reference=verse_reference,
        verse_start=verse_start,
        verse_end=verse_end,
        verse_range_label=verse_range_label,
        reciter_name=reciter_name,
    )
    return template_key, title_text


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
    privacy_status = args.youtube_privacy_status
    if schedule_at is not None:
        privacy_status = "private"

    return YouTubeUploadOptions(
        client_secrets_file=resolve_runtime_path(base_dir, client_secrets_raw),
        token_file=resolve_runtime_path(base_dir, token_file_raw),
        privacy_status=privacy_status,
        schedule_at=schedule_at,
        category_id=require_non_empty_text(args.youtube_category_id, "youtube-category-id"),
        tags=parse_csv_text_list(args.youtube_tags),
        default_language=require_non_empty_text(args.youtube_default_language, "youtube-default-language"),
        made_for_kids=bool(args.youtube_made_for_kids),
    )


def build_tiktok_upload_options(args: argparse.Namespace, base_dir: Path) -> TikTokUploadOptions:
    client_config_raw = (
        normalize_optional_text(args.tiktok_client_config_file)
        or normalize_optional_text(os.getenv("TIKTOK_CLIENT_CONFIG_FILE"))
        or DEFAULT_TIKTOK_CLIENT_CONFIG_FILE
    )
    token_file_raw = (
        normalize_optional_text(args.tiktok_token_file)
        or normalize_optional_text(os.getenv("TIKTOK_TOKEN_FILE"))
        or DEFAULT_TIKTOK_TOKEN_FILE
    )

    return TikTokUploadOptions(
        client_config_file=resolve_runtime_path(base_dir, client_config_raw),
        token_file=resolve_runtime_path(base_dir, token_file_raw),
        privacy_level=require_non_empty_text(args.tiktok_privacy_level, "tiktok-privacy-level"),
        disable_comment=bool(args.tiktok_disable_comment),
        disable_duet=bool(args.tiktok_disable_duet),
        disable_stitch=bool(args.tiktok_disable_stitch),
    )


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


def build_tiktok_caption(config: RenderConfig) -> str:
    lines = [build_youtube_title(config).replace(" #Shorts", "")]
    if config.reciter_name:
        lines.append(f"Reciter: {config.reciter_name}")
    hashtags = " ".join(build_youtube_hashtags(config))
    if hashtags:
        lines.extend(["", hashtags])
    return "\n".join(lines)[:2200].strip()


def upload_video_file_to_tiktok(upload_url: str, video_path: Path) -> None:
    video_size = video_path.stat().st_size
    if video_size <= 0:
        raise RuntimeError("TikTok upload failed: video file is empty.")
    if video_size > TIKTOK_SIMPLE_UPLOAD_MAX_BYTES:
        raise RuntimeError(
            "TikTok upload failed: generated video is larger than the current direct-upload limit "
            "supported by this script (64 MB)."
        )

    content_type = mimetypes.guess_type(str(video_path))[0] or "video/mp4"
    if content_type not in {"video/mp4", "video/quicktime", "video/webm"}:
        content_type = "video/mp4"

    request = Request(
        upload_url,
        data=video_path.read_bytes(),
        headers={
            "Content-Type": content_type,
            "Content-Length": str(video_size),
            "Content-Range": f"bytes 0-{video_size - 1}/{video_size}",
        },
        method="PUT",
    )
    try:
        with urlopen(request, timeout=300):
            return
    except (OSError, URLError) as error:
        raise RuntimeError(f"TikTok video transfer failed: {error}") from error


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


def upload_video_to_tiktok(
    *,
    video_path: Path,
    config: RenderConfig,
    options: TikTokUploadOptions,
    interactive_auth: bool,
) -> dict[str, str]:
    token_payload = get_tiktok_credentials(options, interactive=interactive_auth)
    access_token = require_non_empty_text(token_payload.get("access_token", ""), "tiktok access_token")
    creator_info = query_tiktok_creator_info(access_token)
    privacy_level = resolve_tiktok_privacy_level(options.privacy_level, creator_info)
    disable_comment = options.disable_comment or bool(creator_info.get("comment_disabled"))
    disable_duet = options.disable_duet or bool(creator_info.get("duet_disabled"))
    disable_stitch = options.disable_stitch or bool(creator_info.get("stitch_disabled"))

    init_payload = post_json(
        TIKTOK_DIRECT_POST_INIT_URL,
        {
            "post_info": {
                "title": build_tiktok_caption(config),
                "privacy_level": privacy_level,
                "disable_comment": disable_comment,
                "disable_duet": disable_duet,
                "disable_stitch": disable_stitch,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_path.stat().st_size,
                "chunk_size": video_path.stat().st_size,
                "total_chunk_count": 1,
            },
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )
    init_data = require_tiktok_api_success(init_payload, "direct post init")
    publish_id = require_non_empty_text(init_data.get("publish_id", ""), "tiktok publish_id")
    upload_url = require_non_empty_text(init_data.get("upload_url", ""), "tiktok upload_url")
    upload_video_file_to_tiktok(upload_url, video_path)

    status_payload = poll_tiktok_publish_status(access_token, publish_id)
    status_value = normalize_optional_text(status_payload.get("status")) or "PROCESSING"
    public_post_ids = status_payload.get("publicaly_available_post_id")
    post_id = ""
    if isinstance(public_post_ids, list) and public_post_ids:
        post_id = str(public_post_ids[0]).strip()
    creator_username = normalize_optional_text(creator_info.get("creator_username")) or ""
    watch_url = ""
    if creator_username and post_id:
        watch_url = f"https://www.tiktok.com/@{creator_username}/video/{post_id}"

    return {
        "publish_id": publish_id,
        "status": status_value,
        "privacy_level": privacy_level,
        "post_id": post_id,
        "watch_url": watch_url,
    }


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

    preferred_title = f"{surah_label} | {verse_label}" if verse_label else surah_label
    preferred_title = append_distinct_segment(preferred_title, reciter_label, max_length=92)

    if hook_title:
        hook_title = append_distinct_segment(hook_title, verse_label, max_length=92)
        hook_title = append_distinct_segment(hook_title, reciter_label, max_length=92)
        base_title = hook_title
    else:
        base_title = preferred_title

    shorts_suffix = " #Shorts"
    if "#shorts" not in base_title.lower() and len(base_title) + len(shorts_suffix) <= 100:
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
        "#Shorts",
        "#Quran",
        "#Islam",
        "#QuranShorts",
        "#QuranRecitation",
        "#القرآن",
        "#القرآن_الكريم",
        "#راحه_نفسيه",
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
    lines.extend(["", "Listen, reflect, and share khayr.", "", hashtags_line])
    return "\n".join(lines).strip()


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
    return {
        "video_id": video_id,
        "watch_url": f"https://www.youtube.com/watch?v={video_id}",
        "privacy_status": status["privacyStatus"],
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
    if font_file:
        return font_file

    if sys.platform.startswith("win"):
        for candidate in WINDOWS_ARABIC_FONT_FALLBACKS:
            if candidate.exists():
                return candidate

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


def build_verse_audio_url(relative_path: str, surah_number: int, ayah_number: int) -> str:
    cleaned_relative_path = relative_path.strip().strip("/")
    if not cleaned_relative_path:
        raise ValueError("'recitation_relative_path' cannot be empty")

    verse_code = f"{surah_number:03d}{ayah_number:03d}.mp3"
    return f"{VERSES_AUDIO_BASE_URL}{cleaned_relative_path}/{verse_code}"


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
    asset_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    existing_matches = sorted(cache_dir.glob(f"{asset_name}-*-{asset_hash}.*"))
    if existing_matches:
        return existing_matches[0]

    parsed_url = urlparse(url)
    source_name = Path(unquote(parsed_url.path)).stem or asset_name
    safe_name = sanitize_filename_part(source_name)

    request = Request(url, headers={"User-Agent": "shortQuran/1.0"})
    cache_dir.mkdir(parents=True, exist_ok=True)

    try:
        print(f"Downloading {asset_name} from {url}")
        with urlopen(request, timeout=60) as response:
            content_type = response.headers.get_content_type()
            extension = get_extension_from_url(url) or get_extension_from_content_type(content_type, asset_name)
            target_path = cache_dir / f"{asset_name}-{safe_name}-{asset_hash}{extension}"
            temp_path = target_path.with_suffix(f"{target_path.suffix}.part")

            with temp_path.open("wb") as temp_file:
                shutil.copyfileobj(response, temp_file)

            temp_path.replace(target_path)
            return target_path
    except (OSError, URLError) as error:
        raise RuntimeError(f"Failed to download {asset_name} from {url}: {error}") from error


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
    return " ".join(cleaned.split())


def normalize_audio_download_url(url: str) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"{VERSES_AUDIO_BASE_URL}{url.lstrip('/')}"


def get_verse_number_from_key(verse_key: str) -> int:
    _, _, verse_number = verse_key.partition(":")
    return int(verse_number)


def fetch_auto_chapters() -> list[dict[str, object]]:
    payload = fetch_quran_api_json("/chapters")
    chapters = payload.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        raise RuntimeError("Quran API did not return any chapters.")
    return chapters


def fetch_auto_reciters() -> list[AutoReciter]:
    payload = fetch_quran_api_json("/resources/recitations")
    raw_recitations = payload.get("recitations")
    if not isinstance(raw_recitations, list) or not raw_recitations:
        raise RuntimeError("Quran API did not return any recitations.")

    reciters: list[AutoReciter] = []
    for item in raw_recitations:
        if not isinstance(item, dict):
            continue
        identifier = item.get("id")
        reciter_name = normalize_optional_text(item.get("reciter_name") or item.get("name"))
        if identifier is None or reciter_name is None:
            continue
        reciters.append(AutoReciter(recitation_id=int(identifier), reciter_name=reciter_name))

    if not reciters:
        raise RuntimeError("No usable reciters were returned by Quran API.")
    return reciters


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

    minimum_duration = min(AUTO_MIN_DURATION, max(12.0, target_seconds * 0.75))
    estimated_verses_needed = max(6, int(target_seconds // 5) + 2)
    max_start = max(1, verses_count - estimated_verses_needed + 1)
    start_ayah = random.randint(1, max_start)
    current_ayah = start_ayah
    selected_verses: list[AutoVerse] = []
    total_duration = 0.0
    verses_cache: dict[int, list[dict[str, object]]] = {}
    audio_cache: dict[int, dict[str, str]] = {}

    while current_ayah <= verses_count:
        page = ((current_ayah - 1) // 50) + 1
        if page not in verses_cache:
            verses_cache[page] = fetch_chapter_verses_page(chapter_number, page=page, translation_id=translation_id)
            audio_cache[page] = fetch_chapter_audio_page(chapter_number, page=page, recitation_id=reciter.recitation_id)

        verse_key = f"{chapter_number}:{current_ayah}"
        verse_payload = next((item for item in verses_cache[page] if item.get("verse_key") == verse_key), None)
        if verse_payload is None:
            raise RuntimeError(f"Could not find verse data for {verse_key}.")

        audio_url = audio_cache[page].get(verse_key)
        if not audio_url:
            raise RuntimeError(f"Could not find audio URL for {verse_key} with reciter {reciter.reciter_name}.")

        arabic = require_non_empty_text(verse_payload.get("text_uthmani", ""), f"text_uthmani for {verse_key}")
        word_count = len(arabic.split())
        if word_count > 16:
            if selected_verses and total_duration >= minimum_duration:
                break
            raise RuntimeError(f"Verse {verse_key} is too long for cinematic automatic mode.")

        translation = extract_translation_text(verse_payload) or translation_map.get(verse_key, "")
        audio_path = download_asset(audio_url, cache_dir / "audio", "audio")
        duration = probe_duration(audio_path, ffprobe_command)

        if selected_verses and total_duration >= minimum_duration and (total_duration + duration) > (target_seconds + AUTO_DURATION_OVERSHOOT_TOLERANCE):
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

        if total_duration >= target_seconds:
            break

    if not selected_verses:
        raise RuntimeError("Automatic verse selection returned no verses.")

    if len(selected_verses) > 1:
        trimmed_duration = total_duration - selected_verses[-1].duration
        if (
            trimmed_duration >= minimum_duration
            and abs(trimmed_duration - target_seconds) < abs(total_duration - target_seconds)
        ):
            selected_verses.pop()

    final_duration = sum(verse.duration for verse in selected_verses)
    if final_duration < minimum_duration:
        raise RuntimeError("Selected verses are too short for the requested automatic render.")

    return selected_verses


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
    cache_dir = (base_dir / DEFAULT_CACHE_DIR).resolve()
    output_dir = (base_dir / "outputs").resolve()
    last_error: Exception | None = None

    for _ in range(20):
        recent_chapter_values = get_recent_history_values(
            history_entries,
            "chapter_number",
            limit=AUTO_RECENT_CHAPTER_WINDOW,
        )
        recent_chapter_ids = {int(value) for value in recent_chapter_values if value.isdigit()}
        available_chapters = [
            chapter
            for chapter in chapters
            if int(chapter.get("id") or 0) not in recent_chapter_ids
        ]
        chapter = random.choice(available_chapters or chapters)
        chapter_number = int(chapter.get("id") or 0)
        verses_count = int(chapter.get("verses_count") or 0)
        chapter_name = normalize_optional_text(chapter.get("name_simple")) or f"Surah {chapter_number}"
        if chapter_number <= 0 or verses_count <= 0:
            continue

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
        selected_target_seconds = choose_auto_target_seconds(target_seconds, history_entries)
        try:
            translation_map = fetch_public_translation_map(chapter_number)
            selected_verses = collect_auto_verses(
                chapter_number=chapter_number,
                verses_count=verses_count,
                reciter=reciter,
                translation_id=translation_id,
                translation_map=translation_map,
                target_seconds=selected_target_seconds,
                cache_dir=cache_dir,
                ffprobe_command=ffprobe_command,
            )
        except Exception as error:  # noqa: BLE001
            last_error = error
            continue

        verse_start = get_verse_number_from_key(selected_verses[0].verse_key)
        verse_end = get_verse_number_from_key(selected_verses[-1].verse_key)
        verse_reference = f"{chapter_number}:{verse_start}" if verse_start == verse_end else f"{chapter_number}:{verse_start}-{verse_end}"
        combo_key = build_auto_combo_key(chapter_number, verse_start, verse_end, reciter.reciter_name)
        known_combo_keys = {
            normalize_optional_text(entry.get("combo_key")) or ""
            for entry in history_entries
        }
        if combo_key in known_combo_keys:
            last_error = RuntimeError(f"Automatic mode selected a repeated combination: {combo_key}")
            continue

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

        recent_background_paths = set(
            get_recent_history_values(
                history_entries,
                "background_path",
                limit=AUTO_RECENT_BACKGROUND_WINDOW,
            )
        )
        background_path = choose_random_library_background(base_dir, excluded_paths=recent_background_paths)
        if background_path is not None:
            print(f"Using local background from {background_path}")
        else:
            background_path = download_asset(DEFAULT_BACKGROUND_URL, cache_dir / "background", "background")
        font_file = download_asset(DEFAULT_ARABIC_FONT_URL, cache_dir / "font", "font")
        style_preset = choose_auto_style_preset(history_entries)
        title_template_key, title_text = build_auto_title(
            chapter_name=chapter_name,
            verse_reference=verse_reference,
            verse_start=verse_start,
            verse_end=verse_end,
            reciter_name=reciter.reciter_name,
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
            "background_path": str(background_path.resolve()) if background_path is not None else "",
            "style_preset": style_preset,
            "title_template_key": title_template_key,
            "title_text": title_text,
            "target_seconds": selected_target_seconds,
            "planned_duration_seconds": round(cursor, 2),
            "output_path": str(output_path),
        }

        return RenderConfig(
            audio_path=audio_output,
            output_path=output_path,
            verse_text=" ".join(verse.arabic for verse in selected_verses),
            surah_name=chapter_name,
            verse_reference=verse_reference,
            translation=" ".join(filter(None, (verse.translation for verse in selected_verses))) or None,
            reciter_name=reciter.reciter_name,
            background_path=background_path,
            font_file=font_file,
            brand_text="shortQuran",
            title_text=title_text,
            fps=DEFAULT_FPS,
            timed_segments=timed_segments,
            show_meta=True,
            show_brand=False,
            style_preset=style_preset,
            auto_history_entry=history_entry,
        )

    if last_error is not None:
        raise RuntimeError(f"Automatic render generation failed: {last_error}") from last_error
    raise RuntimeError("Automatic render generation failed before any chapter could be selected.")


def build_auto_render_configs(base_dir: Path, *, count: int, target_seconds: float) -> list[RenderConfig]:
    if count <= 0:
        raise ValueError("'count' must be greater than zero.")
    if target_seconds <= 0:
        raise ValueError("'target-seconds' must be greater than zero.")

    ffmpeg_command = resolve_binary_command("ffmpeg")
    ffprobe_command = resolve_binary_command("ffprobe")
    chapters = [
        chapter
        for chapter in fetch_auto_chapters()
        if int(chapter.get("id") or 0) >= DEFAULT_AUTO_CHAPTER_MIN
    ]
    if not chapters:
        raise RuntimeError("No chapters are available for automatic cinematic mode.")
    reciters = fetch_auto_reciters()
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


def wrap_arabic_text(text: str, words_per_line: int) -> str:
    words = [word for word in text.split() if word.strip()]
    if not words:
        return ""

    lines = []
    for index in range(0, len(words), words_per_line):
        lines.append(" ".join(words[index : index + words_per_line]))
    return "\n".join(lines)


def choose_arabic_words_per_line(text: str, *, is_cinematic: bool) -> int:
    word_count = len([word for word in text.split() if word.strip()])
    if not is_cinematic:
        return 5
    if word_count <= 4:
        return 4
    if word_count <= 8:
        return 4
    return 3


def resolve_arabic_text_metrics(line_count: int, *, is_cinematic: bool) -> tuple[int, int]:
    if not is_cinematic:
        return 88, 24

    if line_count >= 5:
        return 74, 34
    if line_count == 4:
        return 80, 30
    if line_count == 3:
        return 86, 26
    return 92, 22


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
    if translation_line_count <= 0:
        return int(round(preferred_arabic_top)), int(round(preferred_translation_top))

    translation_block_height = (translation_line_count * (translation_font_size + translation_line_spacing)) - translation_line_spacing
    minimum_gap = 54 if is_cinematic else 34
    top_margin = 260 if is_cinematic else 170
    bottom_margin = 250 if is_cinematic else 160

    arabic_top = preferred_arabic_top
    translation_top = max(preferred_translation_top, arabic_top + arabic_block_height + minimum_gap)
    max_translation_top = VIDEO_HEIGHT - bottom_margin - translation_block_height

    if translation_top > max_translation_top:
        shift_up = translation_top - max_translation_top
        arabic_top = max(top_margin, arabic_top - shift_up)
        translation_top = max(preferred_translation_top, arabic_top + arabic_block_height + minimum_gap)
        translation_top = min(translation_top, max_translation_top)

    return int(round(arabic_top)), int(round(translation_top))


def write_text_asset(path: Path, content: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as text_file:
        text_file.write(content)


def escape_filter_path(path: Path) -> str:
    return path.as_posix().replace(":", r"\:").replace("'", r"\'")


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
    fade_in = min(0.6, max(0.2, duration * 0.12))
    fade_out = min(0.8, max(0.3, duration * 0.15))
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


def create_text_assets(config: RenderConfig, temp_dir: Path) -> dict[str, list[Path]]:
    is_cinematic = is_cinematic_style(config.style_preset)
    title_value = config.title_text or f"{config.surah_name} | {config.verse_reference}"
    meta_text = ""
    if config.show_meta:
        meta_value = title_value
        if config.reciter_name:
            if is_cinematic:
                meta_value = f"{title_value}\n{config.reciter_name}"
            else:
                meta_value = f"{title_value}\nReciter: {config.reciter_name}"
        meta_text = wrap_text(meta_value, width=30 if is_cinematic else 36)

    verse_text = wrap_arabic_text(
        config.verse_text,
        words_per_line=choose_arabic_words_per_line(config.verse_text, is_cinematic=is_cinematic),
    )
    translation_text = wrap_text(config.translation, width=30 if is_cinematic else 34) if config.translation else ""
    brand_text = wrap_text(config.brand_text, width=24 if is_cinematic else 32) if config.show_brand else ""

    assets = {
        "meta": build_line_files(temp_dir, "meta", meta_text),
        "verse": build_line_files(temp_dir, "verse", verse_text),
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
        arabic_text = wrap_arabic_text(
            segment.arabic,
            words_per_line=choose_arabic_words_per_line(segment.arabic, is_cinematic=is_cinematic),
        )
        translation_text = wrap_text(segment.translation, width=26 if is_cinematic else 28)
        segment_assets.append(
            SegmentTextAsset(
                arabic_lines=build_line_files(temp_dir, f"segment_arabic_{index}", arabic_text),
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
        arabic_text = wrap_arabic_text(
            segment.arabic,
            words_per_line=choose_arabic_words_per_line(segment.arabic, is_cinematic=is_cinematic),
        )
        translation_text = wrap_text(segment.translation, width=26 if is_cinematic else 28)
        timed_assets.append(
            TimedSegmentTextAsset(
                arabic_lines=build_line_files(temp_dir, f"timed_segment_arabic_{index}", arabic_text),
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
) -> str:
    is_cinematic = is_cinematic_style(config.style_preset)
    cinematic_variant = get_cinematic_variant(config.style_preset)
    cinematic_meta_top = 98 if cinematic_variant == "compact" else 138 if cinematic_variant == "spacious" else 120
    cinematic_meta_font_size = 28 if cinematic_variant == "compact" else 32 if cinematic_variant == "spacious" else 30
    cinematic_arabic_offset = 210 if cinematic_variant == "compact" else 145 if cinematic_variant == "spacious" else 180
    cinematic_translation_top = 1040 if cinematic_variant == "compact" else 1090 if cinematic_variant == "spacious" else 1020
    cinematic_image_blur = 7 if cinematic_variant == "compact" else 4 if cinematic_variant == "spacious" else 6
    cinematic_video_blur = 5 if cinematic_variant == "compact" else 3 if cinematic_variant == "spacious" else 4
    cinematic_overlay_alpha = "0.48" if cinematic_variant == "compact" else "0.34" if cinematic_variant == "spacious" else "0.42"
    cinematic_brightness = "-0.26" if cinematic_variant == "compact" else "-0.17" if cinematic_variant == "spacious" else "-0.22"
    cinematic_video_brightness = "-0.28" if cinematic_variant == "compact" else "-0.19" if cinematic_variant == "spacious" else "-0.24"

    if background_kind == "image":
        if is_cinematic:
            base_filter = (
                "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,format=yuv420p,"
                f"eq=saturation=0.88:brightness={cinematic_brightness},"
                f"gblur=sigma={cinematic_image_blur},"
                "vignette=PI/8,"
                f"drawbox=x=0:y=0:w=iw:h=ih:color=black@{cinematic_overlay_alpha}:t=fill"
                "[base]"
            )
        else:
            base_filter = (
                "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,format=yuv420p,"
                "eq=saturation=1.12:brightness=-0.05,"
                "drawbox=x=0:y=0:w=iw:h=ih:color=black@0.24:t=fill"
                "[base]"
            )
    elif background_kind == "video":
        if is_cinematic:
            base_filter = (
                "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,format=yuv420p,"
                f"eq=saturation=0.88:brightness={cinematic_video_brightness},"
                f"gblur=sigma={cinematic_video_blur},"
                "vignette=PI/8,"
                f"drawbox=x=0:y=0:w=iw:h=ih:color=black@{cinematic_overlay_alpha}:t=fill"
                "[base]"
            )
        else:
            base_filter = (
                "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,format=yuv420p,"
                "eq=saturation=1.10:brightness=-0.06,"
                "drawbox=x=0:y=0:w=iw:h=ih:color=black@0.28:t=fill"
                "[base]"
            )
    else:
        if is_cinematic:
            base_filter = (
                "[0:v]format=yuv420p,"
                "drawbox=x=0:y=0:w=iw:h=ih:color=0x120f1f@1:t=fill,"
                "drawbox=x=0:y=0:w=iw:h=ih:color=0x000000@0.28:t=fill,"
                "gblur=sigma=55,"
                "eq=saturation=0.82:brightness=-0.10,"
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

    alpha_expression = build_alpha_expression(duration)
    filters = [base_filter]

    meta_font_size = cinematic_meta_font_size if is_cinematic else 48
    meta_line_spacing = 8 if is_cinematic else 12
    filters.extend(
        build_text_block_filters(
            input_label="base",
            output_prefix="meta_layer",
            text_paths=text_assets["meta"],
            top_y=cinematic_meta_top if is_cinematic else 140,
            font_size=meta_font_size,
            font_color="0xf8fafccc" if is_cinematic else "0xffd166",
            box_color=None,
            alpha_expression=alpha_expression,
            font_file=None if is_cinematic else config.font_file,
            line_spacing=meta_line_spacing,
            box_border=0,
            border_width=1,
            border_color="0x00000066" if is_cinematic else "0x2a1a00dd",
            shadow_x=0,
            shadow_y=4 if is_cinematic else 6,
            shadow_color="0x000000aa",
        )
    )
    previous_label = get_last_layer_label("meta_layer", text_assets["meta"], "base")

    if timed_segment_assets:
        for index, segment_asset in enumerate(timed_segment_assets):
            segment_alpha = build_timed_alpha_expression(segment_asset.start_time, segment_asset.end_time)

            arabic_font_size, arabic_line_spacing = resolve_arabic_text_metrics(
                len(segment_asset.arabic_lines),
                is_cinematic=is_cinematic,
            )
            translation_font_size = 42 if is_cinematic else 44
            translation_line_spacing = 12 if is_cinematic else 12
            arabic_block_height = (len(segment_asset.arabic_lines) * (arabic_font_size + arabic_line_spacing)) - arabic_line_spacing
            preferred_arabic_top = ((VIDEO_HEIGHT - arabic_block_height) / 2) - (cinematic_arabic_offset if is_cinematic else 100)
            arabic_top, translation_top = resolve_text_stack_positions(
                arabic_block_height=arabic_block_height,
                translation_line_count=len(segment_asset.translation_lines),
                translation_font_size=translation_font_size,
                translation_line_spacing=translation_line_spacing,
                is_cinematic=is_cinematic,
                preferred_arabic_top=preferred_arabic_top,
                preferred_translation_top=cinematic_translation_top if is_cinematic else VIDEO_HEIGHT - 500,
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
                    border_width=2 if is_cinematic else 2,
                    border_color="0x000000cc" if is_cinematic else "0x0f172acc",
                    shadow_x=0,
                    shadow_y=16 if is_cinematic else 12,
                    shadow_color="0x000000ee",
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
                    font_file=None if is_cinematic else config.font_file,
                    line_spacing=translation_line_spacing,
                    box_border=0 if is_cinematic else 12,
                    border_width=0 if is_cinematic else 1,
                    border_color="0x00000000" if is_cinematic else "0x111827aa",
                    shadow_x=0,
                    shadow_y=8 if is_cinematic else 6,
                    shadow_color="0x000000cc",
                )
            )
            previous_label = get_last_layer_label(translation_prefix, segment_asset.translation_lines, previous_label)
    elif segment_assets:
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
            )
            translation_font_size = 42 if is_cinematic else 44
            translation_line_spacing = 12 if is_cinematic else 12
            arabic_block_height = (len(segment_asset.arabic_lines) * (arabic_font_size + arabic_line_spacing)) - arabic_line_spacing
            preferred_arabic_top = ((VIDEO_HEIGHT - arabic_block_height) / 2) - (cinematic_arabic_offset if is_cinematic else 100)
            arabic_top, translation_top = resolve_text_stack_positions(
                arabic_block_height=arabic_block_height,
                translation_line_count=len(segment_asset.translation_lines),
                translation_font_size=translation_font_size,
                translation_line_spacing=translation_line_spacing,
                is_cinematic=is_cinematic,
                preferred_arabic_top=preferred_arabic_top,
                preferred_translation_top=cinematic_translation_top if is_cinematic else VIDEO_HEIGHT - 500,
            )
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
                    border_width=2 if is_cinematic else 2,
                    border_color="0x000000cc" if is_cinematic else "0x0f172acc",
                    shadow_x=0,
                    shadow_y=16 if is_cinematic else 12,
                    shadow_color="0x000000ee" if is_cinematic else "0x000000dd",
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
                    font_file=None if is_cinematic else config.font_file,
                    line_spacing=translation_line_spacing,
                    box_border=0 if is_cinematic else 12,
                    border_width=0 if is_cinematic else 1,
                    border_color="0x00000000" if is_cinematic else "0x111827aa",
                    shadow_x=0,
                    shadow_y=8 if is_cinematic else 6,
                    shadow_color="0x000000cc" if is_cinematic else "0x000000aa",
                )
            )
            previous_label = get_last_layer_label(translation_prefix, segment_asset.translation_lines, previous_label)
    else:
        verse_font_size, verse_line_spacing = resolve_arabic_text_metrics(
            len(text_assets["verse"]),
            is_cinematic=is_cinematic,
        )
        translation_font_size = 42 if is_cinematic else 40
        translation_line_spacing = 12 if is_cinematic else 14
        verse_block_height = (len(text_assets["verse"]) * (verse_font_size + verse_line_spacing)) - verse_line_spacing
        preferred_verse_top = ((VIDEO_HEIGHT - verse_block_height) / 2) - (cinematic_arabic_offset if is_cinematic else 110)
        verse_top, translation_top = resolve_text_stack_positions(
            arabic_block_height=verse_block_height,
            translation_line_count=len(text_assets.get("translation", [])),
            translation_font_size=translation_font_size,
            translation_line_spacing=translation_line_spacing,
            is_cinematic=is_cinematic,
            preferred_arabic_top=preferred_verse_top,
            preferred_translation_top=cinematic_translation_top if is_cinematic else VIDEO_HEIGHT - 470,
        )
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
                border_width=2 if is_cinematic else 2,
                border_color="0x000000cc" if is_cinematic else "0x0f172acc",
                shadow_x=0,
                shadow_y=16 if is_cinematic else 10,
                shadow_color="0x000000ee" if is_cinematic else "0x000000dd",
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
                    box_color=None,
                    alpha_expression=alpha_expression,
                    font_file=None if is_cinematic else config.font_file,
                    line_spacing=translation_line_spacing,
                    box_border=0,
                    border_width=0 if is_cinematic else 1,
                    border_color="0x00000000" if is_cinematic else "0x111827cc",
                    shadow_x=0,
                    shadow_y=8 if is_cinematic else 6,
                    shadow_color="0x000000cc" if is_cinematic else "0x000000bb",
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
            font_file=config.font_file,
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

    filter_complex = build_filter_complex(config, duration, background_kind, text_assets, segment_assets, timed_segment_assets)

    audio_fade_start = max(0.0, duration - 0.8)
    audio_filter = f"afade=t=in:st=0:d=0.4,afade=t=out:st={audio_fade_start:.2f}:d=0.8"

    command.extend(
        [
            "-filter_complex",
            filter_complex,
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
        subprocess.run(command, check=True)


def main() -> int:
    args = parse_args()
    configs: list[RenderConfig] = []
    base_dir = Path.cwd()
    youtube_options = None
    tiktok_options = None
    try:
        if args.youtube_upload or args.youtube_auth_only:
            youtube_options = build_youtube_upload_options(args, base_dir)
        if args.tiktok_upload or args.tiktok_auth_only:
            tiktok_options = build_tiktok_upload_options(args, base_dir)

        if args.youtube_auth_only:
            if youtube_options is None:
                raise RuntimeError("YouTube upload options could not be built.")
            get_youtube_credentials(youtube_options, interactive=True)
            print(f"YouTube token saved to {youtube_options.token_file}")
            return 0
        if args.tiktok_auth_only:
            if tiktok_options is None:
                raise RuntimeError("TikTok upload options could not be built.")
            get_tiktok_credentials(tiktok_options, interactive=True)
            print(f"TikTok token saved to {tiktok_options.token_file}")
            return 0

        use_auto_mode = args.auto or not args.config
        if use_auto_mode:
            configs = build_auto_render_configs(
                base_dir,
                count=args.count,
                target_seconds=args.target_seconds,
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
                tiktok_upload_result = None
                if youtube_options is not None and args.youtube_upload:
                    print(f"Uploading to YouTube: {config.output_path.name}")
                    youtube_upload_result = upload_video_to_youtube(
                        video_path=config.output_path,
                        config=config,
                        options=youtube_options,
                        interactive_auth=False,
                    )
                    print(
                        "Uploaded to YouTube: "
                        f"{youtube_upload_result['watch_url']} "
                        f"({youtube_upload_result['privacy_status']})"
                    )
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
                        config.auto_history_entry["uploaded_at"] = datetime.now(timezone.utc).isoformat()
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
