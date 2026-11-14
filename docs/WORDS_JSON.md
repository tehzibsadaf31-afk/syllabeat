# `words.json` - the word cards

One file per project (`projects/<name>/words.json`). `make_words_skeleton.py` creates it with empty entries.

```json
{
  "words": {
    "along": { "syl": "a-LONG", "bn": "আ-লং", "meaning": "বরাবর; ধরে", "emoji": "↔️" },
    "road":  { "syl": "road",   "bn": "রোড",   "meaning": "রাস্তা",     "emoji": "🛣️" }
  }
}
```

The **key** is the word in lowercase letters only: `"Morning,"` and `"morning"` both use `morning`.
(Apostrophes and hyphens are dropped: `don't` -> `dont`.)

## Fields (all required)
| Field | Rule | Example |
|---|---|---|
| `syl` | Syllables joined with `-`. The **stressed syllable is in CAPITALS**. The pieces, joined, **must spell the word** (case ignored). One-syllable words: no hyphen, no capitals. Multi-syllable words: **exactly one** capitalised piece. | `EV-ery`, `a-LONG`, `com-MU-ni-ty`, `road` |
| `bn` | **Bangla spelling of the sound** (transliteration, British English), joined with `-`, with **exactly as many pieces as `syl`**. | `এভ-রি`, `আ-লং` |
| `meaning` | A short, simple **Bangla meaning**. | `প্রতিটি; প্রত্যেক` |
| `emoji` | A clear picture. Every word gets one. | `🌧️` |
| `image` | *(optional, replaces the emoji)* a file name inside `projects/<name>/images/`. | `rain.png` |

### Why must the letters spell the word?
The Slow button lights up the English syllable that is being spoken. ElevenLabs tells us when each **letter** of the
word was spoken; the page groups those letters into your syllables. So `EV-ry` (which skips an `e`) cannot be mapped -
write `EV-ery`.

### Good practice
- Split the real spelling the way a dictionary hyphenates it (`NO-ticed`, `PUD-dles`, `ob-ser-VA-tions`).
- Pictures: concrete nouns -> the object; verbs -> the action; adjectives -> something that shows it (🥾 muddy);
  tiny grammar words -> a meaning hint (☝️ a, ➕ and, 👉 the, 🤝 with, 🎯 to, 🤏 some).
- Keep meanings short and in everyday Bangla. Have a Bangla reader review every card.

## What the build turns it into
`build_site.py` converts each entry into the page's data: syllable list (lower-case), stress index, Bangla pieces, meaning,
picture, the Listen clip and the Slow clip with a **start/end time for every syllable**.

## Checking
`python scripts/check_words.py projects/<name>` reports every problem word by word. Use `--allow-missing-pictures` only if
you really want cards without pictures.
