#!/usr/bin/env python3
"""Step 5 - build the finished page (a plain folder of HTML, CSS, JavaScript and audio).

    python scripts/build_site.py <project-folder>

Output: <project>/site/   - open index.html, or run  python scripts/serve.py <project>/site
That folder can be put on any web host (GitHub Pages, Netlify, a school server...).

Safety: the site never contains your API key or your voice ID. Before finishing, the builder scans the
whole folder for anything that looks like a key and DELETES the site if it finds one.
Standard library only.
"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common  # noqa: E402
import check_secrets  # noqa: E402

TEMPLATE = HERE.parent / "templates" / "reader"


def build_data(p, text, words, cfg, manifest):
    paras = common.paragraphs_of(text)
    keys = common.unique_words(text)
    if len(manifest.get("paragraphs", [])) != len(paras) or not all(manifest["paragraphs"]):
        raise common.SyllaBeatError("Narration audio is incomplete. Run generate_audio.py first.")
    out_words, images = {}, []
    for k in keys:
        w = words.get(k)
        m = manifest.get("words", {}).get(k)
        if not w or not m:
            raise common.SyllaBeatError("Word '%s' has no audio yet. Run generate_audio.py." % k)
        parts = w["syl"].split("-")
        stress = next((i for i, s in enumerate(parts) if any(c.isupper() for c in s)), -1) if len(parts) > 1 else -1
        entry = {
            "syl": [s.lower() for s in parts],
            "stress": stress,
            "bn": w["bn"].split("-"),
            "meaning": w["meaning"],
            "emoji": w.get("emoji") or "",
            "normal": m["normal"]["file"],
            "slow": {"file": m["slow"]["file"], "syllables": m["slow"]["syllables"]},
        }
        if w.get("image"):
            entry["image"] = "images/" + w["image"]
            images.append(w["image"])
        out_words[k] = entry
    data = {
        "title": cfg.get("title") or "My story",
        "subtitle": cfg.get("subtitle") or "",
        "paragraphs": [{"text": paras[i], "audio": manifest["paragraphs"][i]["file"],
                        "tokens": manifest["paragraphs"][i]["tokens"]} for i in range(len(paras))],
        "slowPlaybackRate": manifest.get("slow_playback_rate", 0.85),
        "words": out_words,
    }
    return data, images


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    try:
        common.reject_key_arguments()
        p = common.project(sys.argv[1])
        text = common.read_text(p)
        words = common.load_json(p["words"]).get("words", {})
        cfg = common.load_json(p["config"], default={})
        manifest = common.load_json(p["build"] / "manifest.json")
        data, images = build_data(p, text, words, cfg, manifest)

        site = p["site"]
        if site.name != "site" or site.parent != p["dir"]:
            raise common.SyllaBeatError("internal error: unexpected site folder")
        if site.exists():
            shutil.rmtree(site)
        shutil.copytree(TEMPLATE, site)
        shutil.copytree(p["build"] / "audio", site / "audio")
        if images:
            (site / "images").mkdir(exist_ok=True)
            for img in set(images):
                shutil.copy2(p["dir"] / "images" / img, site / "images" / img)
        (site / "data").mkdir(exist_ok=True)
        js = "window.SYLLABEAT = " + json.dumps(data, ensure_ascii=False) + ";\n"
        (site / "data" / "syllabeat-data.js").write_text(js, encoding="utf-8")
        (site / ".nojekyll").write_text("", encoding="utf-8")

        problems = check_secrets.scan(site)
        if problems:
            shutil.rmtree(site)
            lines = "\n".join("  %s -> %s" % (r, w) for r, w in problems)
            raise common.SyllaBeatError("The site was NOT created because it looked like it contained a secret:\n" + lines)
    except common.SyllaBeatError as e:
        common.fail(e)

    n_audio = sum(1 for _ in (site / "audio").rglob("*") if _.is_file())
    print("Built %s" % site)
    print("  %d paragraph(s), %d word cards, %d audio files. Security scan: no keys found." % (len(data["paragraphs"]), len(data["words"]), n_audio))
    print("Preview:  python scripts/serve.py %s     then open http://localhost:8080/" % site)


if __name__ == "__main__":
    main()
