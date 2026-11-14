# Instructions for AI agents

This repository is the **SyllaBeat** skill. To help a person with it:

1. Read `SKILL.md` and follow its steps in order.
2. Obey the **hard rules** (also in `SECURITY.md`):
   - **Never ask for, print, store or send the person's ElevenLabs API key.** Ask them to put it in a `.env` file or an
     environment variable themselves.
   - The key may only ever go to `https://api.elevenlabs.io`.
   - **Ask before spending credits**: run `generate_audio.py --dry-run`, show the cost, wait for a clear yes.
   - Clone a voice only with the voice owner's consent.
   - Never publish `.env` or the `projects/` folder.
3. Everyone uses their **own** ElevenLabs account. Nothing here includes a shared key, voice or credit.
4. Be honest: AI-written syllables, Bangla spellings and meanings need a Bangla reader's review; say so.
5. Test offline any time with `SYLLABEAT_MOCK=1` (no key, no network), and run `python -m unittest discover -s tests -v`.
