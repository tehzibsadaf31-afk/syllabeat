"""Tests for SyllaBeat. Run from the SyllaBeat folder:   python -m unittest discover -s tests -v
Everything runs offline (SYLLABEAT_MOCK=1) - no ElevenLabs key or network is used. Standard library only."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
import common  # noqa: E402
import check_secrets  # noqa: E402
import check_words  # noqa: E402
import generate_audio as ga  # noqa: E402

FAKE_KEY = "sk_" + "a1b2c3d4" * 6  # looks like a key, is not one


def run(script, *args, env_extra=None, cwd=None):
    env = dict(os.environ, SYLLABEAT_MOCK="1", PYTHONIOENCODING="utf-8")
    env.pop("ELEVENLABS_API_KEY", None)
    env.update(env_extra or {})
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, text=True,
                          encoding="utf-8", env=env, cwd=cwd)


class KeySafety(unittest.TestCase):
    def test_redact_removes_key_like_text(self):
        header = "xi-api-" + "key: " + "abcdefghijklmnop" + "1234"   # built in pieces so this file itself never looks like a key
        msg = "boom with %s and %s" % (FAKE_KEY, header)
        out = common.redact(msg)
        self.assertNotIn(FAKE_KEY, out)
        self.assertNotIn("abcdefghijklmnop" + "1234", out)

    def test_redact_removes_loaded_key(self):
        common._loaded_key = "plain-looking-secret-value-123"
        try:
            self.assertNotIn("plain-looking-secret-value-123", common.redact("x plain-looking-secret-value-123 y"))
        finally:
            common._loaded_key = None

    def test_command_line_keys_are_refused(self):
        for bad in (["--api-key", "x"], ["--api_key=abc"], ["-key", "abc"], ["--token", "t"], ["whatever", FAKE_KEY]):
            with self.assertRaises(common.SyllaBeatError):
                common.reject_key_arguments(bad)
        common.reject_key_arguments(["projects/demo", "--dry-run"])  # normal options are fine

    def test_scripts_refuse_key_on_command_line(self):
        r = run("list_voices.py", "--api-key", "sk_whatever")
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("sk_whatever", r.stdout + r.stderr)

    def test_requests_never_follow_redirects(self):
        self.assertIsNone(common._NoRedirect().redirect_request(None, None, 302, "", {}, "https://evil.example/"))

    def test_only_elevenlabs_host(self):
        self.assertEqual(common.API_HOST, "api.elevenlabs.io")
        self.assertTrue(common.API_BASE.startswith("https://"))

    def test_missing_key_message_is_helpful_and_safe(self):
        with tempfile.TemporaryDirectory() as d:
            env = dict(os.environ)
            env.pop("ELEVENLABS_API_KEY", None)
            env.pop("SYLLABEAT_MOCK", None)
            r = subprocess.run([sys.executable, str(SCRIPTS / "list_voices.py")], capture_output=True, text=True,
                               encoding="utf-8", env=env, cwd=d)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("OWN", r.stderr)

    def test_env_file_is_read_but_placeholder_is_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / ".env"
            f.write_text("ELEVENLABS_API_KEY=paste-your-own-key-here\n", encoding="utf-8")
            self.assertIsNone(common._read_env_file(f))
            f.write_text('ELEVENLABS_API_KEY="realvalue123456"\n', encoding="utf-8")
            self.assertEqual(common._read_env_file(f), "realvalue123456")


class SecretScan(unittest.TestCase):
    def test_finds_key_and_env_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "ok.html").write_text("<p>hello</p>", encoding="utf-8")
            self.assertEqual(check_secrets.scan(root), [])
            (root / "bad.js").write_text("const k='%s';" % FAKE_KEY, encoding="utf-8")
            (root / ".env").write_text("ELEVENLABS_API_KEY=whatever", encoding="utf-8")
            (root / ".env.example").write_text("ELEVENLABS_API_KEY=paste-your-own-key-here", encoding="utf-8")
            found = {str(r): why for r, why in check_secrets.scan(root)}
            self.assertIn("bad.js", found)
            self.assertIn(".env", found)
            self.assertNotIn(".env.example", found)

    def test_never_prints_the_secret(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "bad.txt").write_text(FAKE_KEY, encoding="utf-8")
            r = run("check_secrets.py", d)
            self.assertEqual(r.returncode, 1)
            self.assertNotIn(FAKE_KEY, r.stdout + r.stderr)


class WordChecks(unittest.TestCase):
    def good(self, **kw):
        w = {"syl": "EV-ery", "bn": "এভ-রি", "meaning": "প্রতিটি", "emoji": "🔁"}
        w.update(kw)
        return w

    def test_good_entry(self):
        errs, _ = check_words.check_entry("every", self.good(), ".", True)
        self.assertEqual(errs, [])

    def test_syllables_must_spell_the_word(self):
        errs, _ = check_words.check_entry("every", self.good(syl="EV-ry"), ".", True)
        self.assertTrue(any("spell" in e for e in errs))

    def test_bangla_pieces_must_match(self):
        errs, _ = check_words.check_entry("every", self.good(bn="এভরি"), ".", True)
        self.assertTrue(any("do not match" in e for e in errs))

    def test_exactly_one_stress(self):
        errs, _ = check_words.check_entry("every", self.good(syl="ev-ery"), ".", True)
        self.assertTrue(any("stressed" in e for e in errs))

    def test_picture_required_by_default(self):
        errs, _ = check_words.check_entry("every", self.good(emoji=""), ".", True)
        self.assertTrue(any("picture" in e for e in errs))
        errs, _ = check_words.check_entry("every", self.good(emoji=""), ".", False)
        self.assertEqual(errs, [])


class Timing(unittest.TestCase):
    def test_syllable_windows_are_contiguous_and_ordered(self):
        text = "muddy."
        starts = [0.10, 0.20, 0.30, 0.50, 0.60, 0.70]
        ends = [0.20, 0.30, 0.50, 0.60, 0.70, 0.75]
        al = {"character_start_times_seconds": starts, "character_end_times_seconds": ends, "characters": list(text)}
        wins = ga.syllable_timings("muddy", ["mud", "dy"], al, text)
        self.assertEqual(len(wins), 2)
        self.assertEqual(wins[0][0], 0.10)
        self.assertEqual(wins[0][1], wins[1][0])          # no gap between syllables
        self.assertEqual(wins[0][1], 0.50)                # 'd' of "dy" starts at 0.50
        self.assertGreater(wins[1][1], wins[1][0])

    def test_token_timings(self):
        para = "Hi there."
        n = len(para)
        al = {"character_start_times_seconds": [i * 0.1 for i in range(n)],
              "character_end_times_seconds": [(i + 1) * 0.1 for i in range(n)], "characters": list(para)}
        t = ga.token_timings(para, al)
        self.assertEqual(len(t), 2)
        self.assertAlmostEqual(t[0][0], 0.0)
        self.assertAlmostEqual(t[1][0], 0.3)


class Pipeline(unittest.TestCase):
    """Run the real scripts end to end in mock mode on a copy of the example project."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.proj = Path(cls.tmp) / "demo"
        shutil.copytree(ROOT / "examples" / "little-kite", cls.proj)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_full_pipeline(self):
        r = run("check_words.py", str(self.proj))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = run("generate_audio.py", str(self.proj), "--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Nothing sent", r.stdout)
        r = run("generate_audio.py", str(self.proj))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = run("build_site.py", str(self.proj))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        site = self.proj / "site"
        self.assertTrue((site / "index.html").exists())
        js = (site / "data" / "syllabeat-data.js").read_text(encoding="utf-8")
        data = json.loads(js[len("window.SYLLABEAT = "):].rstrip().rstrip(";"))
        self.assertEqual(len(data["paragraphs"]), 2)
        self.assertEqual(len(data["words"]), 18)
        w = data["words"]["along"]
        self.assertEqual(w["syl"], ["a", "long"])
        self.assertEqual(w["stress"], 1)
        self.assertEqual(len(w["slow"]["syllables"]), 2)
        self.assertNotIn("voice", js.lower().replace("voice-", ""))   # the voice ID is never shipped
        self.assertEqual(check_secrets.scan(site), [])

    def test_build_refuses_to_publish_a_key(self):
        proj = Path(self.tmp) / "leaky"
        shutil.copytree(ROOT / "examples" / "little-kite", proj)
        run("generate_audio.py", str(proj))
        # a meaning that contains something key-like must make the build delete the site
        words = json.loads((proj / "words.json").read_text(encoding="utf-8"))
        words["words"]["red"]["meaning"] = "লাল " + FAKE_KEY
        (proj / "words.json").write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
        r = run("build_site.py", str(proj))
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((proj / "site").exists())
        self.assertNotIn(FAKE_KEY, r.stdout + r.stderr)


class CleanExport(unittest.TestCase):
    def test_export_leaves_out_private_things_and_is_clean(self):
        with tempfile.TemporaryDirectory() as d:
            dst = Path(d) / "out"
            r = run("export_clean_copy.py", str(dst))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            names = {p.name for p in dst.rglob("*") if p.is_file()}
            self.assertIn("SKILL.md", names)
            self.assertIn(".env.example", names)
            self.assertNotIn(".env", names)
            self.assertFalse((dst / "projects").exists())
            self.assertFalse((dst / "sample").exists())
            self.assertEqual(check_secrets.scan(dst), [])

    def test_export_refuses_a_destination_inside_the_repo(self):
        r = run("export_clean_copy.py", str(ROOT / "oops"))
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
