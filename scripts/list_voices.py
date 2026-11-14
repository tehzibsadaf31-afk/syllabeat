#!/usr/bin/env python3
"""Step 1 - choose the voice. Lists the voices in YOUR ElevenLabs account, or checks one voice ID.

    python scripts/list_voices.py                 list every voice in your account
    python scripts/list_voices.py --search calm   only voices whose name/labels contain "calm"
    python scripts/list_voices.py --check <ID>    confirm that a voice ID exists in your account

Library voices: first add the voice to your account on the ElevenLabs website
(Voices -> Voice Library -> "Add to my voices"). Then it shows up here.
Cloned voices: create the clone on the ElevenLabs website, ONLY from a voice you own or have
written permission to clone, then use its ID.

Needs your own API key (see SECURITY.md). Set SYLLABEAT_MOCK=1 to try it without a key.
Standard library only.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

MOCK_VOICES = [
    {"voice_id": "MOCK_VOICE_ID_1", "name": "Mock Voice (British, calm)", "category": "premade",
     "labels": {"accent": "british", "gender": "female", "descriptive": "calm"}},
    {"voice_id": "MOCK_VOICE_ID_2", "name": "Mock Voice (friendly teacher)", "category": "premade",
     "labels": {"accent": "american", "gender": "male", "descriptive": "friendly"}},
]


def fetch_voices():
    if common.mock_mode():
        return MOCK_VOICES
    data = common.api("GET", "/v1/voices")
    return data.get("voices", [])


def describe(v):
    labels = v.get("labels") or {}
    bits = [str(labels[k]) for k in ("accent", "gender", "age", "descriptive", "use_case") if labels.get(k)]
    return ", ".join(bits)


def main():
    ap = argparse.ArgumentParser(description="List or check ElevenLabs voices in your own account.")
    ap.add_argument("--search", help="only show voices containing this text")
    ap.add_argument("--check", metavar="VOICE_ID", help="check that this voice ID exists in your account")
    ap.add_argument("--json", action="store_true", help="print JSON instead of a table")
    args, extra = ap.parse_known_args()
    try:
        common.reject_key_arguments()
        if extra:
            raise common.SyllaBeatError("Unknown option(s): " + " ".join(extra))
        voices = fetch_voices()
    except common.SyllaBeatError as e:
        common.fail(e)

    if args.check:
        match = [v for v in voices if v.get("voice_id") == args.check]
        if match:
            print("OK - voice found: %s (%s)" % (match[0].get("name"), match[0].get("category")))
            return
        common.fail("That voice ID is not in your account. If it is a library voice, add it to "
                    "'My Voices' on the ElevenLabs website first.")

    if args.search:
        s = args.search.lower()
        voices = [v for v in voices if s in (v.get("name", "") + " " + describe(v)).lower()]
    if args.json:
        print(json.dumps([{"voice_id": v["voice_id"], "name": v.get("name"), "category": v.get("category"),
                           "about": describe(v)} for v in voices], ensure_ascii=False, indent=2))
        return
    if not voices:
        print("No voices found.")
        return
    print("%-34s %-24s %-13s %s" % ("NAME", "VOICE ID", "TYPE", "ABOUT"))
    for v in voices:
        print("%-34s %-24s %-13s %s" % ((v.get("name") or "")[:33], v.get("voice_id"), v.get("category") or "", describe(v)))
    print("\n%d voice(s). Tell the agent which ID to use (voice IDs are not secret, your API key is)." % len(voices))


if __name__ == "__main__":
    main()
