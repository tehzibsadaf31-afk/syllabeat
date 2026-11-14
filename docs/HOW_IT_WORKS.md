# How SyllaBeat works

```
text.txt + config.json ──► make_words_skeleton ──► words.json (filled in)
                                                        │
                                       check_words ◄────┘   (free: catches mistakes first)
                                                        │
                                        generate_audio ─┴─► build/audio/*.mp3  +  build/manifest.json
                                                        │
                                            build_site ─┴─► site/  (plain HTML + JS + audio)
```

## The narration
Each paragraph is sent to ElevenLabs' `text-to-speech/{voice_id}/with-timestamps` endpoint. The answer contains the audio and
the start and end time of **every character**. We turn that into one `[start, end]` per whitespace-separated word. In the page,
a timer reads the audio's own `currentTime` about 30 times a second and compares it with those times to highlight the word - so the
highlight cannot drift, even if the student pauses. (A timer is used instead of `requestAnimationFrame` because browsers pause
animation frames in background tabs.)

## The word clips
For each distinct word we ask for two clips from the same voice:

| Clip | Speed sent to ElevenLabs | Played at | Purpose |
|---|---|---|---|
| **normal** (Listen) | `pace` (same as the narration) | 1.0 | the word at the pace of the story |
| **slow** | 0.7 (ElevenLabs' minimum) | `slow_playback_rate` (0.85) | slower still; carries the syllable timings |

## Exact syllable lighting
The slow clip is requested with timestamps too. We know when each **letter** of the word was spoken. The syllables in
`words.json` spell the word (`a-LONG` = `a` + `long`), so syllable *i* starts when its first letter starts and lasts until the next
syllable's first letter starts (the last one until the end). These windows are stored in **media time**; the page reads
`audio.currentTime` about 30 times a second and lights the block whose window contains it. Because it follows the audio's own clock,
slowing the playback (0.85) changes nothing about correctness.

`generate_audio.py` also flags any syllable shorter than 40 ms in `build/timing_report.txt`; a person should listen to those words.

## The page
`templates/reader/` is a small static page. `build_site.py` copies it, adds `data/syllabeat-data.js` (text, cards, timings -
**never** the API key or the voice ID) and the audio. It then runs `check_secrets.py` on the result and deletes the site if anything
key-like is found. The page needs no server (open `index.html`) and no internet except for the optional Google Fonts.

## Offline testing
`SYLLABEAT_MOCK=1` replaces ElevenLabs with silent placeholder audio and believable timings, so the whole pipeline and the test suite
run with no key and no network.
