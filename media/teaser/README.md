# Teaser (30 s, 16:9)

Built from the running app (`api/server.py` on localhost:8430) with local tools only: macOS `say` for the voice-over,
Playwright (headless Chromium) for the screen scenes, ffmpeg for the edit. Outputs go to `dist/teaser/` (not in git).

```bash
python3 media/teaser/voice.py            # voice-over clips (Daniel, en_GB; --voice Moira / Samantha / a Premium voice)
python3 media/teaser/record.py           # four screen scenes, 1920x1080
python3 media/teaser/cards.py            # title and end cards, figures read from /api/quality
python3 media/teaser/build.py            # dist/teaser/travaux_teaser_16x9.mp4, travaux_teaser.srt, poster.png
python3 media/teaser/subtitle.py         # the same with the captions burned in: travaux_teaser_16x9_subtitled.mp4
```

Scenes: title (3.6 s), search "change his religion" in speeches (9.8 s), the record with the UN scan of the page (3.2 s),
UDHR article 18 from first draft to adopted text (5.4 s), its amendments and votes (3.9 s), end card "Working edition —
coming soon" (4.1 s). The header label is set to "Working edition" by serving another `config.js` to the recording
browser; the app is not changed. A new voice changes only the audio: re-run `voice.py` and `build.py` (each line must
stay shorter than its scene; `build.py` checks).

The captions are rendered in the app's typeface (Source Serif 4) as transparent PNGs and overlaid, because this ffmpeg has
no libass (no `subtitles` filter).
