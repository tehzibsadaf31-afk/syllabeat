"""Shared helpers for SyllaBeat: configuration, API-key handling and safe HTTP.

Standard library only - nothing to install.

SECURITY RULES BUILT INTO THIS FILE
  * The ElevenLabs API key is read ONLY from the environment variable ELEVENLABS_API_KEY
    or from a local .env file that you create yourself. It is never accepted on the
    command line (that would leak it into shell history and process lists).
  * The key is never printed, logged, or written into any output file.
    Every message that could contain it goes through redact().
  * Requests go ONLY to https://api.elevenlabs.io. Redirects are refused, so the key
    can never be sent to any other host.
"""
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_HOST = "api.elevenlabs.io"
API_BASE = "https://" + API_HOST

# Things that look like an ElevenLabs key. Used to scrub messages and to scan files before publishing.
KEY_LIKE = [
    re.compile(r"sk_[0-9a-fA-F]{20,}"),
    re.compile(r"xi-api-key['\"]?\s*[:=]\s*['\"]?[0-9A-Za-z_\-]{16,}", re.I),
]

_loaded_key = None  # remembered only in memory, only so redact() can scrub it


class SyllaBeatError(Exception):
    """A problem the user can fix. The message is always safe to print."""


# --------------------------------------------------------------------------- key handling
def _read_env_file(path):
    """Return ELEVENLABS_API_KEY from a simple KEY=VALUE file, or None."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        m = re.match(r"\s*ELEVENLABS_API_KEY\s*=\s*['\"]?([^'\"\s#]+)['\"]?\s*(#.*)?$", line)
        if m and m.group(1) and not m.group(1).lower().startswith(("paste", "your", "<")):
            return m.group(1)
    return None


def load_api_key():
    """Find the user's own key. Order: environment variable, SYLLABEAT_ENV file, ./.env"""
    global _loaded_key
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key and os.environ.get("SYLLABEAT_ENV"):
        key = _read_env_file(os.environ["SYLLABEAT_ENV"])
    if not key:
        key = _read_env_file(Path.cwd() / ".env")
    if key:
        _loaded_key = key.strip()
    return _loaded_key


def require_api_key():
    key = load_api_key()
    if not key:
        raise SyllaBeatError(
            "No ElevenLabs API key found.\n"
            "  You need your OWN ElevenLabs account and key (SyllaBeat does not include one).\n"
            "  Put it in a file named .env in the folder you run the commands from:\n"
            "      ELEVENLABS_API_KEY=your-own-key\n"
            "  or set the ELEVENLABS_API_KEY environment variable.\n"
            "  Never paste the key into a chat or a command line."
        )
    return key


def mask(key):
    return "(not set)" if not key else key[:3] + "…" + key[-4:]


def redact(text):
    """Remove anything that looks like (or is) the user's key from a message."""
    text = str(text)
    if _loaded_key:
        text = text.replace(_loaded_key, "[KEY REMOVED]")
    for pat in KEY_LIKE:
        text = pat.sub("[KEY REMOVED]", text)
    return text


def reject_key_arguments(argv=None):
    """Refuse any command-line option that tries to pass a key."""
    for a in (argv if argv is not None else sys.argv[1:]):
        if re.match(r"--?(api[-_]?key|key|xi-api-key|token)\b", a, re.I) or KEY_LIKE[0].search(a):
            raise SyllaBeatError(
                "For your safety SyllaBeat never accepts an API key on the command line.\n"
                "Use a .env file or the ELEVENLABS_API_KEY environment variable instead."
            )


def mock_mode():
    """SYLLABEAT_MOCK=1 builds everything with silent placeholder audio and NO network access."""
    return os.environ.get("SYLLABEAT_MOCK") == "1"


# --------------------------------------------------------------------------- safe HTTP
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # never follow a redirect: the key must only ever go to API_HOST


_opener = urllib.request.build_opener(_NoRedirect)


def api(method, path, body=None, timeout=120, retries=3):
    """Call the ElevenLabs API and return the parsed JSON. Only api.elevenlabs.io over HTTPS."""
    key = require_api_key()
    if not path.startswith("/"):
        raise SyllaBeatError("internal error: API path must start with '/'")
    url = API_BASE + path
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != API_HOST:
        raise SyllaBeatError("Refusing to send your key anywhere except " + API_HOST)
    data = None
    headers = {"xi-api-key": key, "Accept": "application/json", "User-Agent": "SyllaBeat/1.0"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with _opener.open(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8", "replace")[:400]
            except Exception:
                pass
            last = "ElevenLabs answered HTTP %s %s" % (e.code, redact(detail))
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            if e.code == 401:
                why = ""
                try:
                    d = json.loads(detail).get("detail", {})
                    why = d.get("message") if isinstance(d, dict) else str(d)
                except Exception:
                    pass
                last = ("ElevenLabs answered 401 (not allowed)%s\n"
                        "  Either the key is wrong or no longer active, OR it is a restricted key that lacks the permission this\n"
                        "  step needs (listing voices needs 'voices_read'; making audio needs 'text_to_speech').\n"
                        "  You can edit a key's permissions on the ElevenLabs website, or skip listing and give the voice ID directly."
                        % ((": " + redact(why)) if why else "."))
            raise SyllaBeatError(last)
        except urllib.error.URLError as e:
            last = "Could not reach ElevenLabs: " + redact(e.reason)
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise SyllaBeatError(last)
    raise SyllaBeatError(last or "request failed")


# --------------------------------------------------------------------------- project files
def load_json(path, default=None):
    p = Path(path)
    if not p.exists():
        if default is not None:
            return default
        raise SyllaBeatError("Missing file: %s" % p)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SyllaBeatError("%s is not valid JSON: %s" % (p, e))


def save_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def project(project_dir):
    """Resolve the files that belong to one project folder."""
    d = Path(project_dir)
    if not d.is_dir():
        raise SyllaBeatError("Project folder not found: %s" % d)
    return {
        "dir": d,
        "text": d / "text.txt",
        "words": d / "words.json",
        "config": d / "config.json",
        "build": d / "build",
        "site": d / "site",
    }


def read_text(project_paths):
    t = project_paths["text"]
    if not t.exists():
        raise SyllaBeatError("Missing %s - put the text to read aloud in it." % t)
    text = t.read_text(encoding="utf-8").replace("\r\n", "\n").strip()
    if not text:
        raise SyllaBeatError("%s is empty." % t)
    return text


# --------------------------------------------------------------------------- text helpers
def paragraphs_of(text, max_chars=2500):
    """Split the text into paragraphs (blank-line separated); long ones are split at sentence ends."""
    out = []
    for block in re.split(r"\n\s*\n", text):
        block = " ".join(block.split())
        if not block:
            continue
        while len(block) > max_chars:
            cut = max(block.rfind(". ", 0, max_chars), block.rfind("? ", 0, max_chars), block.rfind("! ", 0, max_chars))
            if cut < 200:
                cut = block.rfind(" ", 0, max_chars)
            out.append(block[: cut + 1].strip())
            block = block[cut + 1:].strip()
        out.append(block)
    return out


def tokens_of(paragraph):
    """Whitespace tokens with their character offsets - the page uses exactly the same rule."""
    return [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"\S+", paragraph)]


def word_key(token):
    """'Morning,' -> 'morning'. The page uses the same rule, so keys always match."""
    return re.sub(r"[^a-z]", "", token.lower())


def unique_words(text):
    seen, order = set(), []
    for p in paragraphs_of(text):
        for _, _, tok in tokens_of(p):
            k = word_key(tok)
            if k and k not in seen:
                seen.add(k)
                order.append(k)
    return order


def fail(err):
    """Print a safe error and exit with status 1."""
    print("\nERROR: " + redact(err), file=sys.stderr)
    sys.exit(1)
