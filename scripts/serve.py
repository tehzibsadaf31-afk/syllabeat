#!/usr/bin/env python3
"""Preview a finished site on your own computer.

    python scripts/serve.py <site-folder> [--port 8080]

Then open http://localhost:8080/ . It supports audio pause/resume (HTTP Range) and never serves
hidden files such as .env. Only listens on your own machine (127.0.0.1). Standard library only.
"""
import argparse
import os
import re
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class Handler(SimpleHTTPRequestHandler):
    extensions_map = dict(SimpleHTTPRequestHandler.extensions_map, **{".js": "text/javascript", ".mp3": "audio/mpeg", ".wav": "audio/wav"})

    def log_message(self, fmt, *a):  # quiet
        pass

    def _blocked(self):
        parts = [p for p in self.path.split("?")[0].split("/") if p]
        return any(p.startswith(".") for p in parts)

    def do_GET(self):
        if self._blocked():
            self.send_error(404)
            return
        rng = self.headers.get("Range")
        path = self.translate_path(self.path)
        if rng and os.path.isfile(path):
            m = re.match(r"bytes=(\d*)-(\d*)$", rng)
            if m:
                size = os.path.getsize(path)
                start = int(m.group(1)) if m.group(1) else max(0, size - int(m.group(2)))
                end = min(int(m.group(2)), size - 1) if (m.group(1) and m.group(2)) else size - 1
                if start > end or start >= size:
                    self.send_error(416)
                    return
                self.send_response(206)
                self.send_header("Content-Type", self.guess_type(path))
                self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
                self.send_header("Content-Length", str(end - start + 1))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                with open(path, "rb") as f:
                    f.seek(start)
                    self.wfile.write(f.read(end - start + 1))
                return
        super().do_GET()

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--port", type=int, default=8080)
    a = ap.parse_args()
    folder = Path(a.folder)
    if not (folder / "index.html").exists():
        print("No index.html in %s - run build_site.py first." % folder, file=sys.stderr)
        sys.exit(1)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), partial(Handler, directory=str(folder)))
    print("Serving %s at http://localhost:%d/   (Ctrl+C to stop)" % (folder, a.port))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
