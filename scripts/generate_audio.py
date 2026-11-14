#!/usr/bin/env python3
"""Step 4 - make the audio with ElevenLabs, with exact word and syllable timings.

    python scripts/generate_audio.py <project-folder> --dry-run     show what it WOULD send and the size
    python scripts/generate_audio.py <project-folder>               generate (asks you to confirm first)
    python scripts/generate_audio.py <project-folder> --yes         generate without asking (only after the
                                                                    person has approved the cost!)
    options: --force (redo everything)   --only narration|words

What it makes, in <project>/build/:
  audio/p01.mp3 ...                 the text read aloud, one file per paragraph, with the time of every word
  audio/words/<word>.normal.mp3     each word at the SAME pace as the narration            ("Listen")
  audio/words/<word>.slow.mp3       each word slowly, with the exact start/end time of each syllable
                                    so the English syllable boxes light up in step with the voice ("Slow")
  manifest.json                     all the timings

Credits: ElevenLabs charges your own account. Every request is made with YOUR key, from your computer.
Set SYLLABEAT_MOCK=1 to run the whole thing with silent placeholder audio and no network (for testing).
Standard library only.
"""
import argparse
import base64
import hashlib
import io
import re
import sys
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

DEFAULTS = {
    "model": "eleven_multilingual_v2",
    "pace": 0.9,                 # speed of the narration AND of the normal word clip (ElevenLabs allows 0.7 - 1.2)
    "slow_speed": 0.7,           # speed used when generating the slow clip (0.7 is ElevenLabs' minimum)
    "slow_playback_rate": 0.85,  # the page plays the slow clip at this rate, making it slower still
    "voice_settings": {"stability": 0.55, "similarity_boost": 0.8, "style": 0.1},
}
VOICE_ID_RE = re.compile(r"^[A-Za-z0-9]{10,40}$")


# --------------------------------------------------------------------------- TTS (real or mock)
def mock_tts(text, speed):
    """Silent placeholder audio with believable timings, so everything can be tested offline."""
    per = 0.075 / speed
    n = len(text)
    total = n * per + 0.3
    rate = 8000
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(total * rate))
    starts = [0.1 + i * per for i in range(n)]
    ends = [0.1 + (i + 1) * per for i in range(n)]
    return buf.getvalue(), {"characters": list(text), "character_start_times_seconds": starts,
                            "character_end_times_seconds": ends}, ".wav"


def real_tts(text, voice_id, model, settings, speed):
    body = {"text": text, "model_id": model, "voice_settings": dict(settings, speed=speed)}
    data = common.api("POST", "/v1/text-to-speech/%s/with-timestamps?output_format=mp3_44100_128" % voice_id, body)
    if "audio_base64" not in data or not data.get("alignment"):
        raise common.SyllaBeatError("ElevenLabs did not return timing data for this request. "
                                    "Check that the model you chose supports timestamps.")
    return base64.b64decode(data["audio_base64"]), data["alignment"], ".mp3"


def tts(text, cfg, speed):
    if common.mock_mode():
        return mock_tts(text, speed)
    audio, alignment, ext = real_tts(text, cfg["voice_id"], cfg["model"], cfg["voice_settings"], speed)
    time.sleep(0.25)  # be gentle with the API
    return audio, alignment, ext


# --------------------------------------------------------------------------- timing maths
def _idx(i, text_len, align_len):
    """Map a character position of our text onto the alignment arrays (they normally have equal length)."""
    if align_len == text_len:
        return i
    return max(0, min(align_len - 1, int(i * align_len / max(1, text_len))))


def token_timings(paragraph, alignment):
    starts = alignment["character_start_times_seconds"]
    ends = alignment["character_end_times_seconds"]
    n, m = len(paragraph), len(starts)
    out = []
    for s, e, _tok in common.tokens_of(paragraph):
        a, b = _idx(s, n, m), _idx(e - 1, n, m)
        out.append([round(float(starts[a]), 3), round(float(max(ends[b], starts[a])), 3)])
    return out


def syllable_timings(key, syl_parts, alignment, text):
    """Start/end seconds of each syllable, taken from the real audio's letter timings.
    The windows are contiguous (each syllable lasts until the next begins), so something is always lit."""
    starts = alignment["character_start_times_seconds"]
    ends = alignment["character_end_times_seconds"]
    n, m = len(text), len(starts)
    bounds, pos = [], 0
    for part in syl_parts:
        bounds.append(pos)
        pos += len(part)
    bounds.append(pos)  # == len(key)
    wins = []
    for i in range(len(syl_parts)):
        s = float(starts[_idx(bounds[i], n, m)])
        e = float(starts[_idx(bounds[i + 1], n, m)]) if i + 1 < len(syl_parts) else float(ends[_idx(bounds[-1] - 1, n, m)])
        wins.append([s, e])
    # make strictly ordered and contiguous
    for i in range(1, len(wins)):
        wins[i][0] = max(wins[i][0], wins[i - 1][0])
        wins[i - 1][1] = wins[i][0]
    wins[-1][1] = max(wins[-1][1], wins[-1][0] + 0.05)
    return [[round(a, 3), round(b, 3)] for a, b in wins]


def alignment_end(alignment):
    return round(float(max(alignment["character_end_times_seconds"])), 3)


# --------------------------------------------------------------------------- main
def load_config(p):
    cfg = common.load_json(p["config"])
    out = dict(DEFAULTS)
    out.update({k: v for k, v in cfg.items() if v is not None})
    out["voice_settings"] = dict(DEFAULTS["voice_settings"], **(cfg.get("voice_settings") or {}))
    if common.mock_mode():
        out.setdefault("voice_id", "MOCK")
        out["voice_id"] = out.get("voice_id") or "MOCK"
    else:
        vid = str(out.get("voice_id") or "")
        if not VOICE_ID_RE.match(vid):
            raise common.SyllaBeatError(
                "config.json needs a valid \"voice_id\". Run  python scripts/list_voices.py  and ask the person which voice to use.")
    if not (0.7 <= float(out["pace"]) <= 1.2):
        raise common.SyllaBeatError("\"pace\" must be between 0.7 and 1.2 (ElevenLabs' limits).")
    return out


def signature(cfg):
    keep = {k: cfg[k] for k in ("voice_id", "model", "pace", "slow_speed", "voice_settings")}
    return hashlib.sha256(repr(sorted(keep.items())).encode()).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser(description="Generate narration and word audio with exact timings.")
    ap.add_argument("project")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation (only after the person approved the cost)")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", choices=["narration", "words"])
    args, extra = ap.parse_known_args()
    try:
        common.reject_key_arguments()
        if extra:
            raise common.SyllaBeatError("Unknown option(s): " + " ".join(extra))
        p = common.project(args.project)
        text = common.read_text(p)
        cfg = load_config(p)
        words = common.load_json(p["words"]).get("words", {})
        paras = common.paragraphs_of(text)
        keys = common.unique_words(text)
        missing = [k for k in keys if k not in words or not words[k].get("syl")]
        if missing:
            raise common.SyllaBeatError("These words have no syllables yet: %s\nRun check_words.py and complete words.json first."
                                        % ", ".join(missing[:10]))

        build = p["build"]
        manifest = common.load_json(build / "manifest.json", default={})
        sig = signature(cfg)
        if manifest and manifest.get("signature") not in (None, sig) and not args.force:
            raise common.SyllaBeatError("The voice or pace changed since the audio was last made. "
                                        "Run again with --force to regenerate everything with the new settings.")
        manifest.setdefault("paragraphs", [None] * len(paras))
        if len(manifest["paragraphs"]) != len(paras):
            manifest["paragraphs"] = [None] * len(paras)
        manifest.setdefault("words", {})
        manifest.update({"signature": sig, "pace": cfg["pace"], "slow_playback_rate": cfg["slow_playback_rate"]})

        todo_para = [i for i in range(len(paras)) if args.force or not manifest["paragraphs"][i]]
        todo_words = [k for k in keys if args.force or k not in manifest["words"]]
        if args.only == "narration":
            todo_words = []
        if args.only == "words":
            todo_para = []
        chars = sum(len(paras[i]) for i in todo_para) + sum((len(k) + 1) * 2 for k in todo_words)

        print("Project      : %s" % p["dir"])
        print("Mode         : %s" % ("MOCK (silent placeholder audio, no network)" if common.mock_mode() else "REAL ElevenLabs"))
        print("Paragraphs   : %d to make (of %d)" % (len(todo_para), len(paras)))
        print("Words        : %d to make (of %d) - a normal and a slow clip each" % (len(todo_words), len(keys)))
        print("Characters   : about %d will be sent to ElevenLabs" % chars)
        print("               (your plan decides how many credits that costs; a longer text costs more)")
        if args.dry_run or chars == 0:
            print("Nothing sent." if args.dry_run else "Everything is already generated.")
            return
        if not common.mock_mode():
            common.require_api_key()
            if not args.yes:
                if not sys.stdin.isatty():
                    raise common.SyllaBeatError("Not an interactive terminal: ask the person to approve the cost, "
                                                "then re-run with --yes.")
                if input("Send this to ElevenLabs using YOUR account? [y/N] ").strip().lower() != "y":
                    print("Cancelled - nothing was sent.")
                    return

        audio_dir = build / "audio"
        (audio_dir / "words").mkdir(parents=True, exist_ok=True)
        report = []

        for i in todo_para:
            audio, al, ext = tts(paras[i], cfg, cfg["pace"])
            name = "p%02d%s" % (i + 1, ext)
            (audio_dir / name).write_bytes(audio)
            manifest["paragraphs"][i] = {"file": "audio/" + name, "tokens": token_timings(paras[i], al),
                                         "end": alignment_end(al)}
            print("  narration %d/%d done" % (i + 1, len(paras)))

        for n, k in enumerate(todo_words, 1):
            parts = words[k]["syl"].split("-")
            lower = [x.lower() for x in parts]
            speak = k + "."  # the full stop gives the voice a clean, finished intonation
            a1, al1, ext = tts(speak, cfg, cfg["pace"])
            (audio_dir / "words" / (k + ".normal" + ext)).write_bytes(a1)
            a2, al2, ext2 = tts(speak, cfg, cfg["slow_speed"])
            (audio_dir / "words" / (k + ".slow" + ext2)).write_bytes(a2)
            syl = syllable_timings(k, lower, al2, speak)
            manifest["words"][k] = {
                "normal": {"file": "audio/words/%s.normal%s" % (k, ext)},
                "slow": {"file": "audio/words/%s.slow%s" % (k, ext2), "syllables": syl},
            }
            short = [i for i, (s, e) in enumerate(syl) if (e - s) < 0.04]
            if short:
                report.append("%s: syllable(s) %s last under 40 ms - listen to this word's Slow clip" % (k, [x + 1 for x in short]))
            if n % 10 == 0 or n == len(todo_words):
                print("  words %d/%d done" % (n, len(todo_words)))
            common.save_json(build / "manifest.json", manifest)  # save as we go: safe to stop and resume

        common.save_json(build / "manifest.json", manifest)
        (build / "timing_report.txt").write_text("\n".join(report) + ("\n" if report else "All syllable timings look plausible.\n"),
                                                 encoding="utf-8")
        print("\nDone. Timing check: %s" % ("%d word(s) need a listen - see build/timing_report.txt" % len(report) if report else "all plausible."))
        print("Next: python scripts/build_site.py %s" % args.project)
    except common.SyllaBeatError as e:
        common.fail(e)


if __name__ == "__main__":
    main()
