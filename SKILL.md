---
name: syllabeat
description: Turn any English text into a child-friendly read-aloud web page. The text is read aloud with ElevenLabs while each word highlights; tapping any word opens a card with its syllables (stressed one in orange), Bangla sound-spelling per syllable, Bangla meaning, a picture, a Listen button (same pace as the narration) and a Slow button where the English syllable boxes light up exactly in step with the voice. Use when a teacher, parent or tutor wants an interactive pronunciation reader for children who speak Bangla. Needs the PERSON'S OWN ElevenLabs API key and Python 3.9+.
---

# SyllaBeat - agent instructions

You are helping a person turn a text into an interactive reader. Follow the steps in order.
This file is written for **any** AI agent; it assumes only that you can read files, write files and run Python.

## HARD RULES (read first, they override everything else)
1. **Never ask the person to paste their ElevenLabs API key into the chat.** Tell them to put it in a file named `.env`
   (copy `.env.example`) or set the `ELEVENLABS_API_KEY` environment variable *themselves*, then carry on.
2. **Never print, echo, summarise, store, log or transmit the key.** Never put it in code, URLs, commands, messages,
   commits or issues. The scripts refuse `--api-key`-style options on purpose; do not work around that.
3. **The key goes only to `https://api.elevenlabs.io`** - the scripts enforce this. Never send it anywhere else.
4. **Ask before spending credits.** Always run `generate_audio.py --dry-run`, show the person the number of
   characters, get a clear "yes", and only then run the real generation (with `--yes`).
5. **Voice cloning needs consent.** Use a cloned voice only if it is the person's own voice or its owner has given
   clear permission.
6. **Never publish** `.env`, the `projects/` folder, or anything the person is not entitled to publish. Only the finished
   `site/` folder is meant to be published, and `build_site.py` already scans it for secrets.
7. **Nothing in this repository belongs to the author.** There is no shared key, voice, account or credit. Each person
   uses their own ElevenLabs account and pays their own plan.
See `SECURITY.md` for the reasoning and what to do if a key leaks.

## What you will build
A static web page (a folder of HTML, CSS, JS and audio - no server needed) where:
- the text is read aloud, one paragraph after another, the current word highlighted (timings from ElevenLabs);
- **every word** is tappable and opens a card showing:
  - the word with a **picture** (emoji by default, or an image file),
  - the **syllables in English** as colourful blocks, the **stressed syllable in orange**,
  - the **Bangla sound-spelling split into the same syllables**, under each block (static; stressed piece in the stress colour),
  - the **Bangla meaning**,
  - **Listen** - the word at the same pace as the narration,
  - **Slow** - the word slowly; the **English syllable blocks light up one by one exactly while that part is spoken**
    (timings come from ElevenLabs' per-letter timestamps for that very audio file, and the page reads the audio's own clock).

## What the person needs (check before starting)
- Python 3.9+ (`python --version`). The scripts use only the standard library; nothing to install.
- Their **own** ElevenLabs account and API key, on a plan that allows their intended use.
- Optionally: a place to host the finished page, and a teacher who reads Bangla to review the word cards.

## Workflow

### Step 0 - get ready
Work from the SyllaBeat folder. Create a project folder: `projects/<short-name>/` (it is git-ignored).
Ask the person for the **text** to read aloud (English). Save it as `projects/<name>/text.txt`.
Blank lines separate paragraphs.

### Step 1 - ask which voice they want  *(do this before generating anything)*
Ask: *"Which voice should read it? You can give me a voice ID from your ElevenLabs account, a voice you have cloned, or I can list the voices in your account for you to choose."*
- To list: `python scripts/list_voices.py` (optionally `--search calm`). If it says the key is missing, explain rule 1.
- To verify a given ID: `python scripts/list_voices.py --check <VOICE_ID>`.
- If it answers **401 ... missing the permission voices_read**, the person's key is *restricted* (good for security). Do not ask for a
  different key: either they add `voices_read` to it on the ElevenLabs website, or they simply give you the voice ID and you skip
  listing (a wrong ID will show up as an error at generation time).
- Library voices must first be added to "My Voices" on the ElevenLabs website. Clones are created on the website, with consent (rule 5).
- Voice IDs are not secret. Write the chosen one into `projects/<name>/config.json`:
```json
{ "title": "My story", "subtitle": "optional", "voice_id": "THE_ID", "pace": 0.9 }
```
`pace` (0.7-1.2) is the speed of the narration **and** of the Listen button, so they always match. Default 0.9.

### Step 2 - list the words
`python scripts/make_words_skeleton.py projects/<name>` creates `words.json` with one empty entry per distinct word.

### Step 3 - fill in every word card  *(this is your main creative job)*
For **every** word fill all four fields (full rules and examples in `docs/WORDS_JSON.md`):
- `syl` - syllables separated by `-`, **stressed one in CAPITALS**, and the letters **must spell the word**:
  `"EV-ery"`, `"a-LONG"`, `"com-MU-ni-ty"`. One-syllable words have no hyphen and no capitals: `"road"`.
  (The checker rejects `EV-ry` for "every" because the pieces must be real letters of the word - this is what lets the
  Slow clip light up exactly the right letters.)
- `bn` - the **Bangla spelling of how it sounds** (British English), split into **the same number of pieces** as `syl`:
  `"এভ-রি"`, `"আ-লং"`. This is transliteration, not translation.
- `meaning` - a short, simple **Bangla meaning** a child understands.
- `emoji` - a clear picture for the word. **Every word gets one.** Concrete words: the thing (🌧️ rain). Actions: the action (🚶 walked).
  Small grammar words: a meaning hint (☝️ a, ➕ and, 👉 the, 🤝 with, 🎯 to). Optionally use `"image": "file.png"` (a file in
  `projects/<name>/images/`) when the person supplies pictures. You cannot make real illustrations unless you have an image tool - do not pretend to.

### Step 4 - check before spending anything
`python scripts/check_words.py projects/<name>` - repeat until it says "Word list is ready".
Tell the person honestly that you wrote the syllables, Bangla pieces and meanings, so **someone who reads Bangla should review them**
(open `words.json`; it is plain text). Fix what they correct.

### Step 5 - generate the audio (costs the person's credits)
1. `python scripts/generate_audio.py projects/<name> --dry-run` -> show the character count; explain it uses *their* credits.
2. After a clear "yes": `python scripts/generate_audio.py projects/<name> --yes`.
   It is safe to stop and resume; finished files are kept. Use `--force` only if the voice or pace changed.
3. Read `projects/<name>/build/timing_report.txt`. Words it lists have a suspiciously short syllable - ask the person to listen to
   that word's **Slow** button in the finished page, and regenerate it if it sounds off (delete its two files in `build/audio/words/`
   and its entry in `build/manifest.json`, then run step 5 again).

### Step 6 - build and preview
`python scripts/build_site.py projects/<name>` -> `projects/<name>/site/`
`python scripts/serve.py projects/<name>/site` -> open http://localhost:8080/ (or just open `index.html`).
Quality check with the person: tap several words; press **Slow** and watch the English blocks light up with the voice;
press **Listen**; play the whole text. Report problems honestly rather than claiming success.

### Step 7 - publishing (optional, only if the person asks)
Publish **only** the contents of `projects/<name>/site/` (for example with GitHub Pages: make a public repository containing
those files, then Settings -> Pages -> Deploy from a branch -> main / root). Run `python scripts/check_secrets.py projects/<name>/site`
first. Remind them that audio made with ElevenLabs is subject to ElevenLabs' terms and their plan.

## Honest limits (tell the person)
- Syllables, Bangla sound-spelling and meanings written by an AI can contain mistakes - a Bangla reader must review them.
- Bangla letters can only approximate English sounds; the audio is the real guide.
- Syllable lighting uses ElevenLabs' letter timings for each clip; it is checked for plausibility but a person should still listen to a sample.
- Words with digits or symbols inside (for example `3D`) do not get cards. Hyphenated words are treated as one word with the hyphen removed.

## Files you may need
`docs/WORDS_JSON.md` (card format) - `docs/HOW_IT_WORKS.md` (how the timing works) - `SECURITY.md` (rules and leak response) -
`examples/little-kite/` (a complete small project to copy) - `tests/` (`python -m unittest discover -s tests -v`).
Set `SYLLABEAT_MOCK=1` to run every script offline with silent placeholder audio (useful for trying it out or testing; no key needed).
