# Security and responsibility

SyllaBeat is built so that **nobody has to trust anybody else with a key.**
Everyone who uses it brings their **own** ElevenLabs account and API key. The repository contains
no keys, no voice IDs, no credits and no personal data.

## What you need of your own
| You need | Why |
|---|---|
| Your own **ElevenLabs account** and **API key** | The audio is made on *your* account and uses *your* credits. |
| A plan that allows how you will use the audio | Check ElevenLabs' terms - free plans usually restrict public or commercial use and may require credit. |
| **Python 3.9 or newer** | Runs the build scripts (standard library only, nothing to install). |
| *(optional)* a place to host the finished page | e.g. GitHub Pages. The page is just files. |
| *(optional)* an AI agent | An agent can follow `SKILL.md` for you, but you can also run every step yourself. |

## Use a restricted key (recommended)
On the ElevenLabs website you can create an API key that is allowed to do **only some things**. For SyllaBeat the minimum is
**Text to Speech**. If a leaked key can only make audio, the damage is far smaller than for a full-access key.
- Making audio needs the `text_to_speech` permission.
- *Listing* your voices (`list_voices.py`) additionally needs `voices_read`. If your key does not have it, the script says so; either add
  that permission to the key, or skip listing and give the agent your voice ID directly (voice IDs are not secret).

## How your API key is protected (built into the code)
1. **Read from your own machine only.** The key comes from the `ELEVENLABS_API_KEY` environment variable or a
   local `.env` file that you create. `.env` is in `.gitignore`.
2. **Never on the command line.** The scripts refuse `--api-key` and similar options, because command lines end up
   in shell history and process lists.
3. **Never printed or logged.** Every error message passes through a redactor that removes the key.
4. **Only ever sent to `https://api.elevenlabs.io`.** The code checks the host and refuses redirects, so a key can't be
   forwarded anywhere else.
5. **Never in the output.** `build_site.py` scans the finished site for anything that looks like a key (and for your
   real key value) and **deletes the site** if it finds one. It also never copies your voice ID into the site.
6. **You can scan anything yourself:** `python scripts/check_secrets.py <folder>`.
7. **Optional commit guard:** copy `scripts/hooks/pre-commit` to `.git/hooks/pre-commit` to block a commit that contains a key.

## Rules for AI agents running this skill
- **Never ask the person to paste their API key into the chat.** Tell them to create the `.env` file or set the
  environment variable themselves, then continue.
- **Never print, echo, store, summarise or transmit the key.** Do not put it in code, URLs, issue text, logs or commit messages.
- **Never send the key to any host except `api.elevenlabs.io`.**
- **Ask before spending credits.** Run `generate_audio.py --dry-run`, show the person the number of characters, get a clear
  "yes", and only then run it (with `--yes`).
- **Voice cloning needs consent.** Only use a cloned voice if it is the person's own voice or the voice owner has given
  clear permission. Never clone a real person's voice without it.
- **Do not publish** the `projects/` folder, any `.env`, or any audio the person is not entitled to publish.
- **Do not put the author's or anyone else's keys or voice IDs into example files.**

## If a key leaks
1. Open the ElevenLabs website -> your profile -> **API Keys**, **delete (revoke)** the leaked key and create a new one.
2. Remove the key from wherever it appeared. Deleting a file from a public GitHub repository does **not** remove it from its
   history, so assume the old key is public and make sure it is revoked.
3. Check your ElevenLabs usage page for unexpected activity.

## Reporting a problem
If you find a security problem in SyllaBeat, please open an issue **without** including any secret in it.
