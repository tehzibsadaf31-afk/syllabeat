#!/usr/bin/env python3
"""Step 3 - check the word list BEFORE spending any ElevenLabs credits.

    python scripts/check_words.py <project-folder> [--allow-missing-pictures]

For every word in the text it checks that:
  * it has an entry with syllables ("syl"), Bangla sound pieces ("bn") and a Bangla meaning;
  * the letters of the syllables spell the word, e.g. "EV-ery" -> every   (needed so the slow
    clip can light up exactly the right letters);
  * a multi-syllable word has exactly ONE stressed (CAPITAL) syllable;
  * the Bangla pieces match the English syllables one for one;
  * the word has a picture (emoji or image file).

Exit code 0 = ready to generate audio. Standard library only.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

BENGALI = re.compile(r"[ঀ-৿]")


def check_entry(key, w, project_dir, need_picture):
    errs, warns = [], []
    syl = (w.get("syl") or "").strip()
    bn = (w.get("bn") or "").strip()
    meaning = (w.get("meaning") or "").strip()
    if not syl:
        errs.append("no 'syl' (syllables)")
    else:
        parts = syl.split("-")
        if any(not p for p in parts):
            errs.append("'syl' has an empty piece: %r" % syl)
        elif "".join(parts).lower() != key:
            errs.append("syllables %r spell %r, not %r - split the real spelling, e.g. EV-ery for 'every'"
                        % (syl, "".join(parts).lower(), key))
        stressed = [p for p in parts if re.search(r"[A-Z]", p)]
        if len(parts) > 1 and len(stressed) != 1:
            errs.append("'syl' needs exactly one stressed (CAPITAL) syllable, found %d: %r" % (len(stressed), syl))
        if bn:
            bparts = bn.split("-")
            if len(bparts) != len(parts):
                errs.append("Bangla pieces (%d) do not match English syllables (%d): %r vs %r"
                            % (len(bparts), len(parts), bn, syl))
            elif any(not b for b in bparts):
                errs.append("'bn' has an empty piece: %r" % bn)
    if not bn:
        errs.append("no 'bn' (Bangla sound pieces)")
    elif not BENGALI.search(bn):
        errs.append("'bn' should be written in Bangla letters: %r" % bn)
    if not meaning:
        errs.append("no 'meaning'")
    elif not BENGALI.search(meaning):
        warns.append("'meaning' has no Bangla letters: %r" % meaning)
    pic = (w.get("emoji") or "").strip()
    img = (w.get("image") or "").strip()
    if img and not (Path(project_dir) / "images" / img).exists():
        errs.append("image file not found: images/%s" % img)
    if need_picture and not pic and not img:
        errs.append("no picture - add an 'emoji' (or an 'image' file)")
    return errs, warns


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    allow_missing = "--allow-missing-pictures" in sys.argv
    try:
        common.reject_key_arguments()
        if len(args) != 1:
            print(__doc__)
            sys.exit(2)
        p = common.project(args[0])
        text = common.read_text(p)
        words = common.load_json(p["words"]).get("words", {})
    except common.SyllaBeatError as e:
        common.fail(e)

    keys = common.unique_words(text)
    total_err = total_warn = 0
    for k in keys:
        if k not in words:
            print("  %-14s MISSING - not in words.json (run make_words_skeleton.py)" % k)
            total_err += 1
            continue
        errs, warns = check_entry(k, words[k], p["dir"], not allow_missing)
        for e in errs:
            print("  %-14s ERROR   %s" % (k, e))
        for w in warns:
            print("  %-14s warning %s" % (k, w))
        total_err += len(errs)
        total_warn += len(warns)
    extra = [k for k in words if k not in keys]
    if extra:
        print("  note: %d entries are not used by the text: %s" % (len(extra), ", ".join(extra[:8])))
    print("\n%d words checked: %d error(s), %d warning(s)." % (len(keys), total_err, total_warn))
    if total_err:
        print("Fix the errors above, then run this check again.")
        sys.exit(1)
    print("Word list is ready. A teacher who reads Bangla should still review the meanings and sound pieces.")


if __name__ == "__main__":
    main()
