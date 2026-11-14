# SyllaBeat 🥁

**Turn any English text into a colourful, child-friendly read-aloud page.**

The text is read aloud with an [ElevenLabs](https://elevenlabs.io) voice you choose, and each word lights up as it is spoken.
Children tap **any word** to open a card with:

- a **picture** for the word,
- the **syllables** in English, the stressed one in **orange**,
- the **Bangla sound-spelling**, split into the same syllables,
- the **Bangla meaning**,
- a **Listen** button (same pace as the narration) and a **Slow** button - when it plays, the English syllable blocks
  **light up one by one, exactly in step with the voice**.

The result is a plain folder of web files you can open on any computer or put on any website.

> SyllaBeat is a **skill**: instructions plus small scripts that an AI agent (or you) can follow.
> It works with any AI agent that can read files and run Python. It includes **no keys, voices or credits** of anyone.

## What you need - of your own
- an **ElevenLabs account and API key** (the audio is made on *your* account, with *your* credits) - see [SECURITY.md](SECURITY.md)
- **Python 3.9+** (nothing else to install)
- optionally: an AI agent to do the steps for you, and a Bangla reader to check the word cards

## Quick start (by hand)
```bash
# 1. put your own key in a file named .env  (copy .env.example)  - never share this file
# 2. see your voices and pick one
python scripts/list_voices.py

# 3. make a project from the example, or create your own folder with text.txt and config.json
cp -r examples/little-kite projects/my-story        # (Windows: copy the folder in Explorer)
#    edit projects/my-story/text.txt, config.json (add your voice_id)

python scripts/make_words_skeleton.py projects/my-story    # lists every word
#    fill in words.json (see docs/WORDS_JSON.md) - an AI agent can do this for you
python scripts/check_words.py projects/my-story            # checks the word cards
python scripts/generate_audio.py projects/my-story --dry-run   # shows the size, sends nothing
python scripts/generate_audio.py projects/my-story            # makes the audio (asks first)
python scripts/build_site.py projects/my-story                # builds projects/my-story/site
python scripts/serve.py projects/my-story/site                # preview at http://localhost:8080/
```
Try everything **without a key** first: set `SYLLABEAT_MOCK=1` (silent placeholder audio, no network).

## Use it with your AI agent
Give your agent this repository's link (or the downloaded folder) and say something like:

> *Read `README.md` and `SKILL.md` in this repository and follow them to build a SyllaBeat page for my text.
> I will put my own ElevenLabs key in a `.env` file myself - do not ask me to paste it here. Ask me which voice to use,
> and show me the cost before you generate any audio.*

## For AI agents
Read [`SKILL.md`](SKILL.md) and follow it. Obey the **hard rules** at its top and in [`AGENTS.md`](AGENTS.md) and [`SECURITY.md`](SECURITY.md):
never ask for, print or send the user's API key; ask before spending credits; clone voices only with consent.

## Folder map
| Path | What it is |
|---|---|
| `SKILL.md` | the step-by-step instructions for agents |
| `SECURITY.md` | how keys are protected, rules, what to do if one leaks |
| `scripts/` | `list_voices`, `make_words_skeleton`, `check_words`, `generate_audio`, `build_site`, `serve`, `check_secrets`, `export_clean_copy` |
| `templates/reader/` | the child-friendly page (HTML, CSS, JS) |
| `examples/little-kite/` | a small complete example project |
| `docs/` | word-card format and how the timing works |
| `tests/` | `python -m unittest discover -s tests -v` (runs offline) |

## Honest limits
Syllables, Bangla sound-spelling and meanings written by an AI can have mistakes - **have a Bangla reader review them**.
Bangla letters only approximate English sounds. Check ElevenLabs' terms for your plan before publishing the audio.

## License
MIT - see [LICENSE](LICENSE). The license covers the code and templates, not ElevenLabs audio or your own texts and pictures.
