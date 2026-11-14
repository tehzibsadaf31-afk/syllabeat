#!/usr/bin/env python3
"""Step 2 - list every word of the text so the word cards can be filled in.

    python scripts/make_words_skeleton.py <project-folder>

Reads <project>/text.txt and writes <project>/words.json with one empty entry per distinct word.
Entries that already exist are kept, so it is safe to run again after editing the text.

The AI agent (or you) then fills in each entry - see docs/WORDS_JSON.md:
    "syl"      syllables, stressed one in CAPITALS, letters must spell the word:  "EV-ery", "a-LONG"
    "bn"       Bangla spelling of the sound, same number of pieces as "syl":     "এভ-রি", "আ-লং"
    "meaning"  Bangla meaning
    "emoji"    a picture for the word (or "image": a file in <project>/images/)

Standard library only.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402


def main():
    try:
        common.reject_key_arguments()
        if len(sys.argv) != 2:
            print(__doc__)
            sys.exit(2)
        p = common.project(sys.argv[1])
        text = common.read_text(p)
        keys = common.unique_words(text)
        existing = common.load_json(p["words"], default={"words": {}}).get("words", {})
    except common.SyllaBeatError as e:
        common.fail(e)

    odd = sorted({tok for para in common.paragraphs_of(text) for _, _, tok in common.tokens_of(para)
                  if any(not (c.isalpha() or c in ".,;:!?\"'“”‘’()-—") for c in tok)})
    words = {}
    for k in keys:
        words[k] = existing.get(k) or {"syl": "", "bn": "", "meaning": "", "emoji": ""}
    removed = [k for k in existing if k not in words]
    common.save_json(p["words"], {"words": words})

    filled = sum(1 for w in words.values() if w.get("syl") and w.get("bn") and w.get("meaning"))
    print("Wrote %s" % p["words"])
    print("  %d distinct words, %d already filled in, %d still empty." % (len(words), filled, len(words) - filled))
    if removed:
        print("  Note: %d entries are no longer in the text (kept out of the new file): %s" % (len(removed), ", ".join(removed)))
    if odd:
        print("  Heads-up: these tokens contain digits or unusual symbols and may not get a card: " + ", ".join(odd[:10]))
    print("Next: fill in the empty entries, then run  python scripts/check_words.py %s" % sys.argv[1])


if __name__ == "__main__":
    main()
