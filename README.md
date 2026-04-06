# shortQuran MVP

This starter project generates vertical Quran short videos from:

- one ayah config, or a batch of many ayah configs
- one audio source per render
- one verse text per render
- an optional translation
- an optional background image or background video
- an optional Arabic font file
- optional URLs for auto-downloading audio, background, and font assets

The render pipeline uses Python only for orchestration and delegates the actual montage work to `ffmpeg`.

## What it creates

- `1080x1920` vertical short format
- centered Arabic verse text
- optional translation block
- top meta card with surah name, verse reference, and reciter
- bottom brand label
- light fade in and fade out on both text and audio

## Requirements

Install these first:

- Python 3.10+
- FFmpeg with both `ffmpeg` and `ffprobe` available in your `PATH`

## Project structure

Create these folders before your first render:

```text
inputs/
outputs/
```

Then place your source files inside `inputs/`.

## Config

Edit [`example_config.json`](C:/Users/mouad/Desktop/shortQuran/example_config.json) with your own files and verse content.
If you want many outputs in one run, use [`example_batch_config.json`](C:/Users/mouad/Desktop/shortQuran/example_batch_config.json).

Important fields:

- `audio_path` or `audio_url`: recitation file source
- `surah_number` + `ayah_number`: optional verse selectors for smart audio URL generation
- `reciter_key`: built-in verse reciter key such as `alafasy` or `abdulbaset_mujawwad`
- `recitation_relative_path`: manual override for Quran Foundation verse-audio folder paths such as `Alafasy/mp3`
- `background_path` or `background_url`: optional image or video source
- `font_file` or `font_url`: optional `.ttf` or `.otf` font source for better Arabic rendering
- `cache_dir`: where downloaded files are stored locally
- `output_path`: final generated `.mp4`
- `verse_text`: Arabic ayah text
- `translation`: optional translation text

If `background_path` is omitted, the script generates a clean dark animated background automatically.
If a local file is missing and a matching URL is provided, the script downloads it once and reuses the cached copy on future renders.
If `audio_path` and `audio_url` are empty, the script can generate the audio URL automatically from `surah_number`, `ayah_number`, and either `reciter_key` or `recitation_relative_path`.

## Batch mode

You can also render many videos from one config file by adding a top-level `jobs` array.
Each job can override any field, including:

- `surah_number`
- `ayah_number`
- `reciter_key`
- `surah_name`
- `verse_text`
- `translation`
- `output_path`
- `background_path`
- `background_url`
- `font_file`
- `font_url`

Shared defaults can stay at the top level, then each job only changes what it needs.

```json
{
  "background_path": "",
  "font_file": "",
  "brand_text": "shortQuran",
  "fps": 30,
  "jobs": [
    {
      "surah_number": 67,
      "ayah_number": 1,
      "reciter_key": "alafasy",
      "output_path": "outputs/067-001-alafasy.mp4",
      "surah_name": "Surah Al-Mulk",
      "verse_text": "PUT_ARABIC_TEXT_HERE"
    },
    {
      "surah_number": 36,
      "ayah_number": 1,
      "reciter_key": "abdulbaset_mujawwad",
      "output_path": "outputs/036-001-abdulbaset.mp4",
      "surah_name": "Surah Ya-Sin",
      "verse_text": "PUT_ARABIC_TEXT_HERE"
    }
  ]
}
```

Run batch mode exactly the same way:

```powershell
py .\main.py --config .\example_batch_config.json
```

## Auto-fetch example

You can keep local paths, URLs, or mix both:

```json
{
  "audio_url": "https://example.com/recitations/067001.mp3",
  "background_url": "https://example.com/backgrounds/desert.mp4",
  "font_url": "https://example.com/fonts/Amiri-Regular.ttf",
  "output_path": "outputs/surah-al-mulk-1.mp4",
  "surah_name": "Surah Al-Mulk",
  "verse_reference": "67:1",
  "verse_text": "تَبَارَكَ الَّذِي بِيَدِهِ الْمُلْكُ وَهُوَ عَلَىٰ كُلِّ شَيْءٍ قَدِيرٌ"
}
```

## Smart audio example

This example auto-builds the verse audio URL:

```json
{
  "surah_number": 67,
  "ayah_number": 1,
  "reciter_key": "alafasy",
  "background_path": "inputs/background.mp4",
  "font_file": "inputs/Amiri-Regular.ttf",
  "output_path": "outputs/surah-al-mulk-1.mp4",
  "surah_name": "Surah Al-Mulk",
  "verse_text": "تَبَارَكَ الَّذِي بِيَدِهِ الْمُلْكُ وَهُوَ عَلَىٰ كُلِّ شَيْءٍ قَدِيرٌ"
}
```

Built-in `reciter_key` values in this MVP:

- `alafasy`
- `abdulbaset_mujawwad`

If you want another reciter, use `recitation_relative_path` directly instead of `reciter_key`.

## Run

On Windows:

```powershell
py .\main.py --config .\example_config.json
```

Or:

```powershell
python .\main.py --config .\example_config.json
```

For fully automatic mode with anti-repeat rotation:

```powershell
python .\main.py --auto --count 2 --target-seconds 60
```

Automatic mode now keeps a history file at `.cache/auto_history.json` and tries to avoid repeating:

- the same `surah + ayah range + reciter` combination
- the same recent background image/video
- the same recent style preset
- the same recent title template
- the exact same target duration on every clip

The auto presets rotate between multiple cinematic layouts, so the channel does not keep producing one identical visual template every time.

## YouTube upload

You can now upload directly to YouTube after each successful render.

First, create a Google Cloud OAuth desktop app for the YouTube Data API and place the client secrets JSON here:

```text
.secrets/youtube-client-secret.json
```

Then run the one-time OAuth flow locally to save a refresh token:

```powershell
python .\main.py --youtube-auth-only --youtube-client-secrets-file .\.secrets\youtube-client-secret.json --youtube-token-file .\.secrets\youtube-token.json
```

That creates:

```text
.secrets/youtube-token.json
```

After that, uploads can run unattended as long as the token file is available:

```powershell
python .\main.py --auto --count 1 --target-seconds 60 --youtube-upload --youtube-client-secrets-file .\.secrets\youtube-client-secret.json --youtube-token-file .\.secrets\youtube-token.json --youtube-privacy-status private
```

Optional flags:

- `--youtube-schedule-at 2026-04-10T18:00:00+01:00`
- `--youtube-tags "quran,shorts,islam"`
- `--youtube-category-id 27`
- `--youtube-made-for-kids`

When `--youtube-schedule-at` is used, the script automatically forces the upload to `private`, because YouTube scheduling relies on `status.publishAt` for private videos.

## Run while your PC is off

The repo now includes a scheduled GitHub Actions workflow:

```text
.github/workflows/auto-youtube-shorts.yml
```

It runs twice a day in UTC and does this:

- installs FFmpeg and the YouTube client libraries
- generates one automatic short
- uploads it to YouTube as `private`
- commits `.cache/auto_history.json` back to the repo so anti-repeat history survives future runs

To enable it on GitHub, add these repository secrets:

- `YOUTUBE_CLIENT_SECRET_JSON`
- `YOUTUBE_TOKEN_JSON`

The easiest setup is:

1. Run `--youtube-auth-only` on your own PC once.
2. Copy the contents of `.secrets/youtube-client-secret.json` into `YOUTUBE_CLIENT_SECRET_JSON`.
3. Copy the contents of `.secrets/youtube-token.json` into `YOUTUBE_TOKEN_JSON`.
4. Push the repo to GitHub and enable Actions.

The included workflow uploads `private` by default, which is the safest starting point for a new channel automation setup.

## Notes

- For the best Arabic output, use a font file such as Amiri, Noto Naskh Arabic, or another Quran-friendly font.
- If your background is a video, the script loops it automatically until the audio ends.
- If your background is a still image, the script keeps it fixed for now. Motion effects can be added next.

## Good next upgrades

- exact word-by-word subtitle timings
- intro and outro templates
- logo overlay
- background blur layers and animated zoom
- automatic export presets for TikTok, Reels, and Shorts
